"""
Retry service with exponential backoff and circuit breaker patterns
"""

import time
import logging
from typing import Callable, Any, Optional, Dict
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back

class RetryService:
    """
    Service for handling retries with exponential backoff and circuit breaker
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        # Circuit breaker state
        self.circuit_state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = 5
        self.timeout = 60  # seconds
        self.last_failure_time = None
    
    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with exponential backoff retry
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    logger.error(f"Function {func.__name__} failed after {self.max_retries} retries: {str(e)}")
                    break
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {delay}s: {str(e)}")
                
                time.sleep(delay)
        
        raise last_exception
    
    def circuit_breaker(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker pattern
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        # Check circuit state
        if self.circuit_state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.circuit_state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time > self.timeout
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        self.circuit_state = CircuitState.CLOSED
        self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_state = CircuitState.OPEN
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "state": self.circuit_state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "timeout": self.timeout
        }

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    Decorator for retry with exponential backoff
    
    Args:
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_service = RetryService(max_retries, base_delay, max_delay)
            return retry_service.retry_with_backoff(func, *args, **kwargs)
        return wrapper
    return decorator

def circuit_breaker(failure_threshold: int = 5, timeout: int = 60):
    """
    Decorator for circuit breaker pattern
    
    Args:
        failure_threshold: Number of failures before opening circuit
        timeout: Timeout in seconds before attempting reset
    """
    def decorator(func: Callable) -> Callable:
        retry_service = RetryService()
        retry_service.failure_threshold = failure_threshold
        retry_service.timeout = timeout
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_service.circuit_breaker(func, *args, **kwargs)
        return wrapper
    return decorator

# Global retry service instances
retry_service = RetryService()
