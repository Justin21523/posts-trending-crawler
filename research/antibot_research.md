# Dcard Anti-Bot Research & Countermeasures

## Current Status (2026-04-07)

### Anti-Bot Layers Detected
1. **Cloudflare CAPTCHA** - Triggers on automated requests
2. **TLS Fingerprinting** - May detect non-browser TLS handshakes
3. **Browser Fingerprint** - Checks webdriver, plugins, WebGL, canvas
4. **Behavioral Analysis** - Detects non-human navigation patterns
5. **IP-based Blocking** - Your current IP may be flagged

### What Works
- ✅ **Persistent browser context** with existing cookies (verified: page loads successfully)
- ✅ **Manual CAPTCHA solving** followed by automated crawling
- ❌ Direct API requests (403/404)
- ❌ Headless browser (detected and blocked)
- ❌ Fresh browser session without cookies (CAPTCHA wall)

## Implemented Countermeasures

### 12 Stealth Patches (src/dcard_crawler/clients/stealth.py)
1. **webdriver flag** - Set to undefined
2. **plugins spoof** - Fake PDF plugins
3. **mimetypes spoof** - Fake mimeTypes array
4. **window.chrome** - Full chrome object spoof (app, runtime, loadTimes, csi)
5. **permissions fix** - Fix navigator.permissions.query
6. **WebGL spoof** - Return Intel Inc. vendor
7. **languages fix** - Set zh-TW, zh, en-US, en
8. **iframe isolation** - Prevent webdriver leak in iframes
9. **automation removal** - Delete navigator.__proto__.webdriver
10. **connection spoof** - Add fake navigator.connection
11. **hardware spoof** - Set hardwareConcurrency to 8
12. **canvas noise** - Randomize canvas fingerprint

### Browser Configuration
- Persistent context (cookies, localStorage survive restarts)
- Realistic viewport (1280x720 ± random)
- zh-TW locale, Asia/Taipei timezone
- Realistic Chrome 122 user-agent
- Anti-detection launch args (--disable-blink-features=AutomationControlled, etc.)

### Human Behavior Simulation
- Random delays between actions (4-10s)
- Human-like mouse movements (randomized steps)
- Scroll-based content loading
- Reading time simulation
- Randomized viewport positions

## Recommended Workflow

### Option A: Manual CAPTCHA + Automated Crawl (Current Best)
```bash
# 1. Solve CAPTCHA manually and save cookies
conda run -n data_env python scripts/solve_captcha_and_save_cookies.py

# 2. Run automated crawler using saved cookies
conda run -n data_env python scripts/crawl_advanced_stealth.py
```

### Option B: Use Existing Verified Profile
```bash
# If browser_profile already has valid cookies:
conda run -n data_env python scripts/crawl_advanced_stealth.py
```

### Option C: Network Change
If your IP is completely blocked by Cloudflare:
- Try a different network (mobile hotspot, different WiFi)
- Use a residential proxy
- Wait 24-48 hours for IP reputation to reset

## Future Improvements
1. **Proxy rotation** - Add residential proxy support
2. **Network interception** - Monitor API calls from browser
3. **Auto CAPTCHA solving** - Integrate 2Captcha/Anti-Captcha API
4. **Multiple profiles** - Rotate browser profiles
5. **Session management** - Save/load cookies per session

## Files
- `src/dcard_crawler/clients/stealth.py` - 12 stealth patches
- `scripts/crawl_advanced_stealth.py` - Full stealth crawler
- `scripts/solve_captcha_and_save_cookies.py` - CAPTCHA solver
- `scripts/crawl_manual_captcha.py` - Two-stage manual crawler
- `data/browser_profile/` - Persistent browser data
- `data/verified_cookies.json` - Saved cookies (after solving CAPTCHA)
