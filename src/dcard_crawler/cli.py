"""CLI entry point for Dcard Crawler."""

import asyncio
import csv
import json
from pathlib import Path

import typer

from dcard_crawler.clients.browser_client import BrowserClient
from dcard_crawler.connectors.base import ConnectorItem, ConnectorTarget
from dcard_crawler.connectors.dcard import DcardConnector
from dcard_crawler.core.errors import PolicyBlockedError
from dcard_crawler.core.http_client import CrawlerHttpClient
from dcard_crawler.core.rate_limiter import DomainRateLimiter
from dcard_crawler.database import init_db, is_current_schema
from dcard_crawler.services.checkpoint_service import CheckpointService
from dcard_crawler.services.factory import (
    build_ingest_service,
    build_news_ingest_service,
    build_ptt_ingest_service,
)
from dcard_crawler.settings import settings

app = typer.Typer(
    name="dcard-crawler",
    help="Dcard Trending Forum Crawler - Production-style post collection system",
    add_completion=False,
)

KEYWORD_OPTION = typer.Option(
    None,
    "--keyword",
    help="Inline keyword. Can be passed multiple times.",
)


def _require_current_schema() -> bool:
    """Return False and print a user-facing hint when DB schema is stale."""
    if is_current_schema():
        return True
    typer.echo("✗ Database schema is not initialized for the current models.")
    typer.echo("  For local/dev use, run: dcard-crawler init --reset")
    return False


async def _discover_endpoints_async(
    url: str,
    headless: bool,
    output: str | None,
) -> None:
    browser = BrowserClient(headless=headless)
    try:
        await browser.start()
        endpoints = await browser.discover_endpoints(url)

        if endpoints:
            typer.echo(f"\n✓ Discovered {len(endpoints)} endpoints:\n")
            for ep in endpoints:
                typer.echo(f"  URL: {ep.url_pattern}")
                typer.echo(f"  Status: {ep.status}")
                typer.echo(f"  Keys: {ep.sample_response_keys[:5]}")
                typer.echo()

            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    json.dump([ep.model_dump() for ep in endpoints], f, indent=2, default=str)
                typer.echo(f"✓ Endpoints saved to {output_path}")
        else:
            typer.echo("⚠ No endpoints discovered. Try running with --no-headless to debug.")
    finally:
        await browser.close()


def _run_dcard_crawl(
    *,
    forum: str,
    max_posts: int | None,
    popular: bool,
    fetch_details: bool,
    resume: bool,
    label: str,
) -> None:
    if not _require_current_schema():
        raise typer.Exit(1)

    typer.echo(f"Starting {label}: forum={forum} popular={popular} max_posts={max_posts}")

    async def _run():
        ingest_service = build_ingest_service()
        try:
            stats = await ingest_service.crawl_posts(
                forum_alias=forum,
                max_posts=max_posts,
                popular=popular,
                fetch_details=fetch_details,
                resume=resume,
            )

            typer.echo("\n✓ Crawl completed!")
            typer.echo(f"  Posts listed: {stats['posts_listed']}")
            if fetch_details:
                typer.echo(f"  Posts detailed: {stats['posts_detailed']}")
            typer.echo(f"  Posts stored: {stats['posts_stored']}")
            typer.echo(f"  Posts skipped: {stats['posts_skipped']}")
            typer.echo(f"  Errors: {stats['errors']}")
        finally:
            await ingest_service.close()

    asyncio.run(_run())


def _popular_from_mode(mode: str) -> bool:
    normalized = mode.lower()
    if normalized not in {"latest", "popular"}:
        raise typer.BadParameter("mode must be latest or popular")
    return normalized == "popular"


EXPORT_FIELDS = [
    "source",
    "platform",
    "external_id",
    "post_id",
    "forum_alias",
    "board_or_forum",
    "title",
    "excerpt",
    "content",
    "published_at",
    "created_at",
    "crawled_at",
    "like_count",
    "comment_count",
    "share_count",
    "view_count",
    "url",
    "canonical_url",
    "content_hash",
]


def _post_export_record(post, source_name: str) -> dict:
    return {
        "source": source_name,
        "platform": post.platform,
        "external_id": post.external_id,
        "post_id": post.post_id,
        "forum_alias": post.forum_alias,
        "board_or_forum": post.board_or_forum,
        "title": post.title,
        "excerpt": post.excerpt,
        "content": post.content,
        "published_at": post.published_at,
        "created_at": post.created_at,
        "crawled_at": post.crawled_at.isoformat() if post.crawled_at else None,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "share_count": post.share_count,
        "view_count": post.view_count,
        "url": post.url,
        "canonical_url": post.canonical_url,
        "content_hash": post.content_hash,
    }


@app.command()
def init(
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Drop and recreate all SQLite tables. Use only for local/dev databases.",
    ),
):
    """Initialize database and required directories."""
    if reset:
        typer.echo("Resetting database schema...")
    else:
        typer.echo("Initializing database...")
    init_db(reset=reset)

    # Ensure directories exist
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("research").mkdir(exist_ok=True)

    typer.echo("✓ Database initialized")
    typer.echo(f"✓ Database URL: {settings.database.url}")


@app.command("serve-api")
def serve_api(
    host: str = typer.Option("127.0.0.1", "--host", help="API bind host"),
    port: int = typer.Option(8000, "--port", help="API bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable uvicorn reload"),
):
    """Serve the FastAPI backend for the React portfolio UI."""
    import uvicorn

    uvicorn.run(
        "dcard_crawler.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def discover_endpoints(
    url: str = typer.Option(
        "https://www.dcard.tw/f/trending",
        "--url",
        "-u",
        help="URL to monitor for endpoint discovery",
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for discovered endpoints",
    ),
):
    """Use Playwright to discover API endpoints by monitoring network traffic."""
    typer.echo(f"Starting endpoint discovery on {url}")
    asyncio.run(_discover_endpoints_async(url, headless, output))


@app.command()
def discover_dcard_endpoints(
    forum: str = typer.Option(
        "trending",
        "--forum",
        "-f",
        help="Dcard forum alias to monitor",
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for discovered endpoints",
    ),
):
    """Discover public Dcard API endpoints by monitoring page network traffic."""
    url = f"https://www.dcard.tw/f/{forum}"
    typer.echo(f"Starting Dcard endpoint discovery on {url}")
    asyncio.run(_discover_endpoints_async(url, headless, output))


@app.command()
def verify_dcard_endpoints(
    forum: str = typer.Option(
        "trending",
        "--forum",
        "-f",
        help="Dcard forum alias to verify",
    ),
    post_id: int | None = typer.Option(
        None,
        "--post-id",
        help="Optional post ID for detail endpoint verification",
    ),
):
    """Verify Dcard public API endpoints with a tiny fail-closed request budget."""

    async def _run():
        http_client = CrawlerHttpClient(
            base_url=settings.dcard_api_base_url,
            rate_limiter=DomainRateLimiter(
                requests_per_second=settings.crawler.rate_limit_per_second,
                request_budget=2,
            ),
        )
        connector = DcardConnector(http_client=http_client)
        target = ConnectorTarget(url=f"https://www.dcard.tw/f/{forum}", label=forum)
        try:
            typer.echo(f"Checking listing endpoint for forum={forum}")
            items = await connector.fetch_listing(target=target, limit=1, mode="latest")
            typer.echo(f"✓ Listing endpoint returned {len(items)} item(s)")

            detail_id = post_id or (int(items[0].external_id) if items else None)
            if detail_id:
                typer.echo(f"Checking detail endpoint for post_id={detail_id}")
                detail = await connector.fetch_detail(
                    ConnectorItem(external_id=str(detail_id), raw={"id": detail_id})
                )
                if detail is None:
                    typer.echo("⚠ Detail endpoint returned no item")
                else:
                    typer.echo("✓ Detail endpoint returned an item")
        except PolicyBlockedError as exc:
            typer.echo(f"✗ Verification stopped by policy: {exc.category.value} {exc}")
            raise typer.Exit(1) from exc
        finally:
            await connector.close()

    asyncio.run(_run())


@app.command()
def crawl_list(
    forum: str = typer.Option(
        "trending",
        "--forum",
        "-f",
        help="Forum alias to crawl",
    ),
    max_posts: int | None = typer.Option(
        None,
        "--max-posts",
        "-m",
        help="Maximum number of posts to fetch",
    ),
    popular: bool = typer.Option(
        False,
        "--popular",
        "-p",
        help="Fetch popular posts instead of latest",
    ),
    resume: bool = typer.Option(
        True,
        "--resume/--no-resume",
        help="Resume from last checkpoint",
    ),
):
    """Crawl post listing and store basic post data."""
    _run_dcard_crawl(
        forum=forum,
        max_posts=max_posts,
        popular=popular,
        fetch_details=False,
        resume=resume,
        label="crawl list",
    )


@app.command()
def crawl_posts(
    forum: str = typer.Option(
        "trending",
        "--forum",
        "-f",
        help="Forum alias to crawl",
    ),
    max_posts: int | None = typer.Option(
        None,
        "--max-posts",
        "-m",
        help="Maximum number of posts to fetch",
    ),
    popular: bool = typer.Option(
        False,
        "--popular",
        "-p",
        help="Fetch popular posts instead of latest",
    ),
    resume: bool = typer.Option(
        True,
        "--resume/--no-resume",
        help="Resume from last checkpoint",
    ),
):
    """Crawl posts with full details (listing + detail API)."""
    _run_dcard_crawl(
        forum=forum,
        max_posts=max_posts,
        popular=popular,
        fetch_details=True,
        resume=resume,
        label="full post crawl",
    )


@app.command()
def crawl_dcard(
    forum: str = typer.Option(
        "trending",
        "--forum",
        "-f",
        help="Dcard forum alias to crawl",
    ),
    max_posts: int | None = typer.Option(
        None,
        "--max-posts",
        "-m",
        help="Maximum number of posts to fetch",
    ),
    mode: str = typer.Option(
        "latest",
        "--mode",
        help="Dcard listing mode: latest or popular",
    ),
    resume: bool = typer.Option(
        True,
        "--resume/--no-resume",
        help="Resume from last checkpoint",
    ),
):
    """Crawl Dcard posts with full details."""
    _run_dcard_crawl(
        forum=forum,
        max_posts=max_posts,
        popular=_popular_from_mode(mode),
        fetch_details=True,
        resume=resume,
        label="Dcard crawl",
    )


@app.command()
def crawl_dcard_list(
    forum: str = typer.Option(
        "trending",
        "--forum",
        "-f",
        help="Dcard forum alias to crawl",
    ),
    max_posts: int | None = typer.Option(
        None,
        "--max-posts",
        "-m",
        help="Maximum number of posts to fetch",
    ),
    mode: str = typer.Option(
        "latest",
        "--mode",
        help="Dcard listing mode: latest or popular",
    ),
    resume: bool = typer.Option(
        True,
        "--resume/--no-resume",
        help="Resume from last checkpoint",
    ),
):
    """Crawl Dcard post listing only."""
    _run_dcard_crawl(
        forum=forum,
        max_posts=max_posts,
        popular=_popular_from_mode(mode),
        fetch_details=False,
        resume=resume,
        label="Dcard listing crawl",
    )


@app.command()
def crawl_dcard_posts(
    forum: str = typer.Option(
        "trending",
        "--forum",
        "-f",
        help="Dcard forum alias to crawl",
    ),
    max_posts: int | None = typer.Option(
        None,
        "--max-posts",
        "-m",
        help="Maximum number of posts to fetch",
    ),
    mode: str = typer.Option(
        "latest",
        "--mode",
        help="Dcard listing mode: latest or popular",
    ),
    resume: bool = typer.Option(
        True,
        "--resume/--no-resume",
        help="Resume from last checkpoint",
    ),
):
    """Crawl Dcard posts with listing and detail APIs."""
    _run_dcard_crawl(
        forum=forum,
        max_posts=max_posts,
        popular=_popular_from_mode(mode),
        fetch_details=True,
        resume=resume,
        label="Dcard post crawl",
    )


@app.command()
def crawl_ptt(
    board: str = typer.Option(
        "Stock",
        "--board",
        "-b",
        help="PTT board name to crawl",
    ),
    max_pages: int = typer.Option(
        1,
        "--max-pages",
        help="Maximum listing pages to fetch",
    ),
    max_posts: int | None = typer.Option(
        20,
        "--max-posts",
        "-m",
        help="Maximum posts to store",
    ),
    allow_over18_public_confirm: bool = typer.Option(
        False,
        "--allow-over18-public-confirm",
        help="Use PTT public over18 confirmation flow for this session only",
    ),
    allow_robots_unavailable: bool = typer.Option(
        False,
        "--allow-robots-unavailable",
        help="Allow this PTT run when robots.txt is unavailable. Keeps low-volume limits.",
    ),
):
    """Crawl public PTT board articles."""
    if not _require_current_schema():
        raise typer.Exit(1)

    typer.echo(f"Starting PTT crawl: board={board} max_pages={max_pages} max_posts={max_posts}")

    async def _run():
        service = build_ptt_ingest_service(
            board=board,
            allow_over18_public_confirm=allow_over18_public_confirm,
            robots_unavailable_policy="allow" if allow_robots_unavailable else None,
        )
        try:
            target = service.connector.board_target(board)
            stats = await service.crawl_target(
                target,
                max_pages=max_pages,
                max_posts=max_posts,
                fetch_details=True,
                source_base_url="https://www.ptt.cc",
                robots_url="https://www.ptt.cc/robots.txt",
            )
            typer.echo("\n✓ PTT crawl completed!")
            typer.echo(f"  Items listed: {stats['items_listed']}")
            typer.echo(f"  Items detailed: {stats['items_detailed']}")
            typer.echo(f"  Items stored: {stats['items_stored']}")
            typer.echo(f"  Items skipped: {stats['items_skipped']}")
            typer.echo(f"  Errors: {stats['errors']}")
        finally:
            await service.close()

    asyncio.run(_run())


def _run_news_crawl(
    *,
    source_name: str,
    url: str,
    target_type: str,
    max_articles: int,
) -> None:
    if not _require_current_schema():
        raise typer.Exit(1)

    typer.echo(f"Starting news crawl: source={source_name} type={target_type} url={url}")

    async def _run():
        service = build_news_ingest_service(source_name=source_name)
        try:
            target = ConnectorTarget(
                url=url,
                label=source_name,
                metadata={"target_type": target_type},
            )
            stats = await service.crawl_target(
                target,
                max_pages=1,
                max_posts=max_articles,
                max_articles=max_articles,
                fetch_details=True,
                source_base_url=url,
            )
            typer.echo("\n✓ News crawl completed!")
            typer.echo(f"  Items listed: {stats['items_listed']}")
            typer.echo(f"  Items detailed: {stats['items_detailed']}")
            typer.echo(f"  Items stored: {stats['items_stored']}")
            typer.echo(f"  Items skipped: {stats['items_skipped']}")
            typer.echo(f"  Errors: {stats['errors']}")
        finally:
            await service.close()

    asyncio.run(_run())


@app.command()
def crawl_news_rss(
    source_name: str = typer.Option(..., "--source-name", help="News source name"),
    feed_url: str = typer.Option(..., "--feed-url", help="RSS or Atom feed URL"),
    max_articles: int = typer.Option(20, "--max-articles", help="Maximum articles to crawl"),
):
    """Crawl news articles from an RSS or Atom feed."""
    _run_news_crawl(
        source_name=source_name,
        url=feed_url,
        target_type="rss",
        max_articles=max_articles,
    )


@app.command()
def crawl_news_sitemap(
    source_name: str = typer.Option(..., "--source-name", help="News source name"),
    sitemap_url: str = typer.Option(..., "--sitemap-url", help="Sitemap XML URL"),
    max_articles: int = typer.Option(20, "--max-articles", help="Maximum article URLs to crawl"),
):
    """Crawl news articles from a sitemap URL list."""
    _run_news_crawl(
        source_name=source_name,
        url=sitemap_url,
        target_type="sitemap",
        max_articles=max_articles,
    )


@app.command()
def crawl_news_article(
    source_name: str = typer.Option(..., "--source-name", help="News source name"),
    url: str = typer.Option(..., "--url", help="Public article URL"),
):
    """Crawl one public news article URL."""
    _run_news_crawl(
        source_name=source_name,
        url=url,
        target_type="article",
        max_articles=1,
    )


def _print_verify_report(report: dict) -> None:
    """Print a concise verification summary."""
    stats = report["stats"]
    quality = report["quality"]
    typer.echo("\n✓ Live verification finished")
    typer.echo(f"  Platform: {report['platform']}")
    typer.echo(f"  Job ID: {report['job_id']}")
    typer.echo(f"  Status: {stats.get('status')}")
    typer.echo(f"  Requests: {stats.get('request_count', 0)}")
    typer.echo(f"  Stored: {stats.get('posts_stored', stats.get('items_stored', 0))}")
    typer.echo(f"  Skipped: {stats.get('posts_skipped', stats.get('items_skipped', 0))}")
    typer.echo(f"  Errors: {stats.get('errors', 0)}")
    typer.echo(f"  Quality: {quality['status']}")
    if quality.get("issues"):
        typer.echo(f"  Quality issues: {'; '.join(quality['issues'])}")
    if report.get("samples"):
        typer.echo("  Samples:")
        for sample in report["samples"][:3]:
            typer.echo(f"    - {sample['title']}")
    diagnostics = report.get("metadata", {}).get("dcard_diagnostics")
    if diagnostics:
        typer.echo(f"  Diagnostics: {diagnostics['report_path']}")
    typer.echo(f"  Report: {report['report_path']}")


def _print_dcard_diagnostics(report: dict) -> None:
    """Print a concise Dcard diagnostics summary."""
    typer.echo("\n✓ Dcard diagnostics finished")
    typer.echo(f"  Forum: {report['forum']}")
    typer.echo(f"  Endpoints checked: {report['summary']['endpoint_count']}")
    typer.echo(f"  Blocked endpoints: {report['summary']['blocked_count']}")
    for endpoint in report["endpoints"]:
        typer.echo(
            f"  - {endpoint['name']}: status={endpoint['status_code']} "
            f"category={endpoint['policy_category']} reason={endpoint['policy_reason']}"
        )
    typer.echo(f"  Report: {report['report_path']}")


@app.command("diagnose-dcard-endpoints")
def diagnose_dcard_endpoints(
    forum: str = typer.Option("trending", "--forum", "-f", help="Dcard forum alias"),
    sample_post_id: int | None = typer.Option(
        None,
        "--sample-post-id",
        help="Optional Dcard post ID for detail endpoint diagnostics",
    ),
):
    """Diagnose Dcard public page/API endpoint status without bypassing blocks."""
    from dcard_crawler.services.dcard_diagnostics import DcardEndpointDiagnosticsService

    async def _run():
        service = DcardEndpointDiagnosticsService()
        report = await service.diagnose(forum=forum, sample_post_id=sample_post_id)
        _print_dcard_diagnostics(report)

    asyncio.run(_run())


@app.command("verify-live-dcard")
def verify_live_dcard(
    forum: str = typer.Option("trending", "--forum", "-f", help="Dcard forum alias"),
    mode: str = typer.Option(
        "latest",
        "--mode",
        help="Crawl mode: latest or popular",
    ),
    max_posts: int = typer.Option(
        5,
        "--max-posts",
        "-m",
        min=1,
        max=10,
        help="Maximum posts for live verification",
    ),
):
    """Run a low-volume live Dcard crawl verification."""
    from dcard_crawler.services.live_verification import LiveVerificationService

    if not _require_current_schema():
        raise typer.Exit(1)

    async def _run():
        verifier = LiveVerificationService()
        report = await verifier.verify_dcard(
            build_ingest_service(),
            forum=forum,
            max_posts=max_posts,
            popular=_popular_from_mode(mode),
        )
        _print_verify_report(report)

    asyncio.run(_run())


@app.command("verify-live-ptt")
def verify_live_ptt(
    board: str = typer.Option("Stock", "--board", "-b", help="PTT board name"),
    max_pages: int = typer.Option(
        1,
        "--max-pages",
        min=1,
        max=2,
        help="Maximum listing pages for live verification",
    ),
    max_posts: int = typer.Option(
        5,
        "--max-posts",
        "-m",
        min=1,
        max=10,
        help="Maximum posts for live verification",
    ),
    allow_over18_public_confirm: bool = typer.Option(
        False,
        "--allow-over18-public-confirm",
        help="Use PTT public over18 confirmation flow for this session only",
    ),
    allow_robots_unavailable: bool = typer.Option(
        False,
        "--allow-robots-unavailable",
        help="Allow this PTT verify run when robots.txt is unavailable.",
    ),
):
    """Run a low-volume live PTT crawl verification."""
    from dcard_crawler.services.live_verification import LiveVerificationService

    if not _require_current_schema():
        raise typer.Exit(1)

    async def _run():
        service = build_ptt_ingest_service(
            board=board,
            allow_over18_public_confirm=allow_over18_public_confirm,
            robots_unavailable_policy="allow" if allow_robots_unavailable else None,
        )
        verifier = LiveVerificationService()
        report = await verifier.verify_connector(
            service,
            platform="ptt",
            source_name="ptt",
            target=service.connector.board_target(board),
            max_pages=max_pages,
            max_posts=max_posts,
            source_base_url="https://www.ptt.cc",
            robots_url="https://www.ptt.cc/robots.txt",
            metadata={
                "robots_unavailable_policy_override": allow_robots_unavailable,
                "robots_unavailable_policy": "allow" if allow_robots_unavailable else "block",
            },
        )
        _print_verify_report(report)

    asyncio.run(_run())


@app.command("verify-live-news-rss")
def verify_live_news_rss(
    source_name: str = typer.Option(
        "cna-technology",
        "--source-name",
        help="News source name",
    ),
    feed_url: str = typer.Option(
        "https://feeds.feedburner.com/rsscna/technology",
        "--feed-url",
        help="RSS or Atom feed URL",
    ),
    max_articles: int = typer.Option(
        5,
        "--max-articles",
        min=1,
        max=10,
        help="Maximum articles for live verification",
    ),
):
    """Run a low-volume live News RSS crawl verification."""
    from dcard_crawler.services.live_verification import LiveVerificationService

    if not _require_current_schema():
        raise typer.Exit(1)

    async def _run():
        service = build_news_ingest_service(source_name=source_name)
        target = ConnectorTarget(
            url=feed_url,
            label=source_name,
            metadata={"target_type": "rss"},
        )
        verifier = LiveVerificationService()
        report = await verifier.verify_connector(
            service,
            platform="news",
            source_name=source_name,
            target=target,
            max_pages=1,
            max_posts=max_articles,
            max_articles=max_articles,
            source_base_url=feed_url,
        )
        _print_verify_report(report)

    asyncio.run(_run())


@app.command()
def status(
    forum: str = typer.Option(
        "trending",
        "--forum",
        "-f",
        help="Forum alias for checkpoint status",
    ),
):
    """Show current crawl status and statistics."""
    from sqlalchemy import func, select

    from dcard_crawler.database import get_session
    from dcard_crawler.models import CrawlJob, Post, Source

    typer.echo("Crawl Status\n")

    if not _require_current_schema():
        return

    # Database stats
    with get_session() as session:
        total_posts = session.execute(select(func.count(Post.id))).scalar()
        if total_posts:
            typer.echo(f"  Total posts in database: {total_posts}")

            # Get date range
            from sqlalchemy import func as sql_func
            min_created = session.execute(select(sql_func.min(Post.created_at))).scalar()
            max_created = session.execute(select(sql_func.max(Post.created_at))).scalar()

            if min_created and max_created:
                typer.echo(f"  Date range: {min_created} to {max_created}")

            source_rows = session.execute(
                select(Source.name, Post.platform, func.count(Post.id))
                .join(Source, Source.id == Post.source_id)
                .group_by(Source.name, Post.platform)
                .order_by(Source.name, Post.platform)
            ).all()
            if source_rows:
                typer.echo("\n  Sources:")
                for source_name, platform, count in source_rows:
                    typer.echo(f"    {source_name} / {platform}: {count}")
        else:
            typer.echo("  No posts in database yet.")

        jobs = session.execute(
            select(CrawlJob, Source.name)
            .join(Source, Source.id == CrawlJob.source_id)
            .order_by(CrawlJob.started_at.desc())
            .limit(5)
        ).all()
        if jobs:
            typer.echo("\n  Recent crawl jobs:")
            for job, source_name in jobs:
                finished = job.finished_at.isoformat() if job.finished_at else "-"
                error = f" error={job.error_category}" if job.error_category else ""
                reason = f" reason={job.error_reason}" if job.error_reason else ""
                typer.echo(
                    f"    #{job.id} {source_name} {job.status} "
                    f"requests={job.request_count} items={job.item_count} "
                    f"finished={finished}{error}{reason}"
                )

    report_paths = sorted(
        Path("data/reports").glob("*/*.json"),
        key=lambda path: path.stat().st_mtime,
    )
    if report_paths:
        typer.echo("\n  Recent reports:")
        for report_path in report_paths[-5:]:
            typer.echo(f"    {report_path}")

    # Checkpoint status
    checkpoint_service = CheckpointService()
    checkpoint = checkpoint_service.load(forum)

    if checkpoint:
        typer.echo(f"\n  Checkpoint ({forum}):")
        typer.echo(f"    Last post ID: {checkpoint.last_post_id}")
        typer.echo(f"    Total fetched: {checkpoint.total_fetched}")
        typer.echo(f"    Last success: {checkpoint.last_success_at}")
    else:
        typer.echo("\n  No checkpoint found.")


@app.command()
def export(
    format: str = typer.Option(
        "jsonl",
        "--format",
        "-F",
        help="Export format: jsonl or csv",
    ),
    output: str = typer.Option(
        "data/exports/posts.{format}",
        "--output",
        "-o",
        help="Output file path",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-l",
        help="Maximum number of posts to export",
    ),
):
    """Export crawled posts to JSONL or CSV format."""
    from sqlalchemy import select

    from dcard_crawler.database import get_session
    from dcard_crawler.models import Post, Source

    if not _require_current_schema():
        raise typer.Exit(1)

    output = output.replace("{format}", format)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Exporting posts to {output_path} (format={format}, limit={limit})")

    with get_session() as session:
        query = select(Post, Source.name).join(Source, Source.id == Post.source_id).order_by(
            Post.crawled_at.desc()
        )
        if limit:
            query = query.limit(limit)

        rows = session.execute(query).all()

        if not rows:
            typer.echo("⚠ No posts to export")
            return

        typer.echo(f"Exporting {len(rows)} posts...")

        if format == "jsonl":
            with open(output_path, "w", encoding="utf-8") as f:
                for post, source_name in rows:
                    record = _post_export_record(post, source_name)
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        elif format == "csv":
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=EXPORT_FIELDS)
                writer.writeheader()
                for post, source_name in rows:
                    writer.writerow(_post_export_record(post, source_name))
        else:
            typer.echo(f"✗ Unsupported format: {format}")
            raise typer.Exit(1)

    typer.echo(f"✓ Exported to {output_path}")


def _write_analysis_output(rows, output: str, default_format: str = "csv") -> Path:
    """Write an analysis DataFrame to CSV, JSONL, or XLSX."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = output_path.suffix.lower()
    if suffix == ".jsonl":
        rows.to_json(output_path, orient="records", lines=True, force_ascii=False)
    elif suffix in {".xlsx", ".xls"}:
        rows.to_excel(output_path, index=False)
    elif suffix == ".csv" or default_format == "csv":
        rows.to_csv(output_path, index=False)
    else:
        raise typer.BadParameter("output must end with .csv, .jsonl, or .xlsx")
    return output_path


@app.command("analyze-excel")
def analyze_excel(
    input_path: str | None = typer.Option(
        None,
        "--input",
        "-i",
        help="Input SQLite/CSV/JSONL/XLSX path. Defaults to configured SQLite database.",
    ),
    keywords: str | None = typer.Option(
        "configs/keywords.txt",
        "--keywords",
        "-k",
        help="Keyword file path. One keyword per line.",
    ),
    keyword: list[str] | None = KEYWORD_OPTION,
    output: str = typer.Option(
        "data/exports/analysis_report.xlsx",
        "--output",
        "-o",
        help="Excel report output path.",
    ),
):
    """Build an Excel analysis report from SQLite, CSV, JSONL, or XLSX data."""
    from dcard_crawler.analysis.excel_report import export_analysis_report

    if input_path is None and not _require_current_schema():
        raise typer.Exit(1)

    tables = export_analysis_report(input_path, output, keywords, keyword)
    typer.echo(f"✓ Excel analysis report exported to {output}")
    typer.echo(f"  Rows: {len(tables['Raw Data'])}")
    typer.echo(f"  Keyword matches: {len(tables['Keyword Matches'])}")


@app.command("export-excel-report")
def export_excel_report(
    input_path: str | None = typer.Option(
        None,
        "--input",
        "-i",
        help="Input SQLite/CSV/JSONL/XLSX path. Defaults to configured SQLite database.",
    ),
    keywords: str | None = typer.Option(
        "configs/keywords.txt",
        "--keywords",
        "-k",
        help="Keyword file path. One keyword per line.",
    ),
    keyword: list[str] | None = KEYWORD_OPTION,
    output: str = typer.Option(
        "data/exports/analysis_report.xlsx",
        "--output",
        "-o",
        help="Excel report output path.",
    ),
):
    """Alias for analyze-excel."""
    analyze_excel(input_path=input_path, keywords=keywords, keyword=keyword, output=output)


@app.command("analyze-keywords")
def analyze_keywords_command(
    input_path: str | None = typer.Option(
        None,
        "--input",
        "-i",
        help="Input SQLite/CSV/JSONL/XLSX path. Defaults to configured SQLite database.",
    ),
    keywords: str | None = typer.Option(
        "configs/keywords.txt",
        "--keywords",
        "-k",
        help="Keyword file path. One keyword per line.",
    ),
    keyword: list[str] | None = KEYWORD_OPTION,
    output: str = typer.Option(
        "data/exports/keyword_matches.csv",
        "--output",
        "-o",
        help="Output CSV/JSONL/XLSX path.",
    ),
):
    """Analyze keyword matches across title, excerpt, and content."""
    from dcard_crawler.analysis.cleaning import clean_posts_dataframe
    from dcard_crawler.analysis.dataframe_loader import load_posts_dataframe
    from dcard_crawler.analysis.keyword_analysis import analyze_keywords, load_keywords

    if input_path is None and not _require_current_schema():
        raise typer.Exit(1)

    posts = clean_posts_dataframe(load_posts_dataframe(input_path))
    keyword_list = load_keywords(keywords, keyword)
    matches = analyze_keywords(posts, keyword_list)
    output_path = _write_analysis_output(matches, output)
    typer.echo(f"✓ Keyword analysis exported to {output_path}")
    typer.echo(f"  Keyword matches: {len(matches)}")


@app.command("analyze-trending")
def analyze_trending(
    input_path: str | None = typer.Option(
        None,
        "--input",
        "-i",
        help="Input SQLite/CSV/JSONL/XLSX path. Defaults to configured SQLite database.",
    ),
    output: str = typer.Option(
        "data/exports/daily_trend.csv",
        "--output",
        "-o",
        help="Output CSV/JSONL/XLSX path.",
    ),
):
    """Analyze daily post trends by platform and board/forum."""
    from dcard_crawler.analysis.cleaning import clean_posts_dataframe
    from dcard_crawler.analysis.dataframe_loader import load_posts_dataframe
    from dcard_crawler.analysis.trend_analysis import daily_post_counts

    if input_path is None and not _require_current_schema():
        raise typer.Exit(1)

    trends = daily_post_counts(clean_posts_dataframe(load_posts_dataframe(input_path)))
    output_path = _write_analysis_output(trends, output)
    typer.echo(f"✓ Trend analysis exported to {output_path}")
    typer.echo(f"  Rows: {len(trends)}")


@app.command("analyze-source-comparison")
def analyze_source_comparison(
    input_path: str | None = typer.Option(
        None,
        "--input",
        "-i",
        help="Input SQLite/CSV/JSONL/XLSX path. Defaults to configured SQLite database.",
    ),
    output: str = typer.Option(
        "data/exports/source_comparison.csv",
        "--output",
        "-o",
        help="Output CSV/JSONL/XLSX path.",
    ),
):
    """Compare post volume and engagement across sources."""
    from dcard_crawler.analysis.cleaning import clean_posts_dataframe
    from dcard_crawler.analysis.dataframe_loader import load_posts_dataframe
    from dcard_crawler.analysis.engagement_analysis import add_engagement_score
    from dcard_crawler.analysis.source_comparison import source_comparison

    if input_path is None and not _require_current_schema():
        raise typer.Exit(1)

    posts = add_engagement_score(clean_posts_dataframe(load_posts_dataframe(input_path)))
    comparison = source_comparison(posts)
    output_path = _write_analysis_output(comparison, output)
    typer.echo(f"✓ Source comparison exported to {output_path}")
    typer.echo(f"  Rows: {len(comparison)}")


if __name__ == "__main__":
    app()
