"""RunLog – step-level execution logging."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..storage.jsonl_store import JsonlStore
from .time_utils import utcnow_iso


class RunLogEntry(BaseModel):
    run_id: str
    step_name: str
    status: str
    started_at: str
    ended_at: str | None = None
    input_count: int | None = None
    output_count: int | None = None
    errors: list[str] = []
    warnings: list[str] = []
    metadata: dict[str, Any] = {}


class RunLog:
    """Manages in-memory step log entries and persists to JSONL."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._entries: list[RunLogEntry] = []
        self._open: dict[str, RunLogEntry] = {}

    def start_step(self, step_name: str) -> RunLogEntry:
        entry = RunLogEntry(
            run_id=self.run_id,
            step_name=step_name,
            status="running",
            started_at=utcnow_iso(),
        )
        self._open[step_name] = entry
        return entry

    def end_step(
        self,
        step_name: str,
        status: str = "ok",
        input_count: int | None = None,
        output_count: int | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> RunLogEntry | None:
        entry = self._open.pop(step_name, None)
        if entry is None:
            return None
        entry.ended_at = utcnow_iso()
        entry.status = status
        if input_count is not None:
            entry.input_count = input_count
        if output_count is not None:
            entry.output_count = output_count
        if errors:
            entry.errors = errors
        if warnings:
            entry.warnings = warnings
        self._entries.append(entry)
        return entry

    def write_run_log(self, path: str | Path) -> None:
        """Persist all completed log entries to JSONL."""
        JsonlStore.write_records(path, self._entries)

    @staticmethod
    def load_run_log(path: str | Path) -> list[RunLogEntry]:
        """Load persisted log entries from JSONL."""
        return JsonlStore.load_records(path, model=RunLogEntry)  # type: ignore[return-value]
