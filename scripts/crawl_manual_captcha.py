"""Phase 2: Two-stage crawler - manual CAPTCHA then automated crawl.

Usage:
  Stage 1: python scripts/crawl_manual_captcha.py --setup
           Opens browser, solve CAPTCHA, close browser when done.
  Stage 2: python scripts/crawl_manual_captcha.py --crawl [--max-posts 10]
           Crawls posts using the verified browser profile.
"""

import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


USER_DATA_DIR = "data/browser_profile"
OUTPUT_DIR = "data/raw"


async def stage1_setup():
    """Open browser for manual CAPTCHA solving."""
    print("=" * 60)
    print("Stage 1: CAPTCHA Setup")
    print("=" * 60)
    print()
    print("Opening browser...")
    print("1. Navigate to a Dcard post")
    print("2. Solve the CAPTCHA manually")
    print("3. Verify the post content is visible")
    print("4. Close the browser window when done")
    print()

    user_data_dir = Path(USER_DATA_DIR)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        page = context.pages[0]
        await page.goto(
            "https://www.dcard.tw/f/trending/p/261251303",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print("Browser opened. Solve CAPTCHA and close window when ready.")

        # Wait for context to be closed (user closes browser)
        try:
            while True:
                await asyncio.sleep(1)
        except Exception:
            pass

    print("\nBrowser closed. Profile saved. Run --crawl to start crawling.")


async def stage2_crawl(max_posts: int = 5, delay: float = 5.0):
    """Crawl posts using previously verified browser profile."""
    print("=" * 60)
    print("Stage 2: Automated Crawl")
    print("=" * 60)
    print(f"Max posts: {max_posts}, Delay: {delay}s")

    user_data_dir = Path(USER_DATA_DIR)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not user_data_dir.exists():
        print("ERROR: No browser profile found. Run --setup first.")
        return

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        page = context.pages[0]
        crawled_posts = []

        # Collect posts from trending
        print("\nCollecting post URLs...")
        await page.goto(
            "https://www.dcard.tw/f/trending",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.wait_for_timeout(3000)

        # Check if blocked
        title = await page.title()
        print(f"Page title: {title}")
        if "稍候" in title:
            print("ERROR: Still on verification page. Run --setup again.")
            await context.close()
            return

        all_links = set()
        for i in range(10):
            await page.mouse.wheel(0, 600 * (i + 1))
            await page.wait_for_timeout(1500)

            links = await page.evaluate("""
                () => {
                    const links = new Set();
                    document.querySelectorAll('a[href*="/f/trending/p/"]')
                        .forEach(a => {
                            const href = a.getAttribute('href');
                            if (href) links.add(href);
                        });
                    return Array.from(links);
                }
            """)
            all_links.update(links)
            print(f"  Scroll {i+1}/10: {len(all_links)} unique links")
            if len(all_links) >= max_posts:
                break

        post_urls = [
            f"https://www.dcard.tw{link}"
            for link in list(all_links)[:max_posts]
        ]
        print(f"\nCollected {len(post_urls)} post URLs")

        # Crawl each post
        print("\nCrawling posts...")
        for idx, url in enumerate(post_urls, 1):
            post_id = url.split("/p/")[-1].split("/")[0]
            print(f"\n  [{idx}/{len(post_urls)}] {url}")

            try:
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=30000
                )
                await page.wait_for_timeout(4000)

                title = await page.title()
                if "稍候" in title:
                    print(f"    Blocked on verification. Stopping.")
                    break

                post_data = await page.evaluate("""
                    () => {
                        const result = {
                            post_id: '',
                            url: window.location.href,
                            title: '',
                            content: '',
                            created_at: '',
                            forum_name: '',
                            forum_alias: '',
                        };

                        // Post ID from URL
                        const parts = window.location.pathname.split('/');
                        const pIdx = parts.indexOf('p');
                        if (pIdx >= 0 && pIdx < parts.length - 1) {
                            result.post_id = parts[pIdx + 1];
                        }

                        // Title
                        const h1 = document.querySelector('h1');
                        result.title = h1
                            ? h1.textContent.trim()
                            : document.title.replace(' | Dcard', '').trim();

                        // Content - get all meaningful text
                        const body = document.querySelector('main')
                            || document.querySelector('body');
                        if (body) {
                            // Remove nav, header, footer noise
                            const noise = body.querySelectorAll(
                                'nav, header, footer, script, style, link'
                            );
                            noise.forEach(el => el.remove());
                            result.content = body.textContent
                                .replace(/\\s+/g, ' ')
                                .trim();
                        }

                        // Forum
                        const fLink = document.querySelector('a[href*="/f/"]');
                        if (fLink) {
                            result.forum_name = fLink.textContent.trim();
                            const href = fLink.getAttribute('href');
                            const m = href?.match(/\\/f\\/([^/]+)/);
                            if (m) result.forum_alias = m[1];
                        }

                        // Time
                        const t = document.querySelector('time');
                        if (t) result.created_at = t.getAttribute('datetime') || '';

                        return result;
                    }
                """)

                if post_data.get("title"):
                    print(f"    Title: {post_data['title'][:50]}")
                    print(f"    Content: {len(post_data.get('content', ''))} chars")

                    post_data["crawled_at"] = datetime.now().isoformat()
                    post_data["crawl_source"] = "persistent_browser"
                    crawled_posts.append(post_data)

                    post_file = output_dir / f"post_{post_id}.json"
                    with open(post_file, "w", encoding="utf-8") as f:
                        json.dump(post_data, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"    ERROR: {e}")

            if idx < len(post_urls):
                await page.wait_for_timeout(delay * 1000)

        # Save
        batch_file = output_dir / "crawled_posts_batch.json"
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump(crawled_posts, f, ensure_ascii=False, indent=2)

        summary = {
            "total_crawled": len(crawled_posts),
            "crawled_at": datetime.now().isoformat(),
            "method": "persistent_browser_2stage",
        }
        with open(output_dir / "crawl_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'=' * 60}")
        print(f"Done! {len(crawled_posts)}/{len(post_urls)} posts extracted")
        print(f"Results: {batch_file}")
        print(f"{'=' * 60}")

        await context.close()


async def main():
    parser = argparse.ArgumentParser(description="Dcard Manual CAPTCHA Crawler")
    parser.add_argument(
        "--setup", action="store_true",
        help="Stage 1: Open browser for manual CAPTCHA solving",
    )
    parser.add_argument(
        "--crawl", action="store_true",
        help="Stage 2: Crawl posts using verified profile",
    )
    parser.add_argument("--max-posts", type=int, default=5)
    parser.add_argument("--delay", type=float, default=5.0)
    args = parser.parse_args()

    if args.setup:
        await stage1_setup()
    elif args.crawl:
        await stage2_crawl(max_posts=args.max_posts, delay=args.delay)
    else:
        # Default: run both stages interactively
        print("No mode specified. Use --setup and --crawl.")
        print("Running setup mode by default...")
        await stage1_setup()


if __name__ == "__main__":
    asyncio.run(main())
