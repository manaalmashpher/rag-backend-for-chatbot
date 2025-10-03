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
    Delete a document and all related data from both SQLite and Qdrant
    
    - **doc_id**: Document ID to delete
    """
    try:
        # Check if document exists
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        
        # Get chunk hashes before deleting for Qdrant cleanup
        chunks = db.query(Chunk).filter(Chunk.doc_id == doc_id).all()
        chunk_hashes = [chunk.hash for chunk in chunks]
        
        # Delete from Qdrant using hash values
        if chunk_hashes:
            try:
                qdrant_service = QdrantService()
                # Find vectors by hash and delete them
                qdrant_service.delete_vectors_by_hash(chunk_hashes)
            except Exception as e:
                # Log Qdrant deletion error but don't fail the entire operation
                print(f"Warning: Failed to delete vectors from Qdrant: {e}")
        
        # Delete chunks from database (due to foreign key constraints)
        db.query(Chunk).filter(Chunk.doc_id == doc_id).delete()
        
        # Delete ingestions
        db.query(Ingestion).filter(Ingestion.doc_id == doc_id).delete()
        
        # Delete from FTS5 index
        from sqlalchemy import text
        db.execute(text("DELETE FROM chunks_fts WHERE rowid IN (SELECT id FROM chunks WHERE doc_id = :doc_id)"), 
                  {"doc_id": doc_id})
        
        # Delete document
        db.delete(document)
        
        db.commit()
        
        return {
            "message": f"Document {doc_id} deleted successfully",
            "deleted_document": {
                "id": doc_id,
                "title": document.title,
                "mime": document.mime
            },
            "cleanup": {
                "sqlite_chunks_deleted": len(chunk_hashes),
                "qdrant_vectors_deleted": len(chunk_hashes),
                "fts5_entries_deleted": len(chunk_hashes)
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )