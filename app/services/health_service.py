"""
Health and readiness check service
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.services.qdrant import QdrantService
from app.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

class HealthService:
    """
    Service for health and readiness checks
    """
    
    def __init__(self):
        self.qdrant_service = QdrantService()
        self.embedding_service = EmbeddingService()
    
    def liveness_check(self) -> Dict[str, Any]:
        """
        Liveness check - basic process health
        
        Returns:
            Dictionary with liveness status
        """
        try:
            return {
                "status": "healthy",
                "timestamp": self._get_timestamp(),
                "service": "ionologybot-api",
                "version": "1.0.0"
            }
        except Exception as e:
            logger.error(f"Liveness check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "timestamp": self._get_timestamp(),
                "error": str(e)
            }
    
    def readiness_check(self) -> Dict[str, Any]:
        """
        Readiness check - component dependency validation
        
        Returns:
            Dictionary with readiness status and component health
        """
        components = {}
        overall_healthy = True
        
        # Check database connectivity
        try:
            from sqlalchemy import text
            db = next(get_db())
            db.execute(text("SELECT 1"))
            components["database"] = {
                "status": "healthy",
                "type": "postgresql",
                "url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "local"
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            components["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
        
        # Check Qdrant connectivity
        try:
            self.qdrant_service.health_check()
            components["qdrant"] = {
                "status": "healthy",
                "url": settings.qdrant_url,
                "collection": settings.qdrant_collection
            }
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            components["qdrant"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
        
        # Check embedding provider
        try:
            self.embedding_service.health_check()
            components["embeddings"] = {
                "status": "healthy",
                "provider": getattr(settings, 'embedding_provider', 'local'),
                "model": settings.embedding_model
            }
        except Exception as e:
            logger.error(f"Embedding service health check failed: {str(e)}")
            components["embeddings"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
        
        # LLM provider not yet integrated
        components["llm"] = {
            "status": "not_implemented",
            "message": "LLM integration not yet implemented"
        }
        
        return {
            "status": "ready" if overall_healthy else "not_ready",
            "timestamp": self._get_timestamp(),
            "service": "ionologybot-api",
            "version": "1.0.0",
            "components": components
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
