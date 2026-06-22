"""Research Source Foundation 的中文日报生成。

功能说明（小白解读）：
    每次 run 完成后，生成一份中文 Markdown 日报，写到：
        data/research_archive/reports/daily_capture_YYYY-MM-DD.md

    日报内容：
        - 总览（source 数、候选数、新文档数、失败数等）
        - Source 结果表格
        - 新保存文档列表
        - Partial / Failed 详情
        - Source Health 状态
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import ResearchRunResult


def build_research_daily_report(result: ResearchRunResult) -> str:
    """生成一份中文 Markdown 日报。

    参数：
        result: 一次 run 的汇总结果

    返回：
        Markdown 字符串
    """
    # 日期：用 finished_at 解析，失败则用今天
    try:
        date_str = (result.finished_at or result.started_at)[:10]
    except Exception:
        date_str = datetime.now().strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append("# Research Source Foundation 采集日报")
    lines.append("")
    lines.append(f"- 日期：{date_str}")
    lines.append(f"- 运行 ID：{result.run_id}")
    lines.append(f"- 模式：{_mode_label(result.mode)}")
    lines.append(f"- 归档根目录：{result.archive_root}")
    lines.append(f"- 开始时间：{result.started_at}")
    lines.append(f"- 结束时间：{result.finished_at}")
    lines.append("")

    # 总览
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- Source 总数：{result.source_count}")
    lines.append(f"- 启用 Source：{result.enabled_source_count}")
    lines.append(f"- 候选文档：{result.candidate_count}")
    lines.append(f"- 新文档：{result.new_count}")
    lines.append(f"- 成功保存：{result.saved_count}")
    lines.append(f"- 部分保存：{result.partial_count}")
    lines.append(f"- 失败：{result.failed_count}")
    lines.append(f"- 重复：{result.duplicate_count}")
    lines.append(f"- 跳过：{result.skipped_count}")
    lines.append("")

    # Source 结果
    lines.append("## Source 结果")
    lines.append("")
    if result.source_stats:
        lines.append("| Source 名称 | 类型 | 候选 | 保存 | 失败 | 状态 | 错误 |")
        lines.append("|---|---|---|---|---|---|---|")
        for stat in result.source_stats:
            lines.append(
                "| {name} | {stype} | {cand} | {saved} | {failed} | {status} | {err} |".format(
                    name=stat.get("source_name", ""),
                    stype=stat.get("source_type", ""),
                    cand=stat.get("candidate_count", 0),
                    saved=stat.get("saved_count", 0),
                    failed=stat.get("failed_count", 0),
                    status=stat.get("status", ""),
                    err=(stat.get("error") or "").replace("|", "/")[:80],
                )
            )
    else:
        lines.append("（无 source 统计）")
    lines.append("")

    # 新保存文档
    lines.append("## 新保存文档")
    lines.append("")
    saved_docs = [d for d in result.saved_documents if d.status in ("saved", "partial")]
    if saved_docs:
        for doc in saved_docs:
            lines.append(
                f"- [{doc.source_name}] {doc.title} "
                f"（{doc.published_at or '未知日期'}）"
            )
            if doc.markdown_path:
                lines.append(f"  - 本地路径：`{doc.markdown_path}`")
    else:
        lines.append("（本次没有新保存的文档）")
    lines.append("")

    # Partial / Failed
    lines.append("## Partial / Failed")
    lines.append("")
    if result.failed_documents:
        for fail in result.failed_documents:
            retry_label = "可重试" if fail.retryable else "不可重试"
            lines.append(
                f"- [{fail.source_name}] {fail.title or fail.url}"
            )
            lines.append(f"  - 失败时间：{fail.failed_at}")
            lines.append(f"  - 错误：{fail.error}")
            lines.append(f"  - 重试：{retry_label}")
    else:
        lines.append("（本次没有失败文档）")
    lines.append("")

    # Source Health
    lines.append("## Source Health")
    lines.append("")
    if result.source_health:
        lines.append("| Source 名称 | 状态 | 最近成功 | 最近失败 | 连续失败 | 候选 | 保存 |")
        lines.append("|---|---|---|---|---|---|---|")
        for health in result.source_health:
            # 兼容 SourceHealth 对象和 dict
            if hasattr(health, "source_name"):
                name = health.source_name
                status = health.status
                ok = health.last_success_at or "-"
                fail = health.last_failure_at or "-"
                cf = health.consecutive_failures
                cand = health.candidate_count_last_run
                saved = health.saved_count_last_run
            else:
                name = health.get("source_name", "")
                status = health.get("status", "")
                ok = health.get("last_success_at") or "-"
                fail = health.get("last_failure_at") or "-"
                cf = health.get("consecutive_failures", 0)
                cand = health.get("candidate_count_last_run", 0)
                saved = health.get("saved_count_last_run", 0)
            lines.append(
                f"| {name} | {status} | {ok} | {fail} | {cf} | {cand} | {saved} |"
            )
    else:
        lines.append("（无 source 健康记录）")
    lines.append("")

    # 警告
    if result.warnings:
        lines.append("## 警告")
        lines.append("")
        for w in result.warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Research Source Foundation Phase 1 MVP 自动生成*")
    lines.append("")

    return "\n".join(lines)


def daily_report_filename(date_str: str | None = None) -> str:
    """生成日报文件名。

    参数：
        date_str: 日期字符串 YYYY-MM-DD，为空则用今天

    返回：
        文件名，如 daily_capture_2026-06-22.md
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    return f"daily_capture_{date_str}.md"


def _mode_label(mode: str) -> str:
    """把 mode 代码翻译成中文标签。"""
    return {
        "run": "完整运行",
        "dry_run": "试运行（不抓正文）",
        "retry_failed": "重试失败队列",
    }.get(mode, mode or "未知")
