"""Document Extraction 模型测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.document_extraction.models import (
    DocumentExtractionConfig,
    DocumentExtractionDefaults,
    DocumentArchiveConfig,
    DocumentCandidate,
    ExtractedDocument,
    FailedDocument,
    DocumentExtractionHealth,
    build_canonical_key,
    compute_content_hash,
    compute_document_hash,
    infer_source_type_from_path,
    infer_mime_type,
    SOURCE_TYPE_OFFICIAL_FILING_PDF,
    SOURCE_TYPE_LOCAL_DOCUMENT,
    EXTRACTION_STATUS_SUCCESS,
    EXTRACTION_QUALITY_HIGH,
)


class TestComputeHash:
    """测试哈希计算函数。"""

    def test_compute_content_hash_stable(self):
        """content_hash 应该是稳定的。"""
        text = "Hello, World!"
        hash1 = compute_content_hash(text)
        hash2 = compute_content_hash(text)
        assert hash1 == hash2

    def test_compute_content_hash_different_texts(self):
        """不同的文本应该有不同的 hash。"""
        hash1 = compute_content_hash("Hello")
        hash2 = compute_content_hash("World")
        assert hash1 != hash2

    def test_compute_document_hash_stable(self, sample_txt: Path):
        """document_hash 应该是稳定的。"""
        hash1 = compute_document_hash(sample_txt)
        hash2 = compute_document_hash(sample_txt)
        assert hash1 == hash2


class TestBuildCanonicalKey:
    """测试 canonical_key 构建。"""

    def test_build_canonical_key_format(self):
        """canonical_key 格式应该是 source_id::document_hash。"""
        key = build_canonical_key("source1", "abc123")
        assert key == "source1::abc123"


class TestInferSourceType:
    """测试文件类型推断。"""

    def test_infer_from_pdf(self):
        """PDF 文件应该推断为 official_filing_pdf。"""
        assert infer_source_type_from_path("test.pdf") == SOURCE_TYPE_OFFICIAL_FILING_PDF

    def test_infer_from_txt(self):
        """TXT 文件应该推断为 local_document。"""
        assert infer_source_type_from_path("test.txt") == SOURCE_TYPE_LOCAL_DOCUMENT

    def test_infer_from_unknown(self):
        """未知扩展名应该返回 unknown。"""
        assert infer_source_type_from_path("test.xyz") == "unknown"


class TestInferMimeType:
    """测试 MIME type 推断。"""

    def test_infer_pdf_mime(self):
        """PDF 应该返回 application/pdf。"""
        assert infer_mime_type("test.pdf") == "application/pdf"

    def test_infer_html_mime(self):
        """HTML 应该返回 text/html。"""
        assert infer_mime_type("test.html") == "text/html"

    def test_infer_txt_mime(self):
        """TXT 应该返回 text/plain。"""
        assert infer_mime_type("test.txt") == "text/plain"


class TestDocumentExtractionDefaults:
    """测试 DocumentExtractionDefaults。"""

    def test_defaults_values(self):
        """测试默认值。"""
        defaults = DocumentExtractionDefaults()
        assert defaults.max_documents == 20
        assert defaults.save_raw is True
        assert defaults.save_markdown is True
        assert defaults.save_metadata is True
        assert defaults.extract_text is True
        assert defaults.extract_tables is False
        assert defaults.ocr_enabled is False


class TestDocumentExtractionConfig:
    """测试 DocumentExtractionConfig。"""

    def test_config_creation(self):
        """测试配置创建。"""
        config = DocumentExtractionConfig(
            source_id="test_source",
            source_name="Test Source",
            source_type=SOURCE_TYPE_LOCAL_DOCUMENT,
            input_path="/tmp/docs",
            enabled=True,
        )
        assert config.source_id == "test_source"
        assert config.enabled is True
        assert config.ocr_enabled is None  # 未设置，使用 default


class TestDocumentCandidate:
    """测试 DocumentCandidate。"""

    def test_candidate_creation(self):
        """测试候选创建。"""
        candidate = DocumentCandidate(
            source_id="test",
            source_type=SOURCE_TYPE_LOCAL_DOCUMENT,
            document_path="/tmp/test.txt",
            document_title="Test Document",
        )
        assert candidate.source_id == "test"
        assert candidate.document_title == "Test Document"
        assert candidate.legal_profile == "unknown"  # 默认值


class TestExtractedDocument:
    """测试 ExtractedDocument。"""

    def test_extracted_document_creation(self):
        """测试抽取文档创建。"""
        doc = ExtractedDocument(
            document_id="doc1",
            source_id="test",
            source_type=SOURCE_TYPE_LOCAL_DOCUMENT,
            document_title="Test",
            content_hash="abc",
            document_hash="def",
            canonical_key="test::def",
            extraction_status=EXTRACTION_STATUS_SUCCESS,
            extraction_quality=EXTRACTION_QUALITY_HIGH,
            created_at="2024-01-01T00:00:00Z",
        )
        assert doc.document_id == "doc1"
        assert doc.extraction_status == EXTRACTION_STATUS_SUCCESS
