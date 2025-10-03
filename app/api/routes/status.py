"""
Ingestion status API endpoint
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.models.database import Ingestion
from app.schemas.status import IngestionStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/memory-status")
async def get_memory_status():
    """
    Get current memory usage status
    """
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # Get embedding cache size
        from app.services.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        cache_size = len(embedding_service._embedding_cache) if hasattr(embedding_service, '_embedding_cache') else 0
        
        return {
            "memory_usage_mb": round(memory_mb, 1),
            "embedding_cache_size": cache_size,
            "model": embedding_service.model if hasattr(embedding_service, 'model') else "unknown",
            "status": "healthy" if memory_mb < 700 else "warning" if memory_mb < 1000 else "critical"
        }
        
    except Exception as e:
        return {"error": str(e), "status": "error"}

@router.post("/retry-stuck-ingestions")
async def retry_stuck_ingestions(db: Session = Depends(get_db)):
    """
    Retry stuck ingestions that are in embedding/indexing status
    """
    try:
        from datetime import datetime, timedelta
        
        # Find stuck ingestions (embedding/indexing status for more than 5 minutes)
        stuck_time = datetime.utcnow() - timedelta(minutes=3)
        stuck_ingestions = db.query(Ingestion).filter(
            Ingestion.status.in_(["embedding", "indexing"]),
            Ingestion.started_at < stuck_time
        ).all()
        
        retried_count = 0
        for ingestion in stuck_ingestions:
            # Reset to queued status
            ingestion.status = "queued"
            ingestion.started_at = None
            ingestion.error = None
            retried_count += 1
            logger.info(f"Retrying stuck ingestion {ingestion.id}")
        
        db.commit()
        
        return {
            "message": f"Retried {retried_count} stuck ingestions",
            "retried_count": retried_count
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to retry stuck ingestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retry ingestions: {str(e)}")

@router.get("/ingestions/{ingestion_id}", response_model=IngestionStatus)
async def get_ingestion_status(
    ingestion_id: int,
    db: Session = Depends(get_db)
):
    """
    Get ingestion status by ID with optimized query
    """
    try:
        # Try raw SQL first for better performance
        try:
            result = db.execute(
                text("""
                    SELECT id, status, error, started_at, finished_at, created_at
                    FROM ingestions 
                    WHERE id = :ingestion_id
                """),
                {"ingestion_id": ingestion_id}
            ).fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail="Ingestion not found"
                )
            
            # Determine blocked reason if applicable
            blocked_reason = None
            if result.status == "blocked_scanned_pdf":
                blocked_reason = "scanned_pdf"
            
            return IngestionStatus(
                id=result.id,
                status=result.status,
                error=result.error,
                blocked_reason=blocked_reason,
                started_at=result.started_at,
                finished_at=result.finished_at,
                created_at=result.created_at
            )
        except Exception as sql_error:
            # Fallback to ORM if raw SQL fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Raw SQL failed, falling back to ORM: {str(sql_error)}")
            
            ingestion = db.query(Ingestion).filter(Ingestion.id == ingestion_id).first()
            
            if not ingestion:
                raise HTTPException(
                    status_code=404,
                    detail="Ingestion not found"
                )
            
            # Determine blocked reason if applicable
            blocked_reason = None
            if ingestion.status == "blocked_scanned_pdf":
                blocked_reason = "scanned_pdf"
            
            return IngestionStatus(
                id=ingestion.id,
                status=ingestion.status,
                error=ingestion.error,
                blocked_reason=blocked_reason,
                started_at=ingestion.started_at,
                finished_at=ingestion.finished_at,
                created_at=ingestion.created_at
            )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving ingestion {ingestion_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve ingestion status: {str(e)}"
        )
