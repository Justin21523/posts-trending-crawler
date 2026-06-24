# Dcard Trending Crawler

A production-style crawler system for collecting public posts from Dcard's trending forum. Built with an API-first approach, using Playwright only for public page rendering and endpoint discovery.

## Features

- **API-First Crawling**: Uses Dcard's public JSON API endpoints for efficient data collection
- **Browser Discovery**: Playwright-based endpoint discovery when API structure changes
- **Resume Support**: Checkpoint-based resume to continue from last successful position
- **Data Quality**: Validation layer for detecting empty content, duplicates, and malformed records
- **Rate Limiting**: Built-in throttling to avoid overwhelming the target server
- **Retry Logic**: Exponential backoff for handling transient failures
- **Structured Storage**: SQLite database with clean schema for PostgreSQL migration path
- **Export & Analytics**: JSONL/CSV export plus Excel reports for keyword, trend, engagement, and source analysis

## Installation

```bash
# Install dependencies
conda activate data_env
pip install -e ".[dev,analysis]"

# Install Playwright browsers
playwright install chromium
```

## Quick Start

```bash
# 1. Initialize database
dcard-crawler init

# 2. Discover API endpoints (optional, for verification)
dcard-crawler discover-endpoints

# 3. Crawl posts with full details
dcard-crawler crawl-posts --max-posts 100

# 4. Check status
dcard-crawler status

# 5. Export data
dcard-crawler export --format jsonl --output data/exports/posts.jsonl

# 6. Build an Excel analytics report
dcard-crawler analyze-excel \
  --input data/exports/posts.jsonl \
  --keywords configs/keywords.txt \
  --output data/exports/analysis_report.xlsx

# 7. Run a small live crawler verification
dcard-crawler verify-live-dcard --forum trending --max-posts 5

# 8. Serve the backend API for the React portfolio UI
dcard-crawler serve-api --host 127.0.0.1 --port 8000
```

## CLI Commands

### `init`
Initialize database and required directories.

```bash
dcard-crawler init
```

### `discover-endpoints`
Use Playwright to discover API endpoints by monitoring network traffic.

```bash
dcard-crawler discover-endpoints \
    --url https://www.dcard.tw/f/trending \
    --output research/discovered_endpoints.json
```

### `crawl-list`
Crawl post listing and store basic post data (no full content).

```bash
dcard-crawler crawl-list \
    --forum trending \
    --max-posts 500 \
    --resume
```

### `crawl-posts`
Crawl posts with full details (listing + detail API).

```bash
dcard-crawler crawl-posts \
    --forum trending \
    --max-posts 100 \
    --popular \
    --resume
```

### `status`
Show current crawl status and statistics.

```bash
dcard-crawler status
```

### `export`
Export crawled posts to JSONL or CSV format.

```bash
dcard-crawler export --format jsonl --limit 1000
dcard-crawler export --format csv --output posts.csv
```

### `analyze-excel`
Build a formatted Excel report from SQLite, CSV, JSONL, or XLSX input.

```bash
dcard-crawler analyze-excel \
    --input data/exports/posts.csv \
    --keywords configs/keywords.txt \
    --output data/exports/analysis_report.xlsx
```

The report includes:

- `Summary`
- `Raw Data`
- `Keyword Matches`
- `Daily Trend`
- `Top Posts`
- `Source Comparison`

### Analysis Commands
Run focused analysis outputs as CSV, JSONL, or XLSX.

```bash
dcard-crawler analyze-keywords \
    --input data/exports/posts.csv \
    --keywords configs/keywords.txt \
    --output data/exports/keyword_matches.csv

dcard-crawler analyze-trending \
    --input data/exports/posts.csv \
    --output data/exports/daily_trend.csv

dcard-crawler analyze-source-comparison \
    --input data/exports/posts.csv \
    --output data/exports/source_comparison.csv
```

### Live Verification
Run low-volume live smoke checks for crawler health. These commands write normal
`crawl_jobs` records plus a JSON report under `data/reports/crawl_runs/`.

```bash
dcard-crawler verify-live-dcard \
    --forum trending \
    --max-posts 5

dcard-crawler verify-live-ptt \
    --board Stock \
    --max-pages 1 \
    --max-posts 5

dcard-crawler verify-live-news-rss \
    --source-name cna-technology \
    --feed-url https://feeds.feedburner.com/rsscna/technology \
    --max-articles 5
```

Live verification is intentionally small and fail-closed. If a site returns
robots disallow, 403, 429, CAPTCHA, Cloudflare challenge, or login wall, the
run stops and records the reason instead of bypassing the control.

For PTT, robots.txt may be unavailable. The default remains fail-closed. For a
small public-board verification run, explicitly opt in:

```bash
dcard-crawler verify-live-ptt \
    --board Stock \
    --max-pages 1 \
    --max-posts 5 \
    --allow-robots-unavailable
```

For Dcard endpoint health checks, use diagnostics. This records status codes and
policy classifications without trying to bypass 403, 429, login walls, or
challenges.

```bash
dcard-crawler diagnose-dcard-endpoints --forum trending
```

### Backend API
Serve the FastAPI backend for a local React UI.

```bash
dcard-crawler serve-api --host 127.0.0.1 --port 8000
```

Useful endpoints:

- `GET /health`
- `GET /sources`
- `GET /posts?platform=ptt&keyword=AI&limit=50`
- `GET /crawl-jobs`
- `GET /reports`
- `POST /verify/dcard`
- `POST /verify/ptt`
- `POST /verify/news-rss`
- `POST /diagnostics/dcard`

## Architecture

### Dual-Mode Design

**Mode A: API Crawler (Primary)**
- Uses `/forums/{alias}/posts` for listing
- Uses `/posts/{id}` for details
- Fast, efficient, production-ready

**Mode B: Browser-Assisted Discovery**
- Playwright monitors network requests
- Discovers actual API endpoints in use
- Stops when pages require login, CAPTCHA, challenge pages, or other access controls

### Project Structure

```
dcard-trending-crawler/
├─ configs/                  # Configuration files
│  └─ crawler.yaml
├─ data/                     # Data storage
│  ├─ raw/
│  ├─ processed/
│  └─ exports/
├─ logs/                     # Log files
├─ research/                 # Research notes
├─ src/dcard_crawler/
│  ├─ clients/               # HTTP clients
│  │  ├─ api_client.py       # Async API client
│  │  └─ browser_client.py   # Playwright client
│  ├─ parsers/               # Data parsers
│  │  └─ post_parser.py
│  ├─ analysis/              # Pandas and Excel analytics
│  ├─ repositories/          # Data access layer
│  │  └─ post_repository.py
│  ├─ services/              # Business logic
│  │  ├─ checkpoint_service.py
│  │  ├─ ingest_service.py
│  │  └─ quality_service.py
│  ├─ cli.py                 # CLI entry point
│  ├─ database.py            # DB setup
│  ├─ logging_config.py      # Logging setup
│  ├─ models.py              # ORM models
│  ├─ schemas.py             # Pydantic schemas
│  └─ settings.py            # Settings
├─ tests/                    # Test files
└─ pyproject.toml
```

## Configuration

Edit `configs/crawler.yaml` to customize:

- Rate limits
- Batch sizes
- Retry settings
- Database URL
- Checkpoint file location

## Data Schema

The SQLite schema is designed for multiple public data platforms:

- `sources`: public data source metadata such as Dcard, PTT, RSS, or sitemap sources
- `crawl_jobs`: crawl run provenance, status, counts, and error messages
- `posts`: normalized public posts/articles keyed by `source_id + external_id`
- `post_metrics`: time-series engagement metrics captured for a post

`posts` keeps Dcard compatibility fields such as `post_id`, `forum_alias`,
`forum_name`, `topics`, and `media_meta`, while adding cross-platform fields such
as `platform`, `board_or_forum`, `canonical_url`, `published_at`, `content_hash`,
`view_count`, and `share_count`.

For local development, use `dcard-crawler init --reset` after schema changes to
recreate the SQLite database.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

## Important Notes

- This crawler only collects **public posts** from public forums
- **No comments** are collected
- **No login automation** or authentication bypass
- **No CAPTCHA, Turnstile, or reCAPTCHA bypass**
- **No stealth browser fingerprint spoofing**
- **No saved-cookie, token, or browser-profile reuse for crawling**
- **No proxy rotation or IP reputation evasion**
- **No scraping of robots.txt-disallowed paths**
- Built-in rate limiting to be respectful
- Live verification commands default to small request budgets and report data quality
- When a site returns 403, 429, CAPTCHA, Cloudflare challenge, login wall, or robots disallow,
  the crawler must stop, fail closed, or slow down. It must not attempt to bypass the block.

## License

For educational and research purposes only. Not affiliated with Dcard.
