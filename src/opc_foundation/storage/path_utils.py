"""Path helpers shared across storage modules."""
from __future__ import annotations

from pathlib import Path


def ensure_parent(path: str | Path) -> Path:
    """Create parent directories if they don't exist; return Path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def resolve_path(path: str | Path) -> Path:
    """Return an absolute Path."""
    return Path(path).resolve()
