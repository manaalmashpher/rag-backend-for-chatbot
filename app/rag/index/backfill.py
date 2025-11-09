"""
Backfill script for re-chunking and re-indexing documents with clause-aware chunking

Supports safe batch processing with resume capability and memory management
for Railway deployment.
"""

import os
import sys
import argparse
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.core.database import get_db
from app.models.database import Document, Chunk, Ingestion
from app.services.file_processor import FileProcessor
from app.services.embeddings import EmbeddingService
from app.services.qdrant import QdrantService
from app.rag.ingest.clause_chunker import ClauseChunker
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackfillService:
    """
    Service for re-chunking and re-indexing documents with clause-aware chunking
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        batch_size: Optional[int] = None,
        dry_run: bool = False
    ):
        """
        Initialize backfill service
        
        Args:
            model_name: Embedding model name (default: from settings)
            batch_size: Batch size for embedding generation (default: from settings)
            dry_run: If True, don't write to database/Qdrant
        """
        self.model_name = model_name or settings.embedding_model
        self.batch_size = batch_size or settings.rag_backfill_batch_size
        self.dry_run = dry_run
        
        self.file_processor = FileProcessor()
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()
        
        logger.info(f"Initialized BackfillService: model={self.model_name}, batch_size={self.batch_size}, dry_run={dry_run}")
    
    def process_documents(
        self,
        doc_selector: str = "all",
        doc_id: Optional[int] = None,
        last_processed_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process documents for re-chunking and re-indexing
        
        Args:
            doc_selector: "all" or "doc_id=..." format
            doc_id: Specific document ID to process (overrides doc_selector)
            last_processed_id: Resume from this document ID
        
        Returns:
            Dictionary with processing statistics
        """
        db = next(get_db())
        
        try:
            # Determine which documents to process
            if doc_id:
                documents = db.query(Document).filter(Document.id == doc_id).all()
            elif doc_selector.startswith("doc_id="):
                doc_id_str = doc_selector.split("=")[1]
                try:
                    doc_id = int(doc_id_str)
                    documents = db.query(Document).filter(Document.id == doc_id).all()
                except ValueError:
                    logger.error(f"Invalid doc_id in selector: {doc_selector}")
                    return {"error": "Invalid doc_id"}
            elif doc_selector == "all":
                query = db.query(Document)
                if last_processed_id:
                    query = query.filter(Document.id > last_processed_id)
                documents = query.order_by(Document.id).all()
            else:
                logger.error(f"Invalid doc_selector: {doc_selector}")
                return {"error": "Invalid doc_selector"}
            
            logger.info(f"Found {len(documents)} documents to process")
            
            stats = {
                "total_documents": len(documents),
                "processed": 0,
                "failed": 0,
                "chunks_created": 0,
                "vectors_created": 0,
                "errors": []
            }
            
            for doc in documents:
                try:
                    result = self._process_document(doc, db)
                    if result["success"]:
                        stats["processed"] += 1
                        stats["chunks_created"] += result["chunks_created"]
                        stats["vectors_created"] += result["vectors_created"]
                        logger.info(f"Processed document {doc.id}: {result['chunks_created']} chunks")
                    else:
                        stats["failed"] += 1
                        stats["errors"].append({
                            "doc_id": doc.id,
                            "error": result.get("error", "Unknown error")
                        })
                        logger.error(f"Failed to process document {doc.id}: {result.get('error')}")
                except Exception as e:
                    stats["failed"] += 1
                    stats["errors"].append({
                        "doc_id": doc.id,
                        "error": str(e)
                    })
                    logger.error(f"Exception processing document {doc.id}: {e}", exc_info=True)
            
            return stats
            
        finally:
            db.close()
    
    def _process_document(self, document: Document, db: Session) -> Dict[str, Any]:
        """
        Process a single document: extract, chunk, embed, and index
        
        Args:
            document: Document to process
            db: Database session
        
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing document {document.id}: {document.title}")
            
            # Load file content
            file_path = os.path.join(
                settings.storage_path,
                f"{document.sha256}.{self._get_file_extension(document.mime)}"
            )
            
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Extract text with pages
            text_data = self.file_processor.extract_text_with_pages(file_content, document.mime)
            if not text_data or not text_data.get('text'):
                return {
                    "success": False,
                    "error": "Failed to extract text from document"
                }
            
            text = text_data['text']
            pages = text_data.get('pages', [])
            
            # Initialize clause chunker
            chunker = ClauseChunker(
                target_tokens=settings.rag_chunk_target_tokens,
                overlap_tokens=settings.rag_chunk_overlap_tokens,
                model_name=self.model_name
            )
            
            # Chunk document
            chunks = chunker.chunk_document(
                text,
                document.id,
                document.title,
                pages
            )
            
            logger.info(f"Generated {len(chunks)} chunks for document {document.id}")
            
            if self.dry_run:
                logger.info(f"DRY RUN: Would create {len(chunks)} chunks and vectors")
                return {
                    "success": True,
                    "chunks_created": len(chunks),
                    "vectors_created": len(chunks)
                }
            
            # Delete existing chunks for this document (method 9)
            existing_chunks = db.query(Chunk).filter(
                and_(Chunk.doc_id == document.id, Chunk.method == 9)
            ).all()
            
            if existing_chunks:
                logger.info(f"Deleting {len(existing_chunks)} existing chunks for document {document.id}, method 9")
                for chunk in existing_chunks:
                    db.delete(chunk)
                db.commit()
            
            # Store chunks in database
            stored_chunks = []
            for chunk_obj in chunks:
                chunk = Chunk(
                    doc_id=document.id,
                    method=9,  # Clause-aware method
                    page_from=chunk_obj.page_start,
                    page_to=chunk_obj.page_end,
                    hash=chunk_obj.hash,
                    text=chunk_obj.text,
                    section_id=chunk_obj.section_id,
                    section_id_alias=chunk_obj.section_id_alias,
                    title=chunk_obj.title,
                    parent_titles=chunk_obj.parent_titles,
                    level=chunk_obj.level,
                    list_items=chunk_obj.list_items,
                    has_supporting_docs=chunk_obj.has_supporting_docs,
                    token_count=chunk_obj.token_count,
                    text_norm=chunk_obj.text_norm
                )
                db.add(chunk)
                stored_chunks.append(chunk)
            
            db.commit()
            logger.info(f"Stored {len(stored_chunks)} chunks in database")
            
            # Generate embeddings in batches
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = []
            
            for i in range(0, len(chunk_texts), self.batch_size):
                batch_texts = chunk_texts[i:i + self.batch_size]
                batch_embeddings = self.embedding_service.generate_embeddings(batch_texts)
                embeddings.extend(batch_embeddings)
                
                logger.info(f"Generated embeddings for batch {i // self.batch_size + 1}/{(len(chunk_texts) + self.batch_size - 1) // self.batch_size}")
            
            # Prepare Qdrant payloads
            payloads = []
            for chunk_obj, stored_chunk in zip(chunks, stored_chunks):
                payload = chunk_obj.to_qdrant_payload()
                payload['chunk_id'] = stored_chunk.id
                payloads.append(payload)
            
            # Delete existing vectors in Qdrant for this document and method
            try:
                self.qdrant_service.delete_vectors_by_doc_id(document.id, 9)
                logger.info(f"Cleaned up existing vectors in Qdrant for document {document.id}, method 9")
            except Exception as e:
                logger.warning(f"Failed to clean up existing vectors: {e}")
            
            # Store vectors in Qdrant
            self.qdrant_service.store_vectors(embeddings, payloads)
            logger.info(f"Stored {len(embeddings)} vectors in Qdrant")
            
            return {
                "success": True,
                "chunks_created": len(chunks),
                "vectors_created": len(embeddings)
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document.id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_file_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type"""
        mime_to_ext = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'text/plain': 'txt',
            'text/markdown': 'md'
        }
        return mime_to_ext.get(mime_type, 'bin')


def main():
    """CLI entry point for backfill script"""
    parser = argparse.ArgumentParser(
        description="Re-chunk and re-index documents with clause-aware chunking"
    )
    parser.add_argument(
        '--doc-selector',
        type=str,
        default='all',
        help='Document selector: "all" or "doc_id=123"'
    )
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='Embedding model name (default: from settings)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=None,
        help='Batch size for embedding generation (default: from settings)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (don\'t write to database/Qdrant)'
    )
    parser.add_argument(
        '--resume-from',
        type=int,
        default=None,
        help='Resume from document ID (for resuming interrupted backfill)'
    )
    
    args = parser.parse_args()
    
    service = BackfillService(
        model_name=args.model,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made")
    
    result = service.process_documents(
        doc_selector=args.doc_selector,
        last_processed_id=args.resume_from
    )
    
    if "error" in result:
        logger.error(f"Backfill failed: {result['error']}")
        sys.exit(1)
    
    logger.info("Backfill completed:")
    logger.info(f"  Total documents: {result['total_documents']}")
    logger.info(f"  Processed: {result['processed']}")
    logger.info(f"  Failed: {result['failed']}")
    logger.info(f"  Chunks created: {result['chunks_created']}")
    logger.info(f"  Vectors created: {result['vectors_created']}")
    
    if result['errors']:
        logger.warning(f"Errors encountered: {len(result['errors'])}")
        for error in result['errors'][:10]:  # Show first 10 errors
            logger.warning(f"  Doc {error['doc_id']}: {error['error']}")


if __name__ == '__main__':
    main()

