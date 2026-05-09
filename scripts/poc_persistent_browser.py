"""Phase 2: Real browser with persistent context (cookies, cache)."""

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


async def test_persistent_context():
    """Use browser persistent context with real user data directory."""
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Persistent context directory - keeps cookies, cache, etc.
    user_data_dir = Path("data/browser_profile")
    user_data_dir.mkdir(parents=True, exist_ok=True)

    print("Launching browser with persistent context...")
    print(f"User data: {user_data_dir}")

    async with async_playwright() as p:
        # Use launch_persistent_context for real browser behavior
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            viewport={"width": 1280, "height": 900},
            accept_downloads=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        page = context.pages[0]

        print("\nNavigating to Dcard trending...")
        await page.goto(
            "https://www.dcard.tw/f/trending",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        # Wait and see what we get
        await page.wait_for_timeout(5000)

        # Get page title and some content
        title = await page.title()
        print(f"Page title: {title}")

        # Check if blocked
        body_text = await page.inner_text("body")
        if "blocked" in body_text.lower():
            print("\nWARNING: Still being blocked!")
            print("Body preview:")
            print(body_text[:500])
        else:
            print("\nSUCCESS: Page loaded!")
            print(f"Body length: {len(body_text)}")
            print(body_text[:1000])

            # Save full body text for analysis
            output_file = output_dir / "page_content_sample.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(body_text)
            print(f"\nFull content saved to {output_file}")

        await context.close()


async def main():
    await test_persistent_context()


if __name__ == "__main__":
    asyncio.run(main())
