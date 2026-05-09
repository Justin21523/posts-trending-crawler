"""Utility: Solve CAPTCHA manually, then automated crawler uses the session.

Usage:
  python scripts/solve_captcha.py

This will:
  1. Open browser to Dcard trending (triggers CAPTCHA)
  2. Wait until you manually solve it and close the browser
  3. Re-open browser with same profile
  4. Automatically crawl 5 posts

If the browser is already verified (from a previous session),
it skips straight to crawling.
"""

import asyncio
import json
import signal
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from dcard_crawler.clients.stealth import apply_stealth_to_context


USER_DATA_DIR = "data/browser_profile"
OUTPUT_DIR = "data/raw"
READY_FLAG_FILE = "data/.captcha_ready"


async def wait_for_user_solve():
    """Open browser and wait for user to solve CAPTCHA."""
    print("=" * 60)
    print("Step 1: CAPTCHA Verification")
    print("=" * 60)
    print()
    print("Browser will open. Please:")
    print("  1. Solve the CAPTCHA/verification")
    print("  2. Wait until you see actual Dcard posts")
    print("  3. Close the browser window when ready")
    print()
    print("The script will auto-detect when you close the browser.")
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
                "--disable-dev-shm-usage",
            ],
        )

        page = context.pages[0]

        # Navigate to trigger CAPTCHA
        print("Opening Dcard trending...")
        try:
            await page.goto(
                "https://www.dcard.tw/f/trending",
                wait_until="domcontentloaded",
                timeout=60000,
            )
        except Exception as e:
            print(f"Navigation note: {e}")

        print("\nBrowser is open. Solve CAPTCHA now.")
        print("Close the browser window when you're ready.")
        print()

        # Wait for context to close (user closes browser)
        try:
            while True:
                await asyncio.sleep(0.5)
        except Exception:
            pass

    print("\nBrowser closed by user. Profile saved.")


async def crawl_posts(max_posts: int = 5, delay: float = 5.0):
    """Crawl posts using the verified browser profile."""
    print("\n" + "=" * 60)
    print("Step 2: Automated Crawl")
    print("=" * 60)
    print(f"Target: {max_posts} posts, delay: {delay}s")
    print()

    user_data_dir = Path(USER_DATA_DIR)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

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
                "--disable-dev-shm-usage",
            ],
        )

        # Apply stealth
        await apply_stealth_to_context(context)

        page = context.pages[0]

        # Check if still blocked
        print("Verifying session...")
        await page.goto(
            "https://www.dcard.tw/f/trending",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.wait_for_timeout(5000)

        title = await page.title()
        print(f"Page title: {title}")

        if "稍候" in title or "Cloudflare" in title:
            print("\nERROR: Still blocked! Please run Step 1 again.")
            await context.close()
            return

        print("Session verified. Starting crawl...\n")

        # Collect post URLs
        all_links = set()
        for i in range(10):
            await page.mouse.wheel(0, 600 * (i + 1))
            await page.wait_for_timeout(3000)

            links = await page.evaluate("""
                () => {
                    const links = new Set();
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.getAttribute('href');
                        if (href && href.includes('/p/')) {
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
            print(f"  Scroll {i+1}/10: {len(all_links)} links")
            if len(all_links) >= max_posts:
                break

        post_urls = [
            f"https://www.dcard.tw{link}" if not link.startswith("http") else link
            for link in list(all_links)[:max_posts]
        ]
        print(f"\nCollected {len(post_urls)} post URLs")

        # Crawl each post
        crawled = []
        for idx, url in enumerate(post_urls, 1):
            post_id = url.split("/p/")[-1].split("/")[0]
            print(f"\n  [{idx}/{len(post_urls)}] {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(4000)

                title = await page.title()
                if "稍候" in title:
                    print(f"    Blocked. Stopping.")
                    break

                data = await page.evaluate("""
                    () => {
                        const result = {
                            post_id: '',
                            url: window.location.href,
                            title: '',
                            content: '',
                            forum_name: '',
                            forum_alias: '',
                            created_at: '',
                        };

                        const parts = window.location.pathname.split('/');
                        const pIdx = parts.indexOf('p');
                        if (pIdx >= 0 && pIdx < parts.length - 1) {
                            result.post_id = parts[pIdx + 1];
                        }

                        const h1 = document.querySelector('h1');
                        result.title = h1
                            ? h1.textContent.trim()
                            : document.title.replace(' | Dcard', '').trim();

                        const main = document.querySelector('main');
                        if (main) {
                            const clone = main.cloneNode(true);
                            clone.querySelectorAll('nav,header,footer,script,style').forEach(e => e.remove());
                            result.content = clone.textContent.replace(/\\s+/g, ' ').trim().substring(0, 10000);
                        }

                        const fl = document.querySelector('a[href*="/f/"]');
                        if (fl) {
                            result.forum_name = fl.textContent.trim();
                            const m = fl.getAttribute('href')?.match(/\\/f\\/([^/]+)/);
                            if (m) result.forum_alias = m[1];
                        }

                        const t = document.querySelector('time');
                        if (t) result.created_at = t.getAttribute('datetime') || '';

                        return result;
                    }
                """)

                if data.get("title"):
                    print(f"    Title: {data['title'][:50]}")
                    print(f"    Content: {len(data.get('content', ''))} chars")

                    data["crawled_at"] = datetime.now().isoformat()
                    data["crawl_source"] = "stealth_after_captcha"
                    crawled.append(data)

                    post_file = output_dir / f"post_{post_id}.json"
                    with open(post_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"    ERROR: {e}")

            if idx < len(post_urls):
                await page.wait_for_timeout(delay * 1000)

        # Save
        batch = output_dir / "crawled_posts_batch.json"
        with open(batch, "w", encoding="utf-8") as f:
            json.dump(crawled, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}")
        print(f"Done! {len(crawled)}/{len(post_urls)} posts extracted")
        print(f"Results: {batch}")
        print(f"{'=' * 60}")

        await context.close()


async def main():
    print("=" * 60)
    print("Dcard Crawler - CAPTCHA + Stealth")
    print("=" * 60)
    print()

    # Step 1: User solves CAPTCHA
    await wait_for_user_solve()

    # Step 2: Automated crawl
    await crawl_posts(max_posts=5, delay=5.0)


if __name__ == "__main__":
    asyncio.run(main())
