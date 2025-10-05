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

@router.post("/memory-reset")
async def reset_memory(aggressive: bool = False):
    """
    Perform memory cleanup to return to baseline
    
    Args:
        aggressive: If True, clears all caches (slower but more memory freed)
                   If False, uses smart cache management (faster, keeps recent embeddings)
    """
    try:
        import psutil
        import os
        import gc
        import sys
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024
        
        # Clear embedding cache based on mode
        from app.services.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        cache_size_before = len(embedding_service._embedding_cache) if hasattr(embedding_service, '_embedding_cache') else 0
        
        if aggressive:
            # Aggressive mode: clear all caches
            embedding_service.clear_cache()
            cache_cleared = cache_size_before
        else:
            # Smart mode: only clear if cache is too large
            if cache_size_before > 200:
                embedding_service.clear_cache()
                cache_cleared = cache_size_before
            else:
                # Just cleanup old entries
                embedding_service._cleanup_cache()
                cache_cleared = cache_size_before - len(embedding_service._embedding_cache)
        
        # Clear rate limiter cache
        from app.services.rate_limiter import rate_limiter
        rate_limiter.clear_all()
        
        # Force aggressive garbage collection
        collected = 0
        for _ in range(5):  # Multiple aggressive passes
            collected += gc.collect()
        
        # Clear Python internal caches
        if hasattr(sys, '_clear_type_cache'):
            sys._clear_type_cache()
        
        # Force another GC pass
        gc.collect()
        
        memory_after = process.memory_info().rss / 1024 / 1024
        memory_freed = memory_before - memory_after
        
        return {
            "memory_before_mb": round(memory_before, 1),
            "memory_after_mb": round(memory_after, 1),
            "memory_freed_mb": round(memory_freed, 1),
            "embedding_cache_cleared": cache_cleared,
            "embedding_cache_remaining": len(embedding_service._embedding_cache),
            "objects_collected": collected,
            "mode": "aggressive" if aggressive else "smart",
            "status": "success"
        }
        
    except Exception as e:
        return {"error": str(e), "status": "error"}


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
