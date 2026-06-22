"""中文 Markdown 日报生成。

功能说明（小白解读）：
    把一次运行的 WeChatArchiveRunResult 转成中文 Markdown 报告，
    包含：总览、账号健康统计、新保存文章、失败文章列表等。
"""
from __future__ import annotations

from .models import WeChatArchiveRunResult


def _plural_zh(count: int, noun: str) -> str:
    return f"{count} {noun}"


def build_daily_capture_report(result: WeChatArchiveRunResult) -> str:
    """把运行结果汇总成中文 Markdown 日报。"""

    lines: list[str] = []
    lines.append("# 微信公众号归档日报")
    lines.append("")
    lines.append(f"- 运行 ID：{result.run_id}")
    lines.append(f"- 开始时间：{result.started_at}")
    lines.append(f"- 结束时间：{result.ended_at}")
    lines.append(f"- 归档根目录：{result.archive_root}")
    lines.append("")

    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 监控账号：{result.total_accounts} 个")
    lines.append(f"- 发现候选文章：{result.total_candidates} 篇")
    lines.append(f"- 新文章：{result.total_new_articles} 篇")
    lines.append(f"- 成功保存：{result.total_saved} 篇")
    lines.append(f"- 部分保存：{result.total_partial} 篇")
    lines.append(f"- 失败：{result.total_failed} 篇")
    lines.append(f"- 重复跳过：{result.total_duplicate} 篇")
    lines.append("")

    if result.warnings:
        lines.append("## 运行警告")
        lines.append("")
        for w in result.warnings:
            lines.append(f"- {w}")
        lines.append("")

    if result.accounts:
        lines.append("## 账号健康")
        lines.append("")
        lines.append("| 账号 | 候选数 | 新文章 | 成功 | 部分 | 失败 | 重复 | 最近成功时间 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for acc in result.accounts:
            lines.append(
                "| "
                + " | ".join(
                    [
                        acc.account_name,
                        str(acc.candidates),
                        str(acc.new_articles),
                        str(acc.saved),
                        str(acc.partial),
                        str(acc.failed),
                        str(acc.duplicate),
                        (acc.last_success_at or "-"),
                    ]
                )
                + " |"
            )
        lines.append("")

    if result.saved_articles:
        lines.append("## 新保存文章")
        lines.append("")
        for idx, art in enumerate(result.saved_articles, start=1):
            lines.append(f"{idx}. 【{art.account_name or '未知公众号'}】{art.title}")
            if art.published_at:
                lines.append(f"   - 发布时间：{art.published_at}")
            lines.append(f"   - 原文链接：{art.url}")
            lines.append(f"   - 本地路径：{art.archive_dir}")
            if art.digest:
                # 单行截断，避免日报过长
                digest = art.digest.strip().replace("\n", " ")
                if len(digest) > 160:
                    digest = digest[:160] + "…"
                lines.append(f"   - 摘要：{digest}")
            lines.append("")

    if result.failed_articles:
        lines.append("## 失败 / 待重试")
        lines.append("")
        for idx, f in enumerate(result.failed_articles, start=1):
            lines.append(f"{idx}. 【{f.account_name or '未知公众号'}】{f.title}")
            lines.append(f"   - 原文链接：{f.url}")
            lines.append(f"   - 失败时间：{f.failed_at}")
            if f.error:
                lines.append(f"   - 错误信息：{f.error}")
            if f.retry_count:
                lines.append(f"   - 重试次数：{f.retry_count}")
            lines.append("")

    if result.reports:
        lines.append("## 报告文件")
        lines.append("")
        for r in result.reports:
            lines.append(f"- {r}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
