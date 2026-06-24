"""Shared async HTTP client with policy and rate limiting."""

import time
from urllib.parse import urljoin

import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from dcard_crawler.core.errors import CrawlerError, PolicyBlockedError
from dcard_crawler.core.policy import CrawlPolicy
from dcard_crawler.core.rate_limiter import DomainRateLimiter
from dcard_crawler.core.robots import RobotsChecker
from dcard_crawler.settings import settings


class CrawlerHttpClient:
    """Async HTTP client that fails closed on access controls."""

    def __init__(
        self,
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
        rate_limiter: DomainRateLimiter | None = None,
        policy: CrawlPolicy | None = None,
        robots_checker: RobotsChecker | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url or ""
        self.headers = headers or self.default_headers()
        self.rate_limiter = rate_limiter or DomainRateLimiter(
            requests_per_second=settings.crawler.rate_limit_per_second,
            request_budget=settings.crawler.request_budget_per_job,
        )
        self.policy = policy or CrawlPolicy()
        self.robots_checker = robots_checker or RobotsChecker(
            enabled=settings.crawler.respect_robots_txt,
            unavailable_policy=settings.crawler.robots_unavailable_policy,
        )
        self.transport = transport
        self._client: httpx.AsyncClient | None = None

    @property
    def request_count(self) -> int:
        """Return total requests admitted by the rate limiter."""
        return self.rate_limiter.total_request_count

    @staticmethod
    def default_headers() -> dict[str, str]:
        """Return a transparent research user-agent."""
        return {
            "User-Agent": "dcard-trending-crawler/0.1 public-data-research",
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                verify=settings.ssl_verify,
                transport=self.transport,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError,)),
        reraise=True,
    )
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make a policy-checked request."""
        full_url = urljoin(f"{self.base_url}/", url.lstrip("/")) if self.base_url else url
        started_at = time.monotonic()
        status_code = None
        error_category = None
        try:
            await self.robots_checker.ensure_allowed(full_url, self.headers["User-Agent"])
            await self.rate_limiter.wait(full_url)
            client = await self._get_client()
            response = await client.request(method, full_url, **kwargs)
            status_code = response.status_code
            preview = response.text[:4096] if response.content else ""
            self.policy.raise_if_blocked(response.status_code, preview)

            if response.status_code >= 500:
                logger.warning(f"Server error {response.status_code} for {full_url}")
                response.raise_for_status()
            if response.status_code >= 400:
                raise CrawlerError(
                    f"HTTP {response.status_code} for {full_url}",
                    status_code=response.status_code,
                )
            return response
        except PolicyBlockedError as exc:
            error_category = exc.category.value
            if exc.status_code == 429:
                self.rate_limiter.set_cooldown(
                    full_url,
                    settings.crawler.cooldown_seconds_on_429,
                )
            raise
        except CrawlerError as exc:
            error_category = exc.category.value
            raise
        finally:
            elapsed_ms = round((time.monotonic() - started_at) * 1000, 2)
            logger.bind(
                method=method.upper(),
                url=full_url,
                status_code=status_code,
                elapsed_ms=elapsed_ms,
                error_category=error_category,
            ).info("crawler_request")

    async def get_json(self, url: str, **kwargs):
        """GET a URL and decode JSON."""
        response = await self.request("GET", url, **kwargs)
        return response.json()
