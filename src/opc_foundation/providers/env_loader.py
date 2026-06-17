"""Environment variable loader with optional .env file support."""
from __future__ import annotations
import os
from pathlib import Path


def load_env_file(path: str | Path = ".env") -> dict[str, str]:
    """Load KEY=VALUE pairs from a .env file.  Returns {} if file not found.
    Does NOT override already-set environment variables.
    """
    p = Path(path)
    loaded: dict[str, str] = {}
    if not p.exists():
        return loaded
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
                loaded[key] = val
    return loaded


def get_env(key: str) -> str | None:
    """Return env var value or None. Never logs the value."""
    return os.environ.get(key)


def has_env(key: str) -> bool:
    return bool(os.environ.get(key))


def mask_key(key: str) -> str:
    """Return a masked representation for safe logging."""
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "..." + key[-2:]