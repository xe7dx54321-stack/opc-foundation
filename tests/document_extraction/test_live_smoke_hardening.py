"""Document Extraction Live Smoke Hardening 测试。

覆盖：
1. zero-candidate source health = degraded + empty_source
2. malformed PDF enters failed_queue or failed/partial status
3. duplicate run skips duplicates
4. no prohibited investment fields in models/output
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opc_foundation.document_extraction.archiver import DocumentArchiver
from opc_foundation.document_extraction.models import (
    DocumentArchiveConfig,
    DocumentExtractionConfig,
    DocumentExtractionDefaults,
    ExtractedDocument,
    HEALTH_STATUS_DEGRADED,
    HEALTH_STATUS_HEALTHY,
    EXTRACTION_STATUS_SUCCESS,
    EXTRACTION_STATUS_FAILED,
    EXTRACTION_QUALITY_HIGH,
    EXTRACTION_QUALITY_FAILED,
)
from opc_foundation.document_extraction.storage import (
    load_source_health_index,
    load_failed_queue,
    load_documents_index,
)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = PROJECT_ROOT / "tests" / "document_extraction" / "fixtures"


def _make_config(
    archive_root: Path,
    sources: list[DocumentExtractionConfig],
) -> DocumentArchiveConfig:
    """创建测试用配置。"""
    defaults = DocumentExtractionDefaults(
        max_documents=20,
        save_raw=True,
        save_markdown=True,
        save_metadata=True,
        extract_text=True,
        extract_tables=False,
        ocr_enabled=False,
    )
    return DocumentArchiveConfig(
        archive_root=str(archive_root),
        defaults=defaults,
        sources=sources,
    )


# 禁止投资字段列表
PROHIBITED_FIELDS = [
    "affected_tickers",
    "expectation_delta",
    "investment_rating",
    "trade_signal",
    "watchlist",
    "action_decision",
    "recommendation",
    "opportunity_score",
    "risk_score",
    "position_size",
    "target_price",
]


# ---------------------------------------------------------------------------
# 1. zero-candidate source health = degraded + empty_source
# ---------------------------------------------------------------------------


class TestEmptySourceHealth:
    """测试空 source 的 health 语义。"""

    def test_empty_source_is_degraded_with_empty_source(
        self, tmp_path: Path
    ) -> None:
        """enabled + candidate_count = 0 → degraded + empty_source。"""
        archive_root = tmp_path / "archive"
        empty_dir = tmp_path / "empty_docs"
        empty_dir.mkdir()

        source = DocumentExtractionConfig(
            source_id="empty_source_test",
            source_name="Empty Source Test",
            source_type="local_document",
            input_path=str(empty_dir),
            input_glob="*.txt",
            enabled=True,
            legal_profile="user_provided",
            document_type="unknown",
        )

        config = _make_config(archive_root, [source])
        archiver = DocumentArchiver(config)
        result = archiver.run(mode="run")

        # 运行结果中没有文档
        assert result.saved_count == 0
        assert result.failed_count == 0

        # 检查 source health
        health = load_source_health_index(archive_root)
        assert "empty_source_test" in health
        src_health = health["empty_source_test"]
        assert src_health.status == HEALTH_STATUS_DEGRADED
        assert src_health.last_error == "empty_source"

    def test_disabled_empty_source_is_disabled(
        self, tmp_path: Path
    ) -> None:
        """disabled source 无论是否有候选，都是 disabled。"""
        archive_root = tmp_path / "archive"
        empty_dir = tmp_path / "empty_docs"
        empty_dir.mkdir()

        source = DocumentExtractionConfig(
            source_id="disabled_empty_test",
            source_name="Disabled Empty Test",
            source_type="local_document",
            input_path=str(empty_dir),
            input_glob="*.txt",
            enabled=False,
            legal_profile="user_provided",
            document_type="unknown",
        )

        config = _make_config(archive_root, [source])
        archiver = DocumentArchiver(config)
        result = archiver.run(mode="run")

        health = load_source_health_index(archive_root)
        assert "disabled_empty_test" in health
        assert health["disabled_empty_test"].status == "disabled"


# ---------------------------------------------------------------------------
# 2. malformed PDF enters failed_queue or failed/partial status
# ---------------------------------------------------------------------------


class TestMalformedPdfFailSoft:
    """测试损坏 PDF 的 fail-soft 行为。"""

    def test_malformed_pdf_enters_failed_queue(
        self, tmp_path: Path, fixtures_dir: Path
    ) -> None:
        """malformed PDF 应该进入 failed_queue，不拖垮全局。"""
        archive_root = tmp_path / "archive"
        malformed_dir = tmp_path / "malformed_docs"
        malformed_dir.mkdir()

        # 复制 malformed.pdf 到测试目录
        import shutil
        shutil.copy(fixtures_dir / "malformed.pdf", malformed_dir / "malformed.pdf")

        source = DocumentExtractionConfig(
            source_id="malformed_pdf_test",
            source_name="Malformed PDF Test",
            source_type="local_document",
            input_path=str(malformed_dir),
            input_glob="*.pdf",
            enabled=True,
            legal_profile="user_provided",
            document_type="unknown",
        )

        config = _make_config(archive_root, [source])
        archiver = DocumentArchiver(config)
        result = archiver.run(mode="run")

        # 应该有 1 个失败
        assert result.failed_count == 1
        assert result.saved_count == 0

        # 检查 failed_queue
        failed_queue = load_failed_queue(archive_root)
        assert len(failed_queue) == 1
        failed = failed_queue[0]
        assert failed.source_id == "malformed_pdf_test"
        assert failed.error_type is not None
        assert "pdf" in failed.original_path.lower() or "PDF" in failed.original_path

    def test_malformed_pdf_does_not_break_other_docs(
        self, tmp_path: Path, fixtures_dir: Path
    ) -> None:
        """malformed PDF 不影响其他正常文档的抽取。"""
        archive_root = tmp_path / "archive"
        mixed_dir = tmp_path / "mixed_docs"
        mixed_dir.mkdir()

        import shutil
        shutil.copy(fixtures_dir / "sample.txt", mixed_dir / "sample.txt")
        shutil.copy(fixtures_dir / "malformed.pdf", mixed_dir / "malformed.pdf")

        source = DocumentExtractionConfig(
            source_id="mixed_test",
            source_name="Mixed Test",
            source_type="local_document",
            input_path=str(mixed_dir),
            input_glob="*.*",
            enabled=True,
            legal_profile="user_provided",
            document_type="unknown",
        )

        config = _make_config(archive_root, [source])
        archiver = DocumentArchiver(config)
        result = archiver.run(mode="run")

        # sample.txt 应该成功，malformed.pdf 应该失败
        assert result.saved_count >= 1
        assert result.failed_count >= 1

        # source 应该是 degraded（有失败但不是全失败）
        health = load_source_health_index(archive_root)
        assert "mixed_test" in health
        assert health["mixed_test"].status == HEALTH_STATUS_DEGRADED


# ---------------------------------------------------------------------------
# 3. duplicate run skips duplicates
# ---------------------------------------------------------------------------


class TestDuplicateRun:
    """测试重复运行的去重行为。"""

    def test_second_run_skips_duplicates(
        self, tmp_path: Path, fixtures_dir: Path
    ) -> None:
        """第二次运行时，已存在的文档应被跳过，不重复保存。"""
        archive_root = tmp_path / "archive"
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        import shutil
        shutil.copy(fixtures_dir / "sample.txt", docs_dir / "sample.txt")

        source = DocumentExtractionConfig(
            source_id="dup_test",
            source_name="Duplicate Test",
            source_type="local_document",
            input_path=str(docs_dir),
            input_glob="*.txt",
            enabled=True,
            legal_profile="user_provided",
            document_type="unknown",
        )

        config = _make_config(archive_root, [source])
        archiver = DocumentArchiver(config)

        # 第一次运行
        result1 = archiver.run(mode="run")
        assert result1.saved_count == 1
        assert result1.duplicate_count == 0

        # 第二次运行
        result2 = archiver.run(mode="run")
        assert result2.saved_count == 0
        assert result2.duplicate_count == 1

        # 检查 documents.jsonl 中只有一条记录
        index = load_documents_index(archive_root)
        assert len(index) == 1

    def test_duplicate_run_preserves_existing_documents(
        self, tmp_path: Path, fixtures_dir: Path
    ) -> None:
        """重复运行后，已存在的文档信息不应被覆盖或丢失。"""
        archive_root = tmp_path / "archive"
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        import shutil
        shutil.copy(fixtures_dir / "sample.txt", docs_dir / "sample.txt")

        source = DocumentExtractionConfig(
            source_id="dup_preserve_test",
            source_name="Duplicate Preserve Test",
            source_type="local_document",
            input_path=str(docs_dir),
            input_glob="*.txt",
            enabled=True,
            legal_profile="user_provided",
            document_type="unknown",
        )

        config = _make_config(archive_root, [source])
        archiver = DocumentArchiver(config)

        # 第一次运行
        result1 = archiver.run(mode="run")
        index1 = load_documents_index(archive_root)
        first_doc_id = list(index1.values())[0].document_id

        # 第二次运行
        result2 = archiver.run(mode="run")
        index2 = load_documents_index(archive_root)

        # document_id 应该保持一致
        assert len(index2) == 1
        assert list(index2.values())[0].document_id == first_doc_id


# ---------------------------------------------------------------------------
# 4. no prohibited investment fields in models/output
# ---------------------------------------------------------------------------


class TestNoProhibitedInvestmentFields:
    """测试模型和输出中不包含禁止的投资判断字段。"""

    def test_extracted_document_model_has_no_prohibited_fields(self) -> None:
        """ExtractedDocument 模型不应包含禁止字段。"""
        doc = ExtractedDocument(
            document_id="test_doc_001",
            source_id="test_source",
            source_type="local_document",
            content_hash="abc123",
            document_hash="def456",
            canonical_key="test::def456",
            created_at="2024-01-01T00:00:00Z",
        )

        doc_dict = doc.model_dump()
        for field in PROHIBITED_FIELDS:
            assert field not in doc_dict, (
                f"ExtractedDocument 不应包含禁止字段: {field}"
            )

    def test_successful_doc_has_no_prohibited_fields(
        self, tmp_path: Path, fixtures_dir: Path
    ) -> None:
        """成功抽取的文档输出中不应包含禁止字段。"""
        archive_root = tmp_path / "archive"
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        import shutil
        shutil.copy(fixtures_dir / "sample.txt", docs_dir / "sample.txt")

        source = DocumentExtractionConfig(
            source_id="noprohib_test",
            source_name="No Prohibited Test",
            source_type="local_document",
            input_path=str(docs_dir),
            input_glob="*.txt",
            enabled=True,
            legal_profile="user_provided",
            document_type="unknown",
        )

        config = _make_config(archive_root, [source])
        archiver = DocumentArchiver(config)
        archiver.run(mode="run")

        # 检查 documents.latest.jsonl 中的文档
        index = load_documents_index(archive_root)
        assert len(index) > 0

        for canonical_key, doc in index.items():
            doc_dict = doc.model_dump()
            for field in PROHIBITED_FIELDS:
                assert field not in doc_dict, (
                    f"文档 {canonical_key} 包含禁止字段: {field}"
                )

    def test_failed_doc_has_no_prohibited_fields(
        self, tmp_path: Path, fixtures_dir: Path
    ) -> None:
        """失败文档的 failed_queue 中也不应包含禁止字段。"""
        archive_root = tmp_path / "archive"
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        import shutil
        shutil.copy(fixtures_dir / "malformed.pdf", docs_dir / "malformed.pdf")

        source = DocumentExtractionConfig(
            source_id="fail_noprohib_test",
            source_name="Failed No Prohibited Test",
            source_type="local_document",
            input_path=str(docs_dir),
            input_glob="*.pdf",
            enabled=True,
            legal_profile="user_provided",
            document_type="unknown",
        )

        config = _make_config(archive_root, [source])
        archiver = DocumentArchiver(config)
        archiver.run(mode="run")

        failed_queue = load_failed_queue(archive_root)
        assert len(failed_queue) > 0

        for failed in failed_queue:
            failed_dict = failed.model_dump()
            for field in PROHIBITED_FIELDS:
                assert field not in failed_dict, (
                    f"失败文档包含禁止字段: {field}"
                )
