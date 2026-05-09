# Phase 1 PoC Results

## Date: 2026-04-07

## API Connectivity Tests

### Direct API Requests
| Endpoint | Status | Notes |
|---|---|---|
| `api.dcard.tw/service/api/v2/forums/trending/posts` | 404 | Domain not responding |
| `www.dcard.tw/service/api/v2/forums/trending/posts` | 403 | Blocked by anti-bot |
| `www.dcard.tw/service/api/v2/posts` | 403 | Blocked by anti-bot |

### Playwright Browser Test
- Headless Chromium: 0 endpoints discovered
- Dcard appears to detect and block headless browsers

### Conclusion
Dcard has active anti-bot protection. The previously documented API endpoints from community research (2023-2024) may have changed or now require additional headers/cookies.

## Next Steps Options

1. **Use non-headless browser**: Run Playwright with `headless=False` on a real display
2. **Add more browser fingerprinting**: Use playwright-stealth or add more realistic headers
3. **Check if access works from different network**: Current environment may be blocked by IP
4. **Manual investigation**: Visit Dcard trending in real browser, check DevTools Network tab for actual API calls
5. **Use cached/archived data**: If real-time crawling is blocked, use previously collected datasets

## Files Generated
- `data/raw/poc_listing_sample.json` - Not generated (API blocked)
- `data/raw/poc_discovered_endpoints.json` - Empty (no endpoints found)
