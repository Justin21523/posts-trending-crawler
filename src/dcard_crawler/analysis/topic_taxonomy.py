"""Topic taxonomy for portfolio keyword and topic analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dcard_crawler.core.text_utils import normalize_text


@dataclass(frozen=True)
class TopicKeyword:
    keyword: str
    aliases: tuple[str, ...] = ()
    weight: float = 1.0


@dataclass(frozen=True)
class TopicDefinition:
    topic_id: str
    topic_name: str
    topic_name_en: str
    color: str
    keywords: tuple[TopicKeyword, ...]


TOPIC_TAXONOMY: tuple[TopicDefinition, ...] = (
    TopicDefinition(
        topic_id="ai_tech",
        topic_name="AI / 科技",
        topic_name_en="AI / Technology",
        color="#2563eb",
        keywords=(
            TopicKeyword("AI", ("人工智慧", "AI應用")),
            TopicKeyword("生成式AI", ("GenAI", "生成 AI")),
            TopicKeyword("ChatGPT", ("聊天機器人",)),
            TopicKeyword("Python"),
            TopicKeyword("資料科學", ("Data Science",)),
            TopicKeyword("機器學習", ("ML",)),
            TopicKeyword("雲端", ("Cloud",)),
            TopicKeyword("資安", ("資訊安全",)),
            TopicKeyword("開源", ("Open Source",)),
            TopicKeyword("API"),
            TopicKeyword("自動化"),
            TopicKeyword("MLOps"),
        ),
    ),
    TopicDefinition(
        topic_id="semiconductor",
        topic_name="半導體 / 供應鏈",
        topic_name_en="Semiconductor / Supply Chain",
        color="#0f766e",
        keywords=(
            TopicKeyword("台積電", ("TSMC",)),
            TopicKeyword("半導體"),
            TopicKeyword("晶片", ("IC",)),
            TopicKeyword("先進製程"),
            TopicKeyword("封裝"),
            TopicKeyword("供應鏈"),
            TopicKeyword("電子業"),
            TopicKeyword("AI伺服器"),
            TopicKeyword("晶圓"),
            TopicKeyword("庫存"),
        ),
    ),
    TopicDefinition(
        topic_id="career",
        topic_name="職涯 / 求職",
        topic_name_en="Career / Job Search",
        color="#f59e0b",
        keywords=(
            TopicKeyword("工作"),
            TopicKeyword("面試"),
            TopicKeyword("履歷"),
            TopicKeyword("轉職"),
            TopicKeyword("職缺"),
            TopicKeyword("工程師"),
            TopicKeyword("資料分析師"),
            TopicKeyword("產品經理"),
            TopicKeyword("實習"),
            TopicKeyword("職涯"),
        ),
    ),
    TopicDefinition(
        topic_id="salary_workstyle",
        topic_name="薪資 / 工作型態",
        topic_name_en="Salary / Work Style",
        color="#0891b2",
        keywords=(
            TopicKeyword("薪資"),
            TopicKeyword("年薪"),
            TopicKeyword("加班"),
            TopicKeyword("遠端工作"),
            TopicKeyword("混合辦公"),
            TopicKeyword("工時"),
            TopicKeyword("福利"),
            TopicKeyword("升遷"),
            TopicKeyword("接案"),
            TopicKeyword("自由工作者"),
        ),
    ),
    TopicDefinition(
        topic_id="finance_investing",
        topic_name="投資 / 財經",
        topic_name_en="Finance / Investing",
        color="#16a34a",
        keywords=(
            TopicKeyword("投資"),
            TopicKeyword("股票"),
            TopicKeyword("ETF"),
            TopicKeyword("美股"),
            TopicKeyword("台股"),
            TopicKeyword("升息"),
            TopicKeyword("通膨"),
            TopicKeyword("匯率"),
            TopicKeyword("財報"),
            TopicKeyword("景氣"),
        ),
    ),
    TopicDefinition(
        topic_id="public_policy",
        topic_name="公共議題",
        topic_name_en="Public Issues",
        color="#dc2626",
        keywords=(
            TopicKeyword("政策"),
            TopicKeyword("選舉"),
            TopicKeyword("交通"),
            TopicKeyword("能源"),
            TopicKeyword("房價"),
            TopicKeyword("租屋"),
            TopicKeyword("教育"),
            TopicKeyword("醫療"),
            TopicKeyword("社會住宅"),
            TopicKeyword("少子化"),
        ),
    ),
    TopicDefinition(
        topic_id="lifestyle_consumer",
        topic_name="生活 / 消費",
        topic_name_en="Lifestyle / Consumer",
        color="#7c3aed",
        keywords=(
            TopicKeyword("旅遊"),
            TopicKeyword("美食"),
            TopicKeyword("電商"),
            TopicKeyword("手機"),
            TopicKeyword("電動車"),
            TopicKeyword("信用卡"),
            TopicKeyword("健身"),
            TopicKeyword("租屋生活"),
            TopicKeyword("通勤"),
            TopicKeyword("消費"),
        ),
    ),
    TopicDefinition(
        topic_id="platform_social",
        topic_name="平台 / 社群事件",
        topic_name_en="Platforms / Social Signals",
        color="#64748b",
        keywords=(
            TopicKeyword("Dcard"),
            TopicKeyword("PTT"),
            TopicKeyword("Mobile01"),
            TopicKeyword("社群"),
            TopicKeyword("炎上"),
            TopicKeyword("熱門文章"),
            TopicKeyword("留言"),
            TopicKeyword("輿情"),
        ),
    ),
)


def all_topic_keywords() -> list[dict[str, Any]]:
    """Return flattened keyword metadata for matching and UI."""
    rows: list[dict[str, Any]] = []
    for topic in TOPIC_TAXONOMY:
        for item in topic.keywords:
            rows.append(
                {
                    "topic_id": topic.topic_id,
                    "topic_name": topic.topic_name,
                    "topic_name_en": topic.topic_name_en,
                    "color": topic.color,
                    "keyword": item.keyword,
                    "aliases": list(item.aliases),
                    "weight": item.weight,
                    "terms": [item.keyword, *item.aliases],
                }
            )
    return rows


def topic_by_id(topic_id: str) -> TopicDefinition | None:
    return next((topic for topic in TOPIC_TAXONOMY if topic.topic_id == topic_id), None)


def classify_text(text: str) -> list[dict[str, Any]]:
    """Return keyword matches grouped by taxonomy topic."""
    normalized = normalize_text(text)
    matches: list[dict[str, Any]] = []
    for row in all_topic_keywords():
        count = 0
        for term in row["terms"]:
            count += normalized.count(normalize_text(term))
        if count:
            matches.append({**row, "match_count": count})
    return matches


def topic_metadata(topic_id: str) -> dict[str, Any]:
    topic = topic_by_id(topic_id)
    if not topic:
        return {
            "topic_id": topic_id,
            "topic_name": topic_id,
            "topic_name_en": topic_id,
            "color": "#64748b",
            "keywords": [],
        }
    return {
        "topic_id": topic.topic_id,
        "topic_name": topic.topic_name,
        "topic_name_en": topic.topic_name_en,
        "color": topic.color,
        "keywords": [item.keyword for item in topic.keywords],
    }
