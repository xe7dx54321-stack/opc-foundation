"""Markdown Extractor 测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.document_extraction.extractors.markdown import MarkdownExtractor
from opc_foundation.document_extraction.models import DocumentCandidate


class TestMarkdownExtractor:
    """MarkdownExtractor 测试。"""

    def test_can_extract_md_file(self, sample_md: Path):
        """应该能识别 Markdown 文件。"""
        extractor = MarkdownExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="local_document",
            document_path=str(sample_md),
            file_extension=".md",
        )
        assert extractor.can_extract(candidate) is True

    def test_can_extract_markdown_extension(self):
        """应该能识别 .markdown 扩展名。"""
        extractor = MarkdownExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="local_document",
            document_path="/tmp/test.markdown",
        )
        assert extractor.can_extract(candidate) is True

    def test_cannot_extract_txt(self, sample_txt: Path):
        """不应该能识别 TXT 文件。"""
        extractor = MarkdownExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="local_document",
            document_path=str(sample_txt),
            file_extension=".txt",
        )
        assert extractor.can_extract(candidate) is False

    def test_extract_sample_md(self, sample_md: Path):
        """应该能成功抽取 sample Markdown。"""
        extractor = MarkdownExtractor()
        candidate = DocumentCandidate(
            source_id="test",
            source_type="local_document",
            document_path=str(sample_md),
            file_extension=".md",
        )
        result = extractor.extract(candidate)

        assert result.document_id is not None
        assert result.document_hash is not None
        assert result.extraction_status == "success"
        assert result.char_count is not None
        assert result.char_count > 0
