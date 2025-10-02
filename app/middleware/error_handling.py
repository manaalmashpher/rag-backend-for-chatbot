"""
Error handling middleware with graceful degradation
"""

import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive error handling and graceful degradation
    """
    
    def __init__(self, app, enable_graceful_degradation: bool = True):
        super().__init__(app)
        self.enable_graceful_degradation = enable_graceful_degradation
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with error handling
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response or error response
        """
        try:
            response = await call_next(request)
            return response
            
        except StarletteHTTPException as e:
            # Handle FastAPI HTTP exceptions
            return self._handle_http_exception(e, request)
            
        except Exception as e:
            # Handle unexpected exceptions
            return self._handle_unexpected_exception(e, request)
    
    def _handle_http_exception(self, exc: StarletteHTTPException, request: Request) -> JSONResponse:
        """
        Handle HTTP exceptions with proper error formatting
        
        Args:
            exc: HTTP exception
            request: Request object
            
        Returns:
            JSON error response
        """
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        
        # Generate correlation ID if not present
        correlation_id = request.headers.get("X-Correlation-ID", "unknown")
        
        error_response = {
            "error": exc.detail,
            "error_code": self._get_error_code(exc.status_code),
            "status_code": exc.status_code,
            "correlation_id": correlation_id,
            "path": request.url.path
        }
        
        # Add additional details for specific error types
        if exc.status_code == 422:
            error_response["details"] = {"validation_error": "Request validation failed"}
        elif exc.status_code == 429:
            error_response["details"] = {"retry_after": 60}
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
    
    def _handle_unexpected_exception(self, exc: Exception, request: Request) -> JSONResponse:
        """
        Handle unexpected exceptions with graceful degradation
        
        Args:
            exc: Exception
            request: Request object
            
        Returns:
            JSON error response
        """
        logger.error(f"Unexpected exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
        
        # Generate correlation ID if not present
        correlation_id = request.headers.get("X-Correlation-ID", "unknown")
        
        # Determine if we should enable graceful degradation
        if self.enable_graceful_degradation and self._is_degradable_error(exc, request):
            return self._handle_graceful_degradation(exc, request, correlation_id)
        
        # Standard error response
        error_response = {
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "status_code": 500,
            "correlation_id": correlation_id,
            "path": request.url.path
        }
        
        # Include error details in development mode
        if getattr(settings, 'debug', False):
            error_response["details"] = {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc)
            }
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )
    
    def _is_degradable_error(self, exc: Exception, request: Request) -> bool:
        """
        Check if error allows for graceful degradation
        
        Args:
            exc: Exception
            request: Request object
            
        Returns:
            True if graceful degradation is possible
        """
        # Check if it's a search-related error
        if request.url.path.startswith("/api/search"):
            return True
        
        # Check if it's a non-critical service error
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return True
        
        return False
    
    def _handle_graceful_degradation(self, exc: Exception, request: Request, correlation_id: str) -> JSONResponse:
        """
        Handle graceful degradation for specific endpoints
        
        Args:
            exc: Exception
            request: Request object
            correlation_id: Request correlation ID
            
        Returns:
            JSON response with degraded functionality
        """
        if request.url.path.startswith("/api/search"):
            # For search endpoints, return empty results instead of error
            return JSONResponse(
                status_code=200,
                content={
                    "results": [],
                    "total_results": 0,
                    "query": request.query_params.get("q", ""),
                    "limit": int(request.query_params.get("limit", 10)),
                    "search_type": "degraded",
                    "metadata": {
                        "degraded": True,
                        "reason": "Service temporarily unavailable",
                        "error": str(exc)
                    },
                    "latency_ms": 0,
                    "correlation_id": correlation_id
                }
            )
        
        # For other endpoints, return service unavailable
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service temporarily unavailable",
                "error_code": "SERVICE_UNAVAILABLE",
                "status_code": 503,
                "correlation_id": correlation_id,
                "path": request.url.path,
                "details": {
                    "degraded": True,
                    "reason": "Service experiencing issues"
                }
            }
        )
    
    def _get_error_code(self, status_code: int) -> str:
        """
        Get error code for HTTP status code
        
        Args:
            status_code: HTTP status code
            
        Returns:
            Error code string
        """
        error_codes = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE",
            504: "GATEWAY_TIMEOUT"
        }
        
        return error_codes.get(status_code, "UNKNOWN_ERROR")
