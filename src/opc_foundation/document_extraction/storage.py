"""Document Extraction Foundation 的存储模块。

功能说明（小白解读）：
    本文件负责将抽取结果写入磁盘：
    - documents.jsonl        所有文档的索引（全量）
    - documents.latest.jsonl 最新抽取的文档索引
    - source_health.jsonl   源健康状态
    - failed_queue.jsonl    失败队列
    - run_log.jsonl         运行日志
    - metadata sidecar     每个文档的元数据文件

    目录结构：
        archive_root/
            raw/           原始文件副本
            text/          纯文本版本
            markdown/      markdown 版本
            metadata/       元数据 sidecar
            index/
                documents.jsonl
                documents.latest.jsonl
                source_health.jsonl
                failed_queue.jsonl
                run_log.jsonl
            reports/
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    DocumentExtractionHealth,
    DocumentExtractionRunResult,
    ExtractedDocument,
    FailedDocument,
)

# 存储文件名常量
FILENAME_DOCUMENTS = "documents.jsonl"
FILENAME_DOCUMENTS_LATEST = "documents.latest.jsonl"
FILENAME_SOURCE_HEALTH = "source_health.jsonl"
FILENAME_FAILED_QUEUE = "failed_queue.jsonl"
FILENAME_RUN_LOG = "run_log.jsonl"


def get_archive_root(archive_root: str | Path) -> Path:
    """获取归档根目录 Path 对象。"""
    return Path(archive_root)


def ensure_index_dir(archive_root: Path) -> Path:
    """确保索引目录存在，返回索引目录 Path。"""
    index_dir = archive_root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir


def ensure_data_dirs(archive_root: Path) -> dict[str, Path]:
    """确保所有数据子目录存在。"""
    dirs = {
        "raw": archive_root / "raw",
        "text": archive_root / "text",
        "markdown": archive_root / "markdown",
        "metadata": archive_root / "metadata",
        "reports": archive_root / "reports",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


# ---------------------------------------------------------------------------
# 文档索引操作
# ---------------------------------------------------------------------------


def load_documents_index(archive_root: Path) -> dict[str, ExtractedDocument]:
    """加载现有文档索引（全量）。"""
    index_file = archive_root / "index" / FILENAME_DOCUMENTS
    if not index_file.exists():
        return {}

    documents = {}
    with open(index_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                doc = ExtractedDocument(**data)
                documents[doc.canonical_key] = doc
            except Exception:
                continue

    return documents


def append_document_index(archive_root: Path, document: ExtractedDocument) -> None:
    """追加一条文档到 documents.jsonl。"""
    index_file = archive_root / "index" / FILENAME_DOCUMENTS
    ensure_index_dir(archive_root)

    with open(index_file, "a", encoding="utf-8") as f:
        f.write(document.model_dump_json() + "\n")


def write_documents_latest(
    archive_root: Path,
    documents: dict[str, ExtractedDocument],
) -> None:
    """写入 documents.latest.jsonl（最新快照）。"""
    index_file = archive_root / "index" / FILENAME_DOCUMENTS_LATEST
    ensure_index_dir(archive_root)

    with open(index_file, "w", encoding="utf-8") as f:
        for doc in documents.values():
            f.write(doc.model_dump_json() + "\n")


# ---------------------------------------------------------------------------
# 健康状态操作
# ---------------------------------------------------------------------------


def append_source_health(archive_root: Path, health: DocumentExtractionHealth) -> None:
    """追加源健康状态到 source_health.jsonl。"""
    index_file = archive_root / "index" / FILENAME_SOURCE_HEALTH
    ensure_index_dir(archive_root)

    with open(index_file, "a", encoding="utf-8") as f:
        f.write(health.model_dump_json() + "\n")


def load_source_health_index(archive_root: Path) -> dict[str, DocumentExtractionHealth]:
    """加载源健康状态索引（只保留每个 source 最新的）。"""
    index_file = archive_root / "index" / FILENAME_SOURCE_HEALTH
    if not index_file.exists():
        return {}

    health_map: dict[str, DocumentExtractionHealth] = {}
    with open(index_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                health = DocumentExtractionHealth(**data)
                # 保留最新的
                existing = health_map.get(health.source_id)
                if existing is None or health.checked_at > existing.checked_at:
                    health_map[health.source_id] = health
            except Exception:
                continue

    return health_map


# ---------------------------------------------------------------------------
# 失败队列操作
# ---------------------------------------------------------------------------


def append_failed_queue(archive_root: Path, failed: FailedDocument) -> None:
    """追加失败条目到 failed_queue.jsonl。"""
    index_file = archive_root / "index" / FILENAME_FAILED_QUEUE
    ensure_index_dir(archive_root)

    with open(index_file, "a", encoding="utf-8") as f:
        f.write(failed.model_dump_json() + "\n")


def load_failed_queue(archive_root: Path) -> list[FailedDocument]:
    """加载失败队列。"""
    index_file = archive_root / "index" / FILENAME_FAILED_QUEUE
    if not index_file.exists():
        return []

    failed_list = []
    with open(index_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                failed = FailedDocument(**data)
                failed_list.append(failed)
            except Exception:
                continue

    return failed_list


# ---------------------------------------------------------------------------
# 运行日志操作
# ---------------------------------------------------------------------------


def append_run_log(archive_root: Path, result: DocumentExtractionRunResult) -> None:
    """追加运行日志到 run_log.jsonl。"""
    index_file = archive_root / "index" / FILENAME_RUN_LOG
    ensure_index_dir(archive_root)

    with open(index_file, "a", encoding="utf-8") as f:
        f.write(result.model_dump_json() + "\n")


# ---------------------------------------------------------------------------
# 元数据 sidecar 操作
# ---------------------------------------------------------------------------


def save_metadata_sidecar(
    archive_root: Path,
    document: ExtractedDocument,
    metadata: dict[str, Any],
) -> str | None:
    """保存文档元数据到 sidecar 文件。

    返回：
        元数据文件路径，如果保存失败则返回 None
    """
    if not document.metadata_path:
        return None

    metadata_file = archive_root / "metadata" / document.metadata_path
    metadata_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        return str(metadata_file)
    except Exception:
        return None


def save_raw_copy(
    archive_root: Path,
    source_path: str,
    canonical_key: str,
) -> str | None:
    """复制原始文件到 raw 目录。

    返回：
        原始文件副本路径，如果保存失败则返回 None
    """
    source = Path(source_path)
    if not source.exists():
        return None

    # 使用 canonical_key 的一部分作为文件名
    safe_key = canonical_key.replace(":", "_")[:64]
    dest_name = f"{safe_key}{source.suffix}"
    dest_path = archive_root / "raw" / dest_name

    try:
        import shutil

        shutil.copy2(source, dest_path)
        return str(dest_path)
    except Exception:
        return None


def save_text_file(
    archive_root: Path,
    text: str,
    document_id: str,
    extension: str = ".txt",
) -> str | None:
    """保存纯文本到 text 目录。

    返回：
        文本文件路径，如果保存失败则返回 None
    """
    dest_path = archive_root / "text" / f"{document_id}{extension}"

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(text)
        return str(dest_path)
    except Exception:
        return None


def save_markdown_file(
    archive_root: Path,
    markdown: str,
    document_id: str,
) -> str | None:
    """保存 markdown 到 markdown 目录。

    返回：
        markdown 文件路径，如果保存失败则返回 None
    """
    dest_path = archive_root / "markdown" / f"{document_id}.md"

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        return str(dest_path)
    except Exception:
        return None
