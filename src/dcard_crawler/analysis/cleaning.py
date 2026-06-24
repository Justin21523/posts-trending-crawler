"""Clean and normalize crawler data for analysis."""

import re

import pandas as pd

from dcard_crawler.analysis.dataframe_loader import ensure_standard_columns

TEXT_COLUMNS = [
    "source",
    "platform",
    "external_id",
    "board_or_forum",
    "title",
    "excerpt",
    "content",
]
COUNT_COLUMNS = ["like_count", "comment_count", "share_count", "view_count"]


def normalize_text(value) -> str:
    """Normalize whitespace while preserving Chinese text."""
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def clean_posts_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare posts for repeatable analysis."""
    result = ensure_standard_columns(df)

    # 中文註解：文字欄位統一轉字串，避免 pandas NaN 影響關鍵字比對。
    for column in TEXT_COLUMNS:
        result[column] = result[column].map(normalize_text)

    # 中文註解：互動數字缺值視為 0，跨平台來源沒有該欄位也能分析。
    for column in COUNT_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0)

    result["published_at_dt"] = pd.to_datetime(result["published_at"], errors="coerce", utc=True)
    result["created_at_dt"] = pd.to_datetime(result["created_at"], errors="coerce", utc=True)
    result["crawled_at_dt"] = pd.to_datetime(result["crawled_at"], errors="coerce", utc=True)
    result["analysis_datetime"] = (
        result["published_at_dt"].fillna(result["created_at_dt"]).fillna(result["crawled_at_dt"])
    )
    analysis_datetime_naive = result["analysis_datetime"].dt.tz_convert(None)
    result["date"] = analysis_datetime_naive.dt.date
    result["week"] = analysis_datetime_naive.dt.to_period("W").astype(str)
    result["title_length"] = result["title"].str.len()
    result["content_length"] = result["content"].str.len()

    dedupe_keys = ["source", "platform", "external_id"]
    result = result.drop_duplicates(subset=dedupe_keys, keep="first")

    # 中文註解：content_hash 只有在有值時才參與去重，避免空值文章被誤刪。
    hashed = result["content_hash"].notna() & (result["content_hash"].astype(str).str.len() > 0)
    result = pd.concat(
        [
            result.loc[hashed].drop_duplicates(subset=["content_hash"], keep="first"),
            result.loc[~hashed],
        ],
        ignore_index=True,
    )
    return result
