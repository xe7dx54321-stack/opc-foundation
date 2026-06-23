"""HTML 文档提取器。

功能说明（小白解读）：
    本文件实现 HTML 文档的抽取能力：
    - 读取本地 HTML 文件
    - 提取 title
    - 提取正文文本
    - 转 markdown
    - 保存 metadata

    注意：
        - 不访问真实外部网站
        - 不下载远程 HTML
        - 不做投资判断
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

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

QUALITY_HIGH_THRESHOLD = 3000
QUALITY_MEDIUM_THRESHOLD = 500


class HTMLExtractor:
    """HTML 文档提取器。

    使用方式：
        extractor = HTMLExtractor()
        if extractor.can_extract(candidate):
            result = extractor.extract(candidate)
    """

    def can_extract(self, candidate: DocumentCandidate) -> bool:
        """判断是否能处理这个文档。"""
        if candidate.file_extension and candidate.file_extension.lower() in (".html", ".htm"):
            return True

        if candidate.mime_type and candidate.mime_type == "text/html":
            return True

        if candidate.document_path:
            path = Path(candidate.document_path)
            if path.suffix.lower() in (".html", ".htm"):
                return True

        return False

    def extract(self, candidate: DocumentCandidate) -> ExtractedDocument:
        """抽取 HTML 文档。

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
            file_extension=candidate.file_extension or ".html",
            mime_type=candidate.mime_type or "text/html",
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

        # 读取 HTML
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                html_content = f.read()
        except Exception as exc:
            failed_result.error_message = f"读取文件失败: {exc}"
            return failed_result

        # 解析 HTML
        title = ""
        text_content = ""

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            # 提取 title
            if soup.title:
                title = soup.title.string or ""

            # 提取正文文本（使用 get_text）
            # 先尝试提取主要内容区域
            main_content = soup.find("main") or soup.find("article") or soup.find("body")
            if main_content:
                text_content = main_content.get_text(separator="\n", strip=True)
            else:
                text_content = soup.get_text(separator="\n", strip=True)

        except ImportError:
            # 如果没有 BeautifulSoup，使用正则提取
            import re

            # 简单提取 title
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", html_content, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()

            # 简单去除 HTML 标签
            text_content = re.sub(r"<[^>]+>", " ", html_content)
            text_content = re.sub(r"\s+", " ", text_content).strip()

        except Exception as exc:
            failed_result.error_message = f"HTML 解析失败: {exc}"
            return failed_result

        # 计算 content_hash
        content_hash = compute_content_hash(text_content)

        # 计算字符数和词数
        char_count = len(text_content)
        word_count = len(text_content.split()) if text_content else 0

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
        if char_count == 0:
            extraction_status = EXTRACTION_STATUS_PARTIAL
        else:
            extraction_status = EXTRACTION_STATUS_SUCCESS

        # 生成 document_title
        document_title = candidate.document_title or title or path.stem

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
            mime_type=infer_mime_type(path) or "text/html",
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
