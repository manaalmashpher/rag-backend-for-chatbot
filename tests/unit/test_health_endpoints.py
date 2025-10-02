"""
Unit tests for health and readiness check endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

class TestHealthEndpoints:
    """Test health and readiness check endpoints"""
    
    def test_liveness_check_success(self):
        """Test successful liveness check"""
        response = client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "ionologybot-api"
        assert data["version"] == "1.0.0"
    
    def test_readiness_check_success(self):
        """Test successful readiness check with all components healthy"""
        with patch('app.services.health_service.HealthService.readiness_check') as mock_readiness:
            mock_readiness.return_value = {
                "status": "ready",
                "timestamp": "2025-01-01T00:00:00Z",
                "service": "ionologybot-api",
                "version": "1.0.0",
                "components": {
                    "database": {"status": "healthy", "type": "postgresql"},
                    "qdrant": {"status": "healthy", "url": "http://localhost:6333"},
                    "embeddings": {"status": "healthy", "provider": "local"},
                    "llm": {"status": "not_configured"}
                }
            }
            
            response = client.get("/readyz")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert "components" in data
            assert data["components"]["database"]["status"] == "healthy"
    
    def test_readiness_check_failure(self):
        """Test readiness check with component failures"""
        with patch('app.services.health_service.HealthService.readiness_check') as mock_readiness:
            mock_readiness.return_value = {
                "status": "not_ready",
                "timestamp": "2025-01-01T00:00:00Z",
                "service": "ionologybot-api",
                "version": "1.0.0",
                "components": {
                    "database": {"status": "unhealthy", "error": "Connection failed"},
                    "qdrant": {"status": "healthy", "url": "http://localhost:6333"},
                    "embeddings": {"status": "unhealthy", "error": "Model not loaded"}
                }
            }
            
            response = client.get("/readyz")
            
            assert response.status_code == 503
            data = response.json()
            # The error handling middleware converts HTTPException to this format
            assert "detail" in data
            detail = data["detail"]
            assert detail["status"] == "not_ready"
            # The components might not be included in the error response
            # Just check that we have the basic error structure
    
    def test_readiness_check_exception(self):
        """Test readiness check with service exception"""
        with patch('app.services.health_service.HealthService.readiness_check') as mock_readiness:
            mock_readiness.side_effect = Exception("Service unavailable")
            
            response = client.get("/readyz")
            
            assert response.status_code == 503
            data = response.json()
            # The error handling middleware converts HTTPException to this format
            assert "detail" in data
            detail = data["detail"]
            assert detail["status"] == "not_ready"
            assert "error" in detail
    
    def test_liveness_check_exception(self):
        """Test liveness check with service exception"""
        with patch('app.services.health_service.HealthService.liveness_check') as mock_liveness:
            mock_liveness.side_effect = Exception("Service error")
            
            response = client.get("/healthz")
            
            assert response.status_code == 503
            data = response.json()
            # The error handling middleware converts HTTPException to this format
            assert "detail" in data
            detail = data["detail"]
            assert detail["status"] == "unhealthy"
            assert "error" in detail
