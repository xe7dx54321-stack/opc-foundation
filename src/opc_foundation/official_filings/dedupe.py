"""Official Filing Foundation 的去重逻辑。

功能说明（小白解读）：
    每次跑 run，可能会发现很多候选披露。其中有些之前已经归档过，
    不需要再处理一次。本模块提供 canonical_key 生成和去重判断。

去重 key：
    canonical_key = source_type + issuer_code + filing_date + filing_type
                    + (accession_number or announcement_id or document_url)

    用 SHA256 哈希生成稳定的 filing_id。
"""
from __future__ import annotations

import hashlib

from .models import FilingCandidate, NormalizedFiling


def _sha256_hex(text: str, length: int = 16) -> str:
    """对字符串做 SHA256，默认截断前 16 位（够用且更易读）。"""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:length]


def build_canonical_key(candidate: FilingCandidate) -> str:
    """为候选披露生成 canonical_key（用于去重）。

    参数：
        candidate: 候选披露

    返回：
        canonical_key 字符串

    小白解读：
        把能唯一标识一份披露的字段拼起来，生成一个稳定的 key。
        同一公司同一天发布的同类型披露，应该有相同的 canonical_key。
    """
    parts = [
        candidate.source_type or "",
        candidate.issuer_code or "",
        candidate.filing_date or "",
        candidate.filing_type or "",
    ]

    # 用唯一标识字段（优先顺序：accession_number > announcement_id > document_url）
    if candidate.accession_number:
        parts.append(f"acc:{candidate.accession_number}")
    elif candidate.announcement_id:
        parts.append(f"ann:{candidate.announcement_id}")
    elif candidate.document_url:
        parts.append(f"url:{candidate.document_url}")
    elif candidate.pdf_url:
        parts.append(f"pdf:{candidate.pdf_url}")
    else:
        # 兜底：用标题 hash
        parts.append(f"title_hash:{_sha256_hex(candidate.filing_title or '')}")

    return "|".join(parts)


def filing_id_for(candidate: FilingCandidate) -> str:
    """基于 canonical_key 生成稳定的 filing_id。

    参数：
        candidate: 候选披露

    返回：
        filing_id 字符串，前缀 of_ 表示 official_filing
    """
    canonical = build_canonical_key(candidate)
    return "of_" + _sha256_hex(canonical, length=32)


def content_hash_for(candidate: FilingCandidate) -> str:
    """基于内容相关字段生成 content_hash。

    参数：
        candidate: 候选披露

    返回：
        content_hash 字符串

    小白解读：
        用于判断同一份披露的内容有没有变化。
        如果 canonical_key 相同但 content_hash 不同，说明有更新。
    """
    parts = [
        candidate.filing_title or "",
        candidate.filing_date or "",
        candidate.document_url or "",
        candidate.pdf_url or "",
        candidate.html_url or "",
    ]
    return _sha256_hex("||".join(parts), length=32)
