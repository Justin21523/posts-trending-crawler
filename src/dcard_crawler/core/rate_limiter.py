"""Async per-domain rate limiting and request budget management."""

import asyncio
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlparse

from dcard_crawler.core.errors import RateLimitedError, RequestBudgetExceededError


@dataclass
class DomainState:
    """Mutable request state for one domain."""

    last_request_at: float = 0.0
    request_count: int = 0
    cooldown_until: float = 0.0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class DomainRateLimiter:
    """Polite async limiter with per-domain budget and cooldown."""

    def __init__(
        self,
        requests_per_second: float = 1.0,
        jitter_seconds: tuple[float, float] = (0.0, 0.25),
        request_budget: int | None = None,
    ):
        self.requests_per_second = requests_per_second
        self.jitter_seconds = jitter_seconds
        self.request_budget = request_budget
        self._states: dict[str, DomainState] = defaultdict(DomainState)

    async def wait(self, url: str) -> None:
        """Wait until the domain may be requested."""
        domain = self.domain_for_url(url)
        state = self._states[domain]
        async with state.lock:
            now = time.monotonic()
            if state.cooldown_until > now:
                raise RateLimitedError(f"Domain is cooling down: {domain}")
            if self.request_budget is not None and state.request_count >= self.request_budget:
                raise RequestBudgetExceededError(f"Request budget exceeded for domain: {domain}")

            min_interval = 1.0 / self.requests_per_second if self.requests_per_second > 0 else 0
            elapsed = now - state.last_request_at
            wait_time = max(0.0, min_interval - elapsed)
            if self.jitter_seconds != (0.0, 0.0):
                wait_time += random.uniform(*self.jitter_seconds)
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            state.last_request_at = time.monotonic()
            state.request_count += 1

    def set_cooldown(self, url: str, seconds: float) -> None:
        """Set a cooldown for the domain."""
        domain = self.domain_for_url(url)
        self._states[domain].cooldown_until = time.monotonic() + seconds

    def request_count(self, url: str) -> int:
        """Return request count for a URL's domain."""
        return self._states[self.domain_for_url(url)].request_count

    @property
    def total_request_count(self) -> int:
        """Return total request count across all tracked domains."""
        return sum(state.request_count for state in self._states.values())

    @staticmethod
    def domain_for_url(url: str) -> str:
        """Extract normalized domain from a URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()
