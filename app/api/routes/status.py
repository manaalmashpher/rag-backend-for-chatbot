"""
Ingestion status API endpoint
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.models.database import Ingestion
from app.schemas.status import IngestionStatus

router = APIRouter()

@router.get("/ingestions/{ingestion_id}", response_model=IngestionStatus)
async def get_ingestion_status(
    ingestion_id: int,
    db: Session = Depends(get_db)
):
    """
    Get ingestion status by ID with optimized query
    """
    try:
        # Use a more efficient query with only necessary fields
        result = db.execute(
            text("""
                SELECT id, status, error, started_at, finished_at, created_at
                FROM ingestion 
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve ingestion status: {str(e)}"
        )
