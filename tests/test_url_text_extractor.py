"""Test URL text extractor with a fake extractor."""
from opc_foundation.web.url_text_extractor import ExtractedPage, URLTextExtractor
from opc_foundation.web.trafilatura_extractor import TrafilaturaExtractor
from unittest.mock import patch, MagicMock


def _make_mock_httpx_client(text: str = "", exc: Exception | None = None):
    """创建 mock httpx.Client，模拟 with 语句上下文管理器。

    参数：
        text: mock 响应的 body 文本
        exc: 如果提供，get() 方法抛出此异常

    返回：
        MagicMock 对象，可替代 httpx.Client 使用
    """
    mock_resp = MagicMock()
    mock_resp.text = text
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    if exc:
        mock_client.get.side_effect = exc
    else:
        mock_client.get.return_value = mock_resp
    return mock_client


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
    mock_client = _make_mock_httpx_client(text="")
    with patch("opc_foundation.web.trafilatura_extractor.httpx.Client", return_value=mock_client):
        with patch("opc_foundation.web.trafilatura_extractor.trafilatura.extract_metadata", return_value=None):
            with patch("opc_foundation.web.trafilatura_extractor.trafilatura.extract", return_value=""):
                extractor = TrafilaturaExtractor()
                page = extractor.extract("https://nonexistent.invalid/page")
    assert isinstance(page, ExtractedPage)
    assert len(page.errors) > 0


def test_trafilatura_extractor_returns_text():
    mock_client = _make_mock_httpx_client(text="<html><body>Hello world content here</body></html>")
    with patch("opc_foundation.web.trafilatura_extractor.validate_url", return_value=None):
        with patch("opc_foundation.web.trafilatura_extractor.httpx.Client", return_value=mock_client):
            with patch("opc_foundation.web.trafilatura_extractor.trafilatura.extract", return_value="Hello world content here"):
                with patch("opc_foundation.web.trafilatura_extractor.trafilatura.extract_metadata", return_value=None):
                    extractor = TrafilaturaExtractor()
                    page = extractor.extract("https://example.com")
    assert "Hello world" in page.text


def test_trafilatura_extractor_handles_exception():
    mock_client = _make_mock_httpx_client(exc=Exception("timeout"))
    with patch("opc_foundation.web.trafilatura_extractor.validate_url", return_value=None):
        with patch("opc_foundation.web.trafilatura_extractor.httpx.Client", return_value=mock_client):
            extractor = TrafilaturaExtractor()
            page = extractor.extract("https://example.com")
    assert len(page.errors) > 0
    assert page.text == ""
