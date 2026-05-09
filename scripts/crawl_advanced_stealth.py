"""Advanced stealth crawler with all anti-detection techniques.

This crawler integrates:
1. 12 stealth patches (webdriver, plugins, chrome, WebGL, canvas, etc.)
2. Persistent browser context (cookies, localStorage)
3. Human-like behavior simulation (mouse, keyboard, delays)
4. Fingerprint consistency (locale, timezone, viewport, UA)
5. CAPTCHA handling (manual or auto-detection)
6. Smart retry and error recovery
"""

import asyncio
import json
import random
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from dcard_crawler.clients.stealth import apply_stealth_to_context


class AdvancedStealthCrawler:
    """Production-grade crawler with comprehensive anti-detection.

    Usage:
        crawler = AdvancedStealthCrawler()
        await crawler.run(max_posts=10)
    """

    def __init__(
        self,
        user_data_dir: str = "data/browser_profile",
        output_dir: str = "data/raw",
    ):
        self.user_data_dir = Path(user_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.crawled_posts = []
        self.seen_post_ids = set()

    async def run(
        self,
        max_posts: int = 10,
        delay_range: tuple[float, float] = (3.0, 8.0),
        scroll_iterations: int = 12,
    ):
        """Full crawl workflow with all stealth techniques.

        Args:
            max_posts: Max posts to crawl
            delay_range: (min, max) seconds between actions
            scroll_iterations: Number of scroll actions on listing page
        """
        print("=" * 60)
        print("Advanced Stealth Crawler - All Anti-Detection Active")
        print("=" * 60)
        print(f"Target: {max_posts} posts from trending")
        print(f"Delay range: {delay_range}")
        print(f"Stealth patches: 12/12 enabled")
        print()

        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            # Use persistent context with realistic settings
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=False,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="zh-TW",
                timezone_id="Asia/Taipei",
                viewport={
                    "width": 1280 + random.randint(-50, 50),
                    "height": 720 + random.randint(-30, 30),
                },
                screen={"width": 1920, "height": 1080},
                color_scheme="light",
                reduced_motion="no-preference",
                device_scale_factor=1.0,
                has_touch=False,
                is_mobile=False,
                java_script_enabled=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--window-position=0,0",
                    "--ignore-certificate-errors",
                    "--ignore-certificate-errors-spki-list",
                    "--disable-extensions",
                    "--disable-popup-blocking",
                    "--disable-translate",
                    "--lang=zh-TW",
                ],
            )

            # Apply stealth patches to all pages
            await apply_stealth_to_context(context)

            page = context.pages[0]

            # Step 1: Warm up - visit homepage first
            print("Step 1: Warming up browser...")
            await self._human_visit(page, "https://www.dcard.tw", delay_range)

            # Step 2: Visit trending to collect post URLs
            print("\nStep 2: Collecting post URLs from trending...")
            post_urls = await self._collect_post_urls(
                page, max_posts, scroll_iterations, delay_range
            )

            if not post_urls:
                print("No post URLs collected. Aborting.")
                await context.close()
                return

            print(f"\nCollected {len(post_urls)} post URLs")

            # Step 3: Visit each post with human-like behavior
            print(f"\nStep 3: Crawling {len(post_urls)} posts...")
            await self._visit_posts(page, post_urls, delay_range)

            # Step 4: Save results
            self._save_results()

            await context.close()

    async def _human_visit(self, page, url: str, delay_range: tuple):
        """Visit a URL with human-like behavior.

        Args:
            page: Playwright page object
            url: URL to visit
            delay_range: (min, max) seconds for delays
        """
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Random reading time
        await page.wait_for_timeout(
            random.uniform(*delay_range) * 1000
        )

    async def _collect_post_urls(
        self,
        page,
        max_posts: int,
        scroll_iterations: int,
        delay_range: tuple,
    ) -> list[str]:
        """Navigate to trending and collect post URLs with human-like scrolling.

        Args:
            page: Playwright page object
            max_posts: Max posts to collect
            scroll_iterations: Number of scroll actions
            delay_range: Delay range between scrolls

        Returns:
            List of post URLs
        """
        await page.goto(
            "https://www.dcard.tw/f/trending",
            wait_until="networkidle",  # Wait for all network requests
            timeout=60000,
        )

        # Longer initial wait for SSR + JS rendering
        print("  Waiting for page to fully render...")
        await page.wait_for_timeout(8000)

        # Debug: check what's on the page
        page_title = await page.title()
        print(f"  Page title: {page_title}")

        all_links = set()
        for i in range(scroll_iterations):
            # Human-like scroll: random position, multiple steps
            scroll_y = random.randint(400, 800)
            steps = random.randint(5, 15)
            await page.mouse.wheel(0, scroll_y * (i + 1))
            await page.wait_for_timeout(
                random.uniform(*delay_range) * 1000
            )

            # Debug: check page content
            if i == 0:
                body_text = await page.inner_text("body")
                print(f"  Body text length: {len(body_text)}")

            # Extract links - use broader selectors
            links = await page.evaluate("""
                () => {
                    const links = new Set();
                    // Get ALL links that look like post URLs
                    const allAnchors = document.querySelectorAll('a[href]');
                    allAnchors.forEach(a => {
                        const href = a.getAttribute('href');
                        if (href && href.includes('/p/') && !href.includes('/c/')) {
                            // Ensure it's a post link, not a comment
                            const parts = href.split('/p/');
                            if (parts.length === 2 && parts[1].match(/^\\d/)) {
                                links.add(href);
                            }
                        }
                    });
                    return Array.from(links);
                }
            """)

            all_links.update(links)
            unique_count = len(all_links)
            print(
                f"  Scroll {i+1}/{scroll_iterations}: "
                f"{unique_count} unique links"
            )

            if unique_count >= max_posts:
                break

        # Deduplicate and format
        seen = set()
        unique_links = []
        for link in list(all_links):
            if link not in seen:
                seen.add(link)
                full_url = (
                    link if link.startswith("http")
                    else f"https://www.dcard.tw{link}"
                )
                unique_links.append(full_url)
                if len(unique_links) >= max_posts:
                    break

        return unique_links[:max_posts]

    async def _visit_posts(
        self, page, post_urls: list[str], delay_range: tuple
    ):
        """Visit each post with human-like behavior and extract content.

        Args:
            page: Playwright page object
            post_urls: List of URLs to visit
            delay_range: Delay range between actions
        """
        for idx, url in enumerate(post_urls, 1):
            post_id = url.split("/p/")[-1].split("/")[0]

            if post_id in self.seen_post_ids:
                print(f"  [{idx}/{len(post_urls)}] Skipping duplicate {post_id}")
                continue

            print(f"\n  [{idx}/{len(post_urls)}] {url}")

            try:
                # Human-like navigation to post
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=30000
                )

                # Check if blocked
                title = await page.title()
                if self._is_blocked(title):
                    print(f"    BLOCKED! Waiting 15s and retrying...")
                    await page.wait_for_timeout(15000)

                    # Try reload
                    await page.reload(wait_until="domcontentloaded")
                    await page.wait_for_timeout(5000)

                    title = await page.title()
                    if self._is_blocked(title):
                        print(f"    Still blocked. Skipping.")
                        continue

                # Wait for content to render
                await page.wait_for_timeout(
                    random.uniform(3, 6) * 1000
                )

                # Simulate reading behavior
                await self._simulate_reading(page, "body")

                # Extract post data
                post_data = await self._extract_post_data(page, post_id)

                if post_data and post_data.get("title"):
                    print(f"    Title: {post_data['title'][:50]}")
                    print(f"    Content: {len(post_data.get('content', ''))} chars")
                    print(f"    Forum: {post_data.get('forum_name', 'N/A')}")

                    post_data["crawled_at"] = datetime.now().isoformat()
                    post_data["crawl_source"] = "advanced_stealth"
                    self.crawled_posts.append(post_data)
                    self.seen_post_ids.add(post_id)

                    # Save individual post
                    post_file = self.output_dir / f"post_{post_id}.json"
                    with open(post_file, "w", encoding="utf-8") as f:
                        json.dump(post_data, f, ensure_ascii=False, indent=2)
                else:
                    print(f"    Could not extract valid data")

            except Exception as e:
                print(f"    ERROR: {e}")

            # Human-like delay between posts
            if idx < len(post_urls):
                delay = random.uniform(*delay_range)
                print(f"    Waiting {delay:.1f}s...")
                await page.wait_for_timeout(delay * 1000)

    def _is_blocked(self, title: str) -> bool:
        """Check if page is showing CAPTCHA or block message.

        Args:
            title: Page title

        Returns:
            True if blocked
        """
        block_indicators = [
            "稍候",
            "blocked",
            "captcha",
            "驗證",
            "security check",
        ]
        title_lower = title.lower()
        return any(ind in title_lower for ind in block_indicators)

    async def _simulate_reading(self, page, selector: str):
        """Simulate human reading behavior with random scrolling.

        Args:
            page: Playwright page object
            selector: Content selector to "read"
        """
        try:
            # Random small mouse movements
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y, steps=random.randint(10, 25))
                await page.wait_for_timeout(random.uniform(0.5, 2) * 1000)

            # Random scroll down a bit
            await page.mouse.wheel(0, random.randint(200, 600))
            await page.wait_for_timeout(random.uniform(1, 3) * 1000)

        except Exception:
            pass  # Ignore errors in simulation

    async def _extract_post_data(self, page, post_id: str) -> dict | None:
        """Extract post data with multiple fallback strategies.

        Args:
            page: Playwright page object
            post_id: Post ID for reference

        Returns:
            Dict with post data or None
        """
        try:
            # Strategy 1: Try API response monitoring
            # (We'll add network monitoring in next version)

            # Strategy 2: DOM extraction with multiple selectors
            post_data = await page.evaluate("""
                () => {
                    const result = {
                        post_id: '',
                        url: window.location.href,
                        title: '',
                        content: '',
                        excerpt: '',
                        created_at: '',
                        forum_name: '',
                        forum_alias: '',
                        author_school: '',
                        author_department: '',
                        topics: [],
                        like_count: 0,
                        comment_count: 0,
                    };

                    // Post ID from URL
                    const parts = window.location.pathname.split('/');
                    const pIdx = parts.indexOf('p');
                    if (pIdx >= 0 && pIdx < parts.length - 1) {
                        result.post_id = parts[pIdx + 1];
                    }

                    // Title - try multiple approaches
                    const h1 = document.querySelector('h1');
                    const ogTitle = document.querySelector('meta[property="og:title"]');
                    result.title = h1
                        ? h1.textContent.trim()
                        : ogTitle
                            ? ogTitle.getAttribute('content')
                            : document.title.replace(' | Dcard', '').trim();

                    // Content - comprehensive extraction
                    // Try specific Dcard content selectors
                    const contentSelectors = [
                        '[class*="PostContent"]',
                        '[class*="post-content"]',
                        '[class*="content_"]',
                        'article',
                        'main',
                    ];

                    for (const sel of contentSelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const text = el.textContent.trim();
                            if (text.length > 100) {
                                // Remove noise
                                result.content = text
                                    .replace(/Dcard\\s*/g, '')
                                    .replace(/\\s+/g, ' ')
                                    .trim();
                                break;
                            }
                        }
                    }

                    // Fallback: get main content area
                    if (!result.content) {
                        const main = document.querySelector('main');
                        if (main) {
                            // Remove navigation and footer noise
                            const clone = main.cloneNode(true);
                            const noise = clone.querySelectorAll(
                                'nav, header, footer, script, style, noscript'
                            );
                            noise.forEach(el => el.remove());
                            result.content = clone.textContent
                                .replace(/\\s+/g, ' ')
                                .trim()
                                .substring(0, 10000);
                        }
                    }

                    // Excerpt
                    if (result.content) {
                        result.excerpt = result.content.substring(0, 200);
                    }

                    // Forum info
                    const forumLinks = document.querySelectorAll('a[href*="/f/"]');
                    if (forumLinks.length > 0) {
                        result.forum_name = forumLinks[0].textContent.trim();
                        const href = forumLinks[0].getAttribute('href');
                        if (href) {
                            const m = href.match(/\\/f\\/([^/]+)/);
                            if (m) result.forum_alias = m[1];
                        }
                    }

                    // Time
                    const timeEl = document.querySelector('time');
                    if (timeEl) {
                        result.created_at = timeEl.getAttribute('datetime') || '';
                    }

                    // Author info
                    const schoolEl = document.querySelector(
                        '[class*="school"], [class*="School"]'
                    );
                    if (schoolEl) {
                        result.author_school = schoolEl.textContent.trim();
                    }

                    // Topics
                    const topicEls = document.querySelectorAll(
                        '[class*="Topic"], [class*="topic"], a[href*="/t/"]'
                    );
                    topicEls.forEach(el => {
                        const t = el.textContent.trim();
                        if (t && t.length < 50) {
                            result.topics.push(t);
                        }
                    });

                    return result;
                }
            """)

            return post_data

        except Exception as e:
            print(f"    Extraction error: {e}")
            return None

    def _save_results(self):
        """Save all crawled posts and summary."""
        # Save batch
        batch_file = self.output_dir / "crawled_posts_batch.json"
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump(self.crawled_posts, f, ensure_ascii=False, indent=2)

        # Save summary
        summary = {
            "total_crawled": len(self.crawled_posts),
            "total_seen": len(self.seen_post_ids),
            "crawled_at": datetime.now().isoformat(),
            "method": "advanced_stealth_12_patches",
            "post_ids": list(self.seen_post_ids),
        }
        summary_file = self.output_dir / "crawl_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'=' * 60}")
        print(
            f"Crawl complete! {len(self.crawled_posts)} posts extracted"
        )
        print(f"Batch file: {batch_file}")
        print(f"Summary: {summary_file}")
        print(f"{'=' * 60}")


async def main():
    crawler = AdvancedStealthCrawler()
    await crawler.run(
        max_posts=5,
        delay_range=(4.0, 10.0),
        scroll_iterations=12,
    )


if __name__ == "__main__":
    asyncio.run(main())
