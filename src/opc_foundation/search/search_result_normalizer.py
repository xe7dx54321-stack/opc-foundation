"""Normalize, de-duplicate, and clean SearchResult lists."""
from __future__ import annotations
import hashlib
from urllib.parse import urlparse, urlunparse
from .search_schema import SearchResult

_EXAMPLE_DOMAINS = {"example.com", "example.org", "example.net"}


def extract_domain(url: str) -> str | None:
    try:
        return urlparse(url).netloc.lower().lstrip("www.") or None
    except Exception:
        return None


def canonicalize_url(url: str) -> str:
    try:
        p = urlparse(url.strip())
        norm = p._replace(fragment="", scheme=p.scheme.lower())
        return urlunparse(norm).rstrip("/")
    except Exception:
        return url.strip()


def result_hash(url: str) -> str:
    return hashlib.sha256(canonicalize_url(url).encode()).hexdigest()[:16]


def is_example_domain(url: str) -> bool:
    domain = extract_domain(url)
    return domain in _EXAMPLE_DOMAINS if domain else False


def normalize_results(
    results: list[SearchResult],
    filter_example_domains: bool = True,
    deduplicate_urls: bool = True,
) -> list[SearchResult]:
    """Return cleaned and de-duplicated results.

    - Sets result_domain on every item.
    - Optionally filters example.com / example.org / example.net.
    - Optionally removes duplicate canonical URLs.
    - Does NOT apply business-domain relevance filtering.
    """
    seen_hashes: set[str] = set()
    out: list[SearchResult] = []

    for r in results:
        domain = extract_domain(r.url)
        r_copy = r.model_copy(update={"result_domain": domain})

        if filter_example_domains and domain in _EXAMPLE_DOMAINS:
            continue

        if deduplicate_urls:
            h = result_hash(r.url)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

        out.append(r_copy)

    return out