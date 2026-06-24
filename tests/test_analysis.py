"""Tests for DataFrame analysis and Excel reporting."""

import json

import openpyxl
import pandas as pd

from dcard_crawler.analysis.cleaning import clean_posts_dataframe
from dcard_crawler.analysis.dataframe_loader import load_posts_dataframe
from dcard_crawler.analysis.engagement_analysis import add_engagement_score
from dcard_crawler.analysis.excel_report import build_analysis_tables, write_excel_report
from dcard_crawler.analysis.keyword_analysis import analyze_keywords, load_keywords
from dcard_crawler.analysis.source_comparison import source_comparison
from dcard_crawler.analysis.trend_analysis import daily_post_counts
from dcard_crawler.database import init_db
from dcard_crawler.repositories.post_repository import PostRepository
from dcard_crawler.repositories.source_repository import SourceRepository
from dcard_crawler.schemas import NormalizedPost
from dcard_crawler.settings import settings


def sample_rows() -> list[dict]:
    return [
        {
            "source": "dcard",
            "platform": "dcard",
            "external_id": "1",
            "post_id": 1,
            "forum_alias": "tech",
            "board_or_forum": "tech",
            "title": "AI 科技新聞",
            "excerpt": "台灣 AI 討論",
            "content": "AI 正在改變工作與科技產業",
            "published_at": "2024-01-01T10:00:00Z",
            "created_at": "2024-01-01T10:00:00Z",
            "crawled_at": "2024-01-01T11:00:00Z",
            "like_count": 10,
            "comment_count": 2,
            "share_count": 1,
            "view_count": 100,
            "url": "https://www.dcard.tw/f/tech/p/1",
            "canonical_url": "https://www.dcard.tw/f/tech/p/1",
            "content_hash": "hash-1",
        },
        {
            "source": "ptt",
            "platform": "ptt",
            "external_id": "M.1",
            "board_or_forum": "Tech_Job",
            "title": "工作心得",
            "excerpt": "",
            "content": "台灣 科技 工作 分享",
            "published_at": "2024-01-02T10:00:00Z",
            "created_at": "2024-01-02T10:00:00Z",
            "crawled_at": "2024-01-02T11:00:00Z",
            "like_count": 0,
            "comment_count": 5,
            "share_count": 0,
            "view_count": 0,
            "url": "https://www.ptt.cc/bbs/Tech_Job/M.1.html",
            "canonical_url": "https://www.ptt.cc/bbs/Tech_Job/M.1.html",
            "content_hash": "",
        },
    ]


def test_load_posts_dataframe_supports_csv_jsonl_excel(tmp_path):
    rows = sample_rows()
    csv_path = tmp_path / "posts.csv"
    jsonl_path = tmp_path / "posts.jsonl"
    xlsx_path = tmp_path / "posts.xlsx"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    jsonl_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows))
    pd.DataFrame(rows).to_excel(xlsx_path, index=False)

    assert len(load_posts_dataframe(csv_path)) == 2
    assert len(load_posts_dataframe(jsonl_path)) == 2
    assert len(load_posts_dataframe(xlsx_path)) == 2


def test_load_posts_dataframe_supports_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.database, "url", f"sqlite:///{tmp_path / 'crawler.db'}")
    init_db(reset=True)
    source_id = SourceRepository().get_or_create("dcard", source_type="forum")
    PostRepository().upsert(
        NormalizedPost(
            source_id=source_id,
            platform="dcard",
            external_id="1",
            post_id=1,
            title="SQLite title",
            board_or_forum="tech",
            content="SQLite content",
            published_at="2024-01-01T10:00:00Z",
            url="https://www.dcard.tw/f/tech/p/1",
        )
    )

    df = load_posts_dataframe()

    assert len(df) == 1
    assert df.iloc[0]["source"] == "dcard"


def test_cleaning_normalizes_dates_numbers_and_dedupes():
    rows = sample_rows()
    rows.append({**rows[0], "title": "duplicate"})
    rows.append({**rows[1], "external_id": "M.2", "title": "no hash duplicate allowed"})

    cleaned = clean_posts_dataframe(pd.DataFrame(rows))

    assert len(cleaned) == 3
    assert "content_length" in cleaned.columns
    assert cleaned["like_count"].sum() == 10
    assert cleaned["date"].notna().all()


def test_keyword_engagement_trend_and_source_analysis(tmp_path):
    keyword_path = tmp_path / "keywords.txt"
    keyword_path.write_text("# comment\nAI\n工作\n", encoding="utf-8")
    posts = add_engagement_score(clean_posts_dataframe(pd.DataFrame(sample_rows())))
    keywords = load_keywords(keyword_path, ["科技"])

    matches = analyze_keywords(posts, keywords)
    daily = daily_post_counts(posts)
    comparison = source_comparison(posts)

    assert keywords == ["AI", "工作", "科技"]
    assert set(matches["keyword"]) == {"AI", "工作", "科技"}
    assert posts.loc[posts["external_id"] == "1", "engagement_score"].iloc[0] == 18
    assert daily["post_count"].sum() == 2
    assert comparison["post_count"].sum() == 2


def test_excel_report_writes_expected_sheets(tmp_path):
    input_path = tmp_path / "posts.csv"
    keyword_path = tmp_path / "keywords.txt"
    output_path = tmp_path / "report.xlsx"
    pd.DataFrame(sample_rows()).to_csv(input_path, index=False)
    keyword_path.write_text("AI\n工作\n", encoding="utf-8")

    tables = build_analysis_tables(input_path, keyword_path)
    write_excel_report(tables, output_path)

    workbook = openpyxl.load_workbook(output_path)
    expected = {
        "Summary",
        "Raw Data",
        "Keyword Matches",
        "Daily Trend",
        "Top Posts",
        "Source Comparison",
    }
    assert expected.issubset(set(workbook.sheetnames))
    assert workbook["Raw Data"].freeze_panes == "A2"
    assert workbook["Raw Data"].auto_filter.ref is not None
