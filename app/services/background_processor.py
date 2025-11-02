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
        self.poll_interval_idle = 30  # Check every 30 seconds when idle (reduced CPU usage)
        self.poll_interval_active = 12  # Check every 5 seconds when processing
        self.max_retries = 3  # Max retries for failed processing
        self.memory_cleanup_interval = 10  # Cleanup memory every 10 processing cycles (reduced frequency)
        self.processing_count = 0
        self.max_memory_mb = 1200  # Emergency cleanup threshold (higher for all-mpnet-base-v2)
        self.consecutive_empty_polls = 0  # Track consecutive polls with no work
        self.last_memory_check = 0  # Track last memory check time
        self.memory_check_interval = 60  # Only check memory every 60 seconds (reduced CPU usage)
    
    async def start_processing(self):
        """Start the background processing loop"""
        if self.processing:
            logger.info("Background processor already running")
            return
        
        self.processing = True
        logger.info("Starting background document processor")
        
        try:
            while self.processing:
                # Adaptive polling: longer sleep when idle to reduce CPU usage
                had_work = await self._process_pending_ingestions()
                
                # Use adaptive polling interval based on whether there's work
                if had_work:
                    self.consecutive_empty_polls = 0
                    current_poll_interval = self.poll_interval_active
                else:
                    self.consecutive_empty_polls += 1
                    # Gradually increase poll interval when idle (up to 60 seconds max)
                    current_poll_interval = min(
                        self.poll_interval_idle + (self.consecutive_empty_polls * 5),
                        60
                    )
                
                # Periodic memory checks (less frequent to save CPU)
                import time
                current_time = time.time()
                if current_time - self.last_memory_check >= self.memory_check_interval:
                    await self._check_memory_usage()
                    self.last_memory_check = current_time
                
                # Periodic memory cleanup (less frequent)
                self.processing_count += 1
                if self.processing_count % self.memory_cleanup_interval == 0:
                    await self._cleanup_memory()
                
                await asyncio.sleep(current_poll_interval)
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
        """Process any pending ingestion records
        
        Returns:
            bool: True if work was found and processed, False otherwise
        """
        db = None
        try:
            db = next(get_db())
            
            # Find queued ingestions and retry failed ones
            from datetime import datetime, timedelta
            
            # Get queued ingestions
            queued_ingestions = db.query(Ingestion).filter(
                Ingestion.status == "queued"
            ).limit(1).all()
            
            # Get failed ingestions that can be retried (failed more than 1 minute ago, less than 3 retries)
            retry_time = datetime.utcnow() - timedelta(minutes=1)
            try:
                failed_ingestions = db.query(Ingestion).filter(
                    Ingestion.status == "failed",
                    Ingestion.finished_at < retry_time,
                    Ingestion.retry_count < self.max_retries
                ).limit(1).all()
            except Exception as e:
                # If retry_count column doesn't exist, query without it
                logger.warning(f"retry_count column not found, querying without it: {e}")
                failed_ingestions = db.query(Ingestion).filter(
                    Ingestion.status == "failed",
                    Ingestion.finished_at < retry_time
                ).limit(1).all()
            
            # Get stuck ingestions in embedding/indexing status (started more than 6 minutes ago)
            stuck_time = datetime.utcnow() - timedelta(minutes=6)
            try:
                stuck_ingestions = db.query(Ingestion).filter(
                    Ingestion.status.in_(["embedding", "indexing"]),
                    Ingestion.started_at < stuck_time,
                    Ingestion.retry_count < self.max_retries
                ).limit(1).all()
            except Exception as e:
                # If retry_count column doesn't exist, query without it
                logger.warning(f"retry_count column not found for stuck ingestions, querying without it: {e}")
                stuck_ingestions = db.query(Ingestion).filter(
                    Ingestion.status.in_(["embedding", "indexing"]),
                    Ingestion.started_at < stuck_time
                ).limit(1).all()
            
            # Mark stuck ingestions as failed so they can be retried
            for stuck_ingestion in stuck_ingestions:
                original_status = stuck_ingestion.status
                stuck_ingestion.status = "failed"
                stuck_ingestion.error = f"Processing stuck in {original_status} status for more than 10 minutes"
                stuck_ingestion.finished_at = datetime.utcnow()
                logger.warning(f"Marked stuck ingestion {stuck_ingestion.id} as failed for retry (was {original_status})")
            db.commit()
            
            # Combine both lists
            pending_ingestions = queued_ingestions + failed_ingestions
            
            logger.debug(f"Found {len(pending_ingestions)} pending ingestions")
            
            # Return False if no work found
            if not pending_ingestions:
                return False
            
            # Track if we actually processed any work
            work_processed = False
            
            for ingestion in pending_ingestions:
                # Check memory before processing (only if we haven't checked recently)
                import psutil
                import os
                import time
                current_time = time.time()
                
                # Only check memory if it's been more than 30 seconds since last check
                if current_time - self.last_memory_check >= 30:
                    process = psutil.Process(os.getpid())
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    self.last_memory_check = current_time
                    
                    if memory_mb > 1150:  # Skip processing if memory is too high (reduced for Railway deployment)
                        logger.warning(f"Skipping ingestion {ingestion.id} due to high memory usage: {memory_mb:.1f}MB")
                        continue
                else:
                    # Use cached memory value or skip check to save CPU
                    memory_mb = None
                
                # Handle retry logic
                if ingestion.status == "failed":
                    # Check if retry_count field exists, if not set to 0
                    if not hasattr(ingestion, 'retry_count'):
                        ingestion.retry_count = 0
                    ingestion.retry_count += 1
                    ingestion.status = "queued"
                    ingestion.started_at = None
                    ingestion.error = None
                    db.commit()
                    logger.info(f"Retrying ingestion {ingestion.id} (attempt {ingestion.retry_count}/{self.max_retries})")
                
                memory_str = f"{memory_mb:.1f}MB" if memory_mb else "N/A"
                logger.info(f"Processing ingestion {ingestion.id} (memory: {memory_str})")
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
                    work_processed = True  # We attempted/started processing
                    if success:
                        logger.info(f"Successfully processed ingestion {ingestion.id} in {processing_time:.2f}s")
                    else:
                        logger.error(f"Failed to process ingestion {ingestion.id} in {processing_time:.2f}s")
                        
                except asyncio.TimeoutError:
                    processing_time = time.time() - start_time
                    work_processed = True  # We attempted processing (timed out)
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
                    work_processed = True  # We attempted processing (error occurred)
                    logger.error(f"Error processing ingestion {ingestion.id} after {processing_time:.2f}s: {e}")
                    logger.error(f"Error type: {type(e).__name__}")
                    logger.error(f"Error details: {str(e)}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
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
            return False
        finally:
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    logger.error(f"Failed to close database connection: {close_error}")
        
        return work_processed  # Return True only if we actually processed work
    
    async def _cleanup_memory(self):
        """Perform memory cleanup to prevent memory leaks"""
        try:
            import gc
            import psutil
            import os
            
            # Get current memory usage (less frequent checks)
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            logger.info(f"Memory usage before cleanup: {memory_mb:.1f}MB")
            
            # Reduced garbage collection passes to save CPU (1 pass instead of 3)
            collected = gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
            
            # Clear embedding cache if it's getting too large
            from app.services.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            if hasattr(embedding_service, '_embedding_cache'):
                cache_size = len(embedding_service._embedding_cache)
                # Smart cache management for all-mpnet-base-v2 (heavier model)
                if cache_size > 200:  # Clear cache if more than 200 entries (reasonable threshold)
                    embedding_service.clear_cache()
                    logger.info(f"Cleared embedding cache ({cache_size} entries)")
                elif cache_size > 50:  # Log warning for large cache
                    logger.warning(f"Embedding cache is large: {cache_size} entries")
            
            # Single garbage collection after cache clearing (reduced CPU usage)
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
            import time
            
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.max_memory_mb:
                # Only trigger emergency cleanup if we haven't done it recently
                current_time = time.time()
                if not hasattr(self, '_last_emergency_cleanup') or (current_time - self._last_emergency_cleanup) > 30:
                    logger.warning(f"High memory usage detected: {memory_mb:.1f}MB (threshold: {self.max_memory_mb}MB)")
                    await self._emergency_cleanup()
                    self._last_emergency_cleanup = current_time
                else:
                    logger.debug(f"High memory usage detected but cleanup was recent: {memory_mb:.1f}MB")
                
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
            
            # Single garbage collection pass (reduced CPU usage)
            import gc
            gc.collect()
            
            # Try to clear any remaining references
            import sys
            if hasattr(sys, '_clear_type_cache'):
                sys._clear_type_cache()
            
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
