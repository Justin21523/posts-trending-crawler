"""Application settings loaded from environment and config files."""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class CrawlerSettings(BaseModel):
    """Crawler behavior settings."""

    rate_limit_per_second: float = 2.0
    detail_rate_limit_per_second: float = 1.0
    batch_size: int = 100
    batch_rest_interval: int = 5
    max_retries: int = 3
    retry_backoff_factor: int = 2
    popular_mode: bool = False


class DatabaseSettings(BaseModel):
    """Database connection settings."""

    url: str = "sqlite:///data/dcard_crawler.db"


class LoggingSettings(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file: str = "logs/crawler.log"


class CheckpointSettings(BaseModel):
    """Checkpoint persistence settings."""

    file: str = "data/checkpoint.json"


class EndpointSettings(BaseModel):
    """API endpoint patterns."""

    forum_posts: str = "/forums/{forum_alias}/posts"
    post_detail: str = "/posts/{post_id}"
    browser_fallback: list[str] = Field(
        default_factory=lambda: ["/service/api/v2/forums", "/service/api/v2/posts"]
    )


class Settings(BaseModel):
    """Root application settings."""

    dcard_api_base_url: str = "https://www.dcard.tw/service/api/v2"
    dcard_forum_alias: str = "trending"
    dcard_base_url: str = "https://www.dcard.tw"
    ssl_verify: bool = True  # Set False for self-signed cert environments

    crawler: CrawlerSettings = Field(default_factory=CrawlerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    checkpoint: CheckpointSettings = Field(default_factory=CheckpointSettings)
    endpoints: EndpointSettings = Field(default_factory=EndpointSettings)

    @classmethod
    def from_config_file(cls, config_path: str | None = None) -> "Settings":
        """Load settings from YAML config file with env var overrides."""
        default_path = (
            Path(__file__).resolve().parent.parent.parent
            / "configs"
            / "crawler.yaml"
        )
        config_path = config_path or os.getenv(
            "CRAWLER_CONFIG", str(default_path)
        )

        settings = cls()

        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                data = yaml.safe_load(f)

            if "crawler" in data:
                settings.crawler = CrawlerSettings(**data["crawler"])
            if "database" in data:
                settings.database = DatabaseSettings(**data["database"])
            if "logging" in data:
                settings.logging = LoggingSettings(**data["logging"])
            if "checkpoint" in data:
                settings.checkpoint = CheckpointSettings(**data["checkpoint"])
            if "endpoints" in data:
                settings.endpoints = EndpointSettings(**data["endpoints"])

        # Override with environment variables if present
        if os.getenv("DATABASE_URL"):
            settings.database.url = os.getenv("DATABASE_URL", settings.database.url)

        return settings


# Global settings instance
settings = Settings.from_config_file()
