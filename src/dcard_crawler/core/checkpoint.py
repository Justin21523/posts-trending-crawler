"""Generic JSON checkpoint store."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class CheckpointStore:
    """Persist checkpoint state keyed by source/job/target."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def make_key(self, source: str, job_type: str, target: str) -> str:
        """Create a stable checkpoint key."""
        return f"{source}:{job_type}:{target}"

    def load(self, source: str, job_type: str, target: str) -> dict[str, Any] | None:
        """Load checkpoint data for a key."""
        data = self._read_all()
        return data.get(self.make_key(source, job_type, target))

    def save(self, source: str, job_type: str, target: str, state: dict[str, Any]) -> None:
        """Save checkpoint data for a key."""
        data = self._read_all()
        payload = dict(state)
        payload["updated_at"] = datetime.now().isoformat()
        data[self.make_key(source, job_type, target)] = payload
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _read_all(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
