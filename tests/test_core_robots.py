"""Tests for robots.txt guard."""

import pytest

from dcard_crawler.core.errors import RobotsDisallowedError
from dcard_crawler.core.robots import RobotsChecker


@pytest.mark.asyncio
async def test_robots_checker_allows_allowed_path():
    async def fetcher(url: str) -> str:
        return "User-agent: *\nDisallow: /private\n"

    checker = RobotsChecker(fetcher=fetcher)

    await checker.ensure_allowed("https://example.com/public", "test-agent")


@pytest.mark.asyncio
async def test_robots_checker_blocks_disallowed_path():
    async def fetcher(url: str) -> str:
        return "User-agent: *\nDisallow: /private\n"

    checker = RobotsChecker(fetcher=fetcher)

    with pytest.raises(RobotsDisallowedError):
        await checker.ensure_allowed("https://example.com/private/page", "test-agent")


@pytest.mark.asyncio
async def test_robots_checker_blocks_when_unavailable_by_policy():
    async def fetcher(url: str) -> str:
        raise RuntimeError("unavailable")

    checker = RobotsChecker(fetcher=fetcher, unavailable_policy="block")

    with pytest.raises(RobotsDisallowedError):
        await checker.ensure_allowed("https://example.com/public", "test-agent")


@pytest.mark.asyncio
async def test_robots_checker_allows_when_unavailable_policy_allows():
    async def fetcher(url: str) -> str:
        raise RuntimeError("unavailable")

    checker = RobotsChecker(fetcher=fetcher, unavailable_policy="allow")

    await checker.ensure_allowed("https://example.com/public", "test-agent")


@pytest.mark.asyncio
async def test_robots_checker_caches_per_domain():
    calls = []

    async def fetcher(url: str) -> str:
        calls.append(url)
        return "User-agent: *\nDisallow:\n"

    checker = RobotsChecker(fetcher=fetcher)

    await checker.ensure_allowed("https://example.com/a", "test-agent")
    await checker.ensure_allowed("https://example.com/b", "test-agent")

    assert calls == ["https://example.com/robots.txt"]
