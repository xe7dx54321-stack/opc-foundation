"""Test Manual URL connector with a fake extractor."""
from pathlib import Path
from opc_foundation.sources.connectors.manual_url import ManualUrlConnector
from opc_foundation.sources.source_schema import SourceQuery, SourceDefinition
from opc_foundation.run.run_context import RunContext
from opc_foundation.web.url_text_extractor import ExtractedPage


class FakeExtractor:
    def extract(self, url: str) -> ExtractedPage:
        return ExtractedPage(url=url, title="Fake Title", text=f"Extracted text from {url}")


def _source():
    return SourceDefinition(
        source_id="manual_urls", source_name="Manual", source_type="manual_url", connector="manual_url"
    )


def _context():
    return RunContext(pipeline_name="test")


def test_fetch_from_csv(tmp_path):
    csv = tmp_path / "urls.csv"
    csv.write_text("url,source_type,source_name,title,collection_query,notes\nhttps://example.com,web,Ex,T1,q1,note1\n", encoding="utf-8")
    connector = ManualUrlConnector(extractor=FakeExtractor())
    q = SourceQuery(query_id="q1", source_id="manual_urls", url=str(csv), max_items=10)
    result = connector.fetch(q, _source(), _context())
    assert len(result.raw_signals) == 1
    assert result.raw_signals[0].source_url == "https://example.com"
    assert "Extracted text" in result.raw_signals[0].raw_text


def test_missing_csv_returns_error():
    connector = ManualUrlConnector()
    q = SourceQuery(query_id="q1", source_id="manual_urls", url="/nonexistent.csv", max_items=5)
    result = connector.fetch(q, _source(), _context())
    assert len(result.errors) > 0
    assert len(result.raw_signals) == 0


def test_no_extractor_uses_notes(tmp_path):
    csv = tmp_path / "urls.csv"
    csv.write_text("url,source_type,source_name,title,collection_query,notes\nhttps://example.com,web,Ex,T,q,my notes\n", encoding="utf-8")
    connector = ManualUrlConnector(extractor=None)
    q = SourceQuery(query_id="q1", source_id="manual_urls", url=str(csv), max_items=10)
    result = connector.fetch(q, _source(), _context())
    assert len(result.raw_signals) == 1
    assert result.raw_signals[0].raw_text == "my notes"


def test_does_not_raise_on_extractor_failure(tmp_path):
    class BrokenExtractor:
        def extract(self, url):
            raise RuntimeError("network failure")

    csv = tmp_path / "urls.csv"
    csv.write_text("url,source_type,source_name,title,collection_query,notes\nhttps://example.com,web,Ex,T,q,fallback\n", encoding="utf-8")
    connector = ManualUrlConnector(extractor=BrokenExtractor())
    q = SourceQuery(query_id="q1", source_id="manual_urls", url=str(csv), max_items=10)
    result = connector.fetch(q, _source(), _context())
    # Should not raise; errors captured
    assert isinstance(result.errors, list)
