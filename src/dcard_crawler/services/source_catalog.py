"""Source catalog loading and validation."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

CatalogStrategy = Literal["rss", "sitemap", "article", "ptt_board"]


class SourceCatalogEntry(BaseModel):
    """One configured public source target."""

    name: str
    display_name: str
    platform: Literal["news", "ptt", "dcard", "mobile01", "forum"]
    source_type: str
    strategy: CatalogStrategy
    enabled: bool = True
    base_url: str | None = None
    target_url: str | None = None
    board: str | None = None
    robots_url: str | None = None
    default_max_items: int = Field(default=50, ge=1, le=500)
    default_max_pages: int = Field(default=1, ge=1, le=10)
    allow_robots_unavailable: bool = False
    allow_over18_public_confirm: bool = False
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    group: str = ""

    @model_validator(mode="after")
    def validate_target(self) -> "SourceCatalogEntry":
        """Ensure each strategy has the target fields it needs."""
        if self.strategy in {"rss", "sitemap", "article"} and not self.target_url:
            raise ValueError(f"{self.name} requires target_url for strategy={self.strategy}")
        if self.strategy == "ptt_board" and not self.board:
            raise ValueError(f"{self.name} requires board for ptt_board strategy")
        return self


class SourceCatalog(BaseModel):
    """Validated source catalog."""

    groups: dict[str, list[SourceCatalogEntry]]

    @property
    def entries(self) -> list[SourceCatalogEntry]:
        """Flatten all entries with their group name attached."""
        result: list[SourceCatalogEntry] = []
        for group, entries in self.groups.items():
            for entry in entries:
                result.append(entry.model_copy(update={"group": group}))
        return result

    def enabled_entries(self, group: str | None = None) -> list[SourceCatalogEntry]:
        """Return enabled entries, optionally restricted to one group."""
        return [entry for entry in self.select(group=group) if entry.enabled]

    def select(
        self,
        *,
        group: str | None = None,
        names: list[str] | None = None,
        include_disabled: bool = False,
    ) -> list[SourceCatalogEntry]:
        """Select entries by group and/or source names."""
        entries = self.entries
        if group:
            if group not in self.groups:
                raise KeyError(f"Unknown source group: {group}")
            entries = [entry for entry in entries if entry.group == group]
        if names:
            wanted = set(names)
            entries = [entry for entry in entries if entry.name in wanted]
            found = {entry.name for entry in entries}
            missing = sorted(wanted - found)
            if missing:
                raise KeyError(f"Unknown source(s): {', '.join(missing)}")
        if not include_disabled:
            entries = [entry for entry in entries if entry.enabled]
        return entries


def default_catalog_path() -> Path:
    """Return the default source catalog path."""
    return Path(__file__).resolve().parent.parent.parent.parent / "configs" / "sources.yaml"


def load_source_catalog(path: str | Path | None = None) -> SourceCatalog:
    """Load and validate the configured public source catalog."""
    catalog_path = Path(path) if path else default_catalog_path()
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    raw_groups = data.get("groups") or {}
    groups: dict[str, list[SourceCatalogEntry]] = {}
    for group, entries in raw_groups.items():
        groups[group] = [
            SourceCatalogEntry(**entry, group=group)
            for entry in entries
        ]
    return SourceCatalog(groups=groups)
