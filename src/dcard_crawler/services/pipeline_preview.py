"""Preview uploaded datasets through the analytics pipeline."""

import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from dcard_crawler.analysis.cleaning import clean_posts_dataframe
from dcard_crawler.analysis.dataframe_loader import load_posts_dataframe
from dcard_crawler.analysis.engagement_analysis import add_engagement_score
from dcard_crawler.analysis.keyword_analysis import analyze_keywords
from dcard_crawler.analysis.topic_taxonomy import classify_text
from dcard_crawler.analysis.trend_analysis import daily_post_counts
from dcard_crawler.models import CrawlJob
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.schemas import NormalizedPost


class PipelinePreviewService:
    """Build and import temporary pipeline previews for uploaded data."""

    def __init__(self, preview_root: str | Path = "data/uploads/previews") -> None:
        self.preview_root = Path(preview_root)
        self.preview_root.mkdir(parents=True, exist_ok=True)

    def preview_sample(self, *, max_rows: int = 5000) -> dict[str, Any]:
        """Preview the current SQLite/sample dataset without upload."""
        df = load_posts_dataframe().head(max_rows)
        return self._build_preview(df, source_label="sample-data", filename="sample-sqlite")

    def preview_upload(
        self,
        *,
        filename: str,
        content: bytes,
        max_rows: int = 5000,
    ) -> dict[str, Any]:
        """Preview uploaded CSV, JSONL, or Excel content."""
        suffix = Path(filename).suffix.lower()
        if suffix not in {".csv", ".jsonl", ".ndjson", ".xlsx", ".xls"}:
            raise ValueError("Unsupported upload format. Use CSV, JSONL, or Excel.")
        if len(content) > 12 * 1024 * 1024:
            raise ValueError("Uploaded file is too large for preview.")

        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(content)
            tmp.flush()
            df = load_posts_dataframe(tmp.name).head(max_rows)
        return self._build_preview(df, source_label="uploaded-data", filename=filename)

    def get_preview(self, preview_id: str) -> dict[str, Any]:
        """Load a stored preview payload."""
        path = self._preview_path(preview_id)
        if not path.exists():
            raise FileNotFoundError(preview_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def import_preview(self, preview_id: str) -> dict[str, Any]:
        """Persist normalized preview rows into SQLite after user confirmation."""
        payload = self.get_preview(preview_id)
        rows = payload.get("normalized_rows", [])
        source_name = f"upload-{preview_id[:8]}"
        source_repo = SourceRepository()
        source_id = source_repo.get_or_create(
            name=source_name,
            source_type="upload",
            base_url=None,
            notes=f"Imported from guided pipeline preview {preview_id}",
        )
        inserted = 0
        updated = 0
        post_repo = PostRepository(source_repo)
        for row in rows:
            post = self._row_to_post(row, source_id=source_id, source_name=source_name)
            if post_repo.upsert(post):
                inserted += 1
            else:
                updated += 1

        from dcard_crawler.database import get_session

        with get_session() as session:
            # 中文註解：上傳資料沒有對外請求，但仍建立 job 讓 lineage 可追蹤。
            job = CrawlJob(
                source_id=source_id,
                job_type="guided_upload_import",
                target_url=payload.get("filename"),
                status="completed",
                started_at=datetime.now(),
                finished_at=datetime.now(),
                request_count=0,
                item_count=len(rows),
            )
            session.add(job)
        return {
            "status": "completed",
            "preview_id": preview_id,
            "source": source_name,
            "inserted": inserted,
            "updated": updated,
            "row_count": len(rows),
        }

    def _build_preview(
        self,
        df: pd.DataFrame,
        *,
        source_label: str,
        filename: str,
    ) -> dict[str, Any]:
        raw_rows = df.fillna("").head(30).to_dict(orient="records")
        clean = clean_posts_dataframe(df)
        clean = add_engagement_score(clean)
        normalized_rows = clean.head(5000).fillna("").to_dict(orient="records")
        keyword_rows = analyze_keywords(clean, self._default_keywords()).head(30)
        trends = daily_post_counts(clean).head(60)
        topic_matches = self._topic_matches(clean)
        quality_flags = self._quality_flags(df, clean)
        preview_id = uuid4().hex
        payload = {
            "preview_id": preview_id,
            "source_label": source_label,
            "filename": filename,
            "created_at": datetime.now().isoformat(),
            "row_count": int(len(df)),
            "normalized_row_count": int(len(clean)),
            "columns": list(df.columns),
            "raw_sample": raw_rows[:5],
            "normalized_rows": normalized_rows,
            "quality_flags": quality_flags,
            "keyword_matches": keyword_rows.fillna("").to_dict(orient="records"),
            "topic_matches": topic_matches,
            "daily_trend": trends.fillna("").to_dict(orient="records"),
            "stage_summaries": self._stage_summaries(df, clean, quality_flags, topic_matches),
        }
        self._preview_path(preview_id).write_text(
            json.dumps(payload, ensure_ascii=False, default=str, indent=2),
            encoding="utf-8",
        )
        return payload

    def _preview_path(self, preview_id: str) -> Path:
        safe_id = "".join(ch for ch in preview_id if ch.isalnum() or ch in {"-", "_"})
        return self.preview_root / f"{safe_id}.json"

    def _topic_matches(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        counter: dict[tuple[str, str, str], int] = {}
        for _, row in df.head(1000).iterrows():
            text = " ".join([str(row.get("title", "")), str(row.get("content", ""))])
            for match in classify_text(text):
                key = (match["topic_id"], match["topic_name"], match["keyword"])
                counter[key] = counter.get(key, 0) + int(match["match_count"])
        return [
            {
                "topic_id": topic_id,
                "topic_name": topic_name,
                "keyword": keyword,
                "match_count": count,
            }
            for (topic_id, topic_name, keyword), count in sorted(
                counter.items(), key=lambda item: item[1], reverse=True
            )[:30]
        ]

    def _quality_flags(self, raw: pd.DataFrame, clean: pd.DataFrame) -> list[dict[str, Any]]:
        flags = [
            {"name": "missing_title", "count": int((clean["title"].str.len() == 0).sum())},
            {"name": "missing_content", "count": int((clean["content"].str.len() == 0).sum())},
            {"name": "invalid_date", "count": int(clean["analysis_datetime"].isna().sum())},
            {"name": "duplicates_removed", "count": max(int(len(raw) - len(clean)), 0)},
            {
                "name": "missing_engagement_metrics",
                "count": int(
                    (
                        clean[["like_count", "comment_count", "view_count"]]
                        .fillna(0)
                        .sum(axis=1)
                        == 0
                    ).sum()
                ),
            },
        ]
        return flags

    def _stage_summaries(
        self,
        raw: pd.DataFrame,
        clean: pd.DataFrame,
        quality_flags: list[dict[str, Any]],
        topic_matches: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "upload",
                "title_zh": "資料進場",
                "title_en": "Data Intake",
                "input_count": int(len(raw)),
                "output_count": int(len(raw)),
                "artifact": "uploaded file or sample SQLite rows",
            },
            {
                "id": "clean",
                "title_zh": "清理與時間轉換",
                "title_en": "Cleaning and Date Parsing",
                "input_count": int(len(raw)),
                "output_count": int(len(clean)),
                "artifact": "cleaned dataframe",
            },
            {
                "id": "normalize",
                "title_zh": "通用 Schema 標準化",
                "title_en": "Normalized Schema",
                "input_count": int(len(clean.columns)),
                "output_count": 19,
                "artifact": "posts-compatible columns",
            },
            {
                "id": "quality",
                "title_zh": "資料品質檢查",
                "title_en": "Data Quality Gate",
                "input_count": int(len(clean)),
                "output_count": int(sum(item["count"] for item in quality_flags)),
                "artifact": "quality flags",
            },
            {
                "id": "analysis",
                "title_zh": "Topic / Keyword 分析",
                "title_en": "Topic / Keyword Analysis",
                "input_count": int(len(clean)),
                "output_count": int(len(topic_matches)),
                "artifact": "topic signals",
            },
            {
                "id": "export",
                "title_zh": "Excel 報表準備",
                "title_en": "Excel Export Ready",
                "input_count": int(len(clean)),
                "output_count": 6,
                "artifact": "analysis workbook sheets",
            },
        ]

    def _row_to_post(
        self,
        row: dict[str, Any],
        *,
        source_id: int,
        source_name: str,
    ) -> NormalizedPost:
        title = str(row.get("title") or "Untitled uploaded record")
        content = str(row.get("content") or row.get("excerpt") or "")
        external_id = str(row.get("external_id") or self._stable_external_id(row))
        return NormalizedPost(
            source_id=source_id,
            source_name=source_name,
            source_type="upload",
            platform=str(row.get("platform") or "uploaded"),
            external_id=external_id,
            board_or_forum=str(row.get("board_or_forum") or "uploaded"),
            title=title,
            excerpt=str(row.get("excerpt") or content[:180]),
            content=content,
            published_at=str(row.get("published_at") or row.get("created_at") or ""),
            created_at=str(row.get("created_at") or row.get("published_at") or ""),
            like_count=int(float(row.get("like_count") or 0)),
            comment_count=int(float(row.get("comment_count") or 0)),
            share_count=int(float(row.get("share_count") or 0)),
            view_count=int(float(row.get("view_count") or 0)),
            url=str(row.get("url") or ""),
            canonical_url=str(row.get("canonical_url") or row.get("url") or ""),
            crawl_source="upload",
            raw_json=row,
            content_hash=self._content_hash(title, content),
        )

    def _stable_external_id(self, row: dict[str, Any]) -> str:
        raw = json.dumps(row, ensure_ascii=False)
        return self._content_hash(str(row.get("title", "")), raw)[:24]

    def _content_hash(self, title: str, content: str) -> str:
        return hashlib.sha256(f"{title}\n{content}".encode()).hexdigest()

    def _default_keywords(self) -> list[str]:
        return ["AI", "台積電", "工作", "面試", "Python", "資料分析", "投資", "科技"]
