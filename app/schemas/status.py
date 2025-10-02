"""
Status API schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class IngestionStatus(BaseModel):
    """Ingestion status response"""
    id: int
    status: str
    progress: Optional[dict] = None
    error: Optional[str] = None
    blocked_reason: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
