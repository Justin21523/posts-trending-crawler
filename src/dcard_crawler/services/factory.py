"""Factories for assembling application services."""

from dcard_crawler.clients.api_client import DcardAPIClient
from dcard_crawler.connectors.news import NewsConnector
from dcard_crawler.connectors.ptt import PttConnector
from dcard_crawler.connectors.registry import ConnectorRegistry, default_registry
from dcard_crawler.core.http_client import CrawlerHttpClient
from dcard_crawler.core.robots import RobotsChecker
from dcard_crawler.parsers.post_parser import PostParser
from dcard_crawler.repositories.crawl_job_repository import CrawlJobRepository
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.services.checkpoint_service import CheckpointService
from dcard_crawler.services.connector_ingest_service import ConnectorIngestService
from dcard_crawler.services.ingest_service import IngestService
from dcard_crawler.services.quality_service import QualityService


def build_ingest_service(
    *,
    connector_registry: ConnectorRegistry | None = None,
) -> IngestService:
    """Build the default ingest service with registered connectors."""
    parser = PostParser()
    registry = connector_registry or default_registry()
    return IngestService(
        api_client=DcardAPIClient(),
        repository=PostRepository(),
        parser=parser,
        quality_service=QualityService(),
        checkpoint_service=CheckpointService(),
        source_repository=SourceRepository(),
        crawl_job_repository=CrawlJobRepository(),
        connector_registry=registry,
    )


def build_ptt_ingest_service(
    *,
    board: str = "Stock",
    allow_over18_public_confirm: bool = False,
    robots_unavailable_policy: str | None = None,
) -> ConnectorIngestService:
    """Build PTT ingest service."""
    http_client = None
    if robots_unavailable_policy is not None:
        http_client = CrawlerHttpClient(
            base_url="https://www.ptt.cc",
            robots_checker=RobotsChecker(unavailable_policy=robots_unavailable_policy),
        )
    connector = PttConnector(
        http_client=http_client,
        default_board=board,
        allow_over18_public_confirm=allow_over18_public_confirm,
    )
    return ConnectorIngestService(
        connector=connector,
        repository=PostRepository(),
        quality_service=QualityService(),
        source_repository=SourceRepository(),
        crawl_job_repository=CrawlJobRepository(),
    )


def build_news_ingest_service(
    *,
    source_name: str,
) -> ConnectorIngestService:
    """Build News ingest service."""
    connector = NewsConnector(source_name=source_name)
    return ConnectorIngestService(
        connector=connector,
        repository=PostRepository(),
        quality_service=QualityService(),
        source_repository=SourceRepository(),
        crawl_job_repository=CrawlJobRepository(),
    )
