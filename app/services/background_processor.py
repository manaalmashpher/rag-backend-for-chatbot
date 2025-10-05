"""
Background document processing service
"""

import asyncio
import logging
import time
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.ingestion import IngestionService
from app.models.database import Ingestion

logger = logging.getLogger(__name__)

class BackgroundProcessor:
    """
    Handles background processing of document ingestion
    """
    
    def __init__(self):
        self.processing = False
        self.ingestion_service = IngestionService()
        self.max_processing_time = 300  # 5 minutes max per document
        self.poll_interval = 5  # Check every 5 seconds
        self.max_retries = 3  # Max retries for failed processing
        self.memory_cleanup_interval = 3  # Cleanup memory every 3 processing cycles
        self.processing_count = 0
        self.max_memory_mb = 1000  # Emergency cleanup threshold (higher for all-mpnet-base-v2)
    
    async def start_processing(self):
        """Start the background processing loop"""
        if self.processing:
            logger.info("Background processor already running")
            return
        
        self.processing = True
        logger.info("Starting background document processor")
        
        try:
            while self.processing:
                # Check memory usage before processing
                await self._check_memory_usage()
                
                await self._process_pending_ingestions()
                
                # Periodic memory cleanup
                self.processing_count += 1
                if self.processing_count % self.memory_cleanup_interval == 0:
                    await self._cleanup_memory()
                
                await asyncio.sleep(self.poll_interval)  # Check every 5 seconds
        except Exception as e:
            logger.error(f"Background processor error: {e}")
        finally:
            self.processing = False
            logger.info("Background processor stopped")
    
    def stop_processing(self):
        """Stop the background processing loop"""
        self.processing = False
        logger.info("Stopping background document processor")
    
    async def _process_pending_ingestions(self):
        """Process any pending ingestion records"""
        db = None
        try:
            db = next(get_db())
            
            # Find queued ingestions
            pending_ingestions = db.query(Ingestion).filter(
                Ingestion.status == "queued"
            ).limit(1).all()  # Process one at a time
            
            logger.debug(f"Found {len(pending_ingestions)} pending ingestions")
            
            for ingestion in pending_ingestions:
                # Check memory before processing
                import psutil
                import os
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                if memory_mb > 1200:  # Skip processing if memory is too high (increased threshold for all-mpnet-base-v2)
                    logger.warning(f"Skipping ingestion {ingestion.id} due to high memory usage: {memory_mb:.1f}MB")
                    continue
                
                logger.info(f"Processing ingestion {ingestion.id} (memory: {memory_mb:.1f}MB)")
                start_time = time.time()
                
                try:
                    # Process the document with timeout protection
                    success = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, 
                            self.ingestion_service.process_document, 
                            ingestion.id, 
                            db
                        ),
                        timeout=self.max_processing_time
                    )
                    
                    processing_time = time.time() - start_time
                    if success:
                        logger.info(f"Successfully processed ingestion {ingestion.id} in {processing_time:.2f}s")
                    else:
                        logger.error(f"Failed to process ingestion {ingestion.id} in {processing_time:.2f}s")
                        
                except asyncio.TimeoutError:
                    processing_time = time.time() - start_time
                    logger.error(f"Processing timeout for ingestion {ingestion.id} after {processing_time:.2f}s")
                    # Update status to failed due to timeout
                    try:
                        ingestion.status = "failed"
                        ingestion.error = f"Processing timeout after {self.max_processing_time}s"
                        db.commit()
                    except Exception as commit_error:
                        logger.error(f"Failed to update ingestion status: {commit_error}")
                        db.rollback()
                        
                except Exception as e:
                    processing_time = time.time() - start_time
                    logger.error(f"Error processing ingestion {ingestion.id} after {processing_time:.2f}s: {e}")
                    logger.error(f"Error type: {type(e).__name__}")
                    logger.error(f"Error details: {str(e)}")
                    # Update status to failed
                    try:
                        ingestion.status = "failed"
                        ingestion.error = str(e)
                        db.commit()
                    except Exception as commit_error:
                        logger.error(f"Failed to update ingestion status: {commit_error}")
                        db.rollback()
            
        except Exception as e:
            logger.error(f"Error in background processing: {e}")
            if db:
                try:
                    db.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {rollback_error}")
        finally:
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    logger.error(f"Failed to close database connection: {close_error}")
    
    async def _cleanup_memory(self):
        """Perform memory cleanup to prevent memory leaks"""
        try:
            import gc
            import psutil
            import os
            
            # Get current memory usage
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            logger.info(f"Memory usage before cleanup: {memory_mb:.1f}MB")
            
            # Force garbage collection multiple times
            collected = 0
            for _ in range(2):  # Multiple passes
                collected += gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
            
            # Clear embedding cache if it's getting too large
            from app.services.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            if hasattr(embedding_service, '_embedding_cache'):
                cache_size = len(embedding_service._embedding_cache)
                # Very aggressive cache clearing for all-mpnet-base-v2 (heavier model)
                if cache_size > 100:  # Clear cache if more than 100 entries (very low threshold)
                    embedding_service.clear_cache()
                    logger.info(f"Cleared embedding cache ({cache_size} entries)")
                elif cache_size > 50:  # Log warning for large cache
                    logger.warning(f"Embedding cache is large: {cache_size} entries")
            
            # Force another garbage collection after cache clearing
            gc.collect()
            
            # Get memory usage after cleanup
            memory_mb_after = process.memory_info().rss / 1024 / 1024
            memory_freed = memory_mb - memory_mb_after
            
            if memory_freed > 30:  # Only log if significant memory was freed
                logger.info(f"Memory usage after cleanup: {memory_mb_after:.1f}MB (freed {memory_freed:.1f}MB)")
            else:
                logger.debug(f"Memory usage after cleanup: {memory_mb_after:.1f}MB (freed {memory_freed:.1f}MB)")
            
        except Exception as e:
            logger.warning(f"Memory cleanup failed: {e}")
    
    async def _check_memory_usage(self):
        """Check memory usage and trigger emergency cleanup if needed"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.max_memory_mb:
                logger.warning(f"High memory usage detected: {memory_mb:.1f}MB (threshold: {self.max_memory_mb}MB)")
                await self._emergency_cleanup()
                
        except Exception as e:
            logger.warning(f"Memory check failed: {e}")
    
    async def _emergency_cleanup(self):
        """Emergency memory cleanup when usage is too high"""
        try:
            logger.warning("Performing emergency memory cleanup...")
            
            # Clear all caches
            from app.services.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            embedding_service.clear_cache()
            
            # Force aggressive garbage collection
            import gc
            for _ in range(2):  # Multiple aggressive passes
                gc.collect()
            
            # Check memory after cleanup
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            logger.warning(f"Emergency cleanup completed. Memory usage: {memory_mb:.1f}MB")
            
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")

# Global instance
background_processor = BackgroundProcessor()
