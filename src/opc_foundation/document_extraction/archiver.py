"""Document Extraction Foundation 的归档编排器。

功能说明（小白解读）：
    Archiver 是整个模块的总指挥，负责：
    1. 读取配置
    2. 遍历所有 enabled 的 source
    3. 扫描本地文件发现候选文档
    4. 调用对应的 extractor 抽取文档
    5. 去重判断
    6. 保存归档
    7. 更新 source health
    8. 写入失败队列
    9. 生成日报
    10. 返回运行结果

    所有操作都是 fail-soft 的：单个文档失败不会影响全局。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import DocumentArchiveConfig
from .dedupe import is_duplicate
from .extractors.base import DocumentExtractor
from .extractors.html import HTMLExtractor
from .extractors.markdown import MarkdownExtractor
from .extractors.pdf import PDFExtractor
from .extractors.text import TextExtractor
from .health import compute_health_status, update_source_health
from .models import (
    DocumentCandidate,
    DocumentExtractionRunResult,
    ExtractedDocument,
    FailedDocument,
    EXTRACTION_STATUS_FAILED,
    EXTRACTION_STATUS_PARTIAL,
    EXTRACTION_STATUS_SKIPPED,
    EXTRACTION_STATUS_SUCCESS,
    HEALTH_STATUS_DISABLED,
    ERROR_TYPE_EXTRACTOR,
    ERROR_TYPE_PARSE,
    ERROR_TYPE_READ,
    ERROR_TYPE_UNKNOWN,
)
from .reports import build_document_daily_report, daily_report_filename
from .storage import (
    append_document_index,
    append_failed_queue,
    append_run_log,
    ensure_data_dirs,
    load_documents_index,
    save_markdown_file,
    save_metadata_sidecar,
    save_raw_copy,
    save_text_file,
    write_documents_latest,
)
from ..run.id_generator import generate_document_id
from ..run.time_utils import utcnow_iso


class DocumentArchiver:
    """文档归档编排器。

    使用方式：
        archiver = DocumentArchiver(config)
        result = archiver.run(mode="run")
    """

    def __init__(
        self,
        config: DocumentArchiveConfig,
        extractor_overrides: dict[str, DocumentExtractor] | None = None,
    ) -> None:
        """初始化归档器。

        参数：
            config:             归档配置
            extractor_overrides: 测试用，覆盖默认 extractor（用于注入 fixture）
        """
        self._config = config
        self._extractors: dict[str, DocumentExtractor] = extractor_overrides or {}
        self._setup_default_extractors()

    def _setup_default_extractors(self) -> None:
        """设置默认的 extractors。"""
        if not self._extractors:
            self._extractors = {
                "pdf": PDFExtractor(),
                "html": HTMLExtractor(),
                "text": TextExtractor(),
                "markdown": MarkdownExtractor(),
            }

    def _get_extractor(self, candidate: DocumentCandidate) -> DocumentExtractor | None:
        """根据候选类型获取对应的 extractor。"""
        for extractor in self._extractors.values():
            if extractor.can_extract(candidate):
                return extractor
        return None

    def _discover_candidates(
        self,
        source_config: Any,
    ) -> list[DocumentCandidate]:
        """从本地目录扫描发现候选文档。

        参数：
            source_config: 源配置

        返回：
            候选文档列表
        """
        candidates = []

        if not source_config.input_path:
            return candidates

        input_path = Path(source_config.input_path)
        if not input_path.exists() or not input_path.is_dir():
            return candidates

        # 获取 glob 模式
        glob_pattern = source_config.input_glob or "*"

        # 扫描文件
        try:
            for file_path in input_path.glob(glob_pattern):
                if not file_path.is_file():
                    continue

                # 构建候选
                candidate = DocumentCandidate(
                    source_id=source_config.source_id,
                    source_type=source_config.source_type,
                    document_path=str(file_path),
                    document_title=file_path.stem,
                    file_extension=file_path.suffix.lower(),
                    legal_profile=source_config.legal_profile,
                    discovered_at=utcnow_iso(),
                    raw_entry={
                        "source_name": source_config.source_name,
                    },
                )
                candidates.append(candidate)

        except Exception:
            pass

        # 限制数量
        max_docs = source_config.max_documents or self._config.defaults.max_documents
        return candidates[:max_docs]

    def run(self, mode: str = "run") -> DocumentExtractionRunResult:
        """执行一次完整的归档运行。

        参数：
            mode: 运行模式
                - "dry-run": 只发现候选并抽取，不写归档
                - "run": 正常运行，写归档

        返回：
            DocumentExtractionRunResult 运行结果
        """
        run_id = generate_document_id()
        started_at = utcnow_iso()
        archive_root = Path(self._config.archive_root)

        # 确保数据目录存在
        if mode == "run":
            ensure_data_dirs(archive_root)

        # 加载现有索引（用于去重）
        existing_index = load_documents_index(archive_root) if mode == "run" else {}

        result = DocumentExtractionRunResult(
            run_id=run_id,
            mode=mode,
            archive_root=str(archive_root),
            started_at=started_at,
            finished_at="",
            source_count=len(self._config.sources),
        )

        all_documents: dict[str, ExtractedDocument] = dict(existing_index)

        # 遍历所有 source
        for source in self._config.sources:
            source_stats: dict[str, Any] = {
                "source_id": source.source_id,
                "source_type": source.source_type,
                "status": "",
                "candidate_count": 0,
                "saved_count": 0,
                "duplicate_count": 0,
                "failed_count": 0,
            }

            # disabled source
            if not source.enabled:
                source_stats["status"] = "disabled"
                result.skipped_count += 1
                result.source_stats.append(source_stats)

                # 记录 disabled 状态
                from .health import save_source_health
                from .models import DocumentExtractionHealth

                health = DocumentExtractionHealth(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    checked_at=utcnow_iso(),
                    status=HEALTH_STATUS_DISABLED,
                )
                save_source_health(archive_root, health)
                result.source_health.append(health)
                continue

            result.enabled_source_count += 1

            # 发现候选
            try:
                candidates = self._discover_candidates(source)
            except Exception as exc:
                source_stats["status"] = "failed"
                source_stats["error"] = str(exc)
                result.failed_count += 1
                result.warnings.append(
                    f"Source [{source.source_id}] candidate discovery 失败: {exc}"
                )
                result.source_stats.append(source_stats)

                update_source_health(
                    archive_root,
                    source_id=source.source_id,
                    source_type=source.source_type,
                    status="failed",
                    last_error=str(exc),
                    last_error_type=ERROR_TYPE_READ,
                    run_id=run_id,
                )
                continue

            source_stats["candidate_count"] = len(candidates)
            result.candidate_count += len(candidates)

            saved_count = 0
            duplicate_count = 0
            failed_count = 0

            # 处理每个候选
            for candidate in candidates:
                # 去重检查
                if candidate.document_path:
                    is_dup, existing = is_duplicate(
                        candidate.document_path,
                        candidate.source_id,
                        all_documents,
                    )
                    if is_dup:
                        duplicate_count += 1
                        if mode == "run":
                            append_document_index(archive_root, existing)
                        continue

                # 获取 extractor
                extractor = self._get_extractor(candidate)
                if extractor is None:
                    failed_count += 1
                    result.warnings.append(
                        f"Candidate [{candidate.document_path}] 没有对应的 extractor"
                    )
                    continue

                # 抽取文档
                try:
                    extracted = extractor.extract(candidate)
                except Exception as exc:
                    failed_count += 1
                    result.warnings.append(
                        f"Candidate [{candidate.document_path}] extract 异常: {exc}"
                    )
                    if mode == "run":
                        failed_doc = FailedDocument(
                            source_id=source.source_id,
                            source_type=source.source_type,
                            document_title=candidate.document_title,
                            original_path=candidate.document_path,
                            canonical_key="",
                            failed_at=utcnow_iso(),
                            error=str(exc),
                            error_type=ERROR_TYPE_EXTRACTOR,
                            run_id=run_id,
                            raw_entry=candidate.raw_entry,
                        )
                        append_failed_queue(archive_root, failed_doc)
                        result.failed_documents.append(failed_doc)
                    continue

                # 处理抽取结果
                if extracted.extraction_status == EXTRACTION_STATUS_FAILED:
                    failed_count += 1
                    if mode == "run":
                        failed_doc = FailedDocument(
                            source_id=source.source_id,
                            source_type=source.source_type,
                            document_title=extracted.document_title,
                            original_path=extracted.original_path,
                            canonical_key=extracted.canonical_key,
                            failed_at=utcnow_iso(),
                            error=extracted.error_message or "Unknown error",
                            error_type=ERROR_TYPE_EXTRACTOR,
                            run_id=run_id,
                            raw_entry=candidate.raw_entry,
                        )
                        append_failed_queue(archive_root, failed_doc)
                        result.failed_documents.append(failed_doc)

                elif extracted.extraction_status == EXTRACTION_STATUS_PARTIAL:
                    # partial 也保存
                    if mode == "run":
                        _save_extracted_document(
                            archive_root, extracted, source, candidates
                        )
                        append_document_index(archive_root, extracted)
                    result.partial_count += 1
                    saved_count += 1
                    all_documents[extracted.canonical_key] = extracted
                    result.saved_documents.append(extracted)

                else:  # success
                    if mode == "run":
                        _save_extracted_document(
                            archive_root, extracted, source, candidates
                        )
                        append_document_index(archive_root, extracted)
                    saved_count += 1
                    all_documents[extracted.canonical_key] = extracted
                    result.saved_documents.append(extracted)

            source_stats["saved_count"] = saved_count
            source_stats["duplicate_count"] = duplicate_count
            source_stats["failed_count"] = failed_count
            source_stats["status"] = "success" if failed_count == 0 else "partial"

            result.saved_count += saved_count
            result.duplicate_count += duplicate_count
            result.failed_count += failed_count

            # 更新 source health
            # 规则：
            # 1. enabled=True 但 candidate_count=0 → degraded（empty_source）
            # 2. enabled=True 且 candidate_count>0 → 按 compute_health_status 结果
            # 3. enabled=False → disabled（由上层处理）
            if source.enabled and len(candidates) == 0:
                health_status = "degraded"
                last_error_msg = "empty_source"
            else:
                health_status = compute_health_status(
                    candidate_count=len(candidates),
                    saved_count=saved_count,
                    failed_count=failed_count,
                    partial_count=0,
                    consecutive_failures=0,
                    connector_failed=False,
                )
                if health_status == "healthy":
                    last_error_msg = None
                elif len(candidates) == 0:
                    last_error_msg = "empty_source"
                else:
                    last_error_msg = f"{failed_count} failed"

            health = update_source_health(
                archive_root,
                source_id=source.source_id,
                source_type=source.source_type,
                status=health_status,
                last_error=last_error_msg,
                candidate_count=len(candidates),
                saved_count=saved_count,
                duplicate_count=duplicate_count,
                failed_count=failed_count,
                run_id=run_id,
            )
            result.source_health.append(health)
            result.source_stats.append(source_stats)

        # 写 documents.latest.jsonl
        if mode == "run":
            write_documents_latest(archive_root, all_documents)

        # 生成日报
        finished_at = utcnow_iso()
        result.finished_at = finished_at

        if mode == "run":
            report_content = build_document_daily_report(result)
            report_name = daily_report_filename(finished_at)
            report_path = archive_root / "reports" / report_name
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            result.report_path = str(report_path)

            # 更新 health 里的 report_path
            for h in result.source_health:
                h.last_report_path = str(report_path)

            # 写 run log
            append_run_log(archive_root, result)

        # exit code
        if result.failed_count > 0:
            result.exit_code = 2  # 部分失败
        else:
            result.exit_code = 0

        return result

    def retry_failed(self) -> DocumentExtractionRunResult:
        """重试失败队列中的文档。

        MVP 版本：简单重跑一遍所有 enabled source。
        实际项目中应该从 failed_queue.jsonl 读取具体条目重试。
        """
        # MVP：直接跑一次 run
        return self.run(mode="run")


def _save_extracted_document(
    archive_root: Path,
    extracted: ExtractedDocument,
    source_config: Any,
    candidates: list[DocumentCandidate],
) -> None:
    """保存抽取的文档到归档目录。

    参数：
        archive_root:   归档根目录
        extracted:      抽取结果
        source_config:  源配置
        candidates:     候选列表（用于获取原始信息）
    """
    # 保存原始文件副本
    if source_config.save_raw and extracted.original_path:
        raw_path = save_raw_copy(
            archive_root,
            extracted.original_path,
            extracted.canonical_key,
        )
        if raw_path:
            extracted.raw_path = raw_path

    # 保存 metadata sidecar
    if source_config.save_metadata:
        import json

        metadata = {
            "document_id": extracted.document_id,
            "source_id": extracted.source_id,
            "source_type": extracted.source_type,
            "document_title": extracted.document_title,
            "file_extension": extracted.file_extension,
            "mime_type": extracted.mime_type,
            "page_count": extracted.page_count,
            "char_count": extracted.char_count,
            "word_count": extracted.word_count,
            "content_hash": extracted.content_hash,
            "document_hash": extracted.document_hash,
            "extraction_quality": extracted.extraction_quality,
            "extraction_status": extracted.extraction_status,
            "created_at": extracted.created_at,
        }
        metadata_filename = f"{extracted.document_id}_metadata.json"
        save_metadata_sidecar(archive_root, extracted, metadata)
        extracted.metadata_path = metadata_filename
