"""Phase 2: Real browser crawling for Dcard trending posts."""

import asyncio
import json
import time
from pathlib import Path

from playwright.async_api import async_playwright


async def crawl_with_real_browser(
    max_posts: int = 10,
    delay_between_posts: float = 3.0,
):
    """Use real (non-headless) browser to slowly crawl Dcard posts one by one.

    This approach opens a real Chromium browser, navigates to each post page,
    and extracts content. It's slow but much more likely to bypass anti-bot.

    Args:
        max_posts: Number of posts to crawl
        delay_between_posts: Seconds to wait between each post
    """
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Launching real browser (non-headless)...")
    print(f"Will crawl up to {max_posts} posts with {delay_between_posts}s delay")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="zh-TW",
            timezone_id="Asia/Taipei",
        )

        # Step 1: Go to trending page and collect post IDs
        page = await context.new_page()
        post_ids = []
        post_links = []

        print("\nStep 1: Visiting trending page to collect post links...")
        await page.goto(
            "https://www.dcard.tw/f/trending",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        # Wait for content to load
        print("  Waiting for initial load...")
        await page.wait_for_timeout(5000)

        # Scroll to load more content
        print("  Scrolling to load more posts...")
        for i in range(10):
            await page.mouse.wheel(0, 600 * (i + 1))
            await page.wait_for_timeout(2000)

            # Extract links from page
            links = await page.evaluate("""
                () => {
                    const links = [];
                    // Look for post title links
                    const anchors = document.querySelectorAll('a[href*="/p/"]');
                    anchors.forEach(a => {
                        const href = a.getAttribute('href');
                        if (href && !links.includes(href)) {
                            links.push(href);
                        }
                    });
                    return links;
                }
            """)

            post_links.extend(links)
            print(f"    Found {len(post_links)} unique post links so far...")

            if len(post_links) >= max_posts:
                break

        # Deduplicate
        seen = set()
        unique_links = []
        for link in post_links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
                post_ids.append(link.split("/p/")[-1].split("/")[0])

        post_links = unique_links[:max_posts]
        print(f"\n  Total unique posts found: {len(post_links)}")

        # Save post links
        links_file = output_dir / "crawled_post_links.json"
        with open(links_file, "w", encoding="utf-8") as f:
            json.dump(post_links, f, ensure_ascii=False, indent=2)
        print(f"  Saved to {links_file}")

        # Step 2: Visit each post and extract content
        print(f"\nStep 2: Visiting each post to extract content...")
        crawled_posts = []

        for idx, link in enumerate(post_links, 1):
            url = f"https://www.dcard.tw{link}"
            print(f"\n  [{idx}/{len(post_links)}] {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                # Extract post content
                post_data = await page.evaluate("""
                    () => {
                        const data = {
                            url: window.location.href,
                            title: '',
                            content: '',
                            created_at: '',
                            like_count: 0,
                            comment_count: 0,
                            forum: '',
                        };

                        // Try to extract title
                        const h1 = document.querySelector('h1');
                        if (h1) data.title = h1.textContent.trim();

                        // Try to extract content
                        const contentDiv = document.querySelector('[class*="PostContent"]');
                        if (contentDiv) data.content = contentDiv.textContent.trim();

                        // Try to extract forum
                        const forumLink = document.querySelector('a[href*="/f/"]');
                        if (forumLink) data.forum = forumLink.textContent.trim();

                        // Try to extract metadata
                        const timeEl = document.querySelector('time');
                        if (timeEl) data.created_at = timeEl.getAttribute('datetime') || '';

                        return data;
                    }
                """)

                if post_data.get("title"):
                    print(f"    Title: {post_data['title'][:60]}")
                    print(f"    Content length: {len(post_data.get('content', ''))}")
                    print(f"    Forum: {post_data.get('forum', 'N/A')}")

                    crawled_posts.append(post_data)

                    # Save individual post
                    post_id = link.split("/p/")[-1].split("/")[0]
                    post_file = output_dir / f"post_{post_id}.json"
                    with open(post_file, "w", encoding="utf-8") as f:
                        json.dump(post_data, f, ensure_ascii=False, indent=2)
                else:
                    print(f"    WARNING: Could not extract data, may be blocked")

            except Exception as e:
                print(f"    ERROR: {e}")

            # Delay before next post
            if idx < len(post_links):
                print(f"    Waiting {delay_between_posts}s...")
                await page.wait_for_timeout(delay_between_posts * 1000)

        # Save all crawled posts
        output_file = output_dir / "crawled_posts_batch.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(crawled_posts, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}")
        print(f"Crawl complete! Successfully extracted {len(crawled_posts)} posts.")
        print(f"All posts saved to {output_file}")
        print(f"{'=' * 60}")

        await browser.close()


async def main():
    # Start with small batch to test
    await crawl_with_real_browser(max_posts=5, delay_between_posts=3.0)


if __name__ == "__main__":
    asyncio.run(main())
