"""Robots.txt guard for compliant public crawling."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from loguru import logger

from dcard_crawler.core.errors import RobotsDisallowedError
from dcard_crawler.settings import settings

RobotsFetcher = Callable[[str], Awaitable[str]]


@dataclass
class RobotsRules:
    """Cached robots parser and availability state for one domain."""

    parser: RobotFileParser | None
    available: bool
    robots_url: str


class RobotsChecker:
    """Check robots.txt before requesting public pages."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        unavailable_policy: str = "block",
        fetcher: RobotsFetcher | None = None,
    ):
        self.enabled = enabled
        self.unavailable_policy = unavailable_policy
        self.fetcher = fetcher or self._fetch_robots
        self._cache: dict[str, RobotsRules] = {}

    async def ensure_allowed(self, url: str, user_agent: str) -> None:
        """Raise when robots.txt does not allow a URL."""
        if not self.enabled:
            return

        domain = self._domain(url)
        rules = await self._rules_for_domain(domain)
        if not rules.available:
            if self.unavailable_policy == "allow":
                logger.warning(f"robots.txt unavailable; allowing by policy: {rules.robots_url}")
                return
            raise RobotsDisallowedError(
                f"robots.txt unavailable and policy blocks crawling: {rules.robots_url}"
            )

        assert rules.parser is not None
        if not rules.parser.can_fetch(user_agent, url):
            raise RobotsDisallowedError(f"robots.txt disallows URL: {url}")

    async def _rules_for_domain(self, domain: str) -> RobotsRules:
        if domain in self._cache:
            return self._cache[domain]

        robots_url = urljoin(f"https://{domain}", "/robots.txt")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            text = await self.fetcher(robots_url)
            parser.parse(text.splitlines())
            rules = RobotsRules(parser=parser, available=True, robots_url=robots_url)
        except Exception as exc:
            logger.warning(f"Failed to fetch robots.txt {robots_url}: {exc}")
            rules = RobotsRules(parser=None, available=False, robots_url=robots_url)

        self._cache[domain] = rules
        return rules

    @staticmethod
    async def _fetch_robots(url: str) -> str:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            follow_redirects=True,
            verify=settings.ssl_verify,
        ) as client:
            response = await client.get(url, headers=RobotsChecker._headers())
            response.raise_for_status()
            return response.text

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"User-Agent": "dcard-trending-crawler/0.1 public-data-research"}

    @staticmethod
    def _domain(url: str) -> str:
        return urlparse(url).netloc.lower()
