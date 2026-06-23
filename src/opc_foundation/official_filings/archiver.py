"""Official Filing Foundation 的归档编排器。

功能说明（小白解读）：
    Archiver 是整个模块的总指挥，负责：
    1. 读取配置
    2. 遍历所有 enabled 的 source
    3. 调用对应的 connector 发现候选披露
    4. 去重判断
    5. 保存归档
    6. 更新 source health
    7. 写入失败队列
    8. 生成日报
    9. 返回运行结果

    所有操作都是 fail-soft 的：单个 source 失败不会影响全局。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import FilingArchiveConfig
from .connectors.base import OfficialFilingConnector, get_connector
from .health import compute_health_status, update_source_health
from .models import (
    FailedFiling,
    FilingRunResult,
    FILING_STATUS_FAILED,
    FILING_STATUS_SKIPPED,
    HEALTH_STATUS_DISABLED,
    ERROR_TYPE_CONNECTOR,
    ERROR_TYPE_FETCH,
    ERROR_TYPE_PARSE,
    ERROR_TYPE_UNSUPPORTED,
    NormalizedFiling,
)
from .reports import build_filing_daily_report, daily_report_filename
from .storage import (
    append_failed_queue,
    append_run_log,
    archive_filing,
    load_filings_index,
    process_candidate,
    write_filings_latest,
)
from ..run.id_generator import new_run_id as generate_run_id
from ..run.time_utils import utcnow_iso


class FilingArchiver:
    """官方披露归档编排器。

    使用方式：
        archiver = FilingArchiver(config)
        result = archiver.run(mode="run")
    """

    def __init__(
        self,
        config: FilingArchiveConfig,
        connector_overrides: dict[str, OfficialFilingConnector] | None = None,
    ) -> None:
        """初始化归档器。

        参数：
            config:             归档配置
            connector_overrides: 测试用，覆盖默认 connector（用于注入 fixture）
        """
        self._config = config
        self._connector_overrides = connector_overrides or {}

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def run(self, mode: str = "run") -> FilingRunResult:
        """执行一次完整的归档运行。

        参数：
            mode: 运行模式
                - "dry-run": 只发现候选，不写归档
                - "run": 正常运行，写归档

        返回：
            FilingRunResult 运行结果
        """
        run_id = generate_run_id()
        started_at = utcnow_iso()
        archive_root = Path(self._config.archive_root)

        # 加载现有索引（用于去重）
        existing_index = load_filings_index(archive_root) if mode == "run" else {}

        result = FilingRunResult(
            run_id=run_id,
            mode=mode,
            archive_root=str(archive_root),
            started_at=started_at,
            finished_at="",
            source_count=len(self._config.sources),
        )

        all_filings: dict[str, NormalizedFiling] = dict(existing_index)

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
                from .models import FilingSourceHealth
                health = FilingSourceHealth(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    checked_at=utcnow_iso(),
                    status=HEALTH_STATUS_DISABLED,
                )
                save_source_health(archive_root, health)
                result.source_health.append(health)
                continue

            result.enabled_source_count += 1

            # 获取 connector
            connector = self._connector_overrides.get(source.source_type)
            if connector is None:
                connector = get_connector(source.source_type)

            if connector is None:
                # 不支持的 source_type
                source_stats["status"] = "unsupported"
                source_stats["error"] = f"unsupported source_type: {source.source_type}"
                result.skipped_count += 1
                result.warnings.append(
                    f"Source [{source.source_id}] 不支持的类型: {source.source_type}"
                )
                result.source_stats.append(source_stats)

                update_source_health(
                    archive_root,
                    source_id=source.source_id,
                    source_type=source.source_type,
                    status="failed",
                    last_error=f"unsupported source_type: {source.source_type}",
                    last_error_type=ERROR_TYPE_UNSUPPORTED,
                    run_id=run_id,
                )
                continue

            # 执行 discover（fail-soft）
            try:
                candidates = connector.discover(source, self._config)
            except Exception as exc:
                source_stats["status"] = "failed"
                source_stats["error"] = str(exc)
                result.failed_count += 1
                result.warnings.append(
                    f"Source [{source.source_id}] discover 失败: {exc}"
                )
                result.source_stats.append(source_stats)

                # 判断错误类型
                error_type = _classify_error(exc)

                health = update_source_health(
                    archive_root,
                    source_id=source.source_id,
                    source_type=source.source_type,
                    status="failed",
                    last_error=str(exc),
                    last_error_type=error_type,
                    run_id=run_id,
                )
                result.source_health.append(health)
                continue

            source_stats["candidate_count"] = len(candidates)
            result.candidate_count += len(candidates)

            saved_count = 0
            duplicate_count = 0
            failed_count = 0

            # 处理每个候选
            for candidate in candidates:
                try:
                    filing, is_new = process_candidate(
                        candidate, self._config, all_filings
                    )

                    if not is_new:
                        duplicate_count += 1
                        if mode == "run":
                            # 重复也追加到全量索引（标记 duplicate）
                            from .storage import append_filing_index
                            append_filing_index(archive_root, filing)
                        continue

                    # 新披露
                    if mode == "run":
                        # 保存归档
                        filing = archive_filing(archive_root, filing)
                        result.saved_filings.append(filing)
                    else:
                        # dry-run 不保存
                        result.saved_filings.append(filing)

                    all_filings[filing.canonical_key] = filing
                    saved_count += 1

                except Exception as exc:
                    failed_count += 1
                    result.warnings.append(
                        f"Filing [{candidate.filing_title}] 处理失败: {exc}"
                    )

                    # 写入失败队列
                    if mode == "run":
                        from .dedupe import build_canonical_key
                        failed = FailedFiling(
                            source_id=source.source_id,
                            source_type=source.source_type,
                            filing_title=candidate.filing_title,
                            document_url=candidate.document_url,
                            canonical_key=build_canonical_key(candidate),
                            failed_at=utcnow_iso(),
                            error=str(exc),
                            error_type=_classify_error(exc),
                            run_id=run_id,
                            raw_entry=candidate.raw_entry,
                        )
                        append_failed_queue(archive_root, failed)
                        result.failed_filings.append(failed)

            source_stats["saved_count"] = saved_count
            source_stats["duplicate_count"] = duplicate_count
            source_stats["failed_count"] = failed_count
            source_stats["status"] = "success" if failed_count == 0 else "partial"

            result.saved_count += saved_count
            result.duplicate_count += duplicate_count
            result.failed_count += failed_count

            # 更新 source health
            health_status = compute_health_status(
                candidate_count=len(candidates),
                saved_count=saved_count,
                failed_count=failed_count,
                partial_count=0,
                consecutive_failures=0,
                connector_failed=False,
            )
            health = update_source_health(
                archive_root,
                source_id=source.source_id,
                source_type=source.source_type,
                status=health_status,
                last_error=None if health_status == "healthy" else f"{failed_count} failed",
                candidate_count=len(candidates),
                saved_count=saved_count,
                duplicate_count=duplicate_count,
                failed_count=failed_count,
                run_id=run_id,
            )
            result.source_health.append(health)
            result.source_stats.append(source_stats)

        # 写 filings.latest.jsonl
        if mode == "run":
            write_filings_latest(archive_root, all_filings)

        # 生成日报
        finished_at = utcnow_iso()
        result.finished_at = finished_at

        if mode == "run":
            report_content = build_filing_daily_report(result)
            report_name = daily_report_filename(finished_at)
            report_path = Path(archive_root) / "reports" / report_name
            from ..storage.path_utils import ensure_parent
            ensure_parent(report_path)
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

    def retry_failed(self) -> FilingRunResult:
        """重试失败队列中的披露。

        MVP 版本：简单重跑一遍所有 enabled source。
        实际项目中应该从 failed_queue.jsonl 读取具体条目重试。
        """
        # MVP：直接跑一次 run
        return self.run(mode="run")


def _classify_error(exc: Exception) -> str:
    """根据异常类型分类错误。"""
    msg = str(exc).lower()
    if "fetch" in msg or "http" in msg or "network" in msg or "timeout" in msg:
        return ERROR_TYPE_FETCH
    if "parse" in msg or "syntax" in msg or "html" in msg or "json" in msg:
        return ERROR_TYPE_PARSE
    if "connector" in msg or "unsupported" in msg:
        return ERROR_TYPE_CONNECTOR
    return ERROR_TYPE_CONNECTOR
