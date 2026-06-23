"""Document Extraction Foundation 的报告模块。

功能说明（小白解读）：
    本文件负责生成每日运行报告：
    - 总览：运行时间、文档统计
    - Source 健康概览：各源状态
    - 新抽取文档：成功抽取的文档列表
    - Partial / Failed：部分成功和失败的文档
    - Warnings：警告信息
    - 下游消费入口：documents.jsonl 路径
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    DocumentExtractionRunResult,
    DocumentExtractionHealth,
    ExtractedDocument,
    FailedDocument,
    HEALTH_STATUS_HEALTHY,
    HEALTH_STATUS_DISABLED,
    HEALTH_STATUS_DEGRADED,
    HEALTH_STATUS_FAILED,
    HEALTH_STATUS_UNKNOWN,
)


def daily_report_filename(iso_timestamp: str) -> str:
    """生成日报文件名。

    参数：
        iso_timestamp: ISO 格式时间戳

    返回：
        形如 "YYYY-MM-DD_document_extraction_report.md" 的文件名
    """
    # 从 ISO 字符串提取日期
    date_part = iso_timestamp[:10]
    return f"{date_part}_document_extraction_report.md"


def build_document_daily_report(result: DocumentExtractionRunResult) -> str:
    """生成每日报告内容（Markdown 格式）。

    参数：
        result: 运行结果

    返回：
        Markdown 格式的报告字符串
    """
    lines = []

    # 标题
    lines.append("# Document Extraction Daily Report")
    lines.append("")
    lines.append(f"**Run ID:** `{result.run_id}`")
    lines.append(f"**Mode:** `{result.mode}`")
    lines.append(f"**Archive Root:** `{result.archive_root}`")
    lines.append(f"**Started:** `{result.started_at}`")
    lines.append(f"**Finished:** `{result.finished_at}`")
    lines.append("")

    # 总览
    lines.append("## Overview")
    lines.append("")
    overview_data = [
        ("Total Sources", result.source_count),
        ("Enabled Sources", result.enabled_source_count),
        ("Candidates Found", result.candidate_count),
        ("Saved", result.saved_count),
        ("Duplicates", result.duplicate_count),
        ("Partial", result.partial_count),
        ("Failed", result.failed_count),
        ("Skipped", result.skipped_count),
    ]
    for label, value in overview_data:
        lines.append(f"- **{label}:** {value}")
    lines.append("")

    # Source Health 概览
    lines.append("## Source Health Overview")
    lines.append("")
    if result.source_health:
        health_summary: dict[str, int] = {}
        for h in result.source_health:
            status = h.status
            health_summary[status] = health_summary.get(status, 0) + 1

        for status, count in sorted(health_summary.items()):
            status_icon = _health_status_icon(status)
            lines.append(f"- {status_icon} **{status}:** {count}")
    else:
        lines.append("*No health data available.*")
    lines.append("")

    # 新抽取文档
    if result.saved_documents:
        lines.append("## Extracted Documents")
        lines.append("")
        lines.append("| Source | Title | Type | Quality | Pages | Chars |")
        lines.append("|--------|-------|------|---------|-------|-------|")
        for doc in result.saved_documents:
            title = (doc.document_title or "N/A")[:50]
            lines.append(
                f"| {doc.source_id} | {title} | {doc.document_type or 'N/A'} | "
                f"{doc.extraction_quality} | {doc.page_count or 'N/A'} | {doc.char_count or 'N/A'} |"
            )
        lines.append("")
    else:
        lines.append("## Extracted Documents")
        lines.append("")
        lines.append("*No documents extracted in this run.*")
        lines.append("")

    # Partial / Failed
    if result.failed_documents:
        lines.append("## Partial / Failed")
        lines.append("")
        for failed in result.failed_documents:
            error_preview = (failed.error or "Unknown error")[:60]
            lines.append(f"- **{failed.source_id}** | {failed.document_title or 'N/A'} | {error_preview}")
        lines.append("")

    # Warnings
    if result.warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in result.warnings:
            lines.append(f"- ⚠️ {warning}")
        lines.append("")

    # Source Stats
    if result.source_stats:
        lines.append("## Source Statistics")
        lines.append("")
        for stats in result.source_stats:
            source_id = stats.get("source_id", "unknown")
            status = stats.get("status", "unknown")
            candidates = stats.get("candidate_count", 0)
            saved = stats.get("saved_count", 0)
            lines.append(f"- **{source_id}**: status={status}, candidates={candidates}, saved={saved}")
        lines.append("")

    # 下游消费入口
    lines.append("## Downstream Consumer Entry Points")
    lines.append("")
    archive_root = Path(result.archive_root)
    lines.append(f"- **All Documents:** `{archive_root / 'index' / 'documents.jsonl'}`")
    lines.append(f"- **Latest Documents:** `{archive_root / 'index' / 'documents.latest.jsonl'}`")
    lines.append(f"- **Source Health:** `{archive_root / 'index' / 'source_health.jsonl'}`")
    lines.append(f"- **Failed Queue:** `{archive_root / 'index' / 'failed_queue.jsonl'}`")
    lines.append("")

    return "\n".join(lines)


def _health_status_icon(status: str) -> str:
    """获取健康状态的图标。"""
    icons = {
        HEALTH_STATUS_HEALTHY: "✅",
        HEALTH_STATUS_DISABLED: "⏸️",
        HEALTH_STATUS_DEGRADED: "⚠️",
        HEALTH_STATUS_FAILED: "❌",
        HEALTH_STATUS_UNKNOWN: "❓",
    }
    return icons.get(status, "❓")
