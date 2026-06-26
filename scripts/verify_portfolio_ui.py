"""Capture portfolio UI screenshots and a Playwright demo video."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

BASE_URL = os.getenv("PORTFOLIO_UI_BASE_URL", "http://127.0.0.1:5176").rstrip("/")
SEED_DEMO_DATA = os.getenv("PORTFOLIO_UI_SEED_DEMO_DATA", "1") != "0"
DEMO_ROWS = int(os.getenv("PORTFOLIO_UI_DEMO_ROWS", "10000"))
OUTPUT_ROOT = Path("docs/demo")
SCREENSHOT_DIR = OUTPUT_ROOT / "screenshots"
VIDEO_DIR = OUTPUT_ROOT / "videos"
VIEWPORT = {"width": 1440, "height": 1000}
READY_ENDPOINT_COUNT = "25/25 endpoints ready"
IGNORED_CONSOLE_ERROR_PARTS = (
    "favicon",
    "net::ERR_NETWORK_CHANGED",
)

PAGES = [
    ("overview", "/overview", '[data-tour="overview-kpis"]'),
    ("demo-walkthrough", "/demo", '[data-tour="demo-workflow"]'),
    ("architecture-map", "/architecture", '[data-tour="architecture-map"]'),
    ("source-registry", "/sources", '[data-tour="source-registry"]'),
    ("crawler-workflow", "/workflow", '[data-tour="workflow-graph"]'),
    ("data-lifecycle", "/lifecycle", ".content-shell"),
    ("data-journey", "/journey", '[data-tour="journey-transform"]'),
    ("guided-pipeline", "/guided-demo", '[data-tour="guided-upload"]'),
    ("crawl-runs", "/runs", ".content-shell"),
    ("data-explorer", "/explorer", ".content-shell"),
    ("trend-analytics", "/trends", ".content-shell"),
    ("keyword-mining", "/keywords", '[data-tour="keyword-network"]'),
    ("engagement-analysis", "/engagement", ".content-shell"),
    ("platform-comparison", "/platforms", ".content-shell"),
    ("data-quality-lineage", "/quality", '[data-tour="quality-lineage"]'),
    ("excel-report-center", "/reports", '[data-tour="report-center"]'),
    ("compliance-diagnostics", "/compliance", '[data-tour="compliance-summary"]'),
    ("settings", "/settings", ".content-shell"),
]


def reset_output_dirs() -> None:
    for path in [SCREENSHOT_DIR, VIDEO_DIR]:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


def ensure_demo_dataset() -> None:
    """Seed a reproducible demo dataset before screenshot/video capture."""
    if not SEED_DEMO_DATA:
        return

    subprocess.run(["dcard-crawler", "init"], check=True)
    subprocess.run(
        [
            "dcard-crawler",
            "seed-demo-data",
            "--rows",
            str(DEMO_ROWS),
            "--reset-demo",
        ],
        check=True,
    )


def wait_demo_data_ready(page: Page) -> None:
    """Wait until the app has rendered API-backed demo data, not just shells."""
    expect(page.get_by_text("API ready").first).to_be_visible(timeout=180_000)
    expect(page.get_by_text(READY_ENDPOINT_COUNT).first).to_be_visible(timeout=180_000)
    expect(page.locator(".loading-strip")).to_have_count(0, timeout=60_000)
    expect(page.get_by_text("Demo dataset", exact=False).first).to_be_visible(timeout=60_000)
    page.wait_for_timeout(900)


def wait_ready(page: Page, selector: str) -> None:
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator(selector).first).to_be_visible(timeout=30_000)
    wait_demo_data_ready(page)


def capture_segments(page: Page, name: str, selector: str) -> list[str]:
    wait_ready(page, selector)
    total_height = int(page.evaluate("document.documentElement.scrollHeight"))
    viewport_height = VIEWPORT["height"]
    positions = [0]
    if total_height > viewport_height:
        step = viewport_height - 120
        next_position = step
        while next_position < total_height and len(positions) < 4:
            positions.append(next_position)
            next_position += step

    files = []
    for index, y in enumerate(positions, start=1):
        page.evaluate("(scrollY) => window.scrollTo(0, scrollY)", y)
        page.wait_for_timeout(350)
        path = SCREENSHOT_DIR / f"{name}-{index:02d}.png"
        page.screenshot(path=str(path), full_page=False)
        files.append(path.as_posix())
    page.evaluate("window.scrollTo(0, 0)")
    return files


def run_guided_demo(page: Page) -> None:
    fixture = Path("/tmp/guided_demo_upload.csv")
    fixture.write_text(
        "source,platform,external_id,board_or_forum,title,content,published_at,"
        "like_count,comment_count,view_count\n"
        "upload,news,u-1,Tech,AI demo title,AI Python data analysis content,"
        "2024-01-02T00:00:00,5,2,100\n",
        encoding="utf-8",
    )
    page.goto(f"{BASE_URL}/guided-demo", wait_until="domcontentloaded")
    wait_ready(page, '[data-tour="guided-upload"]')
    with page.expect_response(
        lambda response: "/pipeline/preview" in response.url and response.status == 200,
        timeout=180_000,
    ):
        page.get_by_role("button", name="使用 Sample Data").click()
    expect(page.locator(".guided-stage-card").first).to_be_visible(timeout=90_000)
    with page.expect_response(
        lambda response: "/pipeline/preview" in response.url and response.status == 200,
        timeout=120_000,
    ):
        page.locator(".guided-upload-zone input").set_input_files(str(fixture))
    expect(page.locator(".guided-upload-meta").get_by_text(fixture.name)).to_be_visible(
        timeout=60_000
    )
    page.locator(".guided-stage-card").nth(2).click()
    page.wait_for_timeout(700)
    page.screenshot(path=str(SCREENSHOT_DIR / "guided-demo-after-upload.png"), full_page=False)


def run_assistant(page: Page) -> None:
    page.goto(f"{BASE_URL}/journey", wait_until="domcontentloaded")
    wait_ready(page, '[data-tour="journey-transform"]')
    page.locator(".assistant-bubble").click()
    expect(page.locator(".assistant-card")).to_be_visible(timeout=10_000)
    expect(page.locator(".guided-stage")).to_be_visible(timeout=10_000)
    page.screenshot(path=str(SCREENSHOT_DIR / "assistant-stage-overlay.png"), full_page=False)
    for _ in range(3):
        page.locator(".assistant-actions .primary-action").click()
        page.wait_for_timeout(700)
    page.screenshot(path=str(SCREENSHOT_DIR / "assistant-guided-step.png"), full_page=False)
    skip = page.get_by_role("button", name="略過")
    if skip.count():
        skip.click()


def run_detail_routes(page: Page) -> None:
    routes = [
        "/detail/source/demo-ptt",
        "/detail/job/1",
        "/detail/report/data%2Fexports%2Fanalysis_report.xlsx",
        "/detail/keyword/AI",
    ]
    for index, route in enumerate(routes, start=1):
        page.goto(f"{BASE_URL}{route}", wait_until="domcontentloaded")
        expect(page.locator(".detail-page, .panel").first).to_be_visible(timeout=30_000)
        page.screenshot(path=str(SCREENSHOT_DIR / f"detail-route-{index:02d}.png"), full_page=False)


def main() -> None:
    ensure_demo_dataset()
    reset_output_dirs()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORT,
            locale="zh-TW",
            record_video_dir=str(VIDEO_DIR),
            record_video_size=VIEWPORT,
        )
        context.add_init_script(
            """
            window.localStorage.setItem('twCrawlerLang', 'zh');
            window.localStorage.setItem('twCrawlerPipelineJourneyAutoStarted', '1');
            """
        )
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")

        page_errors: list[str] = []
        console_errors: list[str] = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error"
            and not any(part.lower() in msg.text.lower() for part in IGNORED_CONSOLE_ERROR_PARTS)
            else None,
        )

        captured: dict[str, list[str]] = {}
        for name, path, selector in PAGES:
            page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
            captured[name] = capture_segments(page, name, selector)

        run_guided_demo(page)
        run_assistant(page)
        run_detail_routes(page)

        video = page.video
        page.close()
        if video:
            video.save_as(str(VIDEO_DIR / "full-guided-demo.webm"))
        context.close()
        browser.close()
        for raw_video in VIDEO_DIR.glob("*.webm"):
            if raw_video.name != "full-guided-demo.webm":
                raw_video.unlink()

        if page_errors or console_errors:
            raise RuntimeError(
                "Playwright UI verification failed:\n"
                f"page_errors={page_errors}\nconsole_errors={console_errors}"
            )

    manifest = OUTPUT_ROOT / "verification-manifest.md"
    manifest.write_text(
        "# Portfolio UI Verification Manifest\n\n"
        + "\n".join(
            f"- {name}: " + ", ".join(files) for name, files in sorted(captured.items())
        )
        + "\n- assistant: docs/demo/screenshots/assistant-stage-overlay.png\n"
        + "- guided upload: docs/demo/screenshots/guided-demo-after-upload.png\n"
        + "- video: docs/demo/videos/full-guided-demo.webm\n",
        encoding="utf-8",
    )
    print(f"Captured {sum(len(files) for files in captured.values())} page screenshots")
    print(f"Video: {VIDEO_DIR / 'full-guided-demo.webm'}")


if __name__ == "__main__":
    main()
