"""
Ingestion status API endpoint
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
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
    Get ingestion status by ID
    """
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
