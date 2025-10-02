"""
Rate limiting service
"""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiting service using sliding window algorithm
    """
    
    def __init__(self):
        self.rate_limit_qps = getattr(settings, 'rate_limit_qps', 5)
        self.window_size = 60  # 1 minute window
        self.storage: Dict[str, deque] = defaultdict(lambda: deque())
    
    def is_allowed(self, client_id: str, endpoint: Optional[str] = None) -> Dict[str, any]:
        """
        Check if request is allowed based on rate limit
        
        Args:
            client_id: Unique client identifier (IP address, user ID, etc.)
            endpoint: Optional endpoint-specific rate limiting
            
        Returns:
            Dictionary with rate limit status and headers
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_size)
        
        # Get client's request history
        client_requests = self.storage[client_id]
        
        # Remove old requests outside the window
        # The window_start is 60 seconds ago, so we remove requests older than that
        while client_requests and client_requests[0] < window_start:
            client_requests.popleft()
        
        
        # Check if adding this request would exceed rate limit
        if len(client_requests) >= self.rate_limit_qps:
            # Calculate retry after time
            oldest_request = client_requests[0] if client_requests else now
            retry_after = int((oldest_request + timedelta(seconds=self.window_size) - now).total_seconds())
            
            return {
                "allowed": False,
                "retry_after": max(1, retry_after),
                "remaining": 0,
                "reset_time": int((oldest_request + timedelta(seconds=self.window_size)).timestamp())
            }
        
        # Add current request
        client_requests.append(now)
        
        return {
            "allowed": True,
            "remaining": self.rate_limit_qps - len(client_requests),
            "reset_time": int((now + timedelta(seconds=self.window_size)).timestamp())
        }
    
    def get_rate_limit_headers(self, client_id: str, rate_limit_result: Dict[str, any] = None) -> Dict[str, str]:
        """
        Get rate limit headers for response
        
        Args:
            client_id: Client identifier
            rate_limit_result: Optional pre-computed rate limit result to avoid double counting
            
        Returns:
            Dictionary of rate limit headers
        """
        if rate_limit_result is None:
            # Only call is_allowed if no result provided (for backward compatibility)
            result = self.is_allowed(client_id)
        else:
            result = rate_limit_result
        
        headers = {
            "X-RateLimit-Limit": str(self.rate_limit_qps),
            "X-RateLimit-Remaining": str(result["remaining"]),
            "X-RateLimit-Reset": str(result["reset_time"])
        }
        
        if not result["allowed"]:
            headers["Retry-After"] = str(result["retry_after"])
        
        return headers
    
    def cleanup_old_entries(self):
        """
        Clean up old entries to prevent memory leaks
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_size)
        
        # Remove clients with no recent requests
        clients_to_remove = []
        for client_id, requests in self.storage.items():
            # Remove old requests
            while requests and requests[0] < window_start:
                requests.popleft()
            
            # If no requests left, mark for removal
            if not requests:
                clients_to_remove.append(client_id)
        
        # Remove empty client entries
        for client_id in clients_to_remove:
            del self.storage[client_id]
        
        logger.debug(f"Rate limiter cleanup: removed {len(clients_to_remove)} empty client entries")
    
    def clear_all(self):
        """
        Clear all rate limiting data (useful for testing)
        """
        self.storage.clear()
        logger.info("Rate limiter cleared all client data")
    
    def force_reset(self):
        """
        Force reset the rate limiter completely
        """
        self.storage.clear()
        # Reset the rate limit settings to ensure they're current
        self.rate_limit_qps = getattr(settings, 'rate_limit_qps', 5)
        logger.info("Rate limiter force reset completed")
    
    def reset_client(self, client_id: str):
        """
        Reset rate limiting for a specific client
        
        Args:
            client_id: Client identifier to reset
        """
        if client_id in self.storage:
            del self.storage[client_id]
            logger.info(f"Rate limiter reset for client: {client_id}")

# Global rate limiter instance
rate_limiter = RateLimiter()
