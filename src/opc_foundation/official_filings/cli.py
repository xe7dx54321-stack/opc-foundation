"""Official Filing Foundation 的命令行入口。

用法（小白解读）：
    python -m opc_foundation.official_filings.cli validate-config --config configs/official_filings.example.yaml
    python -m opc_foundation.official_filings.cli dry-run --config configs/official_filings.example.yaml
    python -m opc_foundation.official_filings.cli run --config configs/official_filings.example.yaml
    python -m opc_foundation.official_filings.cli source-health --archive-root data/official_filings
    python -m opc_foundation.official_filings.cli source-health --archive-root data/official_filings --format json
    python -m opc_foundation.official_filings.cli report --archive-root data/official_filings --date YYYY-MM-DD
    python -m opc_foundation.official_filings.cli retry-failed --archive-root data/official_filings

Exit code：
    0 = 成功
    1 = 配置错误
    2 = 部分失败
    3 = 严重运行时错误
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import typer
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少 typer 依赖，请先安装：pip install typer\n")
    raise

from .archiver import FilingArchiver
from .config import FilingConfigError, load_filing_config, validate_filing_config
from .health import load_source_health
from .models import FilingRunResult
from .reports import build_filing_daily_report, daily_report_filename
from .storage import load_failed_queue
from ..run.time_utils import utcnow_iso


app = typer.Typer(help="Official Filing Foundation 官方披露归档 CLI")


# ---------------------------------------------------------------------------
# 终端输出工具
# ---------------------------------------------------------------------------


def _print_summary(result: FilingRunResult) -> None:
    """把运行摘要打印到终端（全中文）。"""
    typer.echo("")
    typer.echo(f"运行 ID：{result.run_id}")
    typer.echo(f"模式：{result.mode}")
    typer.echo(f"开始：{result.started_at}")
    typer.echo(f"结束：{result.finished_at}")
    typer.echo(f"Source 总数：{result.source_count}")
    typer.echo(f"启用 Source：{result.enabled_source_count}")
    typer.echo(f"候选披露：{result.candidate_count}")
    typer.echo(f"新保存：{result.saved_count}")
    typer.echo(f"重复跳过：{result.duplicate_count}")
    typer.echo(f"失败：{result.failed_count}")
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
        return load_filing_config(config_path)
    except FilingConfigError as exc:
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
    errors = validate_filing_config(cfg)
    if errors:
        typer.echo("[配置校验失败]", err=True)
        for e in errors:
            typer.echo(f"  - {e}", err=True)
        raise typer.Exit(code=1)
    else:
        typer.echo("[配置校验通过]")
        typer.echo(f"  - archive_root: {cfg.archive_root}")
        typer.echo(f"  - source 总数: {len(cfg.sources)}")
        enabled = sum(1 for s in cfg.sources if s.enabled)
        typer.echo(f"  - 已启用 source: {enabled}")
        typer.echo(f"  - max_items_per_source: {cfg.defaults.max_items_per_source}")


# ---------------------------------------------------------------------------
# 命令：dry-run
# ---------------------------------------------------------------------------


@app.command("dry-run")
def cmd_dry_run(
    config: str = typer.Option(..., "--config", help="配置文件 yaml 路径"),
) -> None:
    """试运行：只发现候选披露，不写入归档。"""
    cfg = _load_config_or_exit(config)
    errors = validate_filing_config(cfg)
    if errors:
        typer.echo("[配置校验失败]", err=True)
        for e in errors:
            typer.echo(f"  - {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo("开始试运行（dry-run）...")
    try:
        archiver = FilingArchiver(cfg)
        result = archiver.run(mode="dry-run")
    except Exception as exc:
        typer.echo(f"[运行时错误] {exc}", err=True)
        raise typer.Exit(code=3)

    _print_summary(result)
    raise typer.Exit(code=result.exit_code)


# ---------------------------------------------------------------------------
# 命令：run
# ---------------------------------------------------------------------------


@app.command("run")
def cmd_run(
    config: str = typer.Option(..., "--config", help="配置文件 yaml 路径"),
) -> None:
    """正式运行：发现候选并写入归档。"""
    cfg = _load_config_or_exit(config)
    errors = validate_filing_config(cfg)
    if errors:
        typer.echo("[配置校验失败]", err=True)
        for e in errors:
            typer.echo(f"  - {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo("开始正式运行...")
    try:
        archiver = FilingArchiver(cfg)
        result = archiver.run(mode="run")
    except Exception as exc:
        typer.echo(f"[运行时错误] {exc}", err=True)
        raise typer.Exit(code=3)

    _print_summary(result)
    raise typer.Exit(code=result.exit_code)


# ---------------------------------------------------------------------------
# 命令：source-health
# ---------------------------------------------------------------------------


@app.command("source-health")
def cmd_source_health(
    archive_root: str = typer.Option(..., "--archive-root", help="归档根目录"),
    format: str = typer.Option("text", "--format", help="输出格式: text / json"),
) -> None:
    """查看 source 健康状态。"""
    health_map = load_source_health(archive_root)

    if not health_map:
        typer.echo("暂无 source health 记录。")
        raise typer.Exit(code=0)

    if format == "json":
        health_list = [h.model_dump(mode="json") for h in health_map.values()]
        typer.echo(json.dumps(health_list, ensure_ascii=False, indent=2))
    else:
        typer.echo("")
        typer.echo(f"共 {len(health_map)} 个 source：")
        typer.echo("")
        typer.echo(f"{'Source ID':<30} {'类型':<20} {'状态':<10} {'候选':>6} {'保存':>6} {'失败':>6}")
        typer.echo("-" * 90)
        for h in health_map.values():
            typer.echo(
                f"{h.source_id:<30} {h.source_type or '-':<20} "
                f"{h.status:<10} {h.candidate_count_last_run:>6} "
                f"{h.saved_count_last_run:>6} {h.failed_count_last_run:>6}"
            )
        typer.echo("")


# ---------------------------------------------------------------------------
# 命令：report
# ---------------------------------------------------------------------------


@app.command("report")
def cmd_report(
    archive_root: str = typer.Option(..., "--archive-root", help="归档根目录"),
    date: str = typer.Option(None, "--date", help="日期 YYYY-MM-DD，默认为今天"),
) -> None:
    """生成并打印指定日期的日报（或打印已有日报）。"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    report_name = daily_report_filename(date)
    report_path = Path(archive_root) / "reports" / report_name

    if report_path.exists():
        content = report_path.read_text(encoding="utf-8")
        typer.echo(content)
    else:
        typer.echo(f"未找到 {date} 的日报文件：{report_path}")
        typer.echo("请先执行 run 命令生成日报。")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# 命令：retry-failed
# ---------------------------------------------------------------------------


@app.command("retry-failed")
def cmd_retry_failed(
    archive_root: str = typer.Option(..., "--archive-root", help="归档根目录"),
) -> None:
    """重试失败队列中的披露。

    MVP 版本：打印失败队列信息。
    实际使用需要配合 config 文件重跑。
    """
    failed_list = load_failed_queue(archive_root)

    if not failed_list:
        typer.echo("失败队列为空。")
        raise typer.Exit(code=0)

    typer.echo("")
    typer.echo(f"失败队列共 {len(failed_list)} 条：")
    typer.echo("")
    for f in failed_list[:20]:
        title = (f.filing_title or "-")[:50]
        typer.echo(f"  - [{f.source_id}] {title}")
        typer.echo(f"    错误: {f.error[:60]}")
    if len(failed_list) > 20:
        typer.echo(f"  ... 其余 {len(failed_list) - 20} 条省略")
    typer.echo("")
    typer.echo("提示：MVP 版本请使用 run 命令重新抓取以重试失败项。")


def main() -> None:  # pragma: no cover
    """CLI 入口函数。"""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
