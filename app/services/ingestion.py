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
            
            # Clean up any existing chunks for this document and method (in case of retry)
            existing_chunks = db.query(Chunk).filter(
                Chunk.doc_id == document.id,
                Chunk.method == ingestion.method
            ).all()
            
            if existing_chunks:
                logger.info(f"Cleaning up {len(existing_chunks)} existing chunks for document {document.id}, method {ingestion.method}")
                for chunk in existing_chunks:
                    db.delete(chunk)
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
            
            # Special handling for dense documents (like markdown files)
            is_dense_document = len(chunk_texts) > 11 or len(text) > 10000  # More than 25 chunks or 25k chars
            if is_dense_document:
                logger.warning(f"Processing dense document with {len(chunk_texts)} chunks, {len(text)} characters")
                # Force single-chunk processing for dense documents
                embeddings = self._process_dense_document_embeddings(chunk_texts, process, ingestion, db)
                if embeddings is None:  # Processing failed
                    return False
            # Check if we have too many chunks for current memory
            elif len(chunk_texts) > 15 and memory_before > 1000:
                logger.warning(f"Large document with {len(chunk_texts)} chunks and {memory_before:.1f}MB memory - processing in smaller batches")
                # Process in smaller batches to prevent OOM
                embeddings = []
                batch_size = 1  # Single chunk processing for memory-constrained environments
                for i in range(0, len(chunk_texts), batch_size):
                    batch_texts = chunk_texts[i:i + batch_size]
                    batch_embeddings = self.embedding_service.generate_embeddings(batch_texts)
                    embeddings.extend(batch_embeddings)
                    
                    # Check memory after each batch
                    memory_after_batch = process.memory_info().rss / 1024 / 1024
                    if memory_after_batch > 1170:
                        logger.error(f"Memory usage too high during processing: {memory_after_batch:.1f}MB")
                        ingestion.status = "failed"
                        ingestion.error = f"Memory usage too high during processing: {memory_after_batch:.1f}MB"
                        db.commit()
                        return False
                    
                    # Force garbage collection after each batch
                    import gc
                    gc.collect()
            else:
                # Normal processing for smaller documents
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
            
            # Clean up existing vectors in Qdrant for this document and method
            try:
                self.qdrant_service.delete_vectors_by_doc_id(document.id, ingestion.method)
                logger.info(f"Cleaned up existing vectors in Qdrant for document {document.id}, method {ingestion.method}")
            except Exception as e:
                # This is expected for the first document upload when no index exists yet
                if "Index required but not found" in str(e):
                    logger.info(f"No existing vectors to clean up for document {document.id} (first upload)")
                else:
                    logger.warning(f"Failed to clean up existing vectors in Qdrant: {e}")
            
            # Store in Qdrant
            self.qdrant_service.store_vectors(embeddings, payloads)
            
            # Force aggressive garbage collection after embedding generation
            import gc
            for _ in range(3):  # Multiple aggressive passes
                gc.collect()
            
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
            
            # Clear any large variables to free memory immediately (after lexical indexing)
            del chunk_texts
            del payloads
            del chunks_data
            del stored_chunks
            
            # Final aggressive cleanup after document processing
            import gc
            for _ in range(3):  # Multiple aggressive passes
                gc.collect()
            
            # Clear embedding cache to free memory
            self.embedding_service.clear_cache()
            logger.info("Performed final cleanup after document processing")
            
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
    
    def _process_dense_document_embeddings(self, chunk_texts: list, process, ingestion, db) -> list:
        """
        Process embeddings for dense documents with aggressive memory management
        """
        import gc
        import logging
        logger = logging.getLogger(__name__)
        
        embeddings = []
        total_chunks = len(chunk_texts)
        
        logger.info(f"Processing {total_chunks} chunks one by one for dense document")
        
        for i, chunk_text in enumerate(chunk_texts):
            try:
                # Process single chunk
                chunk_embeddings = self.embedding_service.generate_embeddings([chunk_text])
                embeddings.extend(chunk_embeddings)
                
                # Aggressive memory cleanup after each chunk
                del chunk_embeddings
                gc.collect()
                
                # Check memory after every chunk for dense documents
                memory_after = process.memory_info().rss / 1024 / 1024
                if (i + 1) % 3 == 0:  # Log every 3 chunks
                    logger.info(f"Processed {i + 1}/{total_chunks} chunks, memory: {memory_after:.1f}MB")
                
                if memory_after > 1000:  # Very conservative threshold for Railway
                    logger.error(f"Memory usage too high during dense document processing: {memory_after:.1f}MB")
                    ingestion.status = "failed"
                    ingestion.error = f"Memory usage too high during dense document processing: {memory_after:.1f}MB"
                    db.commit()
                    return None
                
                # Force garbage collection every 3 chunks for dense documents
                if (i + 1) % 3 == 0:
                    for _ in range(3):  # Multiple aggressive passes
                        gc.collect()
                    
                    # Clear embedding cache if memory is still high
                    if memory_after > 1000:
                        from app.services.embeddings import EmbeddingService
                        embedding_service = EmbeddingService()
                        embedding_service.clear_cache()
                        logger.info("Cleared embedding cache due to high memory usage")
                        
            except Exception as e:
                logger.error(f"Error processing chunk {i + 1}: {e}")
                ingestion.status = "failed"
                ingestion.error = f"Error processing chunk {i + 1}: {str(e)}"
                db.commit()
                return None
        
        logger.info(f"Successfully processed all {total_chunks} chunks for dense document")
        
        # Final aggressive cleanup after dense document processing
        import gc
        for _ in range(3):  # Multiple aggressive passes
            gc.collect()
        
        # Clear embedding cache to free memory
        from app.services.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        embedding_service.clear_cache()
        logger.info("Performed final cleanup after dense document processing")
        
        return embeddings

    def _get_file_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type"""
        mime_to_ext = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'text/plain': 'txt',
            'text/markdown': 'md'
        }
        return mime_to_ext.get(mime_type, 'bin')
