"""Simple file-based checkpoint tracker."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ..storage.jsonl_store import JsonlStore
from .time_utils import utcnow_iso


class CheckpointEntry(BaseModel):
    step_name: str
    completed_at: str
    metadata: dict = {}


class Checkpoint:
    """Persist and query completed pipeline steps."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._completed: set[str] = set()
        self._load()

    def _load(self) -> None:
        for entry in JsonlStore.iter_records(self.path, model=CheckpointEntry):
            self._completed.add(entry.step_name)  # type: ignore[union-attr]

    def is_done(self, step_name: str) -> bool:
        return step_name in self._completed

    def mark_done(self, step_name: str, metadata: dict | None = None) -> None:
        entry = CheckpointEntry(
            step_name=step_name,
            completed_at=utcnow_iso(),
            metadata=metadata or {},
        )
        JsonlStore.append_record(self.path, entry)
        self._completed.add(step_name)
