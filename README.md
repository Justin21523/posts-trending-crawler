# Dcard Trending Crawler

A production-style crawler system for collecting public posts from Dcard's trending forum. Built with an API-first approach, using Playwright only as a fallback for endpoint discovery.

## Features

- **API-First Crawling**: Uses Dcard's public JSON API endpoints for efficient data collection
- **Browser Fallback**: Playwright-based endpoint discovery when API structure changes
- **Resume Support**: Checkpoint-based resume to continue from last successful position
- **Data Quality**: Validation layer for detecting empty content, duplicates, and malformed records
- **Rate Limiting**: Built-in throttling to avoid overwhelming the target server
- **Retry Logic**: Exponential backoff for handling transient failures
- **Structured Storage**: SQLite database with clean schema for PostgreSQL migration path
- **Export**: JSONL and CSV export for downstream NLP/analysis workflows

## Installation

```bash
# Install dependencies
pip install -e .

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

## Architecture

### Dual-Mode Design

**Mode A: API Crawler (Primary)**
- Uses `/forums/{alias}/posts` for listing
- Uses `/posts/{id}` for details
- Fast, efficient, production-ready

**Mode B: Browser-Assisted (Fallback)**
- Playwright monitors network requests
- Discovers actual API endpoints in use
- Extracts post data when API mode fails

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

Each post stores:
- `post_id`: Unique identifier
- `forum_alias`, `forum_name`: Forum information
- `title`, `excerpt`, `content`: Post content
- `created_at`, `updated_at`: Timestamps
- `like_count`, `comment_count`: Engagement metrics
- `topics`: Post topics/tags
- `media_meta`: Media attachments metadata
- `school`, `department`: Author info (if public)
- `anonymous_*`: Anonymity flags
- `url`: Post URL
- `crawl_source`: Source (api/browser)
- `crawled_at`: When the post was crawled
- `raw_json`: Original API response

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
- **No anti-captcha** or stealth mechanisms
- Built-in rate limiting to be respectful
- Follows Dcard's `robots.txt` guidelines

## License

For educational and research purposes only. Not affiliated with Dcard.
