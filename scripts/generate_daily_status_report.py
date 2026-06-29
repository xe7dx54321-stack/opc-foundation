"""Generate Foundation Daily Status Report.

功能说明（小白解读）：
    这个脚本被 check_foundation_daily_status.ps1 调用，
    生成每日状态报告 Markdown 文件。

    从配置文件和 trial 运行时数据读取信息，汇总成报告。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, "src")

from opc_foundation.dashboard.loaders import (
    build_trial_runtime_summary,
    load_capabilities_config,
    load_source_inventory_config,
    summarize_source_inventory,
)


def generate_report() -> str:
    """生成每日状态报告。

    功能说明（小白解读）：
        读取能力配置、信息源清单、trial 运行时数据，
        汇总成一份 Markdown 格式的报告。

    返回：
        str: Markdown 格式的报告内容
    """
    today = date.today().strftime("%Y-%m-%d")

    # Load configs
    cap_path = "configs/foundation_capabilities.yaml"
    inv_path = "configs/foundation_source_inventory.example.yaml"

    registry = load_capabilities_config(cap_path)
    inventory = load_source_inventory_config(inv_path)
    summary = summarize_source_inventory(inventory)

    # Load trial runtime data
    trial = build_trial_runtime_summary()

    # Generate report
    lines = []
    lines.append(f"# Foundation Daily Status Report - {today}")
    lines.append("")
    lines.append("## 1. Capability Status Summary")
    lines.append("")
    lines.append(f"- Total capabilities: {len(registry.capabilities)}")
    lines.append("- Runtime bindings: Awaiting runtime data integration")
    lines.append("")
    lines.append("## 2. Foundation Trial Sources")
    lines.append("")
    if trial.data_exists:
        lines.append(f"- Trial source count: {trial.total_sources}")
        lines.append(f"- Latest run: {trial.latest_run_at or 'N/A'}")
        lines.append(f"- Success: {trial.success_count}")
        lines.append(f"- Failed: {trial.failed_count}")
        lines.append(f"- Transient watch: {trial.transient_count}")
        lines.append(f"- Skipped (dry_run): {trial.skipped_count}")
        lines.append(f"- Empty (candidate_count=0): {trial.empty_count}")
        lines.append(f"- Overall health: {trial.overall_health}")
        lines.append("")
        if trial.transient_sources:
            sources_str = ", ".join(trial.transient_sources)
            lines.append(f"- Transient watch sources: {sources_str}")
            lines.append("  (e.g. cls_cn HTTP 418 - transient anti-bot response, NOT P0/P1 blocker)")
            lines.append("")
        lines.append("- Microsoft IR: url_backlog (excluded from trial)")
        lines.append("- blocked/search/dormant/problem sources: NOT included in trial")
    else:
        lines.append("- Trial data not yet generated.")
        lines.append("  Run: `scripts/run_foundation_trial_sources.ps1 -Mode run`")
    lines.append("")
    lines.append("## 3. Source Inventory Summary")
    lines.append("")
    lines.append(f"- Source groups: {summary.group_count}")
    lines.append(f"- Total sources: {summary.source_count}")
    lines.append(f"- Default enabled: {summary.enabled_count}")
    lines.append(f"- High risk/blocked: {summary.high_risk_count}")
    lines.append(f"- Search providers: {summary.search_provider_count}")
    lines.append(f"- Community sources: {summary.community_count}")
    lines.append("")
    lines.append("### Priority Distribution")
    lines.append("")
    for priority, count in sorted(summary.priority_counts.items()):
        lines.append(f"- {priority}: {count}")
    lines.append("")
    lines.append("### Automation Mode Distribution")
    lines.append("")
    for mode, count in sorted(summary.automation_counts.items()):
        lines.append(f"- {mode}: {count}")
    lines.append("")
    lines.append("## 4. Runtime Binding Summary")
    lines.append("")
    lines.append("- Awaiting runtime data integration")
    lines.append("")
    lines.append("## 5. Known Limited Summary")
    lines.append("")
    lines.append("- Awaiting runtime data integration")
    lines.append("")
    lines.append("## 6. Blocked / High Risk Sources")
    lines.append("")
    lines.append(f"- Total blocked/high risk: {summary.high_risk_count}")
    lines.append("- Not in scheduled tasks")
    lines.append("")
    lines.append("## 7. TRAE Schedule Template Summary")
    lines.append("")
    lines.append("- See configs/trae_foundation_schedule.example.yaml")
    lines.append("- Default enabled: scheduled tasks")
    lines.append("- Search/Community/Dev: on_demand")
    lines.append("")
    lines.append("## 8. Next Steps")
    lines.append("")
    lines.append("- Monitor cls_cn transient watch (HTTP 418)")
    lines.append("- If trial stable for 2 weeks, consider M3C-5 production scheduling")
    lines.append("- Microsoft IR: explore alternative entry points (SEC EDGAR, third-party platforms)")
    lines.append("")
    lines.append("---")
    lines.append(f"*Report generated: {today}*")

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_report())
