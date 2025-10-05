"""
Document ingestion pipeline service
"""

import os
import psutil
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database import Document, Ingestion, Chunk
from app.services.file_processor import FileProcessor
from app.services.chunking import ChunkingService
from app.services.embeddings import EmbeddingService
from app.services.qdrant import QdrantService
from app.services.lexical_index import LexicalIndexService
from app.core.config import settings

class IngestionService:
    """
    Orchestrates the complete document ingestion pipeline
    """
    
    def __init__(self):
        self.file_processor = FileProcessor()
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()
        self.lexical_index_service = LexicalIndexService()
    
    def process_document(self, ingestion_id: int, db: Session) -> bool:
        """
        Process a document through the complete ingestion pipeline
        
        Args:
            ingestion_id: ID of the ingestion record
            db: Database session
            
        Returns:
            True if successful
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Starting to process document for ingestion {ingestion_id}")
            
            # Get ingestion record
            ingestion = db.query(Ingestion).filter(Ingestion.id == ingestion_id).first()
            if not ingestion:
                logger.error(f"Ingestion {ingestion_id} not found in database")
                return False
            
            # Set started_at timestamp
            ingestion.started_at = datetime.utcnow()
            ingestion.status = "extracting"
            db.commit()
            
            # Get document
            document = db.query(Document).filter(Document.id == ingestion.doc_id).first()
            if not document:
                ingestion.status = "failed"
                ingestion.error = "Document not found"
                db.commit()
                return False
            
            # Load file content
            file_path = os.path.join(settings.storage_path, f"{document.sha256}.{self._get_file_extension(document.mime)}")
            if not os.path.exists(file_path):
                ingestion.status = "failed"
                ingestion.error = "File not found in storage"
                db.commit()
                return False
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Extract text with page information
            text_data = self.file_processor.extract_text_with_pages(file_content, document.mime)
            if not text_data or not text_data.get('text'):
                ingestion.status = "failed"
                ingestion.error = "Failed to extract text from document"
                db.commit()
                return False
            
            text = text_data['text']
            pages = text_data.get('pages', [])
            
            # Update status to chunking
            ingestion.status = "chunking"
            db.commit()
            
            # Chunk text with page information
            chunks_data = self.chunking_service.chunk_text_with_pages(text, ingestion.method, pages)
            
            # Store chunks in database
            stored_chunks = []
            for chunk_data in chunks_data:
                chunk = Chunk(
                    doc_id=document.id,
                    method=ingestion.method,
                    page_from=chunk_data.get('page_from'),
                    page_to=chunk_data.get('page_to'),
                    hash=chunk_data['hash'],
                    text=chunk_data['text']
                )
                db.add(chunk)
                stored_chunks.append(chunk)
            
            db.commit()
            
            # Update status to embedding
            ingestion.status = "embedding"
            db.commit()
            
            # Generate embeddings
            chunk_texts = [chunk_data['text'] for chunk_data in chunks_data]
            
            # Check memory before embedding generation
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss / 1024 / 1024
            logger.info(f"Memory before embedding generation: {memory_before:.1f}MB")
            
            embeddings = self.embedding_service.generate_embeddings(chunk_texts)
            
            # Check memory after embedding generation
            memory_after = process.memory_info().rss / 1024 / 1024
            memory_increase = memory_after - memory_before
            logger.info(f"Memory after embedding generation: {memory_after:.1f}MB (increase: {memory_increase:.1f}MB)")
            
            # Prepare payloads for Qdrant using actual chunk IDs
            payloads = []
            for i, (chunk_data, stored_chunk) in enumerate(zip(chunks_data, stored_chunks)):
                payload = {
                    'doc_id': document.id,
                    'chunk_id': stored_chunk.id,  # Use actual database chunk ID
                    'method': ingestion.method,
                    'page_from': chunk_data.get('page_from'),
                    'page_to': chunk_data.get('page_to'),
                    'hash': chunk_data['hash'],
                    'source': document.title
                }
                payloads.append(payload)
            
            # Store in Qdrant
            self.qdrant_service.store_vectors(embeddings, payloads)
            
            # Force aggressive garbage collection after embedding generation
            import gc
            for _ in range(3):  # Multiple aggressive passes
                gc.collect()
            
            # Clear any large variables to free memory immediately
            del chunk_texts
            del payloads
            del chunks_data
            del stored_chunks
            
            # Update status to indexing
            ingestion.status = "indexing"
            db.commit()
            
            # Create lexical index for full-text search
            self.lexical_index_service.create_fts_index(db)
            
            # Update search vectors for the new chunks
            for chunk_data in chunks_data:
                # Get the actual chunk ID from database
                chunk = db.query(Chunk).filter(
                    Chunk.doc_id == document.id,
                    Chunk.hash == chunk_data['hash']
                ).first()
                if chunk:
                    self.lexical_index_service.add_chunk_to_index(
                        chunk.id, chunk_data['text'], db
                    )
            
            # Update status to done and set finished_at timestamp
            ingestion.status = "done"
            ingestion.finished_at = datetime.utcnow()
            db.commit()
            
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing document for ingestion {ingestion_id}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            # Update status to failed and set finished_at timestamp
            ingestion.status = "failed"
            ingestion.error = str(e)
            ingestion.finished_at = datetime.utcnow()
            db.commit()
            return False
    
    def _get_file_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type"""
        mime_to_ext = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'text/plain': 'txt',
            'text/markdown': 'md'
        }
        return mime_to_ext.get(mime_type, 'bin')
