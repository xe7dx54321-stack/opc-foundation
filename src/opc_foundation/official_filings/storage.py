"""Official Filing Foundation 的本地归档存储层。

功能说明（小白解读）：
    负责把披露元数据和原始内容保存到本地文件系统。

    目录结构：
        data/official_filings/
          raw/
            sec/
            cninfo/
            hkex/
          html/
          pdf_metadata/
          metadata/
          index/
            filings.jsonl
            filings.latest.jsonl
            source_health.jsonl
            failed_queue.jsonl
            run_log.jsonl
          reports/

    核心能力：
        1. filings.jsonl append（全量索引，追加写）
        2. filings.latest.jsonl 最新快照（覆盖写）
        3. source_health.jsonl（已在 health.py 中实现）
        4. failed_queue.jsonl（失败队列）
        5. run_log.jsonl（运行日志）
        6. dedupe by canonical_key / content_hash
        7. metadata sidecar（每个 filing 的元数据 JSON）

    所有写入用 UTF-8，中文不转义（ensure_ascii=False）。
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from ..run.time_utils import utcnow_iso
from ..storage.jsonl_store import JsonlStore
from ..storage.path_utils import ensure_parent
from .dedupe import build_canonical_key, content_hash_for, filing_id_for
from .models import (
    FailedFiling,
    FilingArchiveConfig,
    FilingCandidate,
    FilingRunResult,
    FILING_STATUS_DUPLICATE,
    FILING_STATUS_FAILED,
    FILING_STATUS_SAVED,
    NormalizedFiling,
)


# 非法文件名字符
_INVALID_FS = re.compile(r'[\\/:*?"<>|\t]+')

_WS = re.compile(r"\s+")


def sanitize_filename(text: str, max_len: int = 40, default: str = "untitled") -> str:
    """把一段文本转成合法的文件名片段。

    参数：
        text:    原始文本
        max_len: 最大长度
        default: 空文本时的兜底名

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


def _filings_path(archive_root: str | Path) -> Path:
    return Path(archive_root) / "index" / "filings.jsonl"


def _filings_latest_path(archive_root: str | Path) -> Path:
    return Path(archive_root) / "index" / "filings.latest.jsonl"


def _failed_queue_path(archive_root: str | Path) -> Path:
    return Path(archive_root) / "index" / "failed_queue.jsonl"


def _run_log_path(archive_root: str | Path) -> Path:
    return Path(archive_root) / "index" / "run_log.jsonl"


def _raw_dir(archive_root: str | Path, source_type: str) -> Path:
    return Path(archive_root) / "raw" / source_type


def _metadata_dir(archive_root: str | Path) -> Path:
    return Path(archive_root) / "metadata"


# ---------------------------------------------------------------------------
# 加载索引
# ---------------------------------------------------------------------------


def load_filings_index(
    archive_root: str | Path,
) -> dict[str, NormalizedFiling]:
    """加载 filings.latest.jsonl 作为当前索引。

    参数：
        archive_root: 归档根目录

    返回：
        {canonical_key: NormalizedFiling} 字典
    """
    path = _filings_latest_path(archive_root)
    records = JsonlStore.load_records(path, model=NormalizedFiling)
    result: dict[str, NormalizedFiling] = {}
    for r in records:
        if isinstance(r, NormalizedFiling):
            result[r.canonical_key] = r
    return result


def load_failed_queue(
    archive_root: str | Path,
) -> list[FailedFiling]:
    """加载失败队列。

    参数：
        archive_root: 归档根目录

    返回：
        FailedFiling 列表
    """
    path = _failed_queue_path(archive_root)
    records = JsonlStore.load_records(path, model=FailedFiling)
    return [r for r in records if isinstance(r, FailedFiling)]


# ---------------------------------------------------------------------------
# 写入归档
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, data: Any) -> None:
    """原子化写 JSON 文件（tempfile + os.replace）。"""
    ensure_parent(path)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp_", dir=str(path.parent), suffix=".json"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def save_raw_response(
    archive_root: str | Path,
    source_type: str,
    filing_id: str,
    content: str | bytes,
    ext: str = "json",
) -> str:
    """保存原始响应文件。

    参数：
        archive_root: 归档根目录
        source_type:  source 类型
        filing_id:    filing ID
        content:      原始内容
        ext:          文件扩展名

    返回：
        保存后的相对路径
    """
    raw_dir = _raw_dir(archive_root, source_type)
    file_path = raw_dir / f"{filing_id}.{ext}"
    ensure_parent(file_path)

    if isinstance(content, bytes):
        with open(file_path, "wb") as fh:
            fh.write(content)
    else:
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(content)

    return str(file_path.relative_to(Path(archive_root)))


def save_metadata_sidecar(
    archive_root: str | Path,
    filing: NormalizedFiling,
) -> str:
    """保存元数据 sidecar JSON。

    参数：
        archive_root: 归档根目录
        filing:       标准化披露

    返回：
        保存后的相对路径
    """
    meta_dir = _metadata_dir(archive_root)
    file_path = meta_dir / f"{filing.filing_id}.json"
    _atomic_write_json(file_path, filing.model_dump(mode="json"))
    return str(file_path.relative_to(Path(archive_root)))


# ---------------------------------------------------------------------------
# 索引维护
# ---------------------------------------------------------------------------


def append_filing_index(
    archive_root: str | Path,
    filing: NormalizedFiling,
) -> None:
    """追加一条 filing 记录到 filings.jsonl。"""
    JsonlStore.append_record(_filings_path(archive_root), filing)


def write_filings_latest(
    archive_root: str | Path,
    filings: dict[str, NormalizedFiling] | list[NormalizedFiling],
) -> None:
    """覆盖写 filings.latest.jsonl。

    参数：
        archive_root: 归档根目录
        filings:      当前所有 filing（dict 或 list）
    """
    if isinstance(filings, dict):
        records = list(filings.values())
    else:
        records = filings
    JsonlStore.write_records(_filings_latest_path(archive_root), records, overwrite=True)


def append_failed_queue(
    archive_root: str | Path,
    failed: FailedFiling,
) -> None:
    """追加一条失败记录到 failed_queue.jsonl。"""
    JsonlStore.append_record(_failed_queue_path(archive_root), failed)


def append_run_log(
    archive_root: str | Path,
    run_result: FilingRunResult,
) -> None:
    """追加一条运行日志到 run_log.jsonl。"""
    JsonlStore.append_record(_run_log_path(archive_root), run_result)


# ---------------------------------------------------------------------------
# 归档处理
# ---------------------------------------------------------------------------


def process_candidate(
    candidate: FilingCandidate,
    config: FilingArchiveConfig,
    existing_index: dict[str, NormalizedFiling],
) -> tuple[NormalizedFiling, bool]:
    """处理一个候选披露，生成 NormalizedFiling。

    参数：
        candidate:      候选披露
        config:         整体配置
        existing_index: 现有索引（用于去重判断）

    返回：
        (normalized_filing, is_new)
        is_new=True 表示是新披露，is_new=False 表示重复
    """
    canonical_key = build_canonical_key(candidate)
    filing_id = filing_id_for(candidate)
    content_hash = content_hash_for(candidate)
    now_str = utcnow_iso()

    # 检查重复
    if canonical_key in existing_index:
        existing = existing_index[canonical_key]
        # 相同 content_hash 就是完全重复
        if existing.content_hash == content_hash:
            dup = NormalizedFiling(
                **existing.model_dump(exclude={"status", "updated_at"}),
                status=FILING_STATUS_DUPLICATE,
                updated_at=now_str,
            )
            return dup, False
        # content_hash 不同，视为更新
        else:
            updated = NormalizedFiling(
                **candidate.model_dump(),
                filing_id=existing.filing_id,
                content_hash=content_hash,
                canonical_key=canonical_key,
                metadata_path=existing.metadata_path,
                created_at=existing.created_at,
                updated_at=now_str,
                status=FILING_STATUS_SAVED,
            )
            return updated, True

    # 新披露
    filing = NormalizedFiling(
        **candidate.model_dump(),
        filing_id=filing_id,
        content_hash=content_hash,
        canonical_key=canonical_key,
        metadata_path=f"metadata/{filing_id}.json",
        created_at=now_str,
        status=FILING_STATUS_SAVED,
    )
    return filing, True


def archive_filing(
    archive_root: str | Path,
    filing: NormalizedFiling,
    raw_content: str | bytes | None = None,
    raw_ext: str = "json",
) -> NormalizedFiling:
    """执行归档：写索引、写元数据、写原始内容（如果提供）。

    参数：
        archive_root: 归档根目录
        filing:       标准化披露
        raw_content:  原始响应内容（可选）
        raw_ext:      原始文件扩展名

    返回：
        更新后的 NormalizedFiling（含路径信息）
    """
    # 保存原始内容
    if raw_content is not None:
        raw_path = save_raw_response(
            archive_root, filing.source_type, filing.filing_id, raw_content, raw_ext
        )
        filing.raw_path = raw_path

    # 保存元数据 sidecar
    meta_path = save_metadata_sidecar(archive_root, filing)
    filing.metadata_path = meta_path

    # 追加到全量索引
    append_filing_index(archive_root, filing)

    return filing
