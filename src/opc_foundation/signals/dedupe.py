"""Lightweight deduplication for RawSignal lists."""
from __future__ import annotations

import hashlib
import re

from pydantic import BaseModel

from .raw_signal_schema import RawSignal
from ..web.url_utils import canonicalize_url


def normalize_url(url: str) -> str:
    """规范化 URL，委托给 web.url_utils.canonicalize_url 统一处理。"""
    return canonicalize_url(url)


def hash_url(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()[:16]


def hash_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(cleaned.encode()).hexdigest()[:16]


class DedupeResult(BaseModel):
    unique_signals: list[RawSignal]
    duplicate_signals: list[RawSignal]
    duplicate_count: int


def dedupe_by_url_hash(signals: list[RawSignal]) -> DedupeResult:
    seen: set[str] = set()
    unique: list[RawSignal] = []
    duplicates: list[RawSignal] = []
    for sig in signals:
        key = sig.url_hash or (hash_url(sig.source_url) if sig.source_url else None)
        if key is None:
            unique.append(sig)
            continue
        if key in seen:
            duplicates.append(sig)
        else:
            seen.add(key)
            unique.append(sig)
    return DedupeResult(unique_signals=unique, duplicate_signals=duplicates, duplicate_count=len(duplicates))


def dedupe_by_content_hash(signals: list[RawSignal]) -> DedupeResult:
    seen: set[str] = set()
    unique: list[RawSignal] = []
    duplicates: list[RawSignal] = []
    for sig in signals:
        key = sig.content_hash or hash_text(sig.raw_text)
        if key in seen:
            duplicates.append(sig)
        else:
            seen.add(key)
            unique.append(sig)
    return DedupeResult(unique_signals=unique, duplicate_signals=duplicates, duplicate_count=len(duplicates))


def dedupe_raw_signals(
    signals: list[RawSignal],
    by: str = "url",
) -> DedupeResult:
    """Deduplicate by 'url', 'content', or 'both' (url first, then content)."""
    if by == "url":
        return dedupe_by_url_hash(signals)
    if by == "content":
        return dedupe_by_content_hash(signals)
    # both
    result1 = dedupe_by_url_hash(signals)
    result2 = dedupe_by_content_hash(result1.unique_signals)
    all_dupes = result1.duplicate_signals + result2.duplicate_signals
    return DedupeResult(
        unique_signals=result2.unique_signals,
        duplicate_signals=all_dupes,
        duplicate_count=len(all_dupes),
    )
