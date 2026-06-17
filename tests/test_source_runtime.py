"""Test SourceRuntime dispatch."""
from unittest.mock import MagicMock
from opc_foundation.sources_v2 import SourceDefinitionV2, SourceRuntime, SourceRunResult
from opc_foundation.search.search_schema import SearchRunResult, SearchResult
from opc_foundation.run.time_utils import utcnow_iso
from opc_foundation.run.id_generator import new_id


def _make_source(source_id, fetch_method, source_type="search",
                 source_category="search_discovery", **kwargs):
    base = dict(
        source_id=source_id, source_name="T", source_type=source_type,
        source_category=source_category, fetch_method=fetch_method,
        trust_tier="medium",
    )
    base.update(kwargs)
    return SourceDefinitionV2(**base)


def _real_results(n=3):
    return [
        SearchResult(
            result_id=new_id("r_"), provider="tavily", query="q",
            url=f"https://example{i}.io/article", rank=i+1,
            fetched_at=utcnow_iso()
        )
        for i in range(n)
    ]


def _mock_search_registry(results_count=3):
    reg = MagicMock()
    reg.search.return_value = SearchRunResult(
        run_id="r1", provider="tavily", query="q",
        results=_real_results(results_count),
        started_at=utcnow_iso()
    )
    return reg


def test_search_source_dispatch():
    search_reg = _mock_search_registry(3)
    runtime = SourceRuntime(search_registry=search_reg)
    source = _make_source("s1", "search_provider",
                          metadata={"queries": ["test query"]})
    result = runtime.run_source(source)
    assert isinstance(result, SourceRunResult)
    assert result.items_count == 3
    assert result.status in ("success", "partial")
    search_reg.search.assert_called_once()


def test_search_source_no_registry():
    runtime = SourceRuntime(search_registry=None)
    source = _make_source("s1", "search_provider",
                          metadata={"queries": ["test"]})
    result = runtime.run_source(source)
    assert "no search_registry" in " ".join(result.errors).lower()


def test_web_extraction_dispatch():
    mock_extractor = MagicMock()
    mock_page = MagicMock()
    mock_page.text = "Extracted content from URL"
    mock_extractor.extract.return_value = mock_page

    source = _make_source("s2", "url_extraction",
                          source_type="webpage", source_category="manual_seed",
                          metadata={"urls": ["https://example.io/article"]})
    runtime = SourceRuntime(web_extractor=mock_extractor)
    result = runtime.run_source(source)
    assert result.items_count == 1


def test_unknown_fetch_method():
    runtime = SourceRuntime()
    source = _make_source("s3", "custom_unknown",
                          source_type="api", source_category="unknown")
    result = runtime.run_source(source)
    assert any("Unknown fetch_method" in e for e in result.errors)


def test_no_queries_warning():
    search_reg = _mock_search_registry()
    runtime = SourceRuntime(search_registry=search_reg)
    source = _make_source("s4", "search_provider", metadata={})
    result = runtime.run_source(source)
    assert any("no queries" in w for w in result.warnings)