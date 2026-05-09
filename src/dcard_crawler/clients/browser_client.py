"""Playwright-based browser client for endpoint discovery and fallback crawling."""


from loguru import logger
from playwright.async_api import Browser, BrowserContext, async_playwright

from dcard_crawler.schemas import DiscoveredEndpoint
from dcard_crawler.settings import settings


class BrowserClient:
    """Playwright browser client for network monitoring and fallback."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._discovered_endpoints: list[DiscoveredEndpoint] = []

    async def start(self):
        """Launch browser instance."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless
        )
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        logger.info("Browser started")

    async def close(self):
        """Close browser instance."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed")

    async def discover_endpoints(
        self,
        url: str,
        patterns: list[str] | None = None,
        scroll_steps: int = 5,
    ) -> list[DiscoveredEndpoint]:
        """Navigate to URL and monitor network requests for API endpoints.

        Args:
            url: The URL to visit
            patterns: URL patterns to look for in network requests
            scroll_steps: Number of scroll actions to perform

        Returns:
            List of discovered endpoints
        """
        if not patterns:
            patterns = settings.endpoints.browser_fallback

        self._discovered_endpoints = []
        page = await self._context.new_page()

        # Set up network monitoring
        async def _on_response(response):
            await self._handle_response(response, patterns)

        page.on("response", _on_response)

        logger.info(f"Navigating to {url}")
        await page.goto(url, wait_until="domcontentloaded")

        # Wait for initial content to load
        await page.wait_for_timeout(2000)

        # Scroll to trigger lazy loading
        for i in range(scroll_steps):
            logger.debug(f"Scroll step {i + 1}/{scroll_steps}")
            await page.mouse.wheel(0, 1000 * (i + 1))
            await page.wait_for_timeout(1000)

        # Wait for any pending network requests
        await page.wait_for_timeout(2000)

        await page.close()

        logger.info(f"Discovered {len(self._discovered_endpoints)} endpoints")
        return self._discovered_endpoints

    async def _handle_response(self, response, patterns: list[str]):
        """Process network response to identify API endpoints."""
        url = response.url
        status = response.status

        # Check if URL matches any pattern
        for pattern in patterns:
            if pattern in url:
                # Check if it's a JSON response
                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    try:
                        body = await response.json()
                        endpoint = DiscoveredEndpoint(
                            url_pattern=url.split("?")[0],
                            method="GET",
                            status=(
                                "active" if status == 200 else f"http_{status}"
                            ),
                            sample_response_keys=(
                                list(body.keys())
                                if isinstance(body, dict) else []
                            ),
                        )
                        self._discovered_endpoints.append(endpoint)
                        logger.info(f"Discovered endpoint: {endpoint.url_pattern}")
                    except Exception as e:
                        logger.debug(f"Failed to parse JSON from {url}: {e}")
                break

    async def extract_posts_from_page(
        self, forum_url: str, max_posts: int = 50
    ) -> list[dict]:
        """Navigate to forum and extract post data from network responses.

        Args:
            forum_url: The forum URL to visit
            max_posts: Maximum number of posts to collect

        Returns:
            List of post data extracted from network
        """
        posts_data = []
        page = await self._context.new_page()

        # Monitor for API responses containing post data
        async def _on_response(response):
            if "/service/api/v2/forums/" in response.url and "/posts" in response.url:
                try:
                    body = await response.json()
                    if isinstance(body, list):
                        posts_data.extend(body)
                except Exception:
                    pass

        page.on("response", _on_response)

        logger.info(f"Extracting posts from {forum_url}")
        await page.goto(forum_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Scroll to load more content
        scroll_count = 0
        while len(posts_data) < max_posts and scroll_count < 20:
            await page.mouse.wheel(0, 1000 * (scroll_count + 1))
            await page.wait_for_timeout(1000)
            scroll_count += 1

        await page.close()

        # Deduplicate and limit
        seen_ids = set()
        unique_posts = []
        for post in posts_data:
            post_id = post.get("id")
            if post_id and post_id not in seen_ids:
                seen_ids.add(post_id)
                unique_posts.append(post)
                if len(unique_posts) >= max_posts:
                    break

        logger.info(f"Extracted {len(unique_posts)} posts from browser")
        return unique_posts

    @property
    def discovered_endpoints(self) -> list[DiscoveredEndpoint]:
        return self._discovered_endpoints
