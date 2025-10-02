"""
Rate limiting middleware
"""

import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests
    """
    
    def __init__(self, app, excluded_paths: list = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/health",
            "/healthz",
            "/readyz",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request through rate limiting
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Skip rate limiting for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        rate_limit_result = rate_limiter.is_allowed(client_ip, request.url.path)
        
        if not rate_limit_result["allowed"]:
            logger.warning(f"Rate limit exceeded for client {client_ip} on {request.url.path}")
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "details": {
                        "retry_after": rate_limit_result["retry_after"],
                        "limit": rate_limiter.rate_limit_qps
                    }
                },
                headers=rate_limiter.get_rate_limit_headers(client_ip, rate_limit_result)
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        headers = rate_limiter.get_rate_limit_headers(client_ip, rate_limit_result)
        for header, value in headers.items():
            response.headers[header] = value
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check for forwarded IP (from proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if path should be excluded from rate limiting
        
        Args:
            path: Request path
            
        Returns:
            True if path should be excluded
        """
        # Check exact matches
        if path in self.excluded_paths:
            return True
        
        # Check if path starts with any excluded path
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return True
        
        return False
