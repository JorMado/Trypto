import asyncio
import time
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
import random

class CircuitBreakerOpen(Exception):
    pass

class MaxRetriesExceeded(Exception):
    pass
from functools import wraps

class RetryPolicy:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        circuit_timeout: int = 300,
        mock_mode: bool = False,
        mock_failure_rate: float = 0.2
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.circuit_timeout = circuit_timeout
        self.mock_mode = mock_mode
        self.mock_failure_rate = mock_failure_rate
        
        # Initialize internal state
        self._failure_counts = {}
        self._circuit_open_until = {}

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        endpoint = func.__qualname__
        
        if self.mock_mode:
            # Simulate occasional failures in mock mode
            if random.random() < self.mock_failure_rate:
                self._failure_counts[func.__name__] = self._failure_counts.get(func.__name__, 0) + 1
                raise ConnectionError("Simulated failure in mock mode")
            return await func(*args, **kwargs)

        if self._is_circuit_open(endpoint):
            raise CircuitBreakerOpen(f"Circuit breaker open for {endpoint}")

        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                self._reset_failures(endpoint)
                self._failure_counts[endpoint] = 0
                return result
            except Exception as e:
                if not self._should_retry(e):
                    raise
                await self._handle_failure(endpoint, attempt)
                self._failure_counts[endpoint] = self._failure_counts.get(endpoint, 0) + 1
                if self._failure_counts[endpoint] >= self.max_retries:
                    raise

        self._trip_circuit(endpoint)
        raise MaxRetriesExceeded(f"Max retries ({self.max_retries}) exceeded")

    def _should_retry(self, error: Exception) -> bool:
        retriable_errors = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            # Add specific API rate limit errors here
            # e.g., BinanceAPIException, 
        )
        return isinstance(error, retriable_errors)

    def _is_circuit_open(self, operation_name: str) -> bool:
        """Check if circuit breaker is open for given operation"""
        if operation_name not in self._circuit_open_until:
            return False
        
        if datetime.now() >= self._circuit_open_until[operation_name]:
            # Circuit timeout has expired, close the circuit
            del self._circuit_open_until[operation_name]
            self._failure_count[operation_name] = 0
            return False
            
        return True

    def _trip_circuit(self, endpoint: str):
        self._circuit_open_until[endpoint] = datetime.now() + timedelta(seconds=self.circuit_timeout)

    def _reset_failures(self, endpoint: str):
        if endpoint in self._failure_counts:
            del self._failure_counts[endpoint]

    def _handle_failure(self, endpoint: str, attempt: int):
        self._failure_counts[endpoint] = self._failure_counts.get(endpoint, 0) + 1
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        if self._failure_counts[endpoint] >= self.max_retries:
            self._trip_circuit(endpoint)
        return delay

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.execute(func, *args, **kwargs)
        return wrapper
