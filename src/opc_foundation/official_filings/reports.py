"""Official Filing Foundation 的日报生成。

功能说明（小白解读）：
    每次 run 完成后，生成一份中文 Markdown 日报，写到：
        data/official_filings/reports/daily_filing_YYYY-MM-DD.md

    日报内容：
        1. 总览
        2. Source 健康概览
        3. 新保存 filings
        4. Partial / Failed
        5. Warnings
        6. 下游消费入口

    要求：
        - 没有新披露也要输出日报
        - 没有失败也要明确写"无"
        - source health 异常要显眼
        - 不输出正文全文
        - 不输出 secrets
        - 不做投资判断
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import FilingRunResult


def daily_report_filename(finished_at: str | None = None) -> str:
    """生成日报文件名。

    参数：
        finished_at: 运行结束时间（ISO 字符串）

    返回：
        日报文件名字符串，如 daily_filing_2026-06-23.md
    """
    try:
        date_str = (finished_at or "")[:10]
        if not date_str:
            raise ValueError("empty date")
        datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        date_str = datetime.now().strftime("%Y-%m-%d")
    return f"daily_filing_{date_str}.md"


def _mode_label(mode: str) -> str:
    """把 mode 翻译成中文。"""
    mapping = {
        "dry-run": "试运行（只发现，不归档）",
        "run": "正式运行",
        "validate": "配置校验",
    }
    return mapping.get(mode, mode)


def _count_source_health(health_list: list) -> dict[str, int]:
    """统计各健康状态的 source 数量。"""
    counts: dict[str, int] = {}
    for h in health_list:
        s = getattr(h, "status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    return counts


def build_filing_daily_report(result: FilingRunResult) -> str:
    """生成一份中文 Markdown 日报。

    参数：
        result: 一次 run 的汇总结果

    返回：
        Markdown 字符串

    小白解读：
        把运行结果格式化成人类可读的中文日报，方便人工巡检。
        即使没有新披露或没有失败，也会输出完整结构。
    """
    # 日期：用 finished_at 解析，失败则用今天
    try:
        date_str = (result.finished_at or result.started_at)[:10]
    except Exception:
        date_str = datetime.now().strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append("# Official Filing Foundation 采集日报")
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
    health_counts = _count_source_health(result.source_health)

    lines.append("## 1. 总览")
    lines.append("")
    lines.append(f"- Source 总数：{result.source_count}")
    lines.append(f"- 启用 Source：{result.enabled_source_count}")
    lines.append(f"- 候选披露：{result.candidate_count}")
    lines.append(f"- 新保存：{result.saved_count}")
    lines.append(f"- 重复跳过：{result.duplicate_count}")
    lines.append(f"- 部分保存：{result.partial_count}")
    lines.append(f"- 失败：{result.failed_count}")
    lines.append(f"- 跳过：{result.skipped_count}")
    lines.append(f"- Source healthy：{health_counts.get('healthy', 0)}")
    lines.append(f"- Source degraded：{health_counts.get('degraded', 0)}")
    lines.append(f"- Source failed：{health_counts.get('failed', 0)}")
    lines.append(f"- Source disabled：{health_counts.get('disabled', 0)}")
    lines.append("")

    # ------------------------------------------------------------------
    # 2. Source 健康概览
    # ------------------------------------------------------------------
    lines.append("## 2. Source 健康概览")
    lines.append("")
    if result.source_health:
        lines.append("| Source ID | 类型 | 状态 | 候选数 | 保存数 | 失败数 | 连续失败 | 最近错误 |")
        lines.append("|-----------|------|------|--------|--------|--------|----------|----------|")
        for h in result.source_health:
            error_text = (h.last_error or "")[:30] if h.last_error else "-"
            lines.append(
                f"| {h.source_id} | {h.source_type or '-'} | {h.status} | "
                f"{h.candidate_count_last_run} | {h.saved_count_last_run} | "
                f"{h.failed_count_last_run} | {h.consecutive_failures} | "
                f"{error_text} |"
            )
    else:
        lines.append("暂无 source health 记录。")
    lines.append("")

    # ------------------------------------------------------------------
    # 3. 新保存 filings
    # ------------------------------------------------------------------
    lines.append("## 3. 新保存披露")
    lines.append("")
    if result.saved_filings:
        lines.append("| 披露 ID | Source | 公司 | 类型 | 日期 | 标题 |")
        lines.append("|---------|--------|------|------|------|------|")
        for f in result.saved_filings[:20]:
            title = (f.filing_title or "-")[:50]
            issuer = f.issuer_name or f.issuer_code or "-"
            lines.append(
                f"| {f.filing_id[:12]}... | {f.source_id} | {issuer} | "
                f"{f.filing_type or '-'} | {f.filing_date or '-'} | {title} |"
            )
        if len(result.saved_filings) > 20:
            lines.append("")
            lines.append(f"*（仅展示前 20 条，共 {len(result.saved_filings)} 条，详见 filings.jsonl）*")
    else:
        lines.append("本次无新保存的披露。")
    lines.append("")

    # ------------------------------------------------------------------
    # 4. Partial / Failed
    # ------------------------------------------------------------------
    lines.append("## 4. Partial / Failed")
    lines.append("")
    if result.failed_filings:
        lines.append("| Source | 标题 | 错误类型 | 错误信息 | 可重试 |")
        lines.append("|--------|------|----------|----------|--------|")
        for f in result.failed_filings[:20]:
            title = (f.filing_title or "-")[:40]
            error = (f.error or "")[:50]
            lines.append(
                f"| {f.source_id} | {title} | {f.error_type or '-'} | "
                f"{error} | {'是' if f.retryable else '否'} |"
            )
    else:
        lines.append("本次无失败。")
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
        lines.append("本次无警告。")
    lines.append("")

    # ------------------------------------------------------------------
    # 6. 下游消费入口
    # ------------------------------------------------------------------
    lines.append("## 6. 下游消费入口")
    lines.append("")
    lines.append("所有归档数据可通过以下文件消费：")
    lines.append("")
    lines.append("- `index/filings.jsonl`：全量披露索引（追加写）")
    lines.append("- `index/filings.latest.jsonl`：最新状态快照（覆盖写）")
    lines.append("- `index/source_health.jsonl`：source 健康状态历史")
    lines.append("- `index/failed_queue.jsonl`：失败队列")
    lines.append("- `index/run_log.jsonl`：运行日志")
    lines.append("")
    lines.append("> **注意**：Foundation 只提供归档和元数据，不做投资判断。")
    lines.append("> 下游业务系统自行决定如何使用这些披露信息。")
    lines.append("")

    return "\n".join(lines)
