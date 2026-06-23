"""Markdown 文档提取器。

功能说明（小白解读）：
    本文件实现 Markdown 文件的抽取能力：
    - 读取 .md / .markdown 文件
    - 保留 markdown 内容
    - 提取纯文本统计
    - 保存 metadata

    注意：
        - 不做投资判断
"""
from __future__ import annotations

from pathlib import Path

from ..models import (
    DocumentCandidate,
    ExtractedDocument,
    EXTRACTION_QUALITY_EMPTY,
    EXTRACTION_QUALITY_FAILED,
    EXTRACTION_QUALITY_HIGH,
    EXTRACTION_QUALITY_LOW,
    EXTRACTION_QUALITY_MEDIUM,
    EXTRACTION_STATUS_FAILED,
    EXTRACTION_STATUS_PARTIAL,
    EXTRACTION_STATUS_SUCCESS,
    compute_content_hash,
    compute_document_hash,
    build_canonical_key,
    infer_mime_type,
)
from .base import DocumentExtractor

QUALITY_HIGH_THRESHOLD = 5000
QUALITY_MEDIUM_THRESHOLD = 1000


class MarkdownExtractor:
    """Markdown 文档提取器。

    使用方式：
        extractor = MarkdownExtractor()
        if extractor.can_extract(candidate):
            result = extractor.extract(candidate)
    """

    # 支持的扩展名
    SUPPORTED_EXTENSIONS = {".md", ".markdown"}

    def can_extract(self, candidate: DocumentCandidate) -> bool:
        """判断是否能处理这个文档。"""
        if candidate.file_extension and candidate.file_extension.lower() in self.SUPPORTED_EXTENSIONS:
            return True

        if candidate.mime_type and candidate.mime_type == "text/markdown":
            return True

        if candidate.document_path:
            path = Path(candidate.document_path)
            if path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                return True

        return False

    def extract(self, candidate: DocumentCandidate) -> ExtractedDocument:
        """抽取 Markdown 文档。

        fail-soft 设计：任何错误都返回 failed 状态的 ExtractedDocument。
        """
        from ...run.id_generator import generate_document_id
        from ...run.time_utils import utcnow_iso

        document_id = generate_document_id()
        created_at = utcnow_iso()

        # 初始化失败返回值
        failed_result = ExtractedDocument(
            document_id=document_id,
            source_id=candidate.source_id,
            source_type=candidate.source_type,
            document_title=candidate.document_title,
            document_type=candidate.document_type,
            original_path=candidate.document_path,
            document_url=candidate.document_url,
            file_extension=candidate.file_extension or ".md",
            mime_type=candidate.mime_type or "text/markdown",
            content_hash="",
            document_hash="",
            canonical_key="",
            extraction_status=EXTRACTION_STATUS_FAILED,
            extraction_quality=EXTRACTION_QUALITY_FAILED,
            created_at=created_at,
            error_message="",
            raw_entry=candidate.raw_entry,
        )

        if not candidate.document_path:
            failed_result.error_message = "没有 document_path"
            return failed_result

        path = Path(candidate.document_path)
        if not path.exists() or not path.is_file():
            failed_result.error_message = f"文件不存在或不是文件: {candidate.document_path}"
            return failed_result

        # 计算 document_hash
        try:
            document_hash = compute_document_hash(path)
        except Exception as exc:
            failed_result.error_message = f"计算 document_hash 失败: {exc}"
            return failed_result

        # 读取 markdown
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                md_content = f.read()
        except Exception as exc:
            failed_result.error_message = f"读取文件失败: {exc}"
            return failed_result

        # 计算 content_hash（markdown 内容本身）
        content_hash = compute_content_hash(md_content)

        # 提取纯文本用于统计（去掉 markdown 语法）
        import re

        # 移除常见的 markdown 语法
        text_only = md_content
        text_only = re.sub(r"```[\s\S]*?```", " ", text_only)  # 代码块
        text_only = re.sub(r"`[^`]+`", " ", text_only)  # 行内代码
        text_only = re.sub(r"!\[.*?\]\(.*?\)", " ", text_only)  # 图片
        text_only = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text_only)  # 链接
        text_only = re.sub(r"#{1,6}\s+", " ", text_only)  # 标题
        text_only = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", text_only)  # 强调
        text_only = re.sub(r"\n", " ", text_only)  # 换行转空格
        text_only = re.sub(r"\s+", " ", text_only).strip()  # 多空格合并

        # 计算统计
        char_count = len(text_only)
        word_count = len(text_only.split()) if text_only else 0

        # 判断 extraction_quality
        if char_count == 0:
            extraction_quality = EXTRACTION_QUALITY_EMPTY
        elif char_count >= QUALITY_HIGH_THRESHOLD:
            extraction_quality = EXTRACTION_QUALITY_HIGH
        elif char_count >= QUALITY_MEDIUM_THRESHOLD:
            extraction_quality = EXTRACTION_QUALITY_MEDIUM
        else:
            extraction_quality = EXTRACTION_QUALITY_LOW

        # 判断 extraction_status
        extraction_status = EXTRACTION_STATUS_SUCCESS

        # 生成 document_title
        document_title = candidate.document_title or path.stem

        # 构建 canonical_key
        canonical_key = build_canonical_key(candidate.source_id, document_hash)

        # 构建结果
        result = ExtractedDocument(
            document_id=document_id,
            source_id=candidate.source_id,
            source_type=candidate.source_type,
            document_title=document_title,
            document_type=candidate.document_type or path.stem,
            original_path=str(path),
            document_url=candidate.document_url,
            file_extension=path.suffix.lower(),
            mime_type=infer_mime_type(path) or "text/markdown",
            char_count=char_count,
            word_count=word_count,
            content_hash=content_hash,
            document_hash=document_hash,
            canonical_key=canonical_key,
            extraction_quality=extraction_quality,
            extraction_status=extraction_status,
            created_at=created_at,
            raw_entry=candidate.raw_entry,
        )

        return result
