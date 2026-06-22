"""测试 research/storage.py —— 归档存储。"""
from __future__ import annotations

import json
from pathlib import Path

from opc_foundation.research.extractor import extract_html_document
from opc_foundation.research.models import (
    DocumentCandidate,
    ResearchArchiveConfig,
    ResearchDefaults,
)
from opc_foundation.research.storage import (
    append_failed_document,
    append_run_log,
    archive_document,
    compute_content_hash,
    document_directory,
    load_failed_queue,
    load_jsonl,
    overwrite_jsonl,
    sanitize_filename,
    write_latest_documents,
    write_report,
)
from opc_foundation.research.models import FailedDocument


def _make_candidate(
    url: str = "https://example.com/article-1",
    title: str = "测试文章标题",
) -> DocumentCandidate:
    return DocumentCandidate(
        source_id="s1",
        source_name="Source 1",
        source_type="rss_feed",
        title=title,
        url=url,
        canonical_url=url,
        published_at="2026-01-15T09:00:00Z",
        legal_profile="official_public",
        tags=["test"],
    )


def _make_config(archive_root: Path) -> ResearchArchiveConfig:
    return ResearchArchiveConfig(
        archive_root=str(archive_root),
        defaults=ResearchDefaults(),
    )


def test_sanitize_filename_basic() -> None:
    """清洗非法字符。"""
    assert sanitize_filename("正常标题") == "正常标题"
    assert sanitize_filename("a/b:c*d?e") == "a-b-c-d-e"
    assert sanitize_filename("") == "untitled"
    assert sanitize_filename("   ") == "untitled"


def test_sanitize_filename_truncates() -> None:
    """超长标题截断。"""
    long_title = "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的标题"
    result = sanitize_filename(long_title, max_len=10)
    assert len(result) <= 10


def test_document_directory_structure(temp_archive_root: Path) -> None:
    """目录结构正确：documents/YYYY/MM/YYYY-MM-DD__source__title/。"""
    doc_dir = document_directory(
        temp_archive_root,
        published_at="2026-01-15T09:00:00Z",
        source_name="Test Source",
        title="测试标题",
    )
    assert "documents" in str(doc_dir)
    assert "2026" in str(doc_dir)
    assert "01" in str(doc_dir)
    assert "2026-01-15" in str(doc_dir)
    assert "Test-Source" in str(doc_dir)


def test_archive_document_writes_files(temp_archive_root: Path, sample_article_html: str) -> None:
    """归档后生成 document.md / document.html / raw.html / metadata.json。"""
    cfg = _make_config(temp_archive_root)
    cand = _make_candidate()
    extracted = extract_html_document(sample_article_html, cand.url)

    doc = archive_document(
        candidate=cand,
        extracted=extracted,
        config=cfg,
        raw_html=sample_article_html,
    )

    # 文件存在
    assert Path(doc.metadata_path).exists()
    assert Path(doc.markdown_path).exists()
    assert Path(doc.html_path).exists()
    assert Path(doc.raw_path).exists()

    # metadata.json 内容正确
    metadata = json.loads(Path(doc.metadata_path).read_text(encoding="utf-8"))
    assert metadata["document_id"] == doc.document_id
    assert metadata["source_id"] == "s1"
    assert metadata["title"] == doc.title


def test_archive_document_appends_documents_jsonl(
    temp_archive_root: Path,
    sample_article_html: str,
) -> None:
    """归档后追加写 documents.jsonl。"""
    cfg = _make_config(temp_archive_root)
    cand = _make_candidate()
    extracted = extract_html_document(sample_article_html, cand.url)

    archive_document(
        candidate=cand,
        extracted=extracted,
        config=cfg,
        raw_html=sample_article_html,
    )

    jsonl_path = temp_archive_root / "index" / "documents.jsonl"
    assert jsonl_path.exists()
    lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["source_id"] == "s1"
    assert record["title"] == cand.title


def test_archive_document_chinese_no_garble(temp_archive_root: Path) -> None:
    """中文标题不乱码。"""
    cfg = _make_config(temp_archive_root)
    cand = _make_candidate(title="中文标题测试")
    from opc_foundation.research.models import ExtractedResearchContent
    extracted = ExtractedResearchContent(
        title="中文标题测试",
        text="正文内容",
        html="<p>正文</p>",
        extraction_quality="medium",
    )

    doc = archive_document(
        candidate=cand,
        extracted=extracted,
        config=cfg,
        raw_html="<html></html>",
    )

    metadata = json.loads(Path(doc.metadata_path).read_text(encoding="utf-8"))
    assert metadata["title"] == "中文标题测试"
    assert "中文" in Path(doc.markdown_path).read_text(encoding="utf-8")


def test_write_latest_documents_overwrites(temp_archive_root: Path) -> None:
    """documents.latest.jsonl 每次覆盖。"""
    from opc_foundation.research.models import NormalizedDocument

    doc1 = NormalizedDocument(
        document_id="rs_1", source_id="s1", source_name="S1", source_type="rss_feed",
        title="t1", url="u1", canonical_url="u1", published_at=None,
        captured_at="2026-01-01T00:00:00Z", updated_at=None, author=None,
        summary=None, language=None, content_type="article", legal_profile="unknown",
        tags=[], content_hash="a", status="saved", markdown_path=None,
        html_path=None, raw_path=None, metadata_path="/tmp/m.json",
        attachments=[], extraction_quality="high", error=None,
    )
    write_latest_documents(temp_archive_root, [doc1])
    latest_path = temp_archive_root / "index" / "documents.latest.jsonl"
    assert latest_path.exists()
    lines = latest_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1

    # 再次写入不同内容
    doc2 = NormalizedDocument(
        document_id="rs_2", source_id="s1", source_name="S1", source_type="rss_feed",
        title="t2", url="u2", canonical_url="u2", published_at=None,
        captured_at="2026-01-01T00:00:00Z", updated_at=None, author=None,
        summary=None, language=None, content_type="article", legal_profile="unknown",
        tags=[], content_hash="b", status="saved", markdown_path=None,
        html_path=None, raw_path=None, metadata_path="/tmp/m.json",
        attachments=[], extraction_quality="high", error=None,
    )
    write_latest_documents(temp_archive_root, [doc2])
    lines = latest_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["document_id"] == "rs_2"


def test_append_failed_document(temp_archive_root: Path) -> None:
    """追加写 failed_queue.jsonl。"""
    failed = FailedDocument(
        source_id="s1",
        source_name="S1",
        source_type="rss_feed",
        title="t",
        url="https://example.com",
        canonical_url="https://example.com",
        failed_at="2026-01-01T00:00:00Z",
        error="test error",
    )
    append_failed_document(temp_archive_root, failed)

    failed_path = temp_archive_root / "state" / "failed_queue.jsonl"
    assert failed_path.exists()
    loaded = load_failed_queue(temp_archive_root)
    assert len(loaded) == 1
    assert loaded[0].error == "test error"


def test_append_run_log(temp_archive_root: Path) -> None:
    """追加写 run_log.jsonl。"""
    append_run_log(temp_archive_root, {"entry_type": "run_summary", "run_id": "r1"})
    log_path = temp_archive_root / "state" / "run_log.jsonl"
    assert log_path.exists()
    records = load_jsonl(log_path)
    assert len(records) == 1
    assert records[0]["run_id"] == "r1"


def test_write_report(temp_archive_root: Path) -> None:
    """写日报文件。"""
    report_path = write_report(
        temp_archive_root,
        "daily_capture_2026-01-15.md",
        "# 测试日报\n\n内容",
    )
    assert report_path.exists()
    assert "测试日报" in report_path.read_text(encoding="utf-8")


def test_compute_content_hash_stable() -> None:
    """content_hash 稳定。"""
    h1 = compute_content_hash("abc")
    h2 = compute_content_hash("abc")
    h3 = compute_content_hash("abd")
    assert h1 == h2
    assert h1 != h3
