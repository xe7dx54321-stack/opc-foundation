"""Source Inventory Live Smoke 报告生成。

功能说明（小白解读）：
    把 live smoke 的结果生成一份漂亮的 Markdown 报告。
    包含总览、分组统计、每个源的状态表、各种清单。

    报告放哪里？
        - 运行时结果：data/source_inventory_live_smoke/（不提交 Git）
        - 正式报告：docs/foundation_source_live_smoke_report.md（提交）
"""

from __future__ import annotations

from pathlib import Path

from .models import (
    LIVE_SMOKE_STATUS_LABELS,
    LiveSmokeStatus,
    LiveSmokeSummary,
    SourceGroupLiveResult,
    SourceLiveResult,
)


def generate_live_smoke_report(summary: LiveSmokeSummary) -> str:
    """生成 live smoke 报告（Markdown 格式）。

    小白解读：
        根据汇总结果生成一份完整的 Markdown 报告。
        包含：执行信息、总览、分组统计、源清单、各种列表等。

    Args:
        summary: live smoke 汇总结果

    Returns:
        str: Markdown 格式的报告
    """
    lines: list[str] = []

    lines.append("# Foundation Source Inventory Live Smoke 报告")
    lines.append("")
    lines.append("> 版本：1.0  ")
    lines.append(f"> 生成时间：{summary.run_finished_at}  ")
    lines.append(f"> Source 总数：{summary.total_sources}  ")
    lines.append("")
    lines.append("> **重要说明**：")
    lines.append("> - 本报告是 live smoke 结果，不等于正式生产稳定运行")
    lines.append("> - 本阶段用于确认 92 个源的真实接通能力和后续补齐优先级")
    lines.append("> - blocked/high_risk 源按策略未访问")
    lines.append("> - on_demand / dormant 源未默认运行")
    lines.append("> - search provider 未跑真实搜索，仅做配置检查")
    lines.append("")

    # 1. 执行时间
    lines.append("## 1. 执行信息")
    lines.append("")
    lines.append(f"- 开始时间：{summary.run_started_at}")
    lines.append(f"- 结束时间：{summary.run_finished_at}")
    lines.append(f"- 总耗时：{summary.total_duration_ms / 1000:.1f} 秒")
    lines.append(f"- Source 总数：{summary.total_sources}")
    lines.append(f"- 代理启用：{summary.proxy_enabled}")
    lines.append(f"- 代理来源：{summary.proxy_mode}")
    lines.append("")

    # 2. 总览统计
    lines.append("## 2. 总览统计")
    lines.append("")
    lines.append("| 状态 | 数量 | 中文说明 |")
    lines.append("|---|---|---|")
    status_counts = summary.status_counts
    for status_enum in LiveSmokeStatus:
        count = status_counts.get(status_enum.value, 0)
        if count > 0:
            label = LIVE_SMOKE_STATUS_LABELS.get(status_enum, status_enum.value)
            lines.append(f"| {status_enum.value} | {count} | {label} |")
    lines.append("")

    # 关键指标
    success_count = summary.success_count
    blocked_count = summary.blocked_count
    needs_connector = summary.needs_connector_count
    failure_count = summary.failure_count
    on_demand_count = status_counts.get("on_demand_not_run", 0)
    dormant_count = status_counts.get("dormant_not_run", 0)

    lines.append("### 2.1 关键指标")
    lines.append("")
    lines.append(f"- 可访问（live_ok 系列）：{success_count}")
    lines.append(f"- 按策略禁止访问（blocked_by_policy）：{blocked_count}")
    lines.append(f"- 按需源未运行（on_demand_not_run）：{on_demand_count}")
    lines.append(f"- 休眠源未运行（dormant_not_run）：{dormant_count}")
    lines.append(f"- 需要补 connector（needs_connector）：{needs_connector}")
    lines.append(f"- 访问失败（http_error/timeout/failed）：{failure_count}")
    lines.append("")

    # 3. Source Group 总览
    lines.append("## 3. Source Group 总览")
    lines.append("")
    lines.append("| Group | 源数 | 成功 | 失败 | 接通率 |")
    lines.append("|---|---|---|---|---|")
    for group in summary.groups:
        if group.total_sources == 0:
            continue
        rate = (group.success_count / group.total_sources * 100) if group.total_sources > 0 else 0
        lines.append(
            f"| {group.group_name} | {group.total_sources} | {group.success_count} | {group.failure_count} | {rate:.0f}% |"
        )
    lines.append("")

    # 4. 每个 Source Group 的详细结果
    lines.append("## 4. 各 Source Group 详细结果")
    lines.append("")
    for group in summary.groups:
        if group.total_sources == 0:
            continue
        lines.append(f"### 4.{summary.groups.index(group) + 1} {group.group_name}")
        lines.append("")
        lines.append(f"- 源数：{group.total_sources}")
        lines.append(f"- 成功：{group.success_count}")
        lines.append(f"- 失败：{group.failure_count}")
        lines.append("")
        lines.append("| source_id | source_name | status | 中文 | visited | candidates | 备注 |")
        lines.append("|---|---|---|---|---|---|---|")
        for result in group.results:
            label = LIVE_SMOKE_STATUS_LABELS.get(result.status, result.status.value)
            visited = "✅" if result.visited else "❌"
            notes = result.notes[:80] if result.notes else ""
            lines.append(
                f"| {result.source_id} | {result.source_name} | {result.status.value} | {label} | {visited} | {result.candidates_found} | {notes} |"
            )
        lines.append("")

    # 5. Needs Connector 清单
    lines.append("## 5. Needs Connector 清单")
    lines.append("")
    lines.append("这些源目前还没有对应的 connector，需要后续开发。")
    lines.append("")
    needs_list = _collect_results_by_status(summary, LiveSmokeStatus.NEEDS_CONNECTOR)
    if needs_list:
        lines.append("| source_id | source_name | group | access_mode | 备注 |")
        lines.append("|---|---|---|---|---|")
        for r in needs_list:
            lines.append(f"| {r.source_id} | {r.source_name} | {r.source_group} | {r.access_mode} | {r.notes[:80]} |")
    else:
        lines.append("暂无。")
    lines.append("")

    # 6. Parser Mismatch 清单
    lines.append("## 6. Parser Mismatch 清单")
    lines.append("")
    lines.append("这些源能访问，但当前解析规则不匹配。")
    lines.append("")
    mismatch_list = _collect_results_by_status(summary, LiveSmokeStatus.PARSER_MISMATCH)
    if mismatch_list:
        lines.append("| source_id | source_name | group | 备注 |")
        lines.append("|---|---|---|---|")
        for r in mismatch_list:
            lines.append(f"| {r.source_id} | {r.source_name} | {r.source_group} | {r.notes[:80]} |")
    else:
        lines.append("暂无。")
    lines.append("")

    # 7. Failed 源清单
    lines.append("## 7. Failed 源清单")
    lines.append("")
    lines.append("这些源访问失败，需要排查原因。")
    lines.append("")
    failed_list = _collect_results_by_statuses(
        summary,
        {LiveSmokeStatus.HTTP_ERROR, LiveSmokeStatus.TIMEOUT, LiveSmokeStatus.FAILED},
    )
    if failed_list:
        lines.append("| source_id | source_name | group | status | 错误信息 |")
        lines.append("|---|---|---|---|---|")
        for r in failed_list:
            lines.append(f"| {r.source_id} | {r.source_name} | {r.source_group} | {r.status.value} | {r.error_message[:100]} |")
    else:
        lines.append("暂无。")
    lines.append("")

    # 8. Blocked/High Risk 确认
    lines.append("## 8. Blocked / High Risk 源确认")
    lines.append("")
    lines.append("以下源按策略禁止访问，确认全部标记为 `blocked_by_policy`，且 `visited=false`。")
    lines.append("")
    blocked_list = _collect_results_by_status(summary, LiveSmokeStatus.BLOCKED_BY_POLICY)
    if blocked_list:
        lines.append("| source_id | source_name | group | visited | fetched |")
        lines.append("|---|---|---|---|---|")
        for r in blocked_list:
            visited = "false ✅" if not r.visited else "true ❌"
            fetched = "false ✅" if not r.fetched else "true ❌"
            lines.append(f"| {r.source_id} | {r.source_name} | {r.source_group} | {visited} | {fetched} |")
    else:
        lines.append("暂无。")
    lines.append("")

    # 9. On-Demand 源确认
    lines.append("## 9. On-Demand / Search Provider 源确认")
    lines.append("")
    lines.append("以下源是按需/搜索 provider，确认未默认运行。")
    lines.append("")
    on_demand_list = _collect_results_by_status(summary, LiveSmokeStatus.ON_DEMAND_NOT_RUN)
    if on_demand_list:
        lines.append("| source_id | source_name | group | visited | fetched | 备注 |")
        lines.append("|---|---|---|---|---|---|")
        for r in on_demand_list:
            visited = "false ✅" if not r.visited else "true ❌"
            fetched = "false ✅" if not r.fetched else "true ❌"
            lines.append(f"| {r.source_id} | {r.source_name} | {r.source_group} | {visited} | {fetched} | {r.notes[:60]} |")
    else:
        lines.append("暂无。")
    lines.append("")

    # 10. 后续建议
    lines.append("## 10. 后续建议")
    lines.append("")
    lines.append("### 10.1 可进入 TRAE 试运行的源")
    lines.append("")
    lines.append("状态为 `live_ok_candidates_found` 或 `live_ok_saved` 的 scheduled 源。")
    lines.append("")
    ready_list = _collect_results_by_statuses(
        summary,
        {LiveSmokeStatus.LIVE_OK_CANDIDATES_FOUND, LiveSmokeStatus.LIVE_OK_SAVED},
    )
    if ready_list:
        for r in ready_list:
            lines.append(f"- `{r.source_id}`（{r.source_name}）— 候选 {r.candidates_found} 个")
    else:
        lines.append("暂无。")
    lines.append("")

    lines.append("### 10.2 需要补 connector 的源")
    lines.append("")
    if needs_list:
        for r in needs_list:
            lines.append(f"- `{r.source_id}`（{r.source_name}）— {r.access_mode}")
    else:
        lines.append("暂无。")
    lines.append("")

    lines.append("### 10.3 建议继续 blocked 的源")
    lines.append("")
    if blocked_list:
        for r in blocked_list:
            lines.append(f"- `{r.source_id}`（{r.source_name}）")
    else:
        lines.append("暂无。")
    lines.append("")

    # 11. 优先级汇总
    lines.append("## 11. S/A/B/C 优先级接通情况")
    lines.append("")
    lines.append("*待 source inventory 配置中完善 priority 字段后补充。*")
    lines.append("")

    return "\n".join(lines)


def save_report(report_md: str, output_path: str | Path) -> Path:
    """保存报告到文件。

    Args:
        report_md: Markdown 报告内容
        output_path: 输出文件路径

    Returns:
        Path: 输出文件路径
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_md, encoding="utf-8")
    return path


def _collect_results_by_status(
    summary: LiveSmokeSummary,
    status: LiveSmokeStatus,
) -> list[SourceLiveResult]:
    """按状态收集结果。

    Args:
        summary: 汇总
        status: 要筛选的状态

    Returns:
        list[SourceLiveResult]: 匹配的结果列表
    """
    results: list[SourceLiveResult] = []
    for group in summary.groups:
        for r in group.results:
            if r.status == status:
                results.append(r)
    return results


def _collect_results_by_statuses(
    summary: LiveSmokeSummary,
    statuses: set[LiveSmokeStatus],
) -> list[SourceLiveResult]:
    """按多个状态收集结果。

    Args:
        summary: 汇总
        statuses: 要筛选的状态集合

    Returns:
        list[SourceLiveResult]: 匹配的结果列表
    """
    results: list[SourceLiveResult] = []
    for group in summary.groups:
        for r in group.results:
            if r.status in statuses:
                results.append(r)
    return results
