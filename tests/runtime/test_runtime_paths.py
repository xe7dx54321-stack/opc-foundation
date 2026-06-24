"""Runtime paths 测试。

覆盖：
1. build_archive_paths returns expected paths
2. build_archive_paths supports Windows-like paths
3. ensure_archive_dirs creates directories
"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.runtime.paths import (
    ArchivePaths,
    build_archive_paths,
    ensure_archive_dirs,
)


def test_build_archive_paths_documents(tmp_path: Path) -> None:
    """build_archive_paths 应返回正确的 documents 路径。"""
    paths = build_archive_paths(
        archive_root=tmp_path,
        primary_index_name="documents.jsonl",
        latest_index_name="documents.latest.jsonl",
    )
    assert paths.archive_root == tmp_path
    assert paths.index_dir == tmp_path / "index"
    assert paths.reports_dir == tmp_path / "reports"
    assert paths.primary_index == tmp_path / "index" / "documents.jsonl"
    assert paths.latest_index == tmp_path / "index" / "documents.latest.jsonl"
    assert paths.source_health == tmp_path / "index" / "source_health.jsonl"
    assert paths.failed_queue == tmp_path / "index" / "failed_queue.jsonl"
    assert paths.run_log == tmp_path / "index" / "run_log.jsonl"


def test_build_archive_paths_filings(tmp_path: Path) -> None:
    """build_archive_paths 应支持 filings 路径。"""
    paths = build_archive_paths(
        archive_root=tmp_path,
        primary_index_name="filings.jsonl",
        latest_index_name="filings.latest.jsonl",
    )
    assert paths.primary_index == tmp_path / "index" / "filings.jsonl"
    assert paths.latest_index == tmp_path / "index" / "filings.latest.jsonl"


def test_build_archive_paths_windows_style() -> None:
    """build_archive_paths 应支持 Windows 风格路径。"""
    paths = build_archive_paths(
        archive_root="C:\\data\\research_archive",
        primary_index_name="documents.jsonl",
        latest_index_name="documents.latest.jsonl",
    )
    # 在 Windows 上 Path 会自动处理反斜杠
    assert "research_archive" in str(paths.archive_root)
    assert paths.index_dir.name == "index"
    assert paths.primary_index.name == "documents.jsonl"


def test_build_archive_paths_relative() -> None:
    """build_archive_paths 应支持相对路径。"""
    paths = build_archive_paths(
        archive_root="./data/research_archive",
        primary_index_name="documents.jsonl",
        latest_index_name="documents.latest.jsonl",
    )
    assert paths.primary_index.name == "documents.jsonl"
    assert paths.index_dir.name == "index"


def test_build_archive_paths_returns_frozen() -> None:
    """ArchivePaths 应该是 frozen dataclass。"""
    paths = build_archive_paths(
        archive_root="/tmp/test",
        primary_index_name="documents.jsonl",
        latest_index_name="documents.latest.jsonl",
    )
    try:
        paths.archive_root = Path("/other")  # type: ignore[misc]
        assert False, "应该抛出 FrozenInstanceError"
    except AttributeError:
        pass  # frozen dataclass 在 Python 3.11+ 抛 AttributeError


def test_ensure_archive_dirs(tmp_path: Path) -> None:
    """ensure_archive_dirs 应创建 index 和 reports 目录。"""
    paths = build_archive_paths(
        archive_root=tmp_path / "archive",
        primary_index_name="documents.jsonl",
        latest_index_name="documents.latest.jsonl",
    )
    # 目录还不存在
    assert not paths.index_dir.exists()
    assert not paths.reports_dir.exists()

    # 创建目录
    ensure_archive_dirs(paths)

    # 目录应该存在
    assert paths.index_dir.exists()
    assert paths.reports_dir.exists()


def test_ensure_archive_dirs_idempotent(tmp_path: Path) -> None:
    """ensure_archive_dirs 重复调用不应报错。"""
    paths = build_archive_paths(
        archive_root=tmp_path / "archive",
        primary_index_name="documents.jsonl",
        latest_index_name="documents.latest.jsonl",
    )
    ensure_archive_dirs(paths)
    ensure_archive_dirs(paths)  # 不应报错
    assert paths.index_dir.exists()
