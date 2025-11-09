"""
Document ingestion pipeline service
"""

import os
import psutil
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import InvalidRequestError
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
    
    def _safe_commit(self, db: Session, ingestion_id: Optional[int] = None) -> Optional[Ingestion]:
        """
        Safely commit database changes, handling prepared state errors.
        Returns refreshed ingestion object if ingestion_id is provided.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            db.commit()
            if ingestion_id:
                # Re-query to get fresh object
                return db.query(Ingestion).filter(Ingestion.id == ingestion_id).first()
            return None
        except InvalidRequestError as e:
            if "prepared" in str(e).lower():
                logger.warning(f"Session in prepared state, refreshing and retrying commit")
                try:
                    db.expire_all()
                    db.rollback()
                    db.commit()
                    if ingestion_id:
                        return db.query(Ingestion).filter(Ingestion.id == ingestion_id).first()
                    return None
                except Exception as retry_error:
                    logger.error(f"Failed to recover from prepared state: {retry_error}")
                    # Try one more time with fresh session
                    try:
                        db.expire_all()
                        if ingestion_id:
                            ingestion = db.query(Ingestion).filter(Ingestion.id == ingestion_id).first()
                            if ingestion:
                                db.commit()
                            return ingestion
                        db.commit()
                        return None
                    except Exception as final_error:
                        logger.error(f"Final recovery attempt failed: {final_error}")
                        raise
            else:
                raise
    
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
            ingestion = self._safe_commit(db, ingestion_id) or ingestion
            
            # Get document
            document = db.query(Document).filter(Document.id == ingestion.doc_id).first()
            if not document:
                ingestion.status = "failed"
                ingestion.error = "Document not found"
                self._safe_commit(db, ingestion_id)
                return False
            
            # Store document attributes before any session expires to prevent DetachedInstanceError
            doc_id = document.id
            doc_title = document.title
            
            # Store ingestion method before any session expires to prevent DetachedInstanceError
            ingestion_method = ingestion.method
            
            # Load file content
            file_path = os.path.join(settings.storage_path, f"{document.sha256}.{self._get_file_extension(document.mime)}")
            logger.info(f"Looking for file: {file_path}")
            logger.info(f"Storage path exists: {os.path.exists(settings.storage_path)}")
            
            if not os.path.exists(file_path):
                ingestion.status = "failed"
                ingestion.error = f"File not found in storage: {file_path}"
                self._safe_commit(db, ingestion_id)
                return False
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Extract text with page information
            text_data = self.file_processor.extract_text_with_pages(file_content, document.mime)
            if not text_data or not text_data.get('text'):
                ingestion.status = "failed"
                ingestion.error = "Failed to extract text from document"
                self._safe_commit(db, ingestion_id)
                return False
            
            text = text_data['text']
            pages = text_data.get('pages', [])
            
            # Update status to chunking
            ingestion.status = "chunking"
            ingestion = self._safe_commit(db, ingestion_id) or ingestion
            
            # Clean up any existing chunks for this document and method (in case of retry)
            existing_chunks = db.query(Chunk).filter(
                Chunk.doc_id == doc_id,
                Chunk.method == ingestion_method
            ).all()
            
            if existing_chunks:
                for chunk in existing_chunks:
                    db.delete(chunk)
                self._safe_commit(db)
            
            # Chunk text with page information
            # For method 9 (clause-aware), pass doc_id and source_name
            chunk_kwargs = {}
            if ingestion_method == 9:
                chunk_kwargs['doc_id'] = doc_id
                chunk_kwargs['source_name'] = doc_title
            
            chunks_data = self.chunking_service.chunk_text_with_pages(
                text, ingestion_method, pages, **chunk_kwargs
            )
            
            # Check if any chunks were created
            if not chunks_data:
                logger.warning(f"No chunks created for document {doc_id} with method {ingestion_method}. This may indicate the document format is not compatible with the selected chunking method.")
                ingestion.status = "failed"
                ingestion.error = f"No chunks created. Method {ingestion_method} may not be suitable for this document type. Try a different chunking method."
                self._safe_commit(db, ingestion_id)
                return False
            
            # Store chunks in database in batches to prevent session timeout
            stored_chunks = []
            chunk_ids = []  # Store chunk IDs to prevent DetachedInstanceError
            total_chunks = len(chunks_data)
            # Use adaptive batch size: smaller batches for small documents, 100 for larger ones
            # For very small documents (<10 chunks), process all at once
            # For larger documents, use batches of 100
            if total_chunks < 10:
                batch_size = total_chunks  # Process all chunks in one batch
            else:
                batch_size = 100  # Commit every 100 chunks
            
            for batch_start in range(0, total_chunks, batch_size):
                batch_end = min(batch_start + batch_size, total_chunks)
                batch = chunks_data[batch_start:batch_end]
                
                # Refresh session periodically during long insert operations
                # Refresh every 2 batches, or if we're processing a large document (>200 chunks)
                if (batch_start > 0 and batch_start % (batch_size * 2) == 0) or \
                   (total_chunks > 200 and batch_start > 0 and batch_start % batch_size == 0):
                    db.expire_all()
                
                for chunk_data in batch:
                    chunk = Chunk(
                        doc_id=doc_id,
                        method=ingestion_method,
                        page_from=chunk_data.get('page_from') or chunk_data.get('page_start'),
                        page_to=chunk_data.get('page_to') or chunk_data.get('page_end'),
                        hash=chunk_data['hash'],
                        text=chunk_data['text'],
                        # New metadata fields (for method 9 and future use)
                        section_id=chunk_data.get('section_id'),
                        section_id_alias=chunk_data.get('section_id_alias'),
                        title=chunk_data.get('title'),
                        parent_titles=chunk_data.get('parent_titles', []),
                        level=chunk_data.get('level'),
                        list_items=chunk_data.get('list_items', False),
                        has_supporting_docs=chunk_data.get('has_supporting_docs', False),
                        token_count=chunk_data.get('token_count'),
                        text_norm=chunk_data.get('text_norm')
                    )
                    db.add(chunk)
                    stored_chunks.append(chunk)
                
                # Commit after each batch to keep transaction alive and prevent timeout
                # This ALWAYS happens, regardless of batch size
                self._safe_commit(db)
                
                # Extract chunk IDs immediately after commit, before any expire_all() calls
                # This prevents DetachedInstanceError when accessing chunk.id later
                for chunk in stored_chunks[-len(batch):]:  # Only the chunks from this batch
                    chunk_ids.append(chunk.id)
            
            # Update status to embedding
            ingestion.status = "embedding"
            ingestion = self._safe_commit(db, ingestion_id) or ingestion
            
            # Refresh session before long embedding operation to prevent timeout
            db.expire_all()
            
            # Generate embeddings
            chunk_texts = [chunk_data['text'] for chunk_data in chunks_data]
            
            # Check memory before embedding generation
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss / 1024 / 1024
            
            # Special handling for dense documents (like markdown files)
            is_dense_document = len(chunk_texts) > 11 or len(text) > 10000  # More than 25 chunks or 25k chars
            if is_dense_document:
                logger.warning(f"Processing dense document with {len(chunk_texts)} chunks, {len(text)} characters")
                # Force single-chunk processing for dense documents
                embeddings = self._process_dense_document_embeddings(chunk_texts, process, ingestion_id, db)
                if embeddings is None:  # Processing failed
                    return False
            # Check if we have too many chunks for current memory
            elif len(chunk_texts) > 15 and memory_before > 1000:
                logger.info(f"Large document with {len(chunk_texts)} chunks and {memory_before:.1f}MB memory - processing in smaller batches")
                # Process in smaller batches to prevent OOM
                embeddings = []
                batch_size = 1  # Single chunk processing for memory-constrained environments
                for i in range(0, len(chunk_texts), batch_size):
                    batch_texts = chunk_texts[i:i + batch_size]
                    batch_embeddings = self.embedding_service.generate_embeddings(batch_texts)
                    embeddings.extend(batch_embeddings)
                    
                    # Check memory after each batch
                    memory_after_batch = process.memory_info().rss / 1024 / 1024
                    if memory_after_batch > 1500:
                        logger.error(f"Memory usage too high during processing: {memory_after_batch:.1f}MB")
                        ingestion.status = "failed"
                        ingestion.error = f"Memory usage too high during processing: {memory_after_batch:.1f}MB"
                        self._safe_commit(db, ingestion_id)
                        return False
                    
                    # Force garbage collection after each batch
                    import gc
                    gc.collect()
            else:
                # Normal processing for smaller documents
                embeddings = self.embedding_service.generate_embeddings(chunk_texts)
            
            # Check memory after embedding generation
            memory_after = process.memory_info().rss / 1024 / 1024
            
            # Prepare payloads for Qdrant using actual chunk IDs
            payloads = []
            for i, (chunk_data, chunk_id) in enumerate(zip(chunks_data, chunk_ids)):
                payload = {
                    'doc_id': doc_id,
                    'chunk_id': chunk_id,  # Use stored chunk ID to avoid DetachedInstanceError
                    'method': ingestion_method,
                    'page_from': chunk_data.get('page_from') or chunk_data.get('page_start'),
                    'page_to': chunk_data.get('page_to') or chunk_data.get('page_end'),
                    'hash': chunk_data['hash'],
                    'source': doc_title,
                    'source_name': doc_title,
                    # New metadata fields
                    'section_id': chunk_data.get('section_id'),
                    'section_id_alias': chunk_data.get('section_id_alias'),
                    'title': chunk_data.get('title'),
                    'parent_titles': chunk_data.get('parent_titles', []),
                    'level': chunk_data.get('level'),
                    'list_items': chunk_data.get('list_items', False),
                    'is_table': chunk_data.get('is_table', False),
                    'has_supporting_docs': chunk_data.get('has_supporting_docs', False),
                    'token_count': chunk_data.get('token_count'),
                    'text_norm': chunk_data.get('text_norm')
                }
                payloads.append(payload)
            
            # Clean up existing vectors in Qdrant for this document and method
            try:
                self.qdrant_service.delete_vectors_by_doc_id(doc_id, ingestion_method)
            except Exception as e:
                # This is expected for the first document upload when no index exists yet
                if "Index required but not found" not in str(e):
                    logger.warning(f"Failed to clean up existing vectors in Qdrant: {e}")
            
            # Refresh session before Qdrant operation
            db.expire_all()
            
            # Store in Qdrant
            self.qdrant_service.store_vectors(embeddings, payloads)
            
            # Force aggressive garbage collection after embedding generation
            import gc
            for _ in range(3):  # Multiple aggressive passes
                gc.collect()
            
            # Refresh session before status update
            db.expire_all()
            # Re-query ingestion to ensure fresh object
            ingestion = db.query(Ingestion).filter(Ingestion.id == ingestion_id).first()
            
            # Update status to indexing
            if ingestion:
                ingestion.status = "indexing"
                ingestion = self._safe_commit(db, ingestion_id) or ingestion
            
            # Refresh session before long operation to prevent timeout
            db.expire_all()
            
            # Create lexical index for full-text search
            try:
                self.lexical_index_service.create_fts_index(db)
            except Exception as lex_error:
                logger.warning(f"Failed to create FTS index (non-critical): {lex_error}")
            
            # Update search vectors for the new chunks in batches with periodic commits
            # This prevents session timeout during long operations
            total_chunks = len(chunks_data)
            # Use adaptive batch size: smaller for small documents
            # For very small documents (<5 chunks), process all at once
            # For larger documents, use batches of 5-50
            if total_chunks < 5:
                batch_size = total_chunks  # Process all chunks in one batch
            else:
                batch_size = min(50, max(5, total_chunks // 10))  # Between 5-50
            
            for batch_start in range(0, total_chunks, batch_size):
                batch_end = min(batch_start + batch_size, total_chunks)
                batch = chunks_data[batch_start:batch_end]
                
                try:
                    # Refresh session periodically to keep it alive
                    # Refresh every batch for large documents to prevent prepared state
                    if batch_start > 0 and (batch_start % batch_size == 0 or total_chunks > 100):
                        try:
                            db.expire_all()
                            logger.debug(f"Refreshed session at chunk {batch_start}/{total_chunks}")
                        except InvalidRequestError:
                            # Session is in prepared state, rollback and refresh
                            try:
                                db.rollback()
                                db.expire_all()
                            except:
                                pass
                    
                    for chunk_data in batch:
                        try:
                            # Get the actual chunk ID from database
                            chunk = db.query(Chunk).filter(
                                Chunk.doc_id == doc_id,
                                Chunk.hash == chunk_data['hash']
                            ).first()
                            if chunk:
                                self.lexical_index_service.add_chunk_to_index(
                                    chunk.id, chunk_data['text'], db
                                )
                        except InvalidRequestError as query_error:
                            if "prepared" in str(query_error).lower():
                                logger.warning(f"Session in prepared state during chunk query, refreshing")
                                try:
                                    db.rollback()
                                    db.expire_all()
                                    # Re-query the chunk after refresh
                                    chunk = db.query(Chunk).filter(
                                        Chunk.doc_id == doc_id,
                                        Chunk.hash == chunk_data['hash']
                                    ).first()
                                    if chunk:
                                        self.lexical_index_service.add_chunk_to_index(
                                            chunk.id, chunk_data['text'], db
                                        )
                                except Exception as retry_error:
                                    logger.warning(f"Failed to recover from prepared state in chunk query: {retry_error}")
                                    continue
                            else:
                                raise
                    
                    # Commit after each batch to keep transaction alive
                    # This ALWAYS happens, regardless of batch size
                    self._safe_commit(db)
                    logger.debug(f"Processed lexical index batch {batch_start}-{batch_end}/{total_chunks}")
                    
                except Exception as batch_error:
                    logger.warning(f"Error in lexical index batch {batch_start}-{batch_end}: {batch_error}")
                    # Try to rollback and continue with next batch
                    try:
                        db.rollback()
                        db.expire_all()
                    except:
                        pass
            
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
            
            # Refresh session before final commit to prevent prepared state
            db.expire_all()
            # Re-query ingestion to ensure we have a fresh object
            ingestion = db.query(Ingestion).filter(Ingestion.id == ingestion_id).first()
            
            # Update status to done and set finished_at timestamp
            if ingestion:
                ingestion.status = "done"
                ingestion.finished_at = datetime.utcnow()
                self._safe_commit(db, ingestion_id)
            
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing document for ingestion {ingestion_id}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            # Update status to failed and set finished_at timestamp
            try:
                # Refresh session before final commit
                db.expire_all()
                ingestion = db.query(Ingestion).filter(Ingestion.id == ingestion_id).first()
                if ingestion:
                    ingestion.status = "failed"
                    ingestion.error = str(e)
                    ingestion.finished_at = datetime.utcnow()
                    self._safe_commit(db, ingestion_id)
            except Exception as commit_error:
                logger.error(f"Failed to update ingestion status after error: {commit_error}")
            return False
    
    def _process_dense_document_embeddings(self, chunk_texts: list, process, ingestion_id: int, db) -> list:
        """
        Process embeddings for dense documents with aggressive memory management
        """
        import gc
        import logging
        logger = logging.getLogger(__name__)
        
        embeddings = []
        total_chunks = len(chunk_texts)
        
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
                
                if memory_after > 1500:  # Very conservative threshold for Railway
                    logger.error(f"Memory usage too high during dense document processing: {memory_after:.1f}MB")
                    # Re-query ingestion to avoid DetachedInstanceError
                    ingestion = db.query(Ingestion).filter(Ingestion.id == ingestion_id).first()
                    if ingestion:
                        ingestion.status = "failed"
                        ingestion.error = f"Memory usage too high during dense document processing: {memory_after:.1f}MB"
                        self._safe_commit(db, ingestion_id)
                    return None
                
                # Force garbage collection every 3 chunks for dense documents
                if (i + 1) % 3 == 0:
                    for _ in range(3):  # Multiple aggressive passes
                        gc.collect()
                    
                    # Clear embedding cache if memory is still high
                    if memory_after > 1500:
                        from app.services.embeddings import EmbeddingService
                        embedding_service = EmbeddingService()
                        embedding_service.clear_cache()
                
                # Refresh session periodically to prevent prepared state (every 50 chunks)
                if (i + 1) % 50 == 0:
                    try:
                        db.expire_all()
                        logger.debug(f"Refreshed session during dense document processing at chunk {i + 1}/{total_chunks}")
                    except Exception as refresh_error:
                        logger.warning(f"Failed to refresh session at chunk {i + 1}: {refresh_error}")
                        
            except Exception as e:
                logger.error(f"Error processing chunk {i + 1}: {e}")
                # Re-query ingestion to avoid DetachedInstanceError
                ingestion = db.query(Ingestion).filter(Ingestion.id == ingestion_id).first()
                if ingestion:
                    ingestion.status = "failed"
                    ingestion.error = f"Error processing chunk {i + 1}: {str(e)}"
                    self._safe_commit(db, ingestion_id)
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
