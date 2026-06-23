"""HTML Extractor 测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.document_extraction.extractors.html import HTMLExtractor
from opc_foundation.document_extraction.models import DocumentCandidate


class TestHTMLExtractor:
    """HTMLExtractor 测试。"""

    def test_can_extract_html_file(self, sample_html: Path):
        """应该能识别 HTML 文件。"""
        extractor = HTMLExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="public_report",
            document_path=str(sample_html),
            file_extension=".html",
        )
        assert extractor.can_extract(candidate) is True

    def test_can_extract_htm_extension(self):
        """应该能识别 .htm 扩展名。"""
        extractor = HTMLExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="public_report",
            document_path="/tmp/test.htm",
        )
        assert extractor.can_extract(candidate) is True

    def test_cannot_extract_txt(self, sample_txt: Path):
        """不应该能识别 TXT 文件。"""
        extractor = HTMLExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="local_document",
            document_path=str(sample_txt),
            file_extension=".txt",
        )
        assert extractor.can_extract(candidate) is False

    def test_extract_sample_html(self, sample_html: Path):
        """应该能成功抽取 sample HTML。"""
        extractor = HTMLExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="public_report",
            document_path=str(sample_html),
            file_extension=".html",
        )
        result = extractor.extract(candidate)

        assert result.document_id is not None
        assert result.document_hash is not None
        assert result.extraction_status == "success"
        assert result.char_count is not None
        assert result.char_count > 0
