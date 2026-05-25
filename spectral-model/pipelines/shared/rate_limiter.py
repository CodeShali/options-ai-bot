"""Token bucket rate limiter with per-domain support."""

import asyncio
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)


class TokenBucket:
    """Single token bucket for a domain."""

    def __init__(self, rate: float, capacity: float):
        """
        Args:
            rate: tokens added per second
            capacity: max tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        """Wait until tokens are available, then consume them."""
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
                self._last_refill = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return

                # Sleep until enough tokens accumulate
                deficit = tokens - self._tokens
                wait_time = deficit / self.rate
                logger.debug(f"Rate limiter: waiting {wait_time:.2f}s for tokens")
                await asyncio.sleep(wait_time)


class DomainRateLimiter:
    """Per-domain rate limiter using token buckets."""

    def __init__(self, default_rate: float = 1.0, default_capacity: float = 5.0):
        """
        Args:
            default_rate: requests per second (default rate for unknown domains)
            default_capacity: burst capacity
        """
        self._default_rate = default_rate
        self._default_capacity = default_capacity
        self._buckets: dict[str, TokenBucket] = {}
        self._domain_rates: dict[str, tuple[float, float]] = {}
        self._global_lock = asyncio.Lock()

    def set_domain_rate(self, domain: str, rate: float, capacity: float | None = None) -> None:
        """Configure rate for a specific domain."""
        if capacity is None:
            capacity = rate * 5  # 5 second burst by default
        self._domain_rates[domain] = (rate, capacity)

    def _get_bucket(self, domain: str) -> TokenBucket:
        if domain not in self._buckets:
            rate, capacity = self._domain_rates.get(
                domain, (self._default_rate, self._default_capacity)
            )
            self._buckets[domain] = TokenBucket(rate, capacity)
        return self._buckets[domain]

    async def acquire(self, domain: str, tokens: float = 1.0) -> None:
        """Acquire rate limit token for domain."""
        bucket = self._get_bucket(domain)
        await bucket.acquire(tokens)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# Global default rate limiter instance
_global_limiter = DomainRateLimiter(default_rate=1.0, default_capacity=5.0)

# Pre-configure common domains
_global_limiter.set_domain_rate("rfc-editor.org", 2.0, 10.0)
_global_limiter.set_domain_rate("nvlpubs.nist.gov", 0.5, 2.0)
_global_limiter.set_domain_rate("learn.microsoft.com", 1.0, 5.0)
_global_limiter.set_domain_rate("developer.okta.com", 1.0, 5.0)
_global_limiter.set_domain_rate("docs.aws.amazon.com", 1.0, 5.0)
_global_limiter.set_domain_rate("api.stackexchange.com", 0.5, 3.0)


def get_global_limiter() -> DomainRateLimiter:
    return _global_limiter
