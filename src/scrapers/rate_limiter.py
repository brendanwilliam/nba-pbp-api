"""
Rate Limiter for Respectful NBA.com Scraping
Implements dynamic rate limiting with backoff strategies
"""

import time
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from enum import Enum

logger = logging.getLogger(__name__)


class BackoffStrategy(str, Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_second: float = 0.5  # Conservative default
    burst_limit: int = 3  # Max requests in burst
    burst_window_seconds: int = 10  # Burst window
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    max_backoff_seconds: int = 300  # 5 minutes max
    base_backoff_seconds: float = 1.0


@dataclass
class RequestRecord:
    """Record of a request for rate limiting"""
    timestamp: datetime
    was_rate_limited: bool = False
    response_code: Optional[int] = None


class RateLimiter:
    """
    Intelligent rate limiter with adaptive backoff for web scraping
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.lock = threading.Lock()
        
        # Request history tracking
        self.request_history: List[RequestRecord] = []
        self.last_request_time: Optional[datetime] = None
        
        # Backoff state
        self.consecutive_rate_limits = 0
        self.current_backoff_seconds = self.config.base_backoff_seconds
        self.in_backoff_until: Optional[datetime] = None
        
    def wait_if_needed(self) -> float:
        """
        Wait if necessary to respect rate limits
        Returns the actual wait time in seconds
        """
        with self.lock:
            now = datetime.now()
            wait_time = 0.0
            
            # Check if we're in a backoff period
            if self.in_backoff_until and now < self.in_backoff_until:
                backoff_wait = (self.in_backoff_until - now).total_seconds()
                logger.info(f"Waiting {backoff_wait:.1f}s due to rate limit backoff")
                time.sleep(backoff_wait)
                wait_time += backoff_wait
                self.in_backoff_until = None
            
            # Clean old request history
            self._clean_request_history()
            
            # Check burst limits
            recent_requests = self._get_recent_requests(self.config.burst_window_seconds)
            if len(recent_requests) >= self.config.burst_limit:
                burst_wait = self._calculate_burst_wait()
                if burst_wait > 0:
                    logger.debug(f"Waiting {burst_wait:.1f}s for burst limit")
                    time.sleep(burst_wait)
                    wait_time += burst_wait
            
            # Check standard rate limit
            if self.last_request_time:
                min_interval = 1.0 / self.config.requests_per_second
                time_since_last = (now - self.last_request_time).total_seconds()
                
                if time_since_last < min_interval:
                    rate_wait = min_interval - time_since_last
                    logger.debug(f"Waiting {rate_wait:.1f}s for rate limit")
                    time.sleep(rate_wait)
                    wait_time += rate_wait
            
            # Update last request time
            self.last_request_time = datetime.now()
            
            return wait_time
    
    def handle_rate_limit_response(self, response_code: int, retry_after: Optional[int] = None):
        """
        Handle a rate-limited response (429, etc.)
        
        Args:
            response_code: HTTP response code
            retry_after: Retry-After header value in seconds
        """
        with self.lock:
            now = datetime.now()
            
            # Record the rate-limited request
            self.request_history.append(RequestRecord(
                timestamp=now,
                was_rate_limited=True,
                response_code=response_code
            ))
            
            self.consecutive_rate_limits += 1
            
            # Calculate backoff time
            if retry_after:
                backoff_time = min(retry_after, self.config.max_backoff_seconds)
                logger.info(f"Server requested {retry_after}s retry delay, using {backoff_time}s")
            else:
                backoff_time = self._calculate_backoff_time()
                logger.info(f"Calculated backoff time: {backoff_time}s")
            
            # Set backoff period
            self.in_backoff_until = now + timedelta(seconds=backoff_time)
            
            # Adjust rate limit to be more conservative
            self._adjust_rate_limit_down()
            
            logger.warning(f"Rate limited (code {response_code}), backing off for {backoff_time}s "
                          f"(consecutive: {self.consecutive_rate_limits})")
    
    def handle_successful_response(self, response_code: int):
        """Handle a successful response"""
        with self.lock:
            # Record successful request
            self.request_history.append(RequestRecord(
                timestamp=datetime.now(),
                was_rate_limited=False,
                response_code=response_code
            ))
            
            # Reset consecutive rate limits on success
            if self.consecutive_rate_limits > 0:
                logger.info(f"Successful request after {self.consecutive_rate_limits} rate limits")
                self.consecutive_rate_limits = 0
                
                # Gradually increase rate limit back to normal
                self._adjust_rate_limit_up()
    
    def _calculate_backoff_time(self) -> float:
        """Calculate backoff time based on strategy"""
        if self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            backoff = self.config.base_backoff_seconds * (2 ** (self.consecutive_rate_limits - 1))
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            backoff = self.config.base_backoff_seconds * self.consecutive_rate_limits
        else:  # FIXED
            backoff = self.config.base_backoff_seconds
        
        return min(backoff, self.config.max_backoff_seconds)
    
    def _calculate_burst_wait(self) -> float:
        """Calculate wait time for burst limit"""
        recent_requests = self._get_recent_requests(self.config.burst_window_seconds)
        if len(recent_requests) < self.config.burst_limit:
            return 0.0
        
        # Wait until the oldest request in the window expires
        oldest_request = min(recent_requests, key=lambda r: r.timestamp)
        wait_until = oldest_request.timestamp + timedelta(seconds=self.config.burst_window_seconds)
        wait_time = (wait_until - datetime.now()).total_seconds()
        
        return max(0.0, wait_time)
    
    def _get_recent_requests(self, window_seconds: int) -> List[RequestRecord]:
        """Get requests within the specified time window"""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        return [r for r in self.request_history if r.timestamp > cutoff]
    
    def _clean_request_history(self):
        """Remove old requests from history to prevent memory bloat"""
        # Keep only requests from the last hour
        cutoff = datetime.now() - timedelta(hours=1)
        self.request_history = [r for r in self.request_history if r.timestamp > cutoff]
    
    def _adjust_rate_limit_down(self):
        """Make rate limiting more conservative after being rate limited"""
        # Reduce rate by 20% but don't go below 0.1 requests per second
        new_rate = max(0.1, self.config.requests_per_second * 0.8)
        if new_rate != self.config.requests_per_second:
            logger.info(f"Reducing rate limit from {self.config.requests_per_second:.2f} "
                       f"to {new_rate:.2f} requests/second")
            self.config.requests_per_second = new_rate
    
    def _adjust_rate_limit_up(self):
        """Gradually increase rate limit back towards original after successful requests"""
        # Only adjust if we've been rate limited before and rate is below 0.5
        if self.config.requests_per_second < 0.5:
            # Increase by 10% but don't exceed 0.5 requests per second
            new_rate = min(0.5, self.config.requests_per_second * 1.1)
            if new_rate != self.config.requests_per_second:
                logger.info(f"Increasing rate limit from {self.config.requests_per_second:.2f} "
                           f"to {new_rate:.2f} requests/second")
                self.config.requests_per_second = new_rate
    
    def get_rate_limit_stats(self) -> Dict[str, any]:
        """Get current rate limiting statistics"""
        with self.lock:
            recent_requests = self._get_recent_requests(300)  # Last 5 minutes
            rate_limited_count = sum(1 for r in recent_requests if r.was_rate_limited)
            
            return {
                'current_rate_per_second': self.config.requests_per_second,
                'consecutive_rate_limits': self.consecutive_rate_limits,
                'current_backoff_seconds': self.current_backoff_seconds,
                'in_backoff': self.in_backoff_until is not None and datetime.now() < self.in_backoff_until,
                'backoff_until': self.in_backoff_until.isoformat() if self.in_backoff_until else None,
                'recent_requests_5min': len(recent_requests),
                'recent_rate_limits_5min': rate_limited_count,
                'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None
            }
    
    def reset(self):
        """Reset rate limiter state"""
        with self.lock:
            self.request_history.clear()
            self.last_request_time = None
            self.consecutive_rate_limits = 0
            self.current_backoff_seconds = self.config.base_backoff_seconds
            self.in_backoff_until = None
            logger.info("Rate limiter state reset")


class GlobalRateLimiter:
    """
    Singleton rate limiter for use across multiple threads/processes
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config: Optional[RateLimitConfig] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = RateLimiter(config)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> RateLimiter:
        """Get the global rate limiter instance"""
        if cls._instance is None:
            cls._instance = RateLimiter()
        return cls._instance