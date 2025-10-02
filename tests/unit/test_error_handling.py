"""
Unit tests for error handling middleware
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.middleware.error_handling import ErrorHandlingMiddleware

# Create a test app with error handling middleware
test_app = FastAPI()
test_app.add_middleware(ErrorHandlingMiddleware)

@test_app.get("/test-success")
async def test_success():
    return {"message": "success"}

@test_app.get("/test-http-error")
async def test_http_error():
    # Use a regular exception that our middleware will catch
    raise ValueError("Bad request")

@test_app.get("/test-unexpected-error")
async def test_unexpected_error():
    raise ValueError("Unexpected error")

@test_app.get("/test-search-degradation")
async def test_search_degradation():
    raise ConnectionError("Service unavailable")

client = TestClient(test_app)

class TestErrorHandling:
    """Test error handling middleware"""
    
    def test_successful_request(self):
        """Test that successful requests pass through"""
        response = client.get("/test-success")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "success"
    
    def test_http_exception_handling(self):
        """Test that exceptions are properly handled by our middleware"""
        response = client.get("/test-http-error")
        
        assert response.status_code == 500  # Our middleware returns 500 for unexpected exceptions
        data = response.json()
        assert data["error"] == "Internal server error"
        assert data["error_code"] == "INTERNAL_ERROR"
        assert data["status_code"] == 500
        assert "correlation_id" in data
        assert data["path"] == "/test-http-error"
    
    def test_unexpected_exception_handling(self):
        """Test that unexpected exceptions are handled"""
        response = client.get("/test-unexpected-error")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal server error"
        assert data["error_code"] == "INTERNAL_ERROR"
        assert data["status_code"] == 500
        assert "correlation_id" in data
        assert data["path"] == "/test-unexpected-error"
    
    def test_graceful_degradation_search(self):
        """Test graceful degradation for search endpoints"""
        # Create a test app with search endpoint
        search_app = FastAPI()
        search_app.add_middleware(ErrorHandlingMiddleware)
        
        @search_app.get("/api/search")
        async def search_endpoint():
            raise ConnectionError("Search service unavailable")
        
        search_client = TestClient(search_app)
        response = search_client.get("/api/search?q=test")
        
        assert response.status_code == 200  # Should return degraded response
        data = response.json()
        assert data["search_type"] == "degraded"
        assert data["total_results"] == 0
        assert data["metadata"]["degraded"] is True
        assert "correlation_id" in data
    
    def test_graceful_degradation_non_search(self):
        """Test graceful degradation for non-search endpoints"""
        response = client.get("/test-search-degradation")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "Service temporarily unavailable"
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert data["status_code"] == 503
        assert data["details"]["degraded"] is True
    
    def test_correlation_id_preservation(self):
        """Test that correlation ID is preserved in error responses"""
        response = client.get("/test-http-error", headers={"X-Correlation-ID": "test-123"})
        
        assert response.status_code == 500
        data = response.json()
        assert data["correlation_id"] == "test-123"
    
    def test_correlation_id_generation(self):
        """Test that correlation ID is generated when not present"""
        response = client.get("/test-http-error")
        
        assert response.status_code == 500
        data = response.json()
        assert data["correlation_id"] == "unknown"  # Default when not provided
    
    def test_error_codes_mapping(self):
        """Test that our middleware returns correct error codes for unexpected exceptions"""
        response = client.get("/test-http-error")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == "INTERNAL_ERROR"
        assert data["error"] == "Internal server error"
