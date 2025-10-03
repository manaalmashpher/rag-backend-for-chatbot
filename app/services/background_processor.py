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
    
    async def start_processing(self):
        """Start the background processing loop"""
        if self.processing:
            logger.info("Background processor already running")
            return
        
        self.processing = True
        logger.info("Starting background document processor")
        
        try:
            while self.processing:
                await self._process_pending_ingestions()
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
            
            for ingestion in pending_ingestions:
                logger.info(f"Processing ingestion {ingestion.id}")
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

# Global instance
background_processor = BackgroundProcessor()
