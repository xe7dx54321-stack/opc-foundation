"""Document Extraction Foundation 的去重模块。

功能说明（小白解读）：
    本文件负责判断文档是否重复：
    - 使用 canonical_key + document_hash 判断
    - canonical_key = source_id::document_hash
    - 同一个 source 中的同一份文件（相同 hash）被视为重复
"""
from __future__ import annotations

from pathlib import Path

from .models import (
    ExtractedDocument,
    build_canonical_key,
    compute_document_hash,
)


def is_duplicate(
    candidate_path: str | Path,
    source_id: str,
    existing_index: dict[str, ExtractedDocument],
) -> tuple[bool, ExtractedDocument | None]:
    """判断文档是否重复。

    参数：
        candidate_path: 待检查的文件路径
        source_id:      源 ID
        existing_index: 现有文档索引 {canonical_key: ExtractedDocument}

    返回：
        (is_duplicate, existing_document)
        如果是重复的，返回 (True, 已存在的文档)
        如果不是重复的，返回 (False, None)
    """
    path = Path(candidate_path)

    if not path.exists():
        return False, None

    try:
        document_hash = compute_document_hash(path)
    except Exception:
        return False, None

    canonical_key = build_canonical_key(source_id, document_hash)
    existing = existing_index.get(canonical_key)

    if existing:
        return True, existing

    return False, None


def build_canonical_key_from_candidate(
    source_id: str,
    document_path: str | Path | None = None,
    document_hash: str | None = None,
) -> str | None:
    """从候选构建 canonical_key。

    参数：
        source_id:      源 ID
        document_path:  文档路径（用于计算 hash）
        document_hash:  文档哈希（如果已知）

    返回：
        canonical_key，如果无法构建则返回 None
    """
    if document_hash:
        return build_canonical_key(source_id, document_hash)

    if document_path:
        path = Path(document_path)
        if path.exists():
            try:
                doc_hash = compute_document_hash(path)
                return build_canonical_key(source_id, doc_hash)
            except Exception:
                pass

    return None
