"""Checkpoint service for resume functionality."""

import json
from pathlib import Path

from loguru import logger

from dcard_crawler.schemas import Checkpoint
from dcard_crawler.settings import settings


class CheckpointService:
    """Service for saving and loading crawl checkpoints."""

    def __init__(self, checkpoint_file: str | None = None):
        self.checkpoint_file = checkpoint_file or settings.checkpoint.file
        self._ensure_directory()

    def _ensure_directory(self):
        """Ensure checkpoint directory exists."""
        Path(self.checkpoint_file).parent.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: Checkpoint):
        """Save checkpoint to file.

        Args:
            checkpoint: Checkpoint data to save
        """
        try:
            with open(self.checkpoint_file, "w") as f:
                json.dump(checkpoint.model_dump(), f, indent=2)
            logger.info(
                f"Checkpoint saved: {checkpoint.forum_alias} "
                f"last_id={checkpoint.last_post_id}"
            )
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load(self, forum_alias: str, popular_mode: bool = False) -> Checkpoint | None:
        """Load checkpoint from file.

        Args:
            forum_alias: Forum alias to load checkpoint for
            popular_mode: Whether to load popular mode checkpoint

        Returns:
            Checkpoint object or None if not found
        """
        checkpoint_path = Path(self.checkpoint_file)
        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path) as f:
                data = json.load(f)

            # Check if checkpoint matches requested forum and mode
            if data.get("forum_alias") != forum_alias or data.get("popular_mode") != popular_mode:
                logger.warning(
                    f"Checkpoint mismatch: requested {forum_alias} "
                    f"popular={popular_mode}, "
                    f"found {data.get('forum_alias')} "
                    f"popular={data.get('popular_mode')}"
                )
                return None

            return Checkpoint(**data)
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return None

    def clear(self):
        """Clear checkpoint file."""
        checkpoint_path = Path(self.checkpoint_file)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info("Checkpoint cleared")
