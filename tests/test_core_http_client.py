"""Tests for shared crawler HTTP client policy wiring."""

import httpx
import pytest

from dcard_crawler.core.errors import RateLimitedError, RequestBudgetExceededError
from dcard_crawler.core.http_client import CrawlerHttpClient
from dcard_crawler.core.rate_limiter import DomainRateLimiter
from dcard_crawler.core.robots import RobotsChecker
from dcard_crawler.settings import settings


def allow_robots_checker() -> RobotsChecker:
    async def fetcher(url: str) -> str:
        return "User-agent: *\nDisallow:\n"

    return RobotsChecker(fetcher=fetcher)


@pytest.mark.asyncio
async def test_http_client_budget_exceeded_before_transport():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"ok": True})

    client = CrawlerHttpClient(
        rate_limiter=DomainRateLimiter(
            requests_per_second=1000,
            jitter_seconds=(0.0, 0.0),
            request_budget=1,
        ),
        robots_checker=allow_robots_checker(),
        transport=httpx.MockTransport(handler),
    )

    await client.get_json("https://example.com/a")
    with pytest.raises(RequestBudgetExceededError):
        await client.get_json("https://example.com/b")

    assert calls == 1
    await client.close()


@pytest.mark.asyncio
async def test_http_client_429_sets_domain_cooldown(monkeypatch):
    monkeypatch.setattr(settings.crawler, "cooldown_seconds_on_429", 300)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Too many requests")

    client = CrawlerHttpClient(
        rate_limiter=DomainRateLimiter(
            requests_per_second=1000,
            jitter_seconds=(0.0, 0.0),
        ),
        robots_checker=allow_robots_checker(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RateLimitedError):
        await client.request("GET", "https://example.com/a")
    with pytest.raises(RateLimitedError, match="cooling down"):
        await client.request("GET", "https://example.com/b")

    await client.close()
