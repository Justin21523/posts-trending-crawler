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
Dcard has active anti-bot protection. The previously documented API endpoints from community research (2023-2024) may have changed or may be blocked for automated requests from this environment.

## Next Steps Options

1. **Fail closed on 403/challenge pages**: Record the reason and stop instead of retrying aggressively.
2. **Use public endpoint discovery only**: Playwright may observe public page network requests, but must not use stealth, saved cookies, or login state.
3. **Prefer stable public sources where available**: Use RSS, sitemap, or official public endpoints for future multi-source connectors.
4. **Use cached/archived sample data only when it is lawful and public**: Keep samples small and reproducible.

## Files Generated
- `data/raw/poc_listing_sample.json` - Not generated (API blocked)
- `data/raw/poc_discovered_endpoints.json` - Empty (no endpoints found)
