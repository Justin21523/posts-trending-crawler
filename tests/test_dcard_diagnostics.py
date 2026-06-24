"""Tests for Dcard endpoint diagnostics."""

import httpx
import pytest

from dcard_crawler.core.robots import RobotsChecker
from dcard_crawler.services.dcard_diagnostics import DcardEndpointDiagnosticsService


def allow_robots_checker() -> RobotsChecker:
    async def fetcher(url: str) -> str:
        return "User-agent: *\nDisallow:\n"

    return RobotsChecker(fetcher=fetcher)


@pytest.mark.asyncio
async def test_dcard_diagnostics_classifies_success_and_forbidden(tmp_path):
    async def handler(request: httpx.Request) -> httpx.Response:
        if "service/api" in str(request.url):
            return httpx.Response(403, text="Forbidden")
        return httpx.Response(200, text="<html>Dcard</html>", headers={"content-type": "text/html"})

    service = DcardEndpointDiagnosticsService(
        report_dir=tmp_path,
        transport=httpx.MockTransport(handler),
        robots_checker=allow_robots_checker(),
    )

    report = await service.diagnose(forum="trending")

    assert report["summary"]["endpoint_count"] == 2
    assert report["summary"]["blocked_count"] == 1
    assert report["endpoints"][0]["policy_allowed"] is True
    assert report["endpoints"][1]["policy_category"] == "forbidden"
    assert (tmp_path / report["report_path"].split("/")[-1]).exists()


@pytest.mark.asyncio
async def test_dcard_diagnostics_classifies_challenge(tmp_path):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="verify you are human")

    service = DcardEndpointDiagnosticsService(
        report_dir=tmp_path,
        transport=httpx.MockTransport(handler),
        robots_checker=allow_robots_checker(),
    )

    report = await service.diagnose(forum="trending", sample_post_id=123)

    assert report["summary"]["endpoint_count"] == 3
    assert report["summary"]["blocked_count"] == 3
    assert {item["policy_category"] for item in report["endpoints"]} == {"challenge"}
