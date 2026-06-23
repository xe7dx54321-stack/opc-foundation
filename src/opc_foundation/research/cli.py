"""Research Source Foundation 的命令行入口。

用法（小白解读）：
    python -m opc_foundation.research.cli validate-config --config configs/research_sources.example.yaml
    python -m opc_foundation.research.cli dry-run --config configs/research_sources.example.yaml
    python -m opc_foundation.research.cli run --config configs/research_sources.example.yaml
    python -m opc_foundation.research.cli retry-failed --archive-root ./data/research_archive
    python -m opc_foundation.research.cli report --archive-root ./data/research_archive --date YYYY-MM-DD
    python -m opc_foundation.research.cli source-health --archive-root ./data/research_archive

Exit code：
    0 = 成功
    1 = 配置错误
    2 = 部分失败
    3 = 严重运行时错误
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

try:
    import typer
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少 typer 依赖，请先安装：pip install typer\n")
    raise

from .archiver import ResearchArchiver
from .config import ResearchConfigError, load_research_config, validate_research_config
from .models import ResearchRunResult
from .reports import build_research_daily_report, daily_report_filename
from .storage import load_source_health, write_report


app = typer.Typer(help="Research Source Foundation 采集与归档 CLI")


# ---------------------------------------------------------------------------
# 终端输出工具
# ---------------------------------------------------------------------------


def _print_summary(result: ResearchRunResult) -> None:
    """把运行摘要打印到终端（全中文）。"""
    typer.echo("")
    typer.echo(f"运行 ID：{result.run_id}")
    typer.echo(f"模式：{result.mode}")
    typer.echo(f"开始：{result.started_at}")
    typer.echo(f"结束：{result.finished_at}")
    typer.echo(f"Source 总数：{result.source_count}")
    typer.echo(f"启用 Source：{result.enabled_source_count}")
    typer.echo(f"候选文档：{result.candidate_count}")
    typer.echo(f"新文档：{result.new_count}")
    typer.echo(f"成功保存：{result.saved_count}")
    typer.echo(f"部分保存：{result.partial_count}")
    typer.echo(f"失败：{result.failed_count}")
    typer.echo(f"重复跳过：{result.duplicate_count}")
    typer.echo(f"跳过：{result.skipped_count}")
    if result.warnings:
        typer.echo("")
        typer.echo(f"本次运行警告 {len(result.warnings)} 条：")
        for w in result.warnings[:10]:
            typer.echo(f"  - {w}")
        if len(result.warnings) > 10:
            typer.echo(f"  ... 其余 {len(result.warnings) - 10} 条省略，详见 run_log.jsonl")
    if result.report_path:
        typer.echo("")
        typer.echo(f"日报文件：{result.report_path}")
    typer.echo("")


def _load_config_or_exit(config_path: str):
    """加载配置，失败时退出。"""
    try:
        return load_research_config(config_path)
    except ResearchConfigError as exc:
        typer.echo(f"[配置错误] {exc}", err=True)
        raise typer.Exit(code=1)
    except FileNotFoundError as exc:
        typer.echo(f"[配置错误] 文件未找到: {exc}", err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# 命令：validate-config
# ---------------------------------------------------------------------------


@app.command("validate-config")
def cmd_validate_config(
    config: str = typer.Option(..., "--config", help="配置文件 yaml 路径"),
) -> None:
    """校验配置文件，不执行任何抓取。"""
    cfg = _load_config_or_exit(config)
    errors = validate_research_config(cfg)
    if errors:
        typer.echo("[配置校验失败]", err=True)
        for e in errors:
            typer.echo(f"  - {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo("[配置校验通过]")
    typer.echo(f"  archive_root: {cfg.archive_root}")
    typer.echo(f"  sources: {len(cfg.sources)} 个")
    enabled = [s for s in cfg.sources if s.enabled]
    typer.echo(f"  enabled: {len(enabled)} 个")
    for s in cfg.sources:
        flag = "✓" if s.enabled else "✗"
        typer.echo(f"    {flag} {s.source_id} ({s.source_type}) - {s.source_name}")
    raise typer.Exit(code=0)


# ---------------------------------------------------------------------------
# 命令：dry-run
# ---------------------------------------------------------------------------


@app.command("dry-run")
def cmd_dry_run(
    config: str = typer.Option(..., "--config", help="配置文件 yaml 路径"),
) -> None:
    """试运行：只发现候选，不抓正文，不写 documents.jsonl。"""
    cfg = _load_config_or_exit(config)
    archiver = ResearchArchiver(cfg)
    try:
        result = archiver.dry_run()
    except Exception as exc:
        typer.echo(f"[严重错误] {exc}", err=True)
        raise typer.Exit(code=3)
    _print_summary(result)
    raise typer.Exit(code=result.exit_code)


# ---------------------------------------------------------------------------
# 命令：run
# ---------------------------------------------------------------------------


@app.command("run")
def cmd_run(
    config: str = typer.Option(..., "--config", help="配置文件 yaml 路径"),
    archive_root: str | None = typer.Option(
        None, "--archive-root", help="覆盖配置中的 archive_root"
    ),
) -> None:
    """完整运行：发现 → 去重 → 抓取 → 抽取 → 归档 → 日报。"""
    cfg = _load_config_or_exit(config)
    if archive_root:
        cfg.archive_root = archive_root
        cfg.raw["archive_root"] = archive_root

    archiver = ResearchArchiver(cfg)
    try:
        result = archiver.run()
    except Exception as exc:
        typer.echo(f"[严重错误] {exc}", err=True)
        raise typer.Exit(code=3)
    _print_summary(result)
    raise typer.Exit(code=result.exit_code)


# ---------------------------------------------------------------------------
# 命令：retry-failed
# ---------------------------------------------------------------------------


@app.command("retry-failed")
def cmd_retry_failed(
    archive_root: str = typer.Option(
        ..., "--archive-root", help="归档根目录（含 state/failed_queue.jsonl）"
    ),
    config: str | None = typer.Option(
        None, "--config", help="可选配置文件，用于提供 fetch/extract 默认参数"
    ),
) -> None:
    """重试 failed_queue.jsonl 中的 retryable 条目。"""
    # 如果给了 config，加载它；否则构造一个最小 config
    if config:
        cfg = _load_config_or_exit(config)
        cfg.archive_root = archive_root
    else:
        from .models import ResearchArchiveConfig, ResearchDefaults
        cfg = ResearchArchiveConfig(
            archive_root=archive_root,
            defaults=ResearchDefaults(),
            sources=[],
            raw={},
        )

    archiver = ResearchArchiver(cfg)
    try:
        result = archiver.retry_failed()
    except Exception as exc:
        typer.echo(f"[严重错误] {exc}", err=True)
        raise typer.Exit(code=3)
    _print_summary(result)
    raise typer.Exit(code=result.exit_code)


# ---------------------------------------------------------------------------
# 命令：report
# ---------------------------------------------------------------------------


@app.command("report")
def cmd_report(
    archive_root: str = typer.Option(..., "--archive-root", help="归档根目录"),
    date: str | None = typer.Option(
        None, "--date", help="日期 YYYY-MM-DD，默认今天"
    ),
) -> None:
    """按日期生成（或重新生成）日报。

    会读取 state/run_log.jsonl 中该日期的所有 run_summary 记录，
    合并后输出一份日报。
    """
    from .storage import load_jsonl

    date_str = date or datetime.now().strftime("%Y-%m-%d")

    state_dir = Path(archive_root) / "state"
    run_log_path = state_dir / "run_log.jsonl"
    if not run_log_path.exists():
        typer.echo(f"[错误] 找不到 run_log: {run_log_path}", err=True)
        raise typer.Exit(code=1)

    records = load_jsonl(run_log_path)
    summaries = [
        r for r in records
        if isinstance(r, dict)
        and r.get("entry_type") == "run_summary"
        and (r.get("started_at") or "").startswith(date_str)
    ]

    if not summaries:
        typer.echo(f"[提示] {date_str} 没有 run_summary 记录，无法生成日报")
        raise typer.Exit(code=0)

    # 合并多个 run_summary
    merged = _merge_run_summaries(summaries, date_str, archive_root)

    report_text = build_research_daily_report(merged)
    report_path = write_report(
        archive_root,
        daily_report_filename(date_str),
        report_text,
    )
    typer.echo(f"[日报已生成] {report_path}")
    raise typer.Exit(code=0)


def _merge_run_summaries(
    summaries: list[dict],
    date_str: str,
    archive_root: str,
) -> ResearchRunResult:
    """把同一天的多个 run_summary 合并成一个 ResearchRunResult。"""
    total_saved = sum(int(s.get("saved_count", 0)) for s in summaries)
    total_partial = sum(int(s.get("partial_count", 0)) for s in summaries)
    total_failed = sum(int(s.get("failed_count", 0)) for s in summaries)
    total_duplicate = sum(int(s.get("duplicate_count", 0)) for s in summaries)
    total_candidate = sum(int(s.get("candidate_count", 0)) for s in summaries)
    total_new = sum(int(s.get("new_count", 0)) for s in summaries)
    total_skipped = sum(int(s.get("skipped_count", 0)) for s in summaries)

    started_at = summaries[0].get("started_at", date_str)
    finished_at = summaries[-1].get("finished_at", started_at)

    return ResearchRunResult(
        run_id=f"merged_{date_str}",
        mode="report",
        archive_root=archive_root,
        started_at=started_at,
        finished_at=finished_at,
        source_count=sum(int(s.get("source_count", 0)) for s in summaries),
        enabled_source_count=sum(int(s.get("enabled_source_count", 0)) for s in summaries),
        candidate_count=total_candidate,
        new_count=total_new,
        saved_count=total_saved,
        partial_count=total_partial,
        failed_count=total_failed,
        duplicate_count=total_duplicate,
        skipped_count=total_skipped,
        source_stats=[],
        saved_documents=[],
        failed_documents=[],
        source_health=[],
        warnings=[],
        report_path=None,
        exit_code=0,
    )


# ---------------------------------------------------------------------------
# 命令：source-health
# ---------------------------------------------------------------------------


@app.command("source-health")
def cmd_source_health(
    archive_root: str = typer.Option(..., "--archive-root", help="归档根目录"),
    status: str | None = typer.Option(
        None, "--status", help="只看某种状态：healthy/degraded/failed/disabled/unknown"
    ),
    fmt: str = typer.Option(
        "text", "--format", help="输出格式：text 或 json"
    ),
) -> None:
    """输出所有 source 的最新健康状态。

    Phase 2F 增强：
        - 支持 --status 过滤
        - 支持 --format text/json
        - 在没有 source_health.jsonl 时不崩溃
        - 输出中文可读摘要
    """
    import json as json_module

    records = load_source_health(archive_root)

    # 过滤
    if status:
        status_lower = status.lower()
        records = [r for r in records if r.get("status", "").lower() == status_lower]

    if fmt.lower() == "json":
        typer.echo(json_module.dumps(records, ensure_ascii=False, indent=2))
        raise typer.Exit(code=0)

    # text 输出
    if not records:
        typer.echo("[提示] 暂无 source 健康记录")
        raise typer.Exit(code=0)

    # 统计各状态数量
    counts: dict[str, int] = {
        "healthy": 0,
        "degraded": 0,
        "failed": 0,
        "disabled": 0,
        "unknown": 0,
    }
    for r in records:
        s = r.get("status", "unknown")
        if s in counts:
            counts[s] += 1
        else:
            counts["unknown"] += 1

    typer.echo("")
    typer.echo("Research Source Foundation Source Health")
    typer.echo("")
    typer.echo(f"healthy:  {counts['healthy']}")
    typer.echo(f"degraded: {counts['degraded']}")
    typer.echo(f"failed:   {counts['failed']}")
    typer.echo(f"disabled: {counts['disabled']}")
    typer.echo(f"unknown:  {counts['unknown']}")
    typer.echo("")

    # 按状态分组输出详情
    for group_status in ("failed", "degraded", "healthy", "disabled", "unknown"):
        group_records = [r for r in records if r.get("status", "unknown") == group_status]
        if not group_records:
            continue
        typer.echo(f"[{group_status}]")
        for r in group_records:
            source_name = r.get("source_name", "")
            source_type = r.get("source_type") or "-"
            typer.echo(f"- {source_name} ({source_type})")
            if group_status in ("failed", "degraded"):
                cf = r.get("consecutive_failures", 0)
                saved = r.get("saved_count_last_run", 0)
                failed = r.get("failed_count_last_run", 0)
                err_type = r.get("last_error_type") or "-"
                err = r.get("last_error") or "-"
                typer.echo(f"  consecutive_failures: {cf}")
                typer.echo(f"  saved_count_last_run: {saved}")
                typer.echo(f"  failed_count_last_run: {failed}")
                typer.echo(f"  last_error_type: {err_type}")
                typer.echo(f"  last_error: {err}")
        typer.echo("")

    raise typer.Exit(code=0)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    app()
