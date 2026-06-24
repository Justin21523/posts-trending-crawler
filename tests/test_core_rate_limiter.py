"""Tests for domain rate limiter."""

import pytest

from dcard_crawler.core.errors import RateLimitedError, RequestBudgetExceededError
from dcard_crawler.core.rate_limiter import DomainRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_enforces_interval(monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("dcard_crawler.core.rate_limiter.asyncio.sleep", fake_sleep)
    limiter = DomainRateLimiter(requests_per_second=10, jitter_seconds=(0.0, 0.0))

    await limiter.wait("https://example.com/a")
    await limiter.wait("https://example.com/b")

    assert sleeps
    assert sleeps[0] > 0


@pytest.mark.asyncio
async def test_rate_limiter_budget_exceeded():
    limiter = DomainRateLimiter(
        requests_per_second=1000,
        jitter_seconds=(0.0, 0.0),
        request_budget=1,
    )

    await limiter.wait("https://example.com/a")
    with pytest.raises(RequestBudgetExceededError):
        await limiter.wait("https://example.com/b")


def test_rate_limiter_cooldown_blocks_domain():
    limiter = DomainRateLimiter(requests_per_second=1000, jitter_seconds=(0.0, 0.0))
    limiter.set_cooldown("https://example.com/a", seconds=60)

    with pytest.raises(RateLimitedError):
        import asyncio

        asyncio.run(limiter.wait("https://example.com/b"))
