"""Tests for application service factories."""

from dcard_crawler.services.factory import build_ingest_service
from dcard_crawler.services.ingest_service import IngestService


def test_build_ingest_service_registers_dcard_connector():
    service = build_ingest_service()

    assert isinstance(service, IngestService)
    assert service.connector_registry.names() == ["dcard"]
