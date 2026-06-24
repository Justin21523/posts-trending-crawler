"""Dcard endpoint diagnostics without bypassing access controls."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from dcard_crawler.core.errors import RobotsDisallowedError
from dcard_crawler.core.http_client import CrawlerHttpClient
from dcard_crawler.core.policy import CrawlPolicy
from dcard_crawler.core.robots import RobotsChecker
from dcard_crawler.settings import settings


class DcardEndpointDiagnosticsService:
    """Probe public Dcard endpoints and classify outcomes."""

    def __init__(
        self,
        *,
        report_dir: str | Path = "data/reports/diagnostics",
        transport: httpx.AsyncBaseTransport | None = None,
        robots_checker: RobotsChecker | None = None,
        policy: CrawlPolicy | None = None,
    ):
        self.report_dir = Path(report_dir)
        self.transport = transport
        self.robots_checker = robots_checker or RobotsChecker()
        self.policy = policy or CrawlPolicy()

    async def diagnose(
        self,
        *,
        forum: str = "trending",
        sample_post_id: int | None = None,
    ) -> dict[str, Any]:
        """Run low-impact diagnostics for Dcard public endpoints."""
        endpoints = [
            {
                "name": "forum_page",
                "method": "GET",
                "url": f"{settings.dcard_base_url}/f/{forum}",
                "params": None,
            },
            {
                "name": "forum_posts_api",
                "method": "GET",
                "url": f"{settings.dcard_api_base_url}/forums/{forum}/posts",
                "params": {"popular": "false", "limit": "1"},
            },
        ]
        if sample_post_id is not None:
            endpoints.append(
                {
                    "name": "post_detail_api",
                    "method": "GET",
                    "url": f"{settings.dcard_api_base_url}/posts/{sample_post_id}",
                    "params": None,
                }
            )

        results = []
        async with httpx.AsyncClient(
            headers=CrawlerHttpClient.default_headers(),
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
            verify=settings.ssl_verify,
            transport=self.transport,
        ) as client:
            for endpoint in endpoints:
                results.append(await self._diagnose_endpoint(client, endpoint))

        report = {
            "platform": "dcard",
            "forum": forum,
            "sample_post_id": sample_post_id,
            "generated_at": datetime.now().isoformat(),
            "endpoints": results,
            "summary": self._summary(results),
        }
        report_path = self._write_report(report)
        report["report_path"] = str(report_path)
        return report

    async def _diagnose_endpoint(
        self,
        client: httpx.AsyncClient,
        endpoint: dict[str, Any],
    ) -> dict[str, Any]:
        url = endpoint["url"]
        try:
            await self.robots_checker.ensure_allowed(
                url,
                CrawlerHttpClient.default_headers()["User-Agent"],
            )
            robots = {"allowed": True, "reason": None}
        except RobotsDisallowedError as exc:
            return {
                **endpoint,
                "robots": {"allowed": False, "reason": str(exc)},
                "status_code": None,
                "content_type": None,
                "policy_allowed": False,
                "policy_category": "robots_disallowed",
                "policy_reason": str(exc),
            }

        try:
            response = await client.request(
                endpoint["method"],
                url,
                params=endpoint.get("params"),
            )
            preview = response.text[:4096] if response.content else ""
            decision = self.policy.classify(response.status_code, preview)
            return {
                **endpoint,
                "robots": robots,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "policy_allowed": decision.allowed,
                "policy_category": decision.category.value,
                "policy_reason": decision.reason,
                "body_preview": preview[:240],
            }
        except httpx.RequestError as exc:
            return {
                **endpoint,
                "robots": robots,
                "status_code": None,
                "content_type": None,
                "policy_allowed": False,
                "policy_category": "transient",
                "policy_reason": str(exc),
            }

    @staticmethod
    def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
        blocked = [result for result in results if not result["policy_allowed"]]
        return {
            "endpoint_count": len(results),
            "blocked_count": len(blocked),
            "blocked_reasons": [result["policy_reason"] for result in blocked],
        }

    def _write_report(self, report: dict[str, Any]) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.report_dir / f"dcard_{timestamp}.json"
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return path
