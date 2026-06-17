"""Test SearchQuery / SearchResult / SearchRunResult schemas."""
from opc_foundation.search import SearchQuery, SearchResult, SearchRunResult
from opc_foundation.run.time_utils import utcnow_iso


def test_search_query_defaults():
    q = SearchQuery(query="AI tools")
    assert q.max_results == 5
    assert q.provider is None


def test_search_result_valid():
    r = SearchResult(
        result_id="r1", provider="tavily", query="test",
        url="https://example.com/article", rank=1, fetched_at=utcnow_iso()
    )
    assert r.url == "https://example.com/article"
    assert r.rank == 1


def test_search_run_result_empty():
    sr = SearchRunResult(
        run_id="run1", provider="tavily", query="test", started_at=utcnow_iso()
    )
    assert sr.results == []
    assert sr.errors == []


def test_search_run_result_with_results():
    r = SearchResult(result_id="r1", provider="brave", query="q",
                     url="https://news.example.com/", rank=1, fetched_at=utcnow_iso())
    sr = SearchRunResult(run_id="r", provider="brave", query="q",
                         results=[r], started_at=utcnow_iso())
    assert len(sr.results) == 1