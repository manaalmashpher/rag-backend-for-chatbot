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
