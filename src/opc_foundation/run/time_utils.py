"""UTC time helpers."""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def parse_iso(ts: str) -> datetime:
    """Parse an ISO-8601 string into a datetime (UTC-aware)."""
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
