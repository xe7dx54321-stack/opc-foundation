"""Test WebExtractionRequest / WebExtractionResult / extract_page."""
from unittest.mock import MagicMock, patch
from opc_foundation.web.extraction_interface import (
    WebExtractionRequest, WebExtractionResult, extract_page
)
from opc_foundation.web.url_text_extractor import ExtractedPage
from opc_foundation.run.time_utils import utcnow_iso


def _fake_page(text="Hello world content here.", title="Article Title", errors=None):
    return ExtractedPage(url="https://x.com", title=title, text=text,
                         errors=errors or [], fetched_at=utcnow_iso())


def _fake_extractor(text="Content extracted successfully.", title="Test Page"):
    ext = MagicMock()
    ext.extract.return_value = _fake_page(text=text, title=title)
    return ext


def test_extract_success():
    req = WebExtractionRequest(url="https://example.io/article")
    result = extract_page(req, adapter=_fake_extractor())
    assert result.success is True
    assert result.text == "Content extracted successfully."
    assert result.title == "Test Page"
    assert result.text_chars > 0


def test_extract_empty_text():
    req = WebExtractionRequest(url="https://example.io/empty")
    result = extract_page(req, adapter=_fake_extractor(text=""))
    assert result.success is False


def test_extract_exception_does_not_raise():
    bad_extractor = MagicMock()
    bad_extractor.extract.side_effect = RuntimeError("network failure")
    req = WebExtractionRequest(url="https://example.io/bad")
    result = extract_page(req, adapter=bad_extractor)
    assert result.success is False
    assert len(result.errors) > 0


def test_extract_page_errors_propagated():
    ext = MagicMock()
    ext.extract.return_value = _fake_page(text="Some text", errors=["minor issue"])
    req = WebExtractionRequest(url="https://x.io/article")
    result = extract_page(req, adapter=ext)
    assert result.success is True   # still success if text extracted
    assert "minor issue" in result.errors


def test_request_defaults():
    req = WebExtractionRequest(url="https://example.io")
    assert req.preferred_output == "text"
    assert req.timeout_seconds == 20


def test_result_text_chars_computed():
    req = WebExtractionRequest(url="https://x.io")
    result = extract_page(req, adapter=_fake_extractor(text="abc"))
    assert result.text_chars == 3