"""Phase 1 PoC: Verify Dcard API connectivity."""

import asyncio
import json
import ssl
import sys
from pathlib import Path

import httpx


async def check_listing_api():
    """Test forum listing endpoint."""
    url = "https://api.dcard.tw/service/api/v2/forums/trending/posts"
    params = {"popular": "false", "limit": 5}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    # Skip SSL verify for self-signed cert environments
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    print(f"Testing listing API: {url}")
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(url, params=params, headers=headers)
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"  Posts received: {len(data)}")

            if data:
                first = data[0]
                print(f"\n  First post sample:")
                print(f"    ID: {first.get('id')}")
                print(f"    Title: {first.get('title', 'N/A')}")
                print(f"    Excerpt: {first.get('excerpt', 'N/A')[:80]}")
                print(f"    Created: {first.get('created_at')}")
                print(f"    Likes: {first.get('like_count')}")
                print(f"    Comments: {first.get('comment_count')}")
                print(f"    Keys: {list(first.keys())}")

                # Save sample
                output = Path("data/raw/poc_listing_sample.json")
                output.parent.mkdir(parents=True, exist_ok=True)
                with open(output, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"\n  Sample saved to {output}")

            return True
        else:
            print(f"  Error: {response.text[:200]}")
            return False


async def check_detail_api(post_id: int):
    """Test post detail endpoint."""
    url = f"https://api.dcard.tw/service/api/v2/posts/{post_id}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    print(f"\nTesting detail API: {url}")
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(url, headers=headers)
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"  Title: {data.get('title', 'N/A')}")
            print(f"  Content length: {len(data.get('content', ''))}")
            print(f"  Forum: {data.get('forum_alias')} / {data.get('forum_name')}")
            print(f"  Keys: {list(data.keys())}")

            # Save sample
            output = Path(f"data/raw/poc_detail_{post_id}.json")
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  Sample saved to {output}")

            return True
        else:
            print(f"  Error: {response.text[:200]}")
            return False


async def main():
    print("=" * 60)
    print("Dcard API PoC - Connectivity Test")
    print("=" * 60)

    # Test listing
    listing_ok = await check_listing_api()

    if listing_ok:
        # Get a post ID from the sample
        sample_file = Path("data/raw/poc_listing_sample.json")
        if sample_file.exists():
            with open(sample_file) as f:
                data = json.load(f)
            if data:
                post_id = data[0]["id"]
                await check_detail_api(post_id)

    print("\n" + "=" * 60)
    print("PoC Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
