"""
Health and readiness check service
"""

import logging
import time
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
        self.qdrant_service = None
        self.embedding_service = None
        self._last_health_check = 0
        self._cached_health_status = None
        self._health_cache_ttl = 30  # Cache health status for 30 seconds
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize services with error handling for deployment"""
        try:
            self.embedding_service = EmbeddingService()
        except Exception as e:
            logger.warning(f"Failed to initialize embedding service: {str(e)}")
            self.embedding_service = None
        
        try:
            self.qdrant_service = QdrantService()
        except Exception as e:
            logger.warning(f"Failed to initialize Qdrant service: {str(e)}")
            self.qdrant_service = None
    
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
        Readiness check - component dependency validation with caching
        
        Returns:
            Dictionary with readiness status and component health
        """
        # Check if we have a cached result that's still valid
        current_time = time.time()
        if (self._cached_health_status and 
            current_time - self._last_health_check < self._health_cache_ttl):
            return self._cached_health_status
        
        components = {}
        overall_healthy = True
        
        # Check database connectivity (fast check)
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
        
        # Check Qdrant connectivity (only if service is initialized)
        if self.qdrant_service is not None:
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
                # Don't fail overall health if Qdrant is unavailable
                # overall_healthy = False
        else:
            components["qdrant"] = {
                "status": "unavailable",
                "message": "Qdrant service not initialized - check configuration"
            }
        
        # Check embedding provider (only if service is initialized)
        if self.embedding_service is not None:
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
                # Don't fail overall health if embeddings are unavailable
                # overall_healthy = False
        else:
            components["embeddings"] = {
                "status": "unavailable",
                "message": "Embedding service not initialized - check configuration"
            }
        
        # Check DeepSeek LLM provider configuration
        # CRITICAL: Only check configuration presence, DO NOT make actual API calls to avoid billing
        import os
        deepseek_key = settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key and deepseek_key.strip():
            components["llm"] = {
                "status": "configured",
                "provider": "deepseek",
                "message": "DeepSeek API key is configured"
            }
        else:
            components["llm"] = {
                "status": "not_configured",
                "provider": "deepseek",
                "message": "DeepSeek API key is not configured. Set DEEPSEEK_API_KEY or Settings.deepseek_api_key"
            }
        
        result = {
            "status": "ready" if overall_healthy else "not_ready",
            "timestamp": self._get_timestamp(),
            "service": "ionologybot-api",
            "version": "1.0.0",
            "components": components
        }
        
        # Cache the result
        self._cached_health_status = result
        self._last_health_check = current_time
        
        return result
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
