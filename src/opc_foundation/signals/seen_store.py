"""SeenStore – persistent incremental dedupe for RawSignal streams."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..run.id_generator import new_id
from ..run.time_utils import utcnow_iso
from ..storage.jsonl_store import JsonlStore
from ..storage.path_utils import ensure_parent
from .dedupe import hash_url, hash_text
from .raw_signal_schema import RawSignal


class SeenSignalRecord(BaseModel):
    record_id: str
    source_id: str
    source_type: str | None = None
    source_url: str | None = None
    url_hash: str | None = None
    content_hash: str | None = None
    first_seen_at: str
    last_seen_at: str
    seen_count: int = 1
    last_run_id: str | None = None
    metadata: dict[str, Any] = {}


class SeenStore:
    """JSONL-backed store tracking which signals have already been seen.

    Lookup priority: url_hash first, content_hash second.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._by_url: dict[str, SeenSignalRecord] = {}
        self._by_content: dict[str, SeenSignalRecord] = {}
        self._all: list[SeenSignalRecord] = []
        self._load()

    def _load(self) -> None:
        for rec in JsonlStore.iter_records(self._path, model=SeenSignalRecord):
            self._index(rec)  # type: ignore[arg-type]

    def _index(self, rec: SeenSignalRecord) -> None:
        self._all.append(rec)
        if rec.url_hash:
            self._by_url[rec.url_hash] = rec
        if rec.content_hash:
            self._by_content[rec.content_hash] = rec

    def _url_hash(self, signal: RawSignal) -> str | None:
        if signal.url_hash:
            return signal.url_hash
        if signal.source_url:
            return hash_url(signal.source_url)
        return None

    def _content_hash(self, signal: RawSignal) -> str | None:
        if signal.content_hash:
            return signal.content_hash
        return hash_text(signal.raw_text)

    def load(self) -> list[SeenSignalRecord]:
        return list(self._all)

    def has_seen(self, signal: RawSignal) -> bool:
        uh = self._url_hash(signal)
        if uh and uh in self._by_url:
            return True
        ch = self._content_hash(signal)
        if ch and ch in self._by_content:
            return True
        return False

    def mark_seen(
        self, signal: RawSignal, run_id: str | None = None
    ) -> SeenSignalRecord:
        uh = self._url_hash(signal)
        ch = self._content_hash(signal)
        now = utcnow_iso()

        # Update existing record if found
        existing = (uh and self._by_url.get(uh)) or (ch and self._by_content.get(ch))
        if existing:
            existing.seen_count += 1
            existing.last_seen_at = now
            existing.last_run_id = run_id
            JsonlStore.append_record(self._path, existing)
            return existing

        rec = SeenSignalRecord(
            record_id=new_id("seen_"),
            source_id=signal.source_id,
            source_type=signal.source_type,
            source_url=signal.source_url,
            url_hash=uh,
            content_hash=ch,
            first_seen_at=now,
            last_seen_at=now,
            last_run_id=run_id,
        )
        ensure_parent(self._path)
        JsonlStore.append_record(self._path, rec)
        self._index(rec)
        return rec

    def filter_new(
        self,
        signals: list[RawSignal],
        run_id: str | None = None,
    ) -> tuple[list[RawSignal], list[RawSignal]]:
        """Return (new_signals, already_seen_signals).

        Already-seen records are updated (seen_count, last_seen_at).
        New signals are marked seen.
        """
        new: list[RawSignal] = []
        already_seen: list[RawSignal] = []
        for sig in signals:
            if self.has_seen(sig):
                already_seen.append(sig)
                self.mark_seen(sig, run_id=run_id)
            else:
                new.append(sig)
                self.mark_seen(sig, run_id=run_id)
        return new, already_seen