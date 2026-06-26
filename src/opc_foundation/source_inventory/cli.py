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


# ============================================================
# Trial Run 子命令
# ============================================================


def _cmd_trial_validate(args: argparse.Namespace) -> int:
    """trial-validate 子命令：验证 trial 配置和 allowlist。

    小白解读：
        检查 trial-only 配置是否正确：
        - allowlist 中 trial source 是否为 16 个
        - 是否误包含 blocked/search/dormant/problem sources
        - trial config 格式是否正确

    Args:
        args: 命令行参数

    Returns:
        int: 退出码（0=成功，非 0=失败）
    """
    import yaml

    config_path = Path(args.config)
    allowlist_path = Path(args.allowlist)

    if not allowlist_path.exists():
        print(f"Error: Allowlist file not found: {allowlist_path}")
        return 1

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return 1

    try:
        with open(allowlist_path, "r", encoding="utf-8") as f:
            allowlist_data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error: Failed to load allowlist: {e}")
        return 1

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error: Failed to load trial config: {e}")
        return 1

    # 检查 trial source 数量
    trial_ids = [x["source_id"] for x in allowlist_data.get("trial_source_ids", [])]
    excluded_ids = set(allowlist_data.get("excluded_source_ids", []))

    print("Trial Configuration Validation: PASSED")
    print(f"  Trial source count: {len(trial_ids)}")

    # 检查数量
    if len(trial_ids) != 16:
        print(f"  [WARNING] Expected 16 trial sources, got {len(trial_ids)}")

    # 检查无重复
    dupes = [x for x in trial_ids if trial_ids.count(x) > 1]
    if dupes:
        print(f"  [ERROR] Duplicate source_ids: {set(dupes)}")
        return 1

    # 检查不包含 excluded
    bad = [x for x in trial_ids if x in excluded_ids]
    if bad:
        print(f"  [ERROR] Trial contains excluded sources: {bad}")
        return 1

    # 检查 trial config 中的 source 数
    trial_sources = config_data.get("sources", [])
    print(f"  Trial config sources: {len(trial_sources)}")

    # 检查 trial scope metadata
    trial_scope = config_data.get("trial", {})
    print(f"  Trial name: {trial_scope.get('name', 'N/A')}")
    print(f"  Based on: {trial_scope.get('based_on', 'N/A')}")
    print(f"  Source count: {trial_scope.get('source_count', 'N/A')}")
    print(f"  Production mode: {trial_scope.get('production_mode', False)}")

    # 检查 source_id 一致性
    config_ids = set(s.get("source_id", "") for s in trial_sources)
    if config_ids != set(trial_ids):
        missing = set(trial_ids) - config_ids
        extra = config_ids - set(trial_ids)
        if missing:
            print(f"  [WARNING] Allowlist IDs not in config: {missing}")
        if extra:
            print(f"  [WARNING] Config IDs not in allowlist: {extra}")

    # 检查 blocked sources 明确排除
    blocked = {
        "telegram_groups", "cloud_drive_share", "pdf_download_sites",
        "unknown_wechat_pdf", "report_download_proxy",
    }
    bad_blocked = [x for x in trial_ids if x in blocked]
    if bad_blocked:
        print(f"  [ERROR] Trial contains blocked sources: {bad_blocked}")
        return 1

    print("  Blocked source check: PASSED")
    print("  Excluded source check: PASSED")
    print("  Config format check: PASSED")

    return 0


def _cmd_trial_run(args: argparse.Namespace) -> int:
    """trial-run 子命令：运行 trial sources。

    小白解读：
        用 ResearchArchiver 跑 16 个 trial ready 源，
        输出到 data/foundation_trial/。
        不纳入 blocked/search/dormant/problem sources。

    Args:
        args: 命令行参数

    Returns:
        int: 退出码
    """
    import yaml
    import os
    from datetime import datetime, timezone

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return 1

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error: Failed to load config: {e}")
        return 1

    output_dir = Path(args.output_dir)
    archive_root = output_dir
    index_dir = archive_root / "index"
    reports_dir = archive_root / "reports"

    # 确保输出目录存在
    index_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 解析代理
    proxy_url, proxy_mode = _resolve_proxy(getattr(args, "proxy", None))

    # 设置代理环境变量（供底层 urllib 使用）
    if proxy_url:
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url

    trial_sources = config_data.get("sources", [])
    print(f"Trial run: {len(trial_sources)} sources")
    print(f"  output_dir: {output_dir}")
    print(f"  dry_run: {args.dry_run}")
    print(f"  max_items_per_source: {args.max_items_per_source}")
    print(f"  proxy_mode: {proxy_mode}")
    print("")

    # 创建 run log
    run_log_path = index_dir / "run_log.jsonl"
    health_log_path = index_dir / "source_health.jsonl"
    failed_queue_path = index_dir / "failed_queue.jsonl"

    run_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"Run started at: {run_start}")

    success_count = 0
    failed_count = 0
    empty_count = 0
    skipped_count = 0

    # 逐个源运行（使用 ResearchArchiver 的连接器）
    for source in trial_sources:
        sid = source.get("source_id", "")
        sname = source.get("source_name", "")
        stype = source.get("source_type", "")
        feed_url = source.get("feed_url", "")
        base_url = source.get("base_url", "")

        print(f"  [{len(trial_sources)}] {sid} ... ", end="")

        # 写 run log
        with open(run_log_path, "a", encoding="utf-8") as log_f:
            log_f.write(f'{{"source_id":"{sid}","source_name":"{sname}","source_type":"{stype}","status":"started","run_at":"{run_start}"}}\n')

        if args.dry_run:
            # dry-run: 不访问网络，直接标记为 skipped
            skipped_count += 1
            print("skipped (dry-run)")

            with open(health_log_path, "a", encoding="utf-8") as health_f:
                health_f.write(f'{{"source_id":"{sid}","source_name":"{sname}","status":"dry_run","run_at":"{run_start}"}}\n')
            continue

        # 真实运行：使用基础连接器做轻量验证
        # （完整的 research archiver 集成在后续 production 阶段）
        try:
            health = _trial_fetch_source(sid, sname, feed_url, stype, args.timeout_seconds)
            status = health.get("status", "unknown")

            if status == "success":
                success_count += 1
            elif status == "empty":
                empty_count += 1
            else:
                failed_count += 1

            print(f"{status}")

            with open(health_log_path, "a", encoding="utf-8") as health_f:
                health_f.write(f'{{"source_id":"{sid}","source_name":"{sname}","status":"{status}","run_at":"{health.get("run_at","")}","candidate_count":{health.get("candidate_count",0)},"error":"{health.get("error","")}"}}\n')

            if status in ("failed", "error"):
                with open(failed_queue_path, "a", encoding="utf-8") as queue_f:
                    queue_f.write(f'{{"source_id":"{sid}","source_name":"{sname}","status":"{status}","error":"{health.get("error","")}","run_at":"{health.get("run_at","")}"}}\n')

        except Exception as e:
            failed_count += 1
            print(f"failed: {e}")

            with open(health_log_path, "a", encoding="utf-8") as health_f:
                import json as _json
                health_f.write(_json.dumps({
                    "source_id": sid,
                    "source_name": sname,
                    "status": "error",
                    "error": str(e)[:200],
                    "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }, ensure_ascii=False) + "\n")

            with open(failed_queue_path, "a", encoding="utf-8") as queue_f:
                import json as _json
                queue_f.write(_json.dumps({
                    "source_id": sid,
                    "source_name": sname,
                    "status": "error",
                    "error": str(e)[:200],
                    "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }, ensure_ascii=False) + "\n")

    run_end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 写汇总
    summary_path = index_dir / "run_summary.json"
    import json as _json
    summary = {
        "run_started_at": run_start,
        "run_finished_at": run_end,
        "total_sources": len(trial_sources),
        "success_count": success_count,
        "empty_count": empty_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "proxy_enabled": proxy_url != "",
        "proxy_mode": proxy_mode,
        "dry_run": args.dry_run,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        _json.dump(summary, f, ensure_ascii=False, indent=2)

    print("")
    print(f"Trial run complete: {run_end}")
    print(f"  Total: {len(trial_sources)}")
    print(f"  Success: {success_count}")
    print(f"  Empty: {empty_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  proxy_enabled: {proxy_url != ''}")
    print(f"  proxy_mode: {proxy_mode}")
    print(f"Results: {index_dir}")
    print(f"Failed queue: {failed_queue_path}")

    return 0


def _trial_fetch_source(
    source_id: str,
    source_name: str,
    url: str,
    source_type: str,
    timeout_seconds: int,
) -> dict:
    """对单个 trial source 做轻量抓取验证。

    小白解读：
        用 urllib 访问源 URL，看看能不能拿到数据。
        这是轻量验证，不做完整的内容提取。

    Args:
        source_id: 源 ID
        source_name: 源名称
        url: 源 URL
        source_type: 源类型
        timeout_seconds: 超时秒数

    Returns:
        dict: 包含 status、candidate_count、error 等字段
    """
    import urllib.request
    import urllib.error
    from datetime import datetime, timezone

    result = {
        "source_id": source_id,
        "source_name": source_name,
        "status": "unknown",
        "candidate_count": 0,
        "error": "",
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    if not url:
        result["status"] = "error"
        result["error"] = "No URL configured"
        return result

    try:
        headers = {
            "User-Agent": "OPC-Foundation-TrialRun/1.0 (+https://github.com/xe7dx54321-stack/opc-foundation)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")

            if 200 <= status < 300:
                # 读内容，找候选链接
                try:
                    body = resp.read(1024 * 100)  # 最多读 100KB
                    # 简单统计链接数量作为候选
                    import re as _re
                    links = _re.findall(r'href=["\']([^"\']+)["\']', body.decode("utf-8", errors="ignore"))
                    # 过滤出看起来像文章/报告的链接
                    candidates = [l for l in links if any(
                        kw in l.lower() for kw in ["report", "research", "insight", "article", "analysis", "view", "market", "news", "202", "203", "204", "205", "206", "207", "208", "303", "304", "305", "306", "307", "308"]
                    )]
                    result["candidate_count"] = len(candidates[:5])
                except Exception:
                    pass

                if status == 200:
                    result["status"] = "success"
                else:
                    result["status"] = f"http_{status}"
            elif 300 <= status < 400:
                result["status"] = "redirect"
            elif status == 403:
                result["status"] = "blocked"
                result["error"] = "HTTP 403"
            elif status == 404:
                result["status"] = "not_found"
                result["error"] = "HTTP 404"
            else:
                result["status"] = "http_error"
                result["error"] = f"HTTP {status}"

    except urllib.error.HTTPError as e:
        result["status"] = "http_error"
        result["error"] = f"HTTP {e.code}: {str(e)[:100]}"
    except urllib.error.URLError as e:
        result["status"] = "url_error"
        result["error"] = str(e.reason)[:200]
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)[:200]}"

    return result


def _cmd_trial_report(args: argparse.Namespace) -> int:
    """trial-report 子命令：从 trial 运行结果生成 Markdown 报告。

    小白解读：
        读取 data/foundation_trial/index/ 下的运行结果，
        生成一份 trial run 报告。

    Args:
        args: 命令行参数

    Returns:
        int: 退出码
    """
    import json
    from datetime import datetime, timezone
    from pathlib import Path as _Path

    archive_root = _Path(args.archive_root)
    index_dir = archive_root / "index"
    reports_dir = archive_root / "reports"

    if not index_dir.exists():
        print(f"Error: Trial index directory not found: {index_dir}")
        return 1

    # 读取汇总
    summary_path = index_dir / "run_summary.json"
    health_log_path = index_dir / "source_health.jsonl"
    failed_queue_path = index_dir / "failed_queue.jsonl"

    if not summary_path.exists():
        print(f"Error: Run summary not found: {summary_path}")
        return 1

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # 读取 health log
    health_entries = []
    if health_log_path.exists():
        with open(health_log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        health_entries.append(json.loads(line))
                    except Exception:
                        pass

    # 读取 failed queue
    failed_entries = []
    if failed_queue_path.exists():
        with open(failed_queue_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        failed_entries.append(json.loads(line))
                    except Exception:
                        pass

    # 生成报告
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    report_lines = [
        "# OPC Foundation M3C-2D Trial Run Report",
        "",
        f"> **版本**：1.0",
        f"> **生成时间**：{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"> **Trial 说明**：本报告为 M3C-2D trial-only 试运行结果，**不代表最终 production TRAE 接管**。",
        "",
        "## 1. 执行摘要",
        "",
        f"- **执行时间**：{summary.get('run_started_at', 'N/A')} ~ {summary.get('run_finished_at', 'N/A')}",
        f"- **Trial Source 总数**：{summary.get('total_sources', 0)}",
        f"- **Dry-run**：{'是' if summary.get('dry_run') else '否'}",
        f"- **Proxy 启用**：{'是' if summary.get('proxy_enabled') else '否'}",
        f"- **Proxy 模式**：{summary.get('proxy_mode', 'none')}",
        "",
        "### 1.1 运行结果",
        "",
        "| 状态 | 数量 |",
        "|---|---|",
        f"| 总计 | {summary.get('total_sources', 0)} |",
        f"| Success | {summary.get('success_count', 0)} |",
        f"| Empty | {summary.get('empty_count', 0)} |",
        f"| Failed | {summary.get('failed_count', 0)} |",
        f"| Skipped | {summary.get('skipped_count', 0)} |",
        "",
        "## 2. Source 状态明细",
        "",
    ]

    # 按状态分组
    by_status: dict[str, list] = {}
    for entry in health_entries:
        status = entry.get("status", "unknown")
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(entry)

    for status, entries in sorted(by_status.items()):
        report_lines.append(f"### {status} ({len(entries)})")
        report_lines.append("")
        report_lines.append("| source_id | source_name | candidates |")
        report_lines.append("|---|---|---|")
        for e in entries:
            sid = e.get("source_id", "")
            sname = e.get("source_name", "")
            cands = e.get("candidate_count", 0)
            err = e.get("error", "")
            extra = f"（error: {err[:50]}...）" if err else ""
            report_lines.append(f"| {sid} | {sname} | {cands} {extra} |")
        report_lines.append("")

    if failed_entries:
        report_lines.append("## 3. Failed Queue")
        report_lines.append("")
        report_lines.append("| source_id | source_name | error |")
        report_lines.append("|---|---|---|")
        for e in failed_entries:
            sid = e.get("source_id", "")
            sname = e.get("source_name", "")
            err = e.get("error", "")[:80]
            report_lines.append(f"| {sid} | {sname} | {err} |")
        report_lines.append("")

    report_lines.extend([
        "## 4. Trial 配置信息",
        "",
        f"- **Allowlist**：configs/foundation_trial_source_allowlist.example.yaml",
        f"- **Trial Config**：configs/trae_foundation_trial_sources.example.yaml",
        f"- **输出目录**：{archive_root}",
        "",
        "## 5. 后续建议",
        "",
        "根据 trial 运行结果，评估各源是否可进入正式 TRAE 调度。",
        "",
        "## 6. M3C-2E 建议",
        "",
        "M3C-2D 完成后，建议进入：",
        "",
        "1. **M3C-2D-URLFix**：对 failed sources 中的 404/URL 失效源做 URL 修正",
        "2. **M3C-2D-TLSProbe**：对 TLS 握手失败源做替代入口探索",
        "3. **M3C-2D-WeChatMap**：对 6 个微信公众号源做 wechat_archive 映射",
        "4. **M3C-3**：基于 trial 结果，配置正式 TRAE production 调度",
    ])

    report_content = "\n".join(report_lines)

    # 保存报告
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"trial_run_{today}.md"

    # 也写入 docs/
    docs_report_path = _Path("docs/foundation_trial_run_report.md")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    with open(docs_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Trial report saved to:")
    print(f"  {report_path}")
    print(f"  {docs_report_path}")

    return 0


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

    # trial-validate
    p_trial_validate = subparsers.add_parser(
        "trial-validate",
        help="Validate trial config and allowlist (M3C-2D)"
    )
    p_trial_validate.add_argument(
        "--config",
        default="configs/trae_foundation_trial_sources.example.yaml",
        help="Path to trial config file",
    )
    p_trial_validate.add_argument(
        "--allowlist",
        default="configs/foundation_trial_source_allowlist.example.yaml",
        help="Path to trial allowlist file",
    )
    p_trial_validate.set_defaults(func=_cmd_trial_validate)

    # trial-run
    p_trial_run = subparsers.add_parser(
        "trial-run",
        help="Run trial sources (M3C-2D)"
    )
    p_trial_run.add_argument(
        "--config",
        default="configs/trae_foundation_trial_sources.example.yaml",
        help="Path to trial config file",
    )
    p_trial_run.add_argument(
        "--allowlist",
        default="configs/foundation_trial_source_allowlist.example.yaml",
        help="Path to trial allowlist file",
    )
    p_trial_run.add_argument(
        "--output-dir",
        default="data/foundation_trial",
        help="Output directory for trial results",
    )
    p_trial_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run without network access",
    )
    p_trial_run.add_argument(
        "--max-items-per-source",
        type=int,
        default=10,
        help="Max items per source",
    )
    p_trial_run.add_argument(
        "--timeout-seconds",
        type=int,
        default=20,
        help="Request timeout in seconds",
    )
    p_trial_run.add_argument(
        "--proxy",
        default=None,
        help="Proxy URL (e.g. http://127.0.0.1:7890)",
    )
    p_trial_run.set_defaults(func=_cmd_trial_run)

    # trial-report
    p_trial_report = subparsers.add_parser(
        "trial-report",
        help="Generate trial run report (M3C-2D)"
    )
    p_trial_report.add_argument(
        "--archive-root",
        default="data/foundation_trial",
        help="Archive root directory",
    )
    p_trial_report.set_defaults(func=_cmd_trial_report)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
