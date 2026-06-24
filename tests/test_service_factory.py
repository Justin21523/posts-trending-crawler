"""Tests for application service factories."""

from dcard_crawler.services.connector_ingest_service import ConnectorIngestService
from dcard_crawler.services.factory import (
    build_ingest_service,
    build_news_ingest_service,
    build_ptt_ingest_service,
)
from dcard_crawler.services.ingest_service import IngestService


def test_build_ingest_service_registers_dcard_connector():
    service = build_ingest_service()

    assert isinstance(service, IngestService)
    assert service.connector_registry.names() == ["dcard", "news", "ptt"]


def test_build_ptt_ingest_service():
    service = build_ptt_ingest_service(board="Stock")

    assert isinstance(service, ConnectorIngestService)
    assert service.connector.name == "ptt"


def test_build_news_ingest_service():
    service = build_news_ingest_service(source_name="demo-news")

    assert isinstance(service, ConnectorIngestService)
    assert service.connector.name == "news"
