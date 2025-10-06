"""
File upload API endpoint
"""

import hashlib
import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.schemas.upload import UploadResponse, UploadError, ChunkingMethod
from app.models.database import Document, Ingestion, Chunk
from app.services.file_processor import FileProcessor
from app.services.scanned_pdf_detector import ScannedPDFDetector
from app.services.qdrant import QdrantService

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    chunk_method: int = Form(...),
    doc_title: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload a document for ingestion
    
    - **file**: Document file (PDF, DOCX, TXT, MD)
    - **chunk_method**: Chunking method (1-8)
    - **doc_title**: Document title
    """
    
    # Validate chunking method
    if chunk_method not in [method.value for method in ChunkingMethod]:
        valid_methods = [f"{method.value} ({method.name})" for method in ChunkingMethod]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid chunking method. Valid methods: {', '.join(valid_methods)}"
        )
    
    # Validate file size
    max_size_bytes = settings.max_upload_mb * 1024 * 1024
    file_content = await file.read()
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_mb}MB."
        )
    
    # Validate file type
    allowed_types = {
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'text/plain': '.txt',
        'text/markdown': '.md'
    }
    
    # Also check file extension for .md files since browsers might report them as text/plain
    file_extension = os.path.splitext(file.filename or '')[-1].lower()
    if file_extension == '.md' and file.content_type == 'text/plain':
        # Override MIME type for .md files that are reported as text/plain
        file.content_type = 'text/markdown'
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: PDF, DOCX, TXT, MD"
        )
    
    # Sanitize file name and title
    import re
    safe_filename = re.sub(r'[^\w\-_\.]', '_', file.filename or 'unknown')
    safe_title = re.sub(r'[<>:"/\\|?*]', '', doc_title.strip())[:255]
    
    # Calculate file hash
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Check if document already exists
    existing_doc = db.query(Document).filter(Document.sha256 == file_hash).first()
    if existing_doc:
        raise HTTPException(
            status_code=409,
            detail="Document with this content already exists"
        )
    
    # Check for scanned PDF
    if file.content_type == 'application/pdf':
        detector = ScannedPDFDetector()
        if detector.is_scanned_pdf(file_content):
            # Create blocked ingestion record
            doc = Document(
                title=doc_title,
                mime=file.content_type,
                bytes=len(file_content),
                sha256=file_hash
            )
            db.add(doc)
            db.flush()
            
            ingestion = Ingestion(
                doc_id=doc.id,
                method=chunk_method,
                status="blocked_scanned_pdf"
            )
            db.add(ingestion)
            db.commit()
            
            return UploadResponse(
                ingestion_id=ingestion.id,
                status="blocked_scanned_pdf",
                message="Document blocked: scanned PDF detected"
            )
    
    # Store original file
    os.makedirs(settings.storage_path, exist_ok=True)
    file_path = os.path.join(settings.storage_path, f"{file_hash}.{allowed_types[file.content_type][1:]}")
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Create document record
    doc = Document(
        title=safe_title,
        mime=file.content_type,
        bytes=len(file_content),
        sha256=file_hash
    )
    db.add(doc)
    db.flush()
    
    # Create ingestion record
    ingestion = Ingestion(
        doc_id=doc.id,
        method=chunk_method,
        status="queued"
    )
    db.add(ingestion)
    db.commit()
    
    # Return immediately - process asynchronously
    return UploadResponse(
        ingestion_id=ingestion.id,
        status="queued",
        message="Document uploaded successfully. Processing will begin shortly."
    )

@router.get("/chunking-methods")
async def get_chunking_methods():
    """
    Get list of available chunking methods with descriptions
    """
    methods = []
    for method in ChunkingMethod:
        methods.append({
            "id": method.value,
            "name": method.name,
            "description": method.get_description()
        })
    
    return {
        "chunking_methods": methods,
        "total": len(methods)
    }

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a document and all related data from both PostgreSQL and Qdrant
    
    - **doc_id**: Document ID to delete
    """
    try:
        import logging
        import os
        logger = logging.getLogger(__name__)
        
        # Check if document exists
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        
        # Get all chunks and ingestions for this document
        chunks = db.query(Chunk).filter(Chunk.doc_id == doc_id).all()
        ingestions = db.query(Ingestion).filter(Ingestion.doc_id == doc_id).all()
        
        logger.info(f"Deleting document {doc_id}: {len(chunks)} chunks, {len(ingestions)} ingestions")
        
        # Delete from Qdrant using doc_id (with fallback support)
        qdrant_vectors_deleted = 0
        try:
            qdrant_service = QdrantService()
            if qdrant_service.is_available() and chunks:
                # Delete vectors for all methods used by this document
                methods = list(set([ingestion.method for ingestion in ingestions]))
                for method in methods:
                    qdrant_service.delete_vectors_by_doc_id(doc_id, method)
                    qdrant_vectors_deleted += len(chunks)  # Approximate count
                logger.info(f"Deleted vectors from Qdrant for document {doc_id}")
            else:
                logger.warning("Qdrant service not available or no chunks to delete")
        except Exception as e:
            logger.warning(f"Failed to delete vectors from Qdrant: {e}")
        
        # Note: PostgreSQL FTS indexes are automatically maintained when chunks are deleted
        # No manual FTS cleanup needed for PostgreSQL
        
        # Delete chunks from database (due to foreign key constraints)
        chunks_deleted = db.query(Chunk).filter(Chunk.doc_id == doc_id).delete()
        
        # Delete ingestions
        ingestions_deleted = db.query(Ingestion).filter(Ingestion.doc_id == doc_id).delete()
        
        # Delete the physical file from storage
        file_deleted = False
        try:
            file_extension = _get_file_extension(document.mime)
            file_path = os.path.join(settings.storage_path, f"{document.sha256}.{file_extension}")
            logger.info(f"Attempting to delete file: {file_path}")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                file_deleted = True
                logger.info(f"Successfully deleted physical file: {file_path}")
            else:
                logger.warning(f"Physical file not found: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete physical file {file_path}: {e}")
        
        # Store document info before deletion
        doc_info = {
            "id": document.id,
            "title": document.title,
            "mime": document.mime,
            "sha256": document.sha256
        }
        
        # Delete document
        db.delete(document)
        
        db.commit()
        
        logger.info(f"Successfully deleted document {doc_id}")
        
        return {
            "message": f"Document {doc_id} deleted successfully",
            "deleted_document": doc_info,
            "cleanup": {
                "postgresql_chunks_deleted": chunks_deleted,
                "postgresql_ingestions_deleted": ingestions_deleted,
                "qdrant_vectors_deleted": qdrant_vectors_deleted,
                "physical_file_deleted": file_deleted
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete document {doc_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )

@router.post("/qdrant/create-indexes")
async def create_qdrant_indexes():
    """
    Create missing indexes on existing Qdrant collection
    This fixes the issue where existing collections don't have indexes
    """
    try:
        qdrant_service = QdrantService()
        if not qdrant_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Qdrant service is not available"
            )
        
        success = qdrant_service.create_missing_indexes()
        
        if success:
            return {
                "message": "Qdrant indexes created successfully",
                "status": "success"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to create Qdrant indexes"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create indexes: {str(e)}"
        )

def _get_file_extension(mime_type: str) -> str:
    """Get file extension from MIME type"""
    mime_to_ext = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'text/plain': 'txt',
        'text/markdown': 'md'
    }
    return mime_to_ext.get(mime_type, 'bin')