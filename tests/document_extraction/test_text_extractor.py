"""Text Extractor 测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.document_extraction.extractors.text import TextExtractor
from opc_foundation.document_extraction.models import DocumentCandidate


class TestTextExtractor:
    """TextExtractor 测试。"""

    def test_can_extract_txt_file(self, sample_txt: Path):
        """应该能识别 TXT 文件。"""
        extractor = TextExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="local_document",
            document_path=str(sample_txt),
            file_extension=".txt",
        )
        assert extractor.can_extract(candidate) is True

    def test_cannot_extract_pdf(self, sample_pdf: Path):
        """不应该能识别 PDF 文件。"""
        extractor = TextExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="official_filing_pdf",
            document_path=str(sample_pdf),
            file_extension=".pdf",
        )
        assert extractor.can_extract(candidate) is False

    def test_extract_sample_txt(self, sample_txt: Path):
        """应该能成功抽取 sample TXT。"""
        extractor = TextExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="local_document",
            document_path=str(sample_txt),
            file_extension=".txt",
        )
        result = extractor.extract(candidate)

        assert result.document_id is not None
        assert result.document_hash is not None
        assert result.extraction_status == "success"
        assert result.char_count is not None
        assert result.char_count > 0
        assert result.word_count is not None
        assert result.word_count > 0
