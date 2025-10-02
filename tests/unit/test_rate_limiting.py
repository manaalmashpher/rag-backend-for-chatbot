"""
Unit tests for rate limiting functionality
"""

import pytest
import time
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.rate_limiter import RateLimiter

client = TestClient(app)

class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_allows_requests_within_limit(self):
        """Test that requests within rate limit are allowed"""
        rate_limiter = RateLimiter()
        rate_limiter.rate_limit_qps = 5
        
        # Make 5 requests (within limit)
        for i in range(5):
            result = rate_limiter.is_allowed(f"client_{i}")
            assert result["allowed"] is True
            assert result["remaining"] >= 0
    
    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that requests over rate limit are blocked"""
        rate_limiter = RateLimiter()
        rate_limiter.rate_limit_qps = 2
        client_id = "test_client"
        
        # Make requests within limit
        for i in range(2):
            result = rate_limiter.is_allowed(client_id)
            assert result["allowed"] is True
        
        # This request should be blocked
        result = rate_limiter.is_allowed(client_id)
        assert result["allowed"] is False
        assert "retry_after" in result
    
    def test_rate_limiter_headers(self):
        """Test rate limit headers generation"""
        rate_limiter = RateLimiter()
        rate_limiter.rate_limit_qps = 5
        
        result = rate_limiter.is_allowed("test_client")
        headers = rate_limiter.get_rate_limit_headers("test_client")
        
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers
        assert headers["X-RateLimit-Limit"] == "5"
    
    def test_rate_limiter_cleanup(self):
        """Test rate limiter cleanup of old entries"""
        rate_limiter = RateLimiter()
        rate_limiter.rate_limit_qps = 1
        rate_limiter.window_size = 1  # 1 second window for testing
        
        # Make a request
        rate_limiter.is_allowed("test_client")
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Cleanup should remove old entries
        rate_limiter.cleanup_old_entries()
        
        # Should be able to make requests again
        result = rate_limiter.is_allowed("test_client")
        assert result["allowed"] is True
    
    @patch('app.middleware.rate_limiting.rate_limiter')
    def test_rate_limiting_middleware_allows_requests(self, mock_rate_limiter):
        """Test that rate limiting middleware allows requests within limit"""
        mock_rate_limiter.is_allowed.return_value = {
            "allowed": True,
            "remaining": 4,
            "reset_time": int(time.time()) + 60
        }
        mock_rate_limiter.get_rate_limit_headers.return_value = {
            "X-RateLimit-Limit": "5",
            "X-RateLimit-Remaining": "4",
            "X-RateLimit-Reset": str(int(time.time()) + 60)
        }
        
        response = client.get("/api/search?q=test")
        
        # Should not be rate limited (status depends on other factors)
        assert response.status_code != 429
    
    @patch('app.middleware.rate_limiting.rate_limiter')
    def test_rate_limiting_middleware_blocks_requests(self, mock_rate_limiter):
        """Test that rate limiting middleware blocks requests over limit"""
        # Create proper mock return values
        rate_limit_result = {
            "allowed": False,
            "retry_after": 60,
            "remaining": 0,
            "reset_time": int(time.time()) + 60
        }
        headers = {
            "X-RateLimit-Limit": "5",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + 60),
            "Retry-After": "60"
        }
        
        mock_rate_limiter.is_allowed.return_value = rate_limit_result
        mock_rate_limiter.get_rate_limit_headers.return_value = headers
        mock_rate_limiter.rate_limit_qps = 5
        
        response = client.get("/api/search?q=test")
        
        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "Rate limit exceeded"
        assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
    
    def test_rate_limiting_excluded_paths(self):
        """Test that excluded paths are not rate limited"""
        # Health endpoints should not be rate limited
        response = client.get("/healthz")
        assert response.status_code == 200
        
        response = client.get("/readyz")
        # Status depends on health service, but should not be 429
        assert response.status_code != 429
