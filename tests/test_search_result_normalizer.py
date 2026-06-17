"""Test search result normalizer."""
from opc_foundation.search.search_result_normalizer import (
    normalize_results, extract_domain, canonicalize_url, is_example_domain, result_hash
)
from opc_foundation.search.search_schema import SearchResult
from opc_foundation.run.time_utils import utcnow_iso


def _r(url, rank=1):
    return SearchResult(result_id=f"r{rank}", provider="tavily", query="q",
                        url=url, rank=rank, fetched_at=utcnow_iso())


def test_extract_domain():
    assert extract_domain("https://www.example.com/page") == "example.com"
    assert extract_domain("https://aitool.io/review") == "aitool.io"


def test_canonicalize_url():
    assert canonicalize_url("HTTPS://Example.COM/page/") == "https://Example.COM/page"


def test_example_domain_filtered():
    results = [_r("https://example.com/test"), _r("https://real.io/article", 2)]
    normalized = normalize_results(results, filter_example_domains=True)
    assert len(normalized) == 1
    assert normalized[0].url == "https://real.io/article"


def test_url_deduplication():
    results = [_r("https://real.io/article"), _r("https://real.io/article", 2), _r("https://other.io/", 3)]
    normalized = normalize_results(results, deduplicate_urls=True)
    assert len(normalized) == 2


def test_result_domain_set():
    results = [_r("https://news.ai-tools.io/article")]
    normalized = normalize_results(results)
    assert normalized[0].result_domain == "news.ai-tools.io"


def test_no_filter_keeps_example():
    results = [_r("https://example.com/test")]
    normalized = normalize_results(results, filter_example_domains=False)
    assert len(normalized) == 1


def test_result_hash_deterministic():
    h1 = result_hash("https://example.com/page")
    h2 = result_hash("https://example.com/page")
    assert h1 == h2


def test_is_example_domain():
    assert is_example_domain("https://example.com/x")
    assert not is_example_domain("https://real.io/x")