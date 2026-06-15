"""Test URL text extractor with a fake extractor."""
from opc_foundation.web.url_text_extractor import ExtractedPage, URLTextExtractor
from opc_foundation.web.trafilatura_extractor import TrafilaturaExtractor
from unittest.mock import patch


def test_extracted_page_defaults():
    page = ExtractedPage(url="https://example.com", text="hello world")
    assert page.url == "https://example.com"
    assert page.fetched_at != ""
    assert page.errors == []


def test_extracted_page_with_error():
    page = ExtractedPage(url="https://x.com", text="", errors=["failed"])
    assert page.errors == ["failed"]


def test_trafilatura_extractor_no_crash_on_bad_url():
    """Extractor must not raise on bad URL."""
    with patch("opc_foundation.web.trafilatura_extractor.trafilatura.fetch_url", return_value=None):
        extractor = TrafilaturaExtractor()
        page = extractor.extract("https://nonexistent.invalid/page")
    assert isinstance(page, ExtractedPage)
    assert len(page.errors) > 0


def test_trafilatura_extractor_returns_text():
    with patch("opc_foundation.web.trafilatura_extractor.trafilatura.fetch_url", return_value="<html><body>Hello world content here</body></html>"):
        with patch("opc_foundation.web.trafilatura_extractor.trafilatura.extract", return_value="Hello world content here"):
            with patch("opc_foundation.web.trafilatura_extractor.trafilatura.extract_metadata", return_value=None):
                extractor = TrafilaturaExtractor()
                page = extractor.extract("https://example.com")
    assert "Hello world" in page.text


def test_trafilatura_extractor_handles_exception():
    with patch("opc_foundation.web.trafilatura_extractor.trafilatura.fetch_url", side_effect=Exception("timeout")):
        extractor = TrafilaturaExtractor()
        page = extractor.extract("https://example.com")
    assert len(page.errors) > 0
    assert page.text == ""
