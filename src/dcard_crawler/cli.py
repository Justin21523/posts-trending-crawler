"""CLI entry point for Dcard Crawler."""

import asyncio
import json
from pathlib import Path

import typer

from dcard_crawler.clients.api_client import DcardAPIClient
from dcard_crawler.clients.browser_client import BrowserClient
from dcard_crawler.database import init_db
from dcard_crawler.parsers.post_parser import PostParser
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.services.checkpoint_service import CheckpointService
from dcard_crawler.services.ingest_service import IngestService
from dcard_crawler.services.quality_service import QualityService
from dcard_crawler.settings import settings

app = typer.Typer(
    name="dcard-crawler",
    help="Dcard Trending Forum Crawler - Production-style post collection system",
    add_completion=False,
)


@app.command()
def init():
    """Initialize database and required directories."""
    typer.echo("Initializing database...")
    init_db()

    # Ensure directories exist
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("research").mkdir(exist_ok=True)

    typer.echo("✓ Database initialized")
    typer.echo(f"✓ Database URL: {settings.database.url}")


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

    async def _run():
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

                # Save to file if requested
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
    typer.echo(f"Starting crawl list: forum={forum} popular={popular} max_posts={max_posts}")

    async def _run():
        api_client = DcardAPIClient()
        repository = PostRepository()
        parser = PostParser()
        quality_service = QualityService()
        checkpoint_service = CheckpointService()

        ingest_service = IngestService(
            api_client=api_client,
            repository=repository,
            parser=parser,
            quality_service=quality_service,
            checkpoint_service=checkpoint_service,
        )

        try:
            stats = await ingest_service.crawl_posts(
                forum_alias=forum,
                max_posts=max_posts,
                popular=popular,
                fetch_details=False,  # Only fetch listing data
                resume=resume,
            )

            typer.echo("\n✓ Crawl completed!")
            typer.echo(f"  Posts listed: {stats['posts_listed']}")
            typer.echo(f"  Posts stored: {stats['posts_stored']}")
            typer.echo(f"  Posts skipped: {stats['posts_skipped']}")
            typer.echo(f"  Errors: {stats['errors']}")
        finally:
            await api_client.close()

    asyncio.run(_run())


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
    typer.echo(f"Starting full post crawl: forum={forum} popular={popular} max_posts={max_posts}")

    async def _run():
        api_client = DcardAPIClient()
        repository = PostRepository()
        parser = PostParser()
        quality_service = QualityService()
        checkpoint_service = CheckpointService()

        ingest_service = IngestService(
            api_client=api_client,
            repository=repository,
            parser=parser,
            quality_service=quality_service,
            checkpoint_service=checkpoint_service,
        )

        try:
            stats = await ingest_service.crawl_posts(
                forum_alias=forum,
                max_posts=max_posts,
                popular=popular,
                fetch_details=True,  # Fetch full details
                resume=resume,
            )

            typer.echo("\n✓ Crawl completed!")
            typer.echo(f"  Posts listed: {stats['posts_listed']}")
            typer.echo(f"  Posts detailed: {stats['posts_detailed']}")
            typer.echo(f"  Posts stored: {stats['posts_stored']}")
            typer.echo(f"  Posts skipped: {stats['posts_skipped']}")
            typer.echo(f"  Errors: {stats['errors']}")
        finally:
            await api_client.close()

    asyncio.run(_run())


@app.command()
def status():
    """Show current crawl status and statistics."""
    from sqlalchemy import func, select

    from dcard_crawler.database import get_session
    from dcard_crawler.models import Post

    typer.echo("Crawl Status\n")

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
        else:
            typer.echo("  No posts in database yet.")

    # Checkpoint status
    checkpoint_service = CheckpointService()
    checkpoint = checkpoint_service.load("trending")

    if checkpoint:
        typer.echo("\n  Checkpoint (trending):")
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
    from dcard_crawler.models import Post

    output = output.replace("{format}", format)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Exporting posts to {output_path} (format={format}, limit={limit})")

    with get_session() as session:
        query = select(Post).order_by(Post.post_id.desc())
        if limit:
            query = query.limit(limit)

        posts = session.execute(query).scalars().all()

        if not posts:
            typer.echo("⚠ No posts to export")
            return

        typer.echo(f"Exporting {len(posts)} posts...")

        if format == "jsonl":
            with open(output_path, "w") as f:
                for post in posts:
                    record = {
                        "post_id": post.post_id,
                        "forum_alias": post.forum_alias,
                        "title": post.title,
                        "content": post.content,
                        "created_at": post.created_at,
                        "like_count": post.like_count,
                        "comment_count": post.comment_count,
                        "url": post.url,
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        elif format == "csv":
            import csv
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "post_id", "forum_alias", "title", "content",
                    "created_at", "like_count", "comment_count", "url"
                ])
                writer.writeheader()
                for post in posts:
                    writer.writerow({
                        "post_id": post.post_id,
                        "forum_alias": post.forum_alias,
                        "title": post.title,
                        "content": post.content,
                        "created_at": post.created_at,
                        "like_count": post.like_count,
                        "comment_count": post.comment_count,
                        "url": post.url,
                    })
        else:
            typer.echo(f"✗ Unsupported format: {format}")
            raise typer.Exit(1)

    typer.echo(f"✓ Exported to {output_path}")


if __name__ == "__main__":
    app()
