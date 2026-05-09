"""Phase 2: Full crawler using persistent browser context."""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


class DcardPersistentCrawler:
    """Crawler using persistent browser context (cookies, cache) to bypass anti-bot."""

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
        delay_between_posts: float = 5.0,
        scroll_iterations: int = 10,
    ):
        """Full crawl workflow.

        Args:
            max_posts: Max posts to crawl
            delay_between_posts: Seconds between each post visit
            scroll_iterations: Number of scroll actions on listing page
        """
        print("=" * 60)
        print("Dcard Persistent Context Crawler")
        print("=" * 60)
        print(f"Target: {max_posts} posts from trending")
        print(f"Delay: {delay_between_posts}s between posts")

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=False,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="zh-TW",
                timezone_id="Asia/Taipei",
                viewport={"width": 1280, "height": 900},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )

            page = context.pages[0]

            # Step 1: Collect post links from trending page
            post_urls = await self._collect_post_urls(
                page, max_posts, scroll_iterations
            )

            if not post_urls:
                print("No post URLs collected. Aborting.")
                await context.close()
                return

            print(f"\nCollected {len(post_urls)} post URLs")

            # Step 2: Visit each post
            await self._visit_posts(page, post_urls, delay_between_posts)

            # Step 3: Save results
            self._save_results()

            await context.close()

    async def _collect_post_urls(
        self, page, max_posts: int, scroll_iterations: int
    ) -> list[str]:
        """Navigate to trending and collect post URLs."""
        print("\nStep 1: Collecting post URLs from trending...")
        await page.goto(
            "https://www.dcard.tw/f/trending",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.wait_for_timeout(5000)

        all_links = []
        for i in range(scroll_iterations):
            await page.mouse.wheel(0, 600 * (i + 1))
            await page.wait_for_timeout(2000)

            links = await page.evaluate("""
                () => {
                    const links = new Set();
                    const anchors = document.querySelectorAll('a[href*="/f/trending/p/"]');
                    anchors.forEach(a => {
                        const href = a.getAttribute('href');
                        if (href) links.add(href);
                    });
                    return Array.from(links);
                }
            """)

            all_links.extend(links)
            unique = list(set(all_links))
            print(
                f"  Scroll {i+1}/{scroll_iterations}: "
                f"{len(unique)} unique links"
            )

            if len(unique) >= max_posts:
                break

        # Deduplicate and limit
        seen = set()
        unique_links = []
        for link in set(all_links):
            if link not in seen:
                seen.add(link)
                unique_links.append(f"https://www.dcard.tw{link}")
                if len(unique_links) >= max_posts:
                    break

        return unique_links[:max_posts]

    async def _visit_posts(
        self, page, post_urls: list[str], delay: float
    ):
        """Visit each post and extract content."""
        print(f"\nStep 2: Visiting {len(post_urls)} posts...")

        for idx, url in enumerate(post_urls, 1):
            post_id = url.split("/p/")[-1].split("/")[0]

            if post_id in self.seen_post_ids:
                print(f"  [{idx}/{len(post_urls)}] Skipping duplicate {post_id}")
                continue

            print(f"  [{idx}/{len(post_urls)}] {url}")

            try:
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=30000
                )
                await page.wait_for_timeout(4000)

                # Check if blocked
                title = await page.title()
                if "blocked" in title.lower():
                    print(f"    BLOCKED! Waiting longer...")
                    await page.wait_for_timeout(10000)
                    continue

                # Extract post data
                post_data = await page.evaluate("""
                    () => {
                        const data = {
                            post_id: window.location.pathname.split('/p/')[1]?.split('/')[0] || '',
                            url: window.location.href,
                            title: '',
                            content: '',
                            excerpt: '',
                            created_at: '',
                            updated_at: '',
                            like_count: 0,
                            comment_count: 0,
                            forum_alias: '',
                            forum_name: '',
                            school: '',
                            department: '',
                            gender: '',
                            topics: [],
                            media_urls: [],
                        };

                        // Title
                        const h1 = document.querySelector('h1');
                        if (h1) data.title = h1.textContent.trim();

                        // Content - look for post content area
                        const selectors = [
                            '[class*="PostContent"]',
                            '[class*="post-content"]',
                            'article',
                            '[data-testid="post-content"]',
                        ];
                        for (const sel of selectors) {
                            const el = document.querySelector(sel);
                            if (el && el.textContent.trim().length > 20) {
                                data.content = el.textContent.trim();
                                break;
                            }
                        }

                        // Excerpt (first 200 chars of content)
                        if (data.content) {
                            data.excerpt = data.content.substring(0, 200);
                        }

                        // Forum info
                        const forumLink = document.querySelector('a[href*="/f/"]');
                        if (forumLink) {
                            data.forum_name = forumLink.textContent.trim();
                            const href = forumLink.getAttribute('href');
                            if (href) {
                                const match = href.match(/\\/f\\/([^/]+)/);
                                if (match) data.forum_alias = match[1];
                            }
                        }

                        // Timestamps
                        const timeEl = document.querySelector('time');
                        if (timeEl) {
                            data.created_at = timeEl.getAttribute('datetime') || '';
                        }

                        // Author info
                        const schoolEl = document.querySelector('[class*="school"]');
                        if (schoolEl) data.school = schoolEl.textContent.trim();

                        // Topics
                        const topicEls = document.querySelectorAll('[class*="Topic"]');
                        topicEls.forEach(el => {
                            data.topics.push(el.textContent.trim());
                        });

                        // Media URLs
                        const images = document.querySelectorAll('img[src*="dcard"]');
                        images.forEach(img => {
                            data.media_urls.push(img.getAttribute('src'));
                        });

                        return data;
                    }
                """)

                if post_data.get("title") and "blocked" not in post_data[
                    "title"
                ].lower():
                    print(f"    Title: {post_data['title'][:50]}")
                    print(f"    Content: {len(post_data.get('content', ''))} chars")
                    print(f"    Forum: {post_data.get('forum_name', 'N/A')}")

                    post_data["crawled_at"] = datetime.now().isoformat()
                    post_data["crawl_source"] = "persistent_browser"
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

            # Delay
            if idx < len(post_urls):
                await page.wait_for_timeout(delay * 1000)

    def _save_results(self):
        """Save all crawled posts to file."""
        # Save batch
        batch_file = self.output_dir / "crawled_posts_batch.json"
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump(self.crawled_posts, f, ensure_ascii=False, indent=2)

        # Save summary
        summary = {
            "total_crawled": len(self.crawled_posts),
            "crawled_at": datetime.now().isoformat(),
            "post_ids": [p.get("post_id") for p in self.crawled_posts],
        }
        summary_file = self.output_dir / "crawl_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'=' * 60}")
        print(f"Crawl complete! {len(self.crawled_posts)} posts saved")
        print(f"Batch file: {batch_file}")
        print(f"Summary: {summary_file}")
        print(f"{'=' * 60}")


async def main():
    crawler = DcardPersistentCrawler()
    await crawler.run(
        max_posts=5,
        delay_between_posts=5.0,
        scroll_iterations=8,
    )


if __name__ == "__main__":
    asyncio.run(main())
