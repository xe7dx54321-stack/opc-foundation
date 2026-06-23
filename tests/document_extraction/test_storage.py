"""Storage 测试。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opc_foundation.document_extraction.models import ExtractedDocument
from opc_foundation.document_extraction.storage import (
    ensure_index_dir,
    ensure_data_dirs,
    append_document_index,
    load_documents_index,
    write_documents_latest,
)


class TestEnsureDirs:
    """测试目录创建。"""

    def test_ensure_index_dir(self, temp_archive_dir: Path):
        """应该创建索引目录。"""
        index_dir = ensure_index_dir(temp_archive_dir)
        assert index_dir.exists()
        assert index_dir == temp_archive_dir / "index"

    def test_ensure_data_dirs(self, temp_archive_dir: Path):
        """应该创建所有数据子目录。"""
        dirs = ensure_data_dirs(temp_archive_dir)
        assert dirs["raw"].exists()
        assert dirs["text"].exists()
        assert dirs["markdown"].exists()
        assert dirs["metadata"].exists()
        assert dirs["reports"].exists()


class TestDocumentsIndex:
    """测试文档索引操作。"""

    def test_append_and_load_document(self, temp_archive_dir: Path):
        """应该能追加并加载文档。"""
        # 创建测试文档
        doc = ExtractedDocument(
            document_id="test_doc_1",
            source_id="test",
            source_type="local_document",
            content_hash="abc",
            document_hash="def",
            canonical_key="test::def",
            created_at="2024-01-01T00:00:00Z",
        )

        # 追加
        append_document_index(temp_archive_dir, doc)

        # 加载
        index = load_documents_index(temp_archive_dir)
        assert "test::def" in index
        assert index["test::def"].document_id == "test_doc_1"

    def test_write_and_load_latest(self, temp_archive_dir: Path):
        """应该能写入并加载 latest。"""
        # 创建测试文档
        doc1 = ExtractedDocument(
            document_id="doc1",
            source_id="test",
            source_type="local_document",
            content_hash="abc",
            document_hash="def",
            canonical_key="test::def",
            created_at="2024-01-01T00:00:00Z",
        )
        doc2 = ExtractedDocument(
            document_id="doc2",
            source_id="test",
            source_type="local_document",
            content_hash="ghi",
            document_hash="jkl",
            canonical_key="test::jkl",
            created_at="2024-01-01T00:00:00Z",
        )

        # 写入 latest
        write_documents_latest(temp_archive_dir, {"test::def": doc1, "test::jkl": doc2})

        # 验证文件存在
        latest_file = temp_archive_dir / "index" / "documents.latest.jsonl"
        assert latest_file.exists()
