"""PDF 文档提取器。

功能说明（小白解读）：
    本文件实现 PDF 文档的抽取能力：
    - 读取本地 PDF 文件
    - 提取 page_count
    - 提取文本内容
    - 生成 markdown
    - 计算 document_hash / content_hash
    - 判断 extraction_quality
    - malformed PDF fail-soft 处理

    注意：
        - 不做 OCR（OCR 默认关闭且本阶段不实现）
        - 不下载远程 PDF
        - 不处理扫描版 PDF 图像识别
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

# 字符数阈值（用于判断质量）
QUALITY_HIGH_THRESHOLD = 5000
QUALITY_MEDIUM_THRESHOLD = 1000


class PDFExtractor:
    """PDF 文档提取器。

    使用方式：
        extractor = PDFExtractor()
        if extractor.can_extract(candidate):
            result = extractor.extract(candidate)
    """

    def can_extract(self, candidate: DocumentCandidate) -> bool:
        """判断是否能处理这个文档。

        能处理的文档特征：
        - file_extension 是 .pdf
        - document_path 指向本地文件
        - MIME type 是 application/pdf
        """
        # 检查文件扩展名
        if candidate.file_extension and candidate.file_extension.lower() == ".pdf":
            return True

        # 检查 MIME type
        if candidate.mime_type and candidate.mime_type == "application/pdf":
            return True

        # 检查文件路径扩展名
        if candidate.document_path:
            path = Path(candidate.document_path)
            if path.suffix.lower() == ".pdf":
                return True

        return False

    def extract(self, candidate: DocumentCandidate) -> ExtractedDocument:
        """抽取 PDF 文档。

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
            file_extension=candidate.file_extension or ".pdf",
            mime_type=candidate.mime_type or "application/pdf",
            content_hash="",
            document_hash="",
            canonical_key="",
            extraction_status=EXTRACTION_STATUS_FAILED,
            extraction_quality=EXTRACTION_QUALITY_FAILED,
            created_at=created_at,
            error_message="",
            raw_entry=candidate.raw_entry,
        )

        # 检查文件路径
        if not candidate.document_path:
            failed_result.error_message = "没有 document_path"
            return failed_result

        path = Path(candidate.document_path)
        if not path.exists():
            failed_result.error_message = f"文件不存在: {candidate.document_path}"
            return failed_result

        if not path.is_file():
            failed_result.error_message = f"不是文件: {candidate.document_path}"
            return failed_result

        # 计算 document_hash
        try:
            document_hash = compute_document_hash(path)
        except Exception as exc:
            failed_result.error_message = f"计算 document_hash 失败: {exc}"
            return failed_result

        # 尝试读取 PDF
        text_content = ""
        page_count = None
        metadata: dict[str, Any] = {}

        try:
            # 优先使用 PyMuPDF (fitz)
            import fitz

            doc = fitz.open(str(path))
            page_count = len(doc)

            # 提取文本
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())

            text_content = "\n".join(text_parts)
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "mod_date": doc.metadata.get("modDate", ""),
            }
            doc.close()

        except ImportError:
            # 备选：使用 pypdf
            try:
                from pypdf import PdfReader

                reader = PdfReader(path)
                page_count = len(reader.pages)

                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text() or "")

                text_content = "\n".join(text_parts)

                if reader.metadata:
                    metadata = {
                        "title": reader.metadata.get("/Title", ""),
                        "author": reader.metadata.get("/Author", ""),
                        "subject": reader.metadata.get("/Subject", ""),
                        "creator": reader.metadata.get("/Creator", ""),
                        "producer": reader.metadata.get("/Producer", ""),
                    }

            except ImportError:
                failed_result.error_message = "没有可用的 PDF 库（请安装 PyMuPDF 或 pypdf）"
                return failed_result
            except Exception as exc:
                failed_result.error_message = f"pypdf 读取失败: {exc}"
                return failed_result

        except Exception as exc:
            # malformed PDF 或其他错误
            failed_result.error_message = f"PyMuPDF 读取失败: {exc}"
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

        # 生成 document_title（如果缺失）
        document_title = candidate.document_title
        if not document_title:
            document_title = path.stem  # 使用文件名（不含扩展名）

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
            mime_type=infer_mime_type(path) or "application/pdf",
            page_count=page_count,
            char_count=char_count,
            word_count=word_count,
            content_hash=content_hash,
            document_hash=document_hash,
            canonical_key=canonical_key,
            extraction_quality=extraction_quality,
            extraction_status=extraction_status,
            created_at=created_at,
            raw_entry={
                **candidate.raw_entry,
                "metadata": metadata,
            },
        )

        return result
