"""
Health and readiness check API endpoints
"""

from fastapi import APIRouter, HTTPException
from app.services.health_service import HealthService

router = APIRouter()
health_service = HealthService()

@router.get("/healthz")
async def liveness_check():
    """
    Liveness check endpoint
    
    Returns:
        Basic health status indicating if the service is running
    """
    try:
        result = health_service.liveness_check()
        
        if result["status"] == "healthy":
            return result
        else:
            raise HTTPException(status_code=503, detail=result)
            
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@router.get("/readyz")
async def readiness_check():
    """
    Readiness check endpoint
    
    Returns:
        Detailed readiness status with component health checks
    """
    try:
        result = health_service.readiness_check()
        
        if result["status"] == "ready":
            return result
        else:
            raise HTTPException(status_code=503, detail=result)
            
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "error": str(e)
            }
        )

@router.get("/health/quick")
async def quick_health_check():
    """
    Quick health check endpoint - only checks database connectivity
    
    Returns:
        Basic health status for fast response times
    """
    try:
        from sqlalchemy import text
        from app.core.database import get_db
        
        db = next(get_db())
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "timestamp": health_service._get_timestamp(),
            "service": "ionologybot-api",
            "version": "1.0.0",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": health_service._get_timestamp()
            }
        )