# Anti-Bot Findings and Compliance Boundary

## Status

This project is a public-data crawler and analytics portfolio project. It must not implement or
recommend anti-bot bypasses. Earlier experiments showed that Dcard may return 403 responses,
CAPTCHA pages, or browser challenge pages for automated access. Those signals are treated as
stop conditions, not obstacles to bypass.

## Prohibited Approaches

- Browser fingerprint spoofing or stealth patches
- CAPTCHA, Turnstile, or reCAPTCHA bypass
- Saved-cookie, token, or browser-profile reuse for crawling
- Login automation or authentication bypass
- Proxy rotation or IP reputation evasion
- High-speed retry loops after 403, 429, CAPTCHA, or challenge pages

## Accepted Handling

- Check robots.txt before crawling
- Use public APIs, RSS feeds, sitemaps, and public pages only
- Apply conservative rate limits and request budgets
- Use Playwright only for public page rendering and endpoint discovery
- Stop or slow down on 403, 429, CAPTCHA, Cloudflare challenge, login wall, or robots disallow
- Log the reason for stopping so the dataset remains auditable

## Historical Note

Prior proof-of-concept scripts explored persistent browser profiles, saved cookies, and stealth
patches. Those scripts have been removed from the executable codebase because they conflict with
the project's compliance goals.
