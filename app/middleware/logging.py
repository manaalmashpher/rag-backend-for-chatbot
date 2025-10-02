"""
Structured logging middleware
"""

import time
import logging
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging
    """
    
    def __init__(self, app, excluded_paths: list = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/healthz",
            "/readyz",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with structured logging
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response with logging
        """
        # Skip logging for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Log request
        self._log_request(request, correlation_id)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            self._log_response(request, response, correlation_id, process_time)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log error
            self._log_error(request, e, correlation_id, process_time)
            
            # Re-raise the exception
            raise
    
    def _log_request(self, request: Request, correlation_id: str):
        """
        Log incoming request
        
        Args:
            request: FastAPI request object
            correlation_id: Request correlation ID
        """
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Get user agent
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Log request details
        logger.info(
            "Request received",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "content_type": request.headers.get("Content-Type"),
                "content_length": request.headers.get("Content-Length"),
                "event_type": "request"
            }
        )
    
    def _log_response(self, request: Request, response: Response, correlation_id: str, process_time: float):
        """
        Log outgoing response
        
        Args:
            request: FastAPI request object
            response: Response object
            correlation_id: Request correlation ID
            process_time: Processing time in seconds
        """
        logger.info(
            "Response sent",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2),
                "content_type": response.headers.get("Content-Type"),
                "content_length": response.headers.get("Content-Length"),
                "event_type": "response"
            }
        )
    
    def _log_error(self, request: Request, error: Exception, correlation_id: str, process_time: float):
        """
        Log error response
        
        Args:
            request: FastAPI request object
            error: Exception that occurred
            correlation_id: Request correlation ID
            process_time: Processing time in seconds
        """
        logger.error(
            "Request failed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "process_time_ms": round(process_time * 1000, 2),
                "event_type": "error"
            },
            exc_info=True
        )
    
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
