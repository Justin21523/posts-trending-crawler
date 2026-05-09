"""Phase 1 PoC: Use Playwright to discover Dcard API endpoints."""

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


async def discover_endpoints():
    """Navigate to Dcard trending and monitor network requests."""
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Launching real browser (non-headless)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )

        page = await context.new_page()
        endpoints_found = []

        async def on_response(response):
            url = response.url
            status = response.status
            content_type = response.headers.get("content-type", "")

            # Filter for API-like URLs
            if any(kw in url for kw in [
                "/service/api",
                "/api/v2",
                "/posts",
                "/forums",
            ]):
                info = {
                    "url": url,
                    "status": status,
                    "content_type": content_type,
                }

                if "json" in content_type:
                    try:
                        body = await response.json()
                        info["response_keys"] = (
                            list(body.keys())
                            if isinstance(body, dict)
                            else f"array[{len(body)}]"
                        )
                        info["sample"] = (
                            body[:2] if isinstance(body, list) else body
                        )
                    except Exception:
                        info["response_keys"] = "parse_failed"

                endpoints_found.append(info)
                print(f"  [{status}] {url}")
                if "response_keys" in info:
                    print(f"    Keys: {info['response_keys']}")

        page.on("response", on_response)

        print("Navigating to Dcard trending...")
        try:
            await page.goto(
                "https://www.dcard.tw/f/trending",
                wait_until="domcontentloaded",
                timeout=30000,
            )
        except Exception as e:
            print(f"Navigation error: {e}")

        # Wait for initial load
        print("Waiting for initial content load...")
        await page.wait_for_timeout(5000)

        # Scroll to trigger lazy loading
        for i in range(8):
            print(f"  Scroll step {i+1}/8...")
            await page.mouse.wheel(0, 800 * (i + 1))
            await page.wait_for_timeout(1500)

        # Wait for pending requests
        await page.wait_for_timeout(3000)

        # Save results
        output_file = output_dir / "poc_discovered_endpoints.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(endpoints_found, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print(f"Discovery complete. Found {len(endpoints_found)} endpoints.")
        print(f"Results saved to {output_file}")
        print(f"{'='*60}")

        # Print summary of working API endpoints
        working = [ep for ep in endpoints_found if ep["status"] == 200]
        if working:
            print("\nWorking endpoints (200 OK):")
            for ep in working:
                print(f"  {ep['url']}")
        else:
            print("\nNo working endpoints found. Dcard may block headless browsers.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(discover_endpoints())
