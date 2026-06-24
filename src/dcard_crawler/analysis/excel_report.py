"""Excel report generation for crawler analysis outputs."""

from pathlib import Path

import pandas as pd

from dcard_crawler.analysis.cleaning import clean_posts_dataframe
from dcard_crawler.analysis.dataframe_loader import load_posts_dataframe
from dcard_crawler.analysis.engagement_analysis import add_engagement_score, top_posts
from dcard_crawler.analysis.keyword_analysis import analyze_keywords, load_keywords
from dcard_crawler.analysis.source_comparison import source_comparison
from dcard_crawler.analysis.trend_analysis import daily_post_counts


def build_analysis_tables(
    input_path: str | Path | None = None,
    keyword_path: str | Path | None = "configs/keywords.txt",
    inline_keywords: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Build all report tables from one input source."""
    raw = load_posts_dataframe(input_path)
    posts = add_engagement_score(clean_posts_dataframe(raw))
    keywords = load_keywords(keyword_path, inline_keywords)
    matches = analyze_keywords(posts, keywords) if keywords else pd.DataFrame()
    daily = daily_post_counts(posts)
    sources = source_comparison(posts)
    summary = _summary_table(posts, matches, keywords)
    return {
        "Summary": summary,
        "Raw Data": posts,
        "Keyword Matches": matches,
        "Daily Trend": daily,
        "Top Posts": top_posts(posts),
        "Source Comparison": sources,
    }


def write_excel_report(tables: dict[str, pd.DataFrame], output_path: str | Path) -> Path:
    """Write formatted Excel report and return its path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        for sheet_name, table in tables.items():
            safe_table = _excel_safe(table)
            safe_table.to_excel(writer, sheet_name=sheet_name, index=False)
            _format_sheet(writer, sheet_name, safe_table)
        _add_charts(writer, tables)
    return path


def export_analysis_report(
    input_path: str | Path | None,
    output_path: str | Path,
    keyword_path: str | Path | None = "configs/keywords.txt",
    inline_keywords: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Build and write the Excel report."""
    tables = build_analysis_tables(input_path, keyword_path, inline_keywords)
    write_excel_report(tables, output_path)
    return tables


def _summary_table(posts: pd.DataFrame, matches: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    rows = [
        {"metric": "post_count", "value": len(posts)},
        {"metric": "source_count", "value": posts["source"].nunique() if not posts.empty else 0},
        {
            "metric": "platform_count",
            "value": posts["platform"].nunique() if not posts.empty else 0,
        },
        {"metric": "keyword_count", "value": len(keywords)},
        {"metric": "keyword_match_rows", "value": len(matches)},
    ]
    if not posts.empty:
        rows.extend(
            [
                {"metric": "avg_engagement_score", "value": posts["engagement_score"].mean()},
                {"metric": "max_engagement_score", "value": posts["engagement_score"].max()},
            ]
        )
    return pd.DataFrame(rows)


def _excel_safe(table: pd.DataFrame) -> pd.DataFrame:
    result = table.copy()
    for column in result.columns:
        if pd.api.types.is_datetime64_any_dtype(result[column]):
            result[column] = result[column].dt.tz_localize(None)
    return result


def _format_sheet(writer: pd.ExcelWriter, sheet_name: str, table: pd.DataFrame) -> None:
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
    date_format = workbook.add_format({"num_format": "yyyy-mm-dd"})
    number_format = workbook.add_format({"num_format": "#,##0.00"})

    for col_idx, column in enumerate(table.columns):
        worksheet.write(0, col_idx, column, header_format)
        max_content_width = table[column].astype(str).str.len().max() if len(table) else 0
        width = min(max(len(str(column)), max_content_width) + 2, 60)
        worksheet.set_column(col_idx, col_idx, width)
        if "date" in str(column).lower() or str(column).endswith("_at"):
            worksheet.set_column(col_idx, col_idx, width, date_format)
        elif pd.api.types.is_numeric_dtype(table[column]):
            worksheet.set_column(col_idx, col_idx, width, number_format)
    worksheet.freeze_panes(1, 0)
    if table.columns.size:
        worksheet.autofilter(0, 0, max(len(table), 1), len(table.columns) - 1)


def _add_charts(writer: pd.ExcelWriter, tables: dict[str, pd.DataFrame]) -> None:
    workbook = writer.book
    daily = tables.get("Daily Trend", pd.DataFrame())
    if not daily.empty and {"date", "post_count"}.issubset(daily.columns):
        chart = workbook.add_chart({"type": "line"})
        max_row = len(daily)
        chart.add_series(
            {
                "name": "Daily posts",
                "categories": ["Daily Trend", 1, 0, max_row, 0],
                "values": ["Daily Trend", 1, 3, max_row, 3],
            }
        )
        chart.set_title({"name": "Daily Post Count"})
        writer.sheets["Daily Trend"].insert_chart("F2", chart)

    sources = tables.get("Source Comparison", pd.DataFrame())
    if not sources.empty and {"source", "post_count"}.issubset(sources.columns):
        chart = workbook.add_chart({"type": "column"})
        max_row = len(sources)
        chart.add_series(
            {
                "name": "Posts by source",
                "categories": ["Source Comparison", 1, 0, max_row, 0],
                "values": ["Source Comparison", 1, 2, max_row, 2],
            }
        )
        chart.set_title({"name": "Source Comparison"})
        writer.sheets["Source Comparison"].insert_chart("K2", chart)
