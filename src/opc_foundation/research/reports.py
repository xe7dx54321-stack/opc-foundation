"""Research Source Foundation 的中文日报生成。

功能说明（小白解读）：
    每次 run 完成后，生成一份中文 Markdown 日报，写到：
        data/research_archive/reports/daily_capture_YYYY-MM-DD.md

    日报内容（Phase 2F 增强）：
        1. 总览（source 数、候选数、新文档数、失败数、source 健康分布等）
        2. Source 健康概览（表格，含 status/error_type/last_error）
        3. 新保存文档（表格，含本地路径）
        4. Partial / Failed（表格，含 error_type/retryable）
        5. Warnings
        6. 下游消费入口（documents.jsonl / documents.latest.jsonl 路径）

    要求：
        - 没有新文档也要输出日报
        - 没有失败也要明确写"无"
        - source health 异常要显眼
        - 不输出正文全文
        - 不输出 secrets
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

    小白解读：
        把运行结果格式化成人类可读的中文日报，方便人工巡检。
        即使没有新文档或没有失败，也会输出完整结构。
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
    lines.append(f"- Archive Root：{result.archive_root}")
    lines.append(f"- 开始时间：{result.started_at}")
    lines.append(f"- 结束时间：{result.finished_at}")
    lines.append("")

    # ------------------------------------------------------------------
    # 1. 总览
    # ------------------------------------------------------------------
    # 统计 source health 分布
    health_counts = _count_source_health(result.source_health)

    lines.append("## 1. 总览")
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
    lines.append(f"- Source healthy：{health_counts.get('healthy', 0)}")
    lines.append(f"- Source degraded：{health_counts.get('degraded', 0)}")
    lines.append(f"- Source failed：{health_counts.get('failed', 0)}")
    lines.append(f"- Source disabled：{health_counts.get('disabled', 0)}")
    lines.append(f"- Source unknown：{health_counts.get('unknown', 0)}")
    lines.append("")

    # ------------------------------------------------------------------
    # 2. Source 健康概览
    # ------------------------------------------------------------------
    lines.append("## 2. Source 健康概览")
    lines.append("")
    if result.source_stats:
        lines.append(
            "| Source | Type | Status | Candidates | Saved | Partial | Failed | Duplicates | Error Type | Last Error |"
        )
        lines.append("|---|---|---|---:|---:|---:|---:|---:|---|---|")
        for stat in result.source_stats:
            err = (stat.get("error") or "")
            # 截断过长的错误信息，避免表格变形
            if len(err) > 80:
                err = err[:77] + "..."
            # 转义管道符
            err = err.replace("|", "/").replace("\n", " ")
            lines.append(
                "| {name} | {stype} | {status} | {cand} | {saved} | {partial} | {failed} | {dup} | {etype} | {err} |".format(
                    name=stat.get("source_name", ""),
                    stype=stat.get("source_type", ""),
                    status=stat.get("status", ""),
                    cand=stat.get("candidate_count", 0),
                    saved=stat.get("saved_count", 0),
                    partial=stat.get("partial_count", 0),
                    failed=stat.get("failed_count", 0),
                    dup=stat.get("duplicate_count", 0),
                    etype=stat.get("error_type") or "-",
                    err=err or "-",
                )
            )
    else:
        lines.append("（无 source 统计）")
    lines.append("")

    # ------------------------------------------------------------------
    # 3. 新保存文档
    # ------------------------------------------------------------------
    lines.append("## 3. 新保存文档")
    lines.append("")
    saved_docs = [d for d in result.saved_documents if d.status in ("saved", "partial")]
    if saved_docs:
        lines.append("| Source | Title | Published At | Local Path |")
        lines.append("|---|---|---|---|")
        for doc in saved_docs:
            title = (doc.title or "").replace("|", "/").replace("\n", " ")
            if len(title) > 60:
                title = title[:57] + "..."
            md_path = doc.markdown_path or "-"
            lines.append(
                f"| {doc.source_name} | {title} | {doc.published_at or '未知日期'} | `{md_path}` |"
            )
    else:
        lines.append("（本次没有新保存的文档）")
    lines.append("")

    # ------------------------------------------------------------------
    # 4. Partial / Failed
    # ------------------------------------------------------------------
    lines.append("## 4. Partial / Failed")
    lines.append("")
    if result.failed_documents:
        lines.append("| Source | Title/URL | Error Type | Error | Retryable |")
        lines.append("|---|---|---|---|---|")
        for fail in result.failed_documents:
            title_or_url = (fail.title or fail.url).replace("|", "/").replace("\n", " ")
            if len(title_or_url) > 60:
                title_or_url = title_or_url[:57] + "..."
            err = (fail.error or "").replace("|", "/").replace("\n", " ")
            if len(err) > 80:
                err = err[:77] + "..."
            retry_label = "可重试" if fail.retryable else "不可重试"
            lines.append(
                f"| {fail.source_name} | {title_or_url} | {fail.error_type or '-'} | {err} | {retry_label} |"
            )
    else:
        lines.append("（本次没有失败文档）")
    lines.append("")

    # ------------------------------------------------------------------
    # 5. Warnings
    # ------------------------------------------------------------------
    lines.append("## 5. Warnings")
    lines.append("")
    if result.warnings:
        for w in result.warnings:
            lines.append(f"- {w}")
    else:
        lines.append("（无）")
    lines.append("")

    # ------------------------------------------------------------------
    # 6. 下游消费入口
    # ------------------------------------------------------------------
    lines.append("## 6. 下游消费入口")
    lines.append("")
    archive_root = result.archive_root or "."
    lines.append(f"- documents.jsonl：`{archive_root}/index/documents.jsonl`")
    lines.append(f"- documents.latest.jsonl：`{archive_root}/index/documents.latest.jsonl`")
    lines.append(f"- source_health：`{archive_root}/state/source_health.jsonl`")
    lines.append(f"- run_log：`{archive_root}/state/run_log.jsonl`")
    lines.append(f"- failed_queue：`{archive_root}/state/failed_queue.jsonl`")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Research Source Foundation Phase 2F 自动生成*")
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


def _count_source_health(source_health: list) -> dict[str, int]:
    """统计 source health 各状态的数量。

    参数：
        source_health: SourceHealth 对象列表或 dict 列表

    返回：
        {"healthy": X, "degraded": X, "failed": X, "disabled": X, "unknown": X}
    """
    counts: dict[str, int] = {
        "healthy": 0,
        "degraded": 0,
        "failed": 0,
        "disabled": 0,
        "unknown": 0,
    }
    for h in source_health:
        if hasattr(h, "status"):
            status = h.status
        else:
            status = h.get("status", "unknown") if isinstance(h, dict) else "unknown"
        if status in counts:
            counts[status] += 1
        else:
            counts["unknown"] += 1
    return counts


def _mode_label(mode: str) -> str:
    """把 mode 代码翻译成中文标签。"""
    return {
        "run": "完整运行",
        "dry_run": "试运行（不抓正文）",
        "retry_failed": "重试失败队列",
        "report": "日报合并",
    }.get(mode, mode or "未知")
