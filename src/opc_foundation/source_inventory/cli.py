"""Source Inventory Live Smoke CLI。

功能说明（小白解读）：
    命令行入口，用 argparse 实现。
    支持 validate-config / dry-run / run / report 四个子命令。

    怎么用？
        python -m opc_foundation.source_inventory.cli validate-config --config configs/foundation_source_inventory.example.yaml
        python -m opc_foundation.source_inventory.cli dry-run --config configs/foundation_source_inventory.example.yaml
        python -m opc_foundation.source_inventory.cli run --config configs/foundation_source_inventory.example.yaml
        python -m opc_foundation.source_inventory.cli report --archive-root data/source_inventory_live_smoke
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cmd_validate_config(args: argparse.Namespace) -> int:
    """validate-config 子命令：验证配置文件。

    小白解读：
        加载 source inventory 配置，看看格式对不对、有多少个源、有多少个 group。
        不访问网络，只做配置校验。

    Args:
        args: 命令行参数

    Returns:
        int: 退出码（0=成功，非 0=失败）
    """
    try:
        from ..dashboard.loaders import load_source_inventory_config
    except ImportError as e:
        print(f"Error: Failed to import loaders: {e}")
        return 1

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return 1

    try:
        inventory = load_source_inventory_config(str(config_path))
    except Exception as e:
        print(f"Error: Failed to load config: {e}")
        return 1

    if inventory.load_error:
        print(f"Config load error: {inventory.load_error}")
        return 1

    print("Source Inventory config validation: PASSED")
    print(f"  Version: {inventory.version}")
    print(f"  Updated at: {inventory.updated_at}")
    print(f"  Groups: {len(inventory.groups)}")
    print(f"  Sources: {len(inventory.sources)}")

    for group in inventory.groups:
        count = sum(1 for s in inventory.sources if s.source_group == group.group_id)
        print(f"  - {group.group_name}: {count} sources")

    return 0


def _cmd_dry_run(args: argparse.Namespace) -> int:
    """dry-run 子命令：dry-run live smoke（不访问网络）。

    小白解读：
        模拟跑一遍 live smoke，但不真实访问网络。
        用于验证流程是否正常，比如 92 个源是不是都被遍历到了。

    Args:
        args: 命令行参数

    Returns:
        int: 退出码
    """
    try:
        from ..dashboard.loaders import load_source_inventory_config
    except ImportError as e:
        print(f"Error: Failed to import loaders: {e}")
        return 1

    from .live_smoke import run_live_smoke
    from .models import LiveSmokeRunConfig

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return 1

    try:
        inventory = load_source_inventory_config(str(config_path))
    except Exception as e:
        print(f"Error: Failed to load config: {e}")
        return 1

    if inventory.load_error:
        print(f"Config load error: {inventory.load_error}")
        return 1

    run_config = LiveSmokeRunConfig(dry_run=True)
    print(f"Running live smoke dry-run for {len(inventory.sources)} sources...")

    summary = run_live_smoke(inventory, run_config)

    print(f"Dry-run complete: {summary.total_sources} sources in {summary.total_duration_ms}ms")
    print(f"  Status counts: {summary.status_counts}")

    output_dir = Path(args.output_dir) if args.output_dir else Path("data/source_inventory_live_smoke")
    from .live_smoke import save_live_smoke_results

    save_live_smoke_results(summary, str(output_dir))
    print(f"Results saved to: {output_dir}")

    return 0


def _resolve_proxy(cli_proxy: str | None) -> tuple[str, str]:
    """解析代理配置，返回 (proxy_url, proxy_mode)。

    小白解读：
        代理优先级：
        1. CLI 参数 --proxy（mode=cli）
        2. 环境变量 HTTPS_PROXY / HTTP_PROXY（mode=env）
        3. 都没有就不用代理（mode=none）

    Args:
        cli_proxy: CLI 传入的代理地址（可能为 None）

    Returns:
        tuple[str, str]: (代理地址, 代理来源模式 cli/env/none)
    """
    import os

    if cli_proxy:
        return cli_proxy, "cli"

    env_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not env_proxy:
        env_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if env_proxy:
        return env_proxy, "env"

    return "", "none"


def _cmd_run(args: argparse.Namespace) -> int:
    """run 子命令：真实跑 live smoke。

    小白解读：
        真实访问每个源（除了 blocked/on_demand/dormant）。
        每个源最多抓 max_candidates_per_source 个候选。

    Args:
        args: 命令行参数

    Returns:
        int: 退出码
    """
    try:
        from ..dashboard.loaders import load_source_inventory_config
    except ImportError as e:
        print(f"Error: Failed to import loaders: {e}")
        return 1

    from .live_smoke import run_live_smoke, save_live_smoke_results
    from .models import LiveSmokeRunConfig

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return 1

    try:
        inventory = load_source_inventory_config(str(config_path))
    except Exception as e:
        print(f"Error: Failed to load config: {e}")
        return 1

    if inventory.load_error:
        print(f"Config load error: {inventory.load_error}")
        return 1

    proxy_url, proxy_mode = _resolve_proxy(getattr(args, "proxy", None))

    run_config = LiveSmokeRunConfig(
        max_candidates_per_source=args.max_candidates_per_source,
        timeout_seconds=args.timeout_seconds,
        max_retries=1,
        proxy_url=proxy_url,
        proxy_mode=proxy_mode,
    )

    print(f"Running live smoke for {len(inventory.sources)} sources...")
    print(f"  max_candidates_per_source: {run_config.max_candidates_per_source}")
    print(f"  timeout_seconds: {run_config.timeout_seconds}")
    print(f"  proxy_enabled: {run_config.proxy_url != ''}")
    print(f"  proxy_mode: {run_config.proxy_mode}")
    print("")

    summary = run_live_smoke(inventory, run_config)

    print("")
    print(f"Live smoke complete: {summary.total_sources} sources in {summary.total_duration_ms / 1000:.1f}s")
    print(f"  Status counts:")
    for status, count in summary.status_counts.items():
        print(f"    {status}: {count}")

    output_dir = Path(args.output_dir) if args.output_dir else Path("data/source_inventory_live_smoke")
    save_live_smoke_results(summary, str(output_dir))
    print(f"Results saved to: {output_dir}")

    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    """report 子命令：从已有结果生成 Markdown 报告。

    小白解读：
        读取 data/source_inventory_live_smoke/index/source_live_status.latest.json，
        生成一份 Markdown 报告。

    Args:
        args: 命令行参数

    Returns:
        int: 退出码
    """
    from .live_smoke import LiveSmokeSummary, SourceGroupLiveResult, SourceLiveResult
    from .reports import generate_live_smoke_report, save_report

    archive_root = Path(args.archive_root)
    latest_path = archive_root / "index" / "source_live_status.latest.json"

    if not latest_path.exists():
        print(f"Error: Latest status file not found: {latest_path}")
        return 1

    try:
        data = json.loads(latest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error: Failed to read latest status: {e}")
        return 1

    summary = _summary_from_dict(data)
    report = generate_live_smoke_report(summary)

    if args.output:
        output_path = Path(args.output)
    else:
        reports_dir = archive_root / "reports"
        from datetime import datetime

        today = datetime.utcnow().strftime("%Y-%m-%d")
        output_path = reports_dir / f"source_live_smoke_{today}.md"

    save_report(report, output_path)
    print(f"Report saved to: {output_path}")

    return 0


def _summary_from_dict(data: dict) -> LiveSmokeSummary:
    """从字典重建 LiveSmokeSummary。

    Args:
        data: 字典数据

    Returns:
        LiveSmokeSummary: 汇总对象
    """
    from .models import LiveSmokeStatus, LiveSmokeSummary, SourceGroupLiveResult, SourceLiveResult

    groups: list[SourceGroupLiveResult] = []

    results_by_group: dict[str, list[SourceLiveResult]] = {}
    for r_data in data.get("results", []):
        result = SourceLiveResult.from_dict(r_data)
        group_id = result.source_group
        if group_id not in results_by_group:
            results_by_group[group_id] = []
        results_by_group[group_id].append(result)

    for group_id, results in results_by_group.items():
        group = SourceGroupLiveResult(
            group_id=group_id,
            group_name=group_id,
            total_sources=len(results),
            results=results,
        )
        groups.append(group)

    return LiveSmokeSummary(
        total_sources=data.get("total_sources", 0),
        groups=groups,
        run_started_at=data.get("run_started_at", ""),
        run_finished_at=data.get("run_finished_at", ""),
        total_duration_ms=data.get("total_duration_ms", 0),
        proxy_enabled=data.get("proxy_enabled", False),
        proxy_mode=data.get("proxy_mode", "none"),
    )


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    Args:
        argv: 命令行参数列表（不传则用 sys.argv）

    Returns:
        int: 退出码
    """
    parser = argparse.ArgumentParser(
        prog="opc_foundation.source_inventory",
        description="Source Inventory Live Smoke CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # validate-config
    p_validate = subparsers.add_parser("validate-config", help="Validate source inventory config")
    p_validate.add_argument("--config", required=True, help="Path to source inventory config file")
    p_validate.set_defaults(func=_cmd_validate_config)

    # dry-run
    p_dry = subparsers.add_parser("dry-run", help="Dry-run live smoke (no network)")
    p_dry.add_argument("--config", required=True, help="Path to source inventory config file")
    p_dry.add_argument("--output-dir", default="data/source_inventory_live_smoke", help="Output directory")
    p_dry.set_defaults(func=_cmd_dry_run)

    # run
    p_run = subparsers.add_parser("run", help="Run live smoke (real network access)")
    p_run.add_argument("--config", required=True, help="Path to source inventory config file")
    p_run.add_argument("--max-candidates-per-source", type=int, default=5, help="Max candidates per source")
    p_run.add_argument("--timeout-seconds", type=int, default=20, help="Request timeout in seconds")
    p_run.add_argument("--proxy", default=None, help="Proxy URL (e.g. http://127.0.0.1:7890). Also reads HTTPS_PROXY/HTTP_PROXY env vars.")
    p_run.add_argument("--output-dir", default="data/source_inventory_live_smoke", help="Output directory")
    p_run.set_defaults(func=_cmd_run)

    # report
    p_report = subparsers.add_parser("report", help="Generate Markdown report from results")
    p_report.add_argument("--archive-root", default="data/source_inventory_live_smoke", help="Archive root directory")
    p_report.add_argument("--output", help="Output report file path")
    p_report.set_defaults(func=_cmd_report)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
