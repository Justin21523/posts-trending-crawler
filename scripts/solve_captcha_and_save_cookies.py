"""Utility: Solve CAPTCHA manually and save cookies for automated crawling.

Usage:
  python scripts/solve_captcha_and_save_cookies.py

Workflow:
  1. Opens browser to Dcard (triggers CAPTCHA)
  2. You solve CAPTCHA manually
  3. When content is visible, press 's' key in terminal to save cookies
  4. Press 'q' to quit
  5. Future crawls will use saved cookies
"""

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


COOKIES_FILE = "data/verified_cookies.json"
USER_DATA_DIR = "data/browser_profile"


async def solve_and_save():
    """Open browser, let user solve CAPTCHA, save cookies."""
    print("=" * 60)
    print("CAPTCHA Solver & Cookie Saver")
    print("=" * 60)
    print()
    print("Opening browser...")
    print("1. Solve the CAPTCHA when it appears")
    print("2. Wait until you can see actual Dcard content")
    print("3. Type 's' and press ENTER to save cookies")
    print("4. Type 'q' and press ENTER to quit")
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

        # Navigate to trending
        print("Navigating to Dcard trending...")
        await page.goto(
            "https://www.dcard.tw/f/trending",
            wait_until="networkidle",
            timeout=60000,
        )

        # Wait for user input
        while True:
            title = await page.title()
            print(f"\nCurrent title: {title}")

            if "稍候" in title or "Cloudflare" in title:
                print("  -> Still on verification page. Solve CAPTCHA first.")
            else:
                print("  -> Looks like content is loaded!")

            user_input = input("\nCommand (s=save, q=quit, r=reload): ").strip().lower()

            if user_input == "s":
                # Save cookies
                cookies = await context.cookies()
                cookies_file = Path(COOKIES_FILE)
                cookies_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cookies_file, "w") as f:
                    json.dump(cookies, f, indent=2)
                print(f"\nSaved {len(cookies)} cookies to {cookies_file}")
                print("These cookies can be used for future automated crawls.")

            elif user_input == "r":
                await page.reload(wait_until="networkidle", timeout=60000)

            elif user_input == "q":
                print("Quitting...")
                break

        await context.close()


async def main():
    await solve_and_save()


if __name__ == "__main__":
    asyncio.run(main())
