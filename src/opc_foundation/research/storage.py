"""Research Source Foundation 的本地归档存储层。

功能说明（小白解读）：
    - 为每篇文档生成稳定目录名（日期_source_slug_title_slug）
    - 写 metadata.json / document.md / document.html / raw.html
    - 追加写 index/documents.jsonl
    - 覆盖写 index/documents.latest.jsonl
    - 追加写 state/failed_queue.jsonl / state/run_log.jsonl / state/source_health.jsonl

    所有写入用 UTF-8，中文不转义（ensure_ascii=False）。
    所有写入尽量原子化（tempfile + os.replace）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from ..run.time_utils import utcnow_iso
from ..storage.path_utils import ensure_parent
from .dedupe import document_id_for
from .markdown import build_document_markdown
from .models import (
    DocumentCandidate,
    ExtractedResearchContent,
    FailedDocument,
    NormalizedDocument,
    ResearchArchiveConfig,
)


# 非法文件名字符（Windows 下更严格，这里统一处理）
_INVALID_FS = re.compile(r'[\\/:*?"<>|\r\n\t]+')
_WS = re.compile(r"\s+")


def sanitize_filename(text: str, max_len: int = 40, default: str = "untitled") -> str:
    """把一段文本转成合法的文件名片段（保留中英文、数字、常见符号）。

    参数：
        text:    原始文本
        max_len: 最大长度（按字符算）
        default: 文本为空时的兜底名

    返回：
        清洗后的文件名片段
    """
    if not text:
        return default
    cleaned = _INVALID_FS.sub(" ", text).strip()
    cleaned = _WS.sub("-", cleaned)
    cleaned = cleaned.strip("-.")
    if not cleaned:
        return default
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip("-")
    return cleaned or default


def document_directory(
    archive_root: str | Path,
    published_at: str | None,
    source_name: str | None,
    title: str,
    fallback_datetime: datetime | None = None,
) -> Path:
    """为一篇文档生成稳定、可读、无非法字符的本地目录。

    目录结构：
        <archive_root>/documents/YYYY/MM/<YYYY-MM-DD>__<source>__<title-slug>/

    参数：
        archive_root:      归档根目录
        published_at:      发布时间（ISO 字符串）
        source_name:       source 名称
        title:             文档标题
        fallback_datetime: 没有发布时间时的兜底时间

    返回：
        Path 对象
    """
    root = Path(archive_root)
    try:
        if published_at:
            date_part = re.split(r"[T ]", published_at.strip(), maxsplit=1)[0]
            y, m, d = date_part.split("-")
        else:
            raise ValueError("no date")
    except Exception:
        now = fallback_datetime or datetime.now()
        y, m, d = f"{now.year:04d}", f"{now.month:02d}", f"{now.day:02d}"

    dir_name = (
        f"{y}-{m}-{d}__"
        f"{sanitize_filename(source_name or 'unknown', max_len=30)}__"
        f"{sanitize_filename(title, max_len=40)}"
    )
    return root / "documents" / y / m / dir_name


# ---------------------------------------------------------------------------
# 原子化文件写入
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """原子写文件：先写到临时文件，再 rename 过去，避免写入过程中断造成半文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    """原子写二进制文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# JSONL 写入
# ---------------------------------------------------------------------------


def append_jsonl(path: str | Path, record: dict[str, Any] | object) -> None:
    """追加写一行 JSON 到 JSONL 文件。

    参数：
        path:   文件路径
        record: dict 或 pydantic 模型对象
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(record, dict):
        line = json.dumps(record, ensure_ascii=False)
    elif hasattr(record, "model_dump_json"):
        line = record.model_dump_json(exclude_none=True)
    else:
        line = json.dumps(record, ensure_ascii=False, default=str)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def overwrite_jsonl(path: str | Path, records: list[dict[str, Any]] | list[object]) -> None:
    """覆盖写 JSONL 文件（用于 documents.latest.jsonl 等）。

    参数：
        path:    文件路径
        records: 记录列表
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for record in records:
        if isinstance(record, dict):
            lines.append(json.dumps(record, ensure_ascii=False))
        elif hasattr(record, "model_dump_json"):
            lines.append(record.model_dump_json(exclude_none=True))
        else:
            lines.append(json.dumps(record, ensure_ascii=False, default=str))
    _atomic_write(p, "\n".join(lines) + ("\n" if lines else ""))


def load_jsonl(path: str | Path, model_cls: type | None = None) -> list[Any]:
    """读取 JSONL 文件，返回 dict 列表或模型对象列表。

    参数：
        path:      文件路径
        model_cls: 若提供，会把每行 dict 转成该 pydantic 模型

    返回：
        记录列表
    """
    p = Path(path)
    if not p.exists():
        return []
    out: list[Any] = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if model_cls is not None:
                    out.append(model_cls(**data))
                else:
                    out.append(data)
            except Exception:
                continue
    return out


# ---------------------------------------------------------------------------
# 核心归档函数
# ---------------------------------------------------------------------------


def compute_content_hash(text: str) -> str:
    """计算正文的 SHA256 hash（前 32 位），用于去重和审计。"""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:32]


def archive_document(
    candidate: DocumentCandidate,
    extracted: ExtractedResearchContent,
    config: ResearchArchiveConfig,
    *,
    raw_html: str | None = None,
    captured_at: str | None = None,
    document_id: str | None = None,
    status: str = "saved",
    error: str | None = None,
) -> NormalizedDocument:
    """把一篇候选文档归档到本地文件系统。

    参数：
        candidate:   候选文档
        extracted:   抽取结果
        config:      全局配置
        raw_html:    原始 HTML（可选，保存为 raw.html）
        captured_at: 抓取时间（ISO 字符串），为空则用当前 UTC
        document_id: 文档 ID，为空则基于 canonical_url 生成
        status:      saved / partial / failed / skipped / duplicate
        error:       失败时的错误信息

    返回：
        NormalizedDocument 对象
    """
    captured = captured_at or utcnow_iso()
    doc_id = document_id or document_id_for(candidate)
    title = (extracted.title or candidate.title or "（无标题）").strip()
    content_hash = compute_content_hash(extracted.text or extracted.html or title)

    # 生成归档目录
    doc_dir = document_directory(
        config.archive_root,
        candidate.published_at or extracted.published_at,
        candidate.source_name,
        title,
    )
    doc_dir.mkdir(parents=True, exist_ok=True)

    # 准备各文件路径
    md_path = doc_dir / "document.md"
    html_path = doc_dir / "document.html"
    raw_path = doc_dir / "raw.html"
    metadata_path = doc_dir / "metadata.json"

    # 写 Markdown
    markdown_text = build_document_markdown(
        candidate,
        extracted,
        metadata={
            "captured_at": captured,
            "document_id": doc_id,
        },
    )
    if config.defaults.save_markdown:
        _atomic_write(md_path, markdown_text)

    # 写清洗后 HTML
    if config.defaults.save_html and extracted.html:
        _atomic_write(html_path, extracted.html)

    # 写原始 HTML
    if config.defaults.save_raw and raw_html:
        _atomic_write(raw_path, raw_html)

    # 写 metadata.json
    metadata = _build_metadata(
        candidate=candidate,
        extracted=extracted,
        doc_id=doc_id,
        captured_at=captured,
        content_hash=content_hash,
        status=status,
        error=error,
        markdown_path=str(md_path) if config.defaults.save_markdown else None,
        html_path=str(html_path) if config.defaults.save_html and extracted.html else None,
        raw_path=str(raw_path) if config.defaults.save_raw and raw_html else None,
    )
    _atomic_write(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2))

    # 构建 NormalizedDocument
    doc = NormalizedDocument(
        document_id=doc_id,
        source_id=candidate.source_id,
        source_name=candidate.source_name,
        source_type=candidate.source_type,
        title=title,
        url=candidate.url,
        canonical_url=candidate.canonical_url,
        published_at=extracted.published_at or candidate.published_at,
        captured_at=captured,
        updated_at=None,
        author=extracted.author or candidate.author,
        summary=extracted.summary or candidate.summary,
        language=extracted.language or candidate.language,
        content_type="article",
        legal_profile=candidate.legal_profile,
        tags=list(candidate.tags),
        content_hash=content_hash,
        status=status,
        markdown_path=str(md_path) if config.defaults.save_markdown else None,
        html_path=str(html_path) if config.defaults.save_html and extracted.html else None,
        raw_path=str(raw_path) if config.defaults.save_raw and raw_html else None,
        metadata_path=str(metadata_path),
        attachments=[],
        extraction_quality=extracted.extraction_quality,
        error=error,
    )

    # 追加写 documents.jsonl
    index_dir = Path(config.archive_root) / "index"
    append_jsonl(index_dir / "documents.jsonl", doc.model_dump(exclude_none=True))

    return doc


def write_latest_documents(
    archive_root: str | Path,
    documents: list[NormalizedDocument],
) -> None:
    """覆盖写 documents.latest.jsonl（本次 run 的 saved/partial 文档）。"""
    index_dir = Path(archive_root) / "index"
    overwrite_jsonl(index_dir / "documents.latest.jsonl", [d.model_dump(exclude_none=True) for d in documents])


def append_failed_document(
    archive_root: str | Path,
    failed: FailedDocument,
) -> None:
    """追加写 failed_queue.jsonl。"""
    state_dir = Path(archive_root) / "state"
    append_jsonl(state_dir / "failed_queue.jsonl", failed.model_dump(exclude_none=True))


def append_run_log(
    archive_root: str | Path,
    record: dict[str, Any],
) -> None:
    """追加写 run_log.jsonl。"""
    state_dir = Path(archive_root) / "state"
    append_jsonl(state_dir / "run_log.jsonl", record)


def append_source_health(
    archive_root: str | Path,
    record: dict[str, Any],
) -> None:
    """追加写 source_health.jsonl。"""
    state_dir = Path(archive_root) / "state"
    append_jsonl(state_dir / "source_health.jsonl", record)


def overwrite_source_health(
    archive_root: str | Path,
    records: list[dict[str, Any]],
) -> None:
    """覆盖写 source_health.jsonl（保留每个 source 最新一条）。"""
    state_dir = Path(archive_root) / "state"
    overwrite_jsonl(state_dir / "source_health.jsonl", records)


def load_failed_queue(archive_root: str | Path) -> list[FailedDocument]:
    """读取 failed_queue.jsonl，返回 FailedDocument 列表。"""
    state_dir = Path(archive_root) / "state"
    return load_jsonl(state_dir / "failed_queue.jsonl", FailedDocument)


def load_source_health(archive_root: str | Path) -> list[dict[str, Any]]:
    """读取 source_health.jsonl，返回 dict 列表。"""
    state_dir = Path(archive_root) / "state"
    return load_jsonl(state_dir / "source_health.jsonl")


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------


def _build_metadata(
    candidate: DocumentCandidate,
    extracted: ExtractedResearchContent,
    doc_id: str,
    captured_at: str,
    content_hash: str,
    status: str,
    error: str | None,
    markdown_path: str | None,
    html_path: str | None,
    raw_path: str | None,
) -> dict[str, Any]:
    """构建 metadata.json 的内容。"""
    return {
        "document_id": doc_id,
        "source_id": candidate.source_id,
        "source_name": candidate.source_name,
        "source_type": candidate.source_type,
        "title": extracted.title or candidate.title,
        "url": candidate.url,
        "canonical_url": candidate.canonical_url,
        "published_at": extracted.published_at or candidate.published_at,
        "captured_at": captured_at,
        "author": extracted.author or candidate.author,
        "summary": extracted.summary or candidate.summary,
        "language": extracted.language or candidate.language,
        "legal_profile": candidate.legal_profile,
        "tags": list(candidate.tags),
        "content_hash": content_hash,
        "status": status,
        "extraction_quality": extracted.extraction_quality,
        "error": error,
        "markdown_path": markdown_path,
        "html_path": html_path,
        "raw_path": raw_path,
        "raw_entry": candidate.raw_entry,
    }


def write_report(archive_root: str | Path, filename: str, content: str) -> Path:
    """写日报文件到 reports/ 目录。

    参数：
        archive_root: 归档根目录
        filename:     文件名（如 daily_capture_2026-06-22.md）
        content:      报告内容

    返回：
        报告文件路径
    """
    reports_dir = Path(archive_root) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    p = reports_dir / filename
    _atomic_write(p, content)
    return p
