"""Keyword matching for public posts and articles."""

from pathlib import Path

import pandas as pd

MATCH_FIELDS = ["title", "excerpt", "content"]


def load_keywords(
    path: str | Path | None = None,
    inline_keywords: list[str] | None = None,
) -> list[str]:
    """Load keywords from a file and CLI options."""
    keywords: list[str] = []
    if path:
        keyword_path = Path(path)
        if keyword_path.exists():
            for line in keyword_path.read_text(encoding="utf-8").splitlines():
                keyword = line.strip()
                if keyword and not keyword.startswith("#"):
                    keywords.append(keyword)
    if inline_keywords:
        keywords.extend(k.strip() for k in inline_keywords if k.strip())
    return list(dict.fromkeys(keywords))


def analyze_keywords(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    """Return one row per matched post/keyword."""
    rows: list[dict] = []
    for _, row in df.iterrows():
        for keyword in keywords:
            matched_fields: list[str] = []
            match_count = 0
            keyword_cmp = keyword.lower()
            for field in MATCH_FIELDS:
                text = str(row.get(field, "") or "")
                count = text.lower().count(keyword_cmp)
                if count:
                    matched_fields.append(field)
                    match_count += count
            if match_count:
                rows.append(
                    {
                        "source": row.get("source"),
                        "platform": row.get("platform"),
                        "board_or_forum": row.get("board_or_forum"),
                        "date": row.get("date"),
                        "external_id": row.get("external_id"),
                        "title": row.get("title"),
                        "url": row.get("url"),
                        "keyword": keyword,
                        "match_count": match_count,
                        "matched_fields": ",".join(matched_fields),
                    }
                )
    return pd.DataFrame(rows)


def summarize_keyword_matches(matches: pd.DataFrame) -> pd.DataFrame:
    """Summarize keyword hits by keyword, platform, board, and date."""
    if matches.empty:
        return pd.DataFrame(
            columns=[
                "keyword",
                "platform",
                "board_or_forum",
                "date",
                "posts_matched",
                "match_count",
            ]
        )
    return (
        matches.groupby(["keyword", "platform", "board_or_forum", "date"], dropna=False)
        .agg(posts_matched=("external_id", "nunique"), match_count=("match_count", "sum"))
        .reset_index()
        .sort_values(["match_count", "posts_matched"], ascending=False)
    )
