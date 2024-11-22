# rate_limiter.py
import time
import asyncio
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
from collections import defaultdict

@dataclass
class RateLimitConfig:
    max_calls: int
    period: float  # seconds
    burst_allowance: float = 1.0  # multiplier for burst capacity
    strategy: str = 'sliding_window'  # 'sliding_window', 'token_bucket', or 'leaky_bucket'

@dataclass
class RateLimit:
    calls: List[float]
    last_check: float
    tokens: float = 0.0  # for token bucket strategy
    last_token_update: float = 0.0  # for token bucket strategy

@dataclass
class TokenBucket:
    capacity: float
    rate: float
    tokens: float = 0.0
    last_update: float = time.time()

class RateLimiter:
    def __init__(self, 
                 config: Dict[str, RateLimitConfig] = None,
                 default_config: RateLimitConfig = None):
        """
        Initialize the rate limiter
        
        Args:
            config: Dictionary of rate limit configurations by route/endpoint
            default_config: Default configuration for unconfigured routes
        """
        self.config = config or {}
        self.default_config = default_config or RateLimitConfig(
            max_calls=60,
            period=60.0
        )
        self.limits = defaultdict(self._create_default_limit)
        self.lock = asyncio.Lock()
        
        # Setup logging
        self.logger = logging.getLogger('RateLimiter')
        self.logger.setLevel(logging.INFO)
        
        self.buckets = defaultdict(lambda: {
            'public': TokenBucket(capacity=100, rate=10),
            'private': TokenBucket(capacity=50, rate=5),
            'websocket': TokenBucket(capacity=200, rate=20)
        })
        
    def _create_default_limit(self) -> RateLimit:
        """Create a default rate limit instance"""
        return RateLimit(
            calls=[],
            last_check=time.time(),
            tokens=self.default_config.max_calls
        )
        
    async def acquire(self, route: str = 'default') -> Tuple[bool, float]:
        """
        Attempt to acquire a rate limit token
        
        Args:
            route: Route or endpoint identifier
            
        Returns:
            Tuple of (success, wait_time)
        """
        async with self.lock:
            config = self.config.get(route, self.default_config)
            limit = self.limits[route]
            
            if config.strategy == 'sliding_window':
                return await self._check_sliding_window(limit, config)
            elif config.strategy == 'token_bucket':
                return await self._check_token_bucket(limit, config)
            else:  # leaky bucket
                return await self._check_leaky_bucket(limit, config)
                
    async def _check_sliding_window(
        self,
        limit: RateLimit,
        config: RateLimitConfig
    ) -> Tuple[bool, float]:
        """
        Check rate limit using sliding window algorithm
        
        Args:
            limit: Current rate limit state
            config: Rate limit configuration
            
        Returns:
            Tuple of (success, wait_time)
        """
        current_time = time.time()
        window_start = current_time - config.period
        
        # Remove old calls
        limit.calls = [call for call in limit.calls if call > window_start]
        
        # Check if we're under the limit
        max_allowed = int(config.max_calls * config.burst_allowance)
        if len(limit.calls) < max_allowed:
            limit.calls.append(current_time)
            return True, 0.0
            
        # Calculate wait time
        if limit.calls:
            wait_time = limit.calls[0] + config.period - current_time
            return False, max(0, wait_time)
            
        return False, config.period
        
    async def _check_token_bucket(
        self,
        limit: RateLimit,
        config: RateLimitConfig
    ) -> Tuple[bool, float]:
        """
        Check rate limit using token bucket algorithm
        
        Args:
            limit: Current rate limit state
            config: Rate limit configuration
            
        Returns:
            Tuple of (success, wait_time)
        """
        current_time = time.time()
        time_passed = current_time - limit.last_token_update
        
        # Add new tokens based on time passed
        tokens_to_add = time_passed * (config.max_calls / config.period)
        limit.tokens = min(
            config.max_calls * config.burst_allowance,
            limit.tokens + tokens_to_add
        )
        limit.last_token_update = current_time
        
        if limit.tokens >= 1:
            limit.tokens -= 1
            return True, 0.0
            
        # Calculate wait time for next token
        wait_time = (1 - limit.tokens) / (config.max_calls / config.period)
        return False, wait_time
        
    async def _check_leaky_bucket(
        self,
        limit: RateLimit,
        config: RateLimitConfig
    ) -> Tuple[bool, float]:
        """
        Check rate limit using leaky bucket algorithm
        
        Args:
            limit: Current rate limit state
            config: Rate limit configuration
            
        Returns:
            Tuple of (success, wait_time)
        """
        current_time = time.time()
        time_passed = current_time - limit.last_check
        limit.last_check = current_time
        
        # Calculate leak
        leak_rate = config.max_calls / config.period
        leaked = time_passed * leak_rate
        limit.tokens = max(0, limit.tokens - leaked)
        
        if limit.tokens < config.max_calls * config.burst_allowance:
            limit.tokens += 1
            return True, 0.0
            
        # Calculate wait time
        wait_time = (limit.tokens - config.max_calls + 1) / leak_rate
        return False, wait_time
        
    async def wait_and_acquire(self, route: str = 'default') -> bool:
        """
        Wait for and acquire a rate limit token
        
        Args:
            route: Route or endpoint identifier
            
        Returns:
            True if acquired, False if timeout
        """
        success, wait_time = await self.acquire(route)
        if success:
            return True
            
        if wait_time > 0:
            try:
                await asyncio.sleep(wait_time)
                return await self.wait_and_acquire(route)
            except asyncio.CancelledError:
                return False
                
        return False
        
    def get_remaining_calls(self, route: str = 'default') -> int:
        """
        Get remaining calls allowed in current period
        
        Args:
            route: Route or endpoint identifier
            
        Returns:
            Number of remaining calls allowed
        """
        config = self.config.get(route, self.default_config)
        limit = self.limits[route]
        
        if config.strategy == 'sliding_window':
            current_time = time.time()
            window_start = current_time - config.period
            valid_calls = [call for call in limit.calls if call > window_start]
            max_allowed = int(config.max_calls * config.burst_allowance)
            return max(0, max_allowed - len(valid_calls))
            
        elif config.strategy == 'token_bucket':
            return int(limit.tokens)
            
        else:  # leaky bucket
            current_time = time.time()
            time_passed = current_time - limit.last_check
            leak_rate = config.max_calls / config.period
            tokens = max(0, limit.tokens - (time_passed * leak_rate))
            max_allowed = int(config.max_calls * config.burst_allowance)
            return max(0, max_allowed - int(tokens))
            
    def reset_limits(self, route: Optional[str] = None):
        """
        Reset rate limits
        
        Args:
            route: Optional route to reset, if None resets all routes
        """
        if route:
            self.limits[route] = self._create_default_limit()
        else:
            self.limits.clear()
            
    async def monitor_limits(self):
        """Monitor rate limits and log warnings when approaching limits"""
        while True:
            try:
                for route, limit in self.limits.items():
                    remaining = self.get_remaining_calls(route)
                    config = self.config.get(route, self.default_config)
                    
                    if remaining < config.max_calls * 0.2:  # Less than 20% remaining
                        self.logger.warning(
                            f"Rate limit warning for {route}: {remaining} calls remaining"
                        )
                        
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error monitoring rate limits: {str(e)}")
                await asyncio.sleep(1)

    async def acquire(self, exchange: str, api_type: str = 'public') -> bool:
        bucket = self.buckets[exchange][api_type]
        now = time.time()
        
        # Refill tokens
        elapsed = now - bucket.last_update
        new_tokens = elapsed * bucket.rate
        bucket.tokens = min(bucket.capacity, bucket.tokens + new_tokens)
        bucket.last_update = now
        
        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True
            
        return False

# Example usage:
RATE_LIMIT_CONFIG = {
    'exchange_api': RateLimitConfig(
        max_calls=100,
        period=60.0,
        burst_allowance=1.2,
        strategy='sliding_window'
    ),
    'blockchain_api': RateLimitConfig(
        max_calls=50,
        period=30.0,
        burst_allowance=1.1,
        strategy='token_bucket'
    ),
    'websocket': RateLimitConfig(
        max_calls=1000,
        period=60.0,
        burst_allowance=1.5,
        strategy='leaky_bucket'
    )
}