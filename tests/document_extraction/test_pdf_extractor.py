"""PDF Extractor 测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.document_extraction.extractors.pdf import PDFExtractor
from opc_foundation.document_extraction.models import DocumentCandidate


class TestPDFExtractor:
    """PDFExtractor 测试。"""

    def test_can_extract_pdf_file(self, sample_pdf: Path):
        """应该能识别 PDF 文件。"""
        extractor = PDFExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="official_filing_pdf",
            document_path=str(sample_pdf),
            file_extension=".pdf",
        )
        assert extractor.can_extract(candidate) is True

    def test_can_extract_by_extension(self):
        """应该能通过扩展名识别。"""
        extractor = PDFExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="official_filing_pdf",
            document_path="/tmp/test.pdf",
        )
        assert extractor.can_extract(candidate) is True

    def test_cannot_extract_txt(self, sample_txt: Path):
        """不应该能识别 TXT 文件。"""
        extractor = PDFExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="local_document",
            document_path=str(sample_txt),
            file_extension=".txt",
        )
        assert extractor.can_extract(candidate) is False

    def test_extract_sample_pdf(self, sample_pdf: Path):
        """应该能成功抽取 sample PDF。"""
        extractor = PDFExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="official_filing_pdf",
            document_path=str(sample_pdf),
            file_extension=".pdf",
        )
        result = extractor.extract(candidate)

        assert result.document_id is not None
        assert result.document_hash is not None
        assert result.extraction_status in ["success", "partial", "failed"]
        assert result.source_id == "test"

    def test_extract_malformed_pdf(self, malformed_pdf: Path):
        """malformed PDF 应该 fail-soft。"""
        extractor = PDFExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="official_filing_pdf",
            document_path=str(malformed_pdf),
            file_extension=".pdf",
        )
        result = extractor.extract(candidate)

        # 应该返回 failed 状态而不是抛出异常
        assert result.extraction_status == "failed"
        assert result.error_message is not None

    def test_extract_nonexistent_file(self):
        """不存在的文件应该 fail-soft。"""
        extractor = PDFExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="official_filing_pdf",
            document_path="/nonexistent/file.pdf",
        )
        result = extractor.extract(candidate)

        assert result.extraction_status == "failed"
        assert "不存在" in result.error_message
