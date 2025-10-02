"""
Unit tests for retry service functionality
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from app.services.retry_service import RetryService, retry_with_backoff, circuit_breaker, CircuitState

class TestRetryService:
    """Test retry service functionality"""
    
    def test_retry_with_backoff_success(self):
        """Test retry with backoff on successful execution"""
        retry_service = RetryService(max_retries=3, base_delay=0.1, max_delay=1.0)
        
        def successful_func():
            return "success"
        
        result = retry_service.retry_with_backoff(successful_func)
        assert result == "success"
    
    def test_retry_with_backoff_failure(self):
        """Test retry with backoff on failed execution"""
        retry_service = RetryService(max_retries=2, base_delay=0.1, max_delay=1.0)
        
        call_count = 0
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            retry_service.retry_with_backoff(failing_func)
        
        # Should have been called 3 times (1 initial + 2 retries)
        assert call_count == 3
    
    def test_retry_with_backoff_eventual_success(self):
        """Test retry with backoff on eventual success"""
        retry_service = RetryService(max_retries=3, base_delay=0.1, max_delay=1.0)
        
        call_count = 0
        def eventually_successful_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = retry_service.retry_with_backoff(eventually_successful_func)
        assert result == "success"
        assert call_count == 3
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state (normal operation)"""
        retry_service = RetryService()
        retry_service.circuit_state = CircuitState.CLOSED
        
        def successful_func():
            return "success"
        
        result = retry_service.circuit_breaker(successful_func)
        assert result == "success"
        assert retry_service.circuit_state == CircuitState.CLOSED
        assert retry_service.failure_count == 0
    
    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold"""
        retry_service = RetryService()
        retry_service.failure_threshold = 3
        
        def failing_func():
            raise ValueError("Test error")
        
        # First 2 failures should be allowed
        for i in range(2):
            with pytest.raises(ValueError):
                retry_service.circuit_breaker(failing_func)
            assert retry_service.circuit_state == CircuitState.CLOSED
        
        # 3rd failure should open the circuit (but still raise the original exception)
        with pytest.raises(ValueError):
            retry_service.circuit_breaker(failing_func)
        
        assert retry_service.circuit_state == CircuitState.OPEN
        
        # 4th call should raise circuit breaker exception
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            retry_service.circuit_breaker(failing_func)
    
    def test_circuit_breaker_reset_after_timeout(self):
        """Test circuit breaker resets after timeout"""
        retry_service = RetryService()
        retry_service.failure_threshold = 1
        retry_service.timeout = 0.1  # 100ms timeout
        
        def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        with pytest.raises(ValueError):
            retry_service.circuit_breaker(failing_func)
        
        assert retry_service.circuit_state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Should now be in half-open state
        def successful_func():
            return "success"
        
        result = retry_service.circuit_breaker(successful_func)
        assert result == "success"
        assert retry_service.circuit_state == CircuitState.CLOSED
    
    def test_circuit_breaker_half_open_failure(self):
        """Test circuit breaker half-open state on failure"""
        retry_service = RetryService()
        retry_service.failure_threshold = 1
        retry_service.timeout = 0.1
        
        def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        with pytest.raises(ValueError):
            retry_service.circuit_breaker(failing_func)
        
        assert retry_service.circuit_state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Should be in half-open state, failure should open it again
        with pytest.raises(ValueError):
            retry_service.circuit_breaker(failing_func)
        
        assert retry_service.circuit_state == CircuitState.OPEN
    
    def test_get_circuit_status(self):
        """Test circuit breaker status reporting"""
        retry_service = RetryService()
        retry_service.failure_count = 2
        retry_service.failure_threshold = 5
        retry_service.timeout = 60
        
        status = retry_service.get_circuit_status()
        
        assert status["state"] == CircuitState.CLOSED.value
        assert status["failure_count"] == 2
        assert status["failure_threshold"] == 5
        assert status["timeout"] == 60
    
    def test_retry_decorator(self):
        """Test retry decorator"""
        call_count = 0
        
        @retry_with_backoff(max_retries=2, base_delay=0.1, max_delay=1.0)
        def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"
        
        result = decorated_func()
        assert result == "success"
        assert call_count == 3
    
    def test_circuit_breaker_decorator(self):
        """Test circuit breaker decorator"""
        call_count = 0
        
        @circuit_breaker(failure_threshold=2, timeout=0.1)
        def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"
        
        # First two calls should fail
        for i in range(2):
            with pytest.raises(ValueError):
                decorated_func()
        
        # Third call should open circuit
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            decorated_func()
        
        assert call_count == 2
