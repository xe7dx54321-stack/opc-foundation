"""Document Extraction Foundation 的命令行接口。

功能说明（小白解读）：
    本文件提供 CLI 命令，用于：
    - validate-config: 验证配置文件
    - dry-run:          试运行（不写归档）
    - run:              正式运行
    - source-health:    查看源健康状态
    - report:           生成日报
    - retry-failed:     重试失败队列

    使用方式：
        python -m opc_foundation.document_extraction.cli validate-config --config xxx.yaml
        python -m opc_foundation.document_extraction.cli dry-run --config xxx.yaml
        python -m opc_foundation.document_extraction.cli run --config xxx.yaml
        python -m opc_foundation.document_extraction.cli source-health --archive-root data/document_extraction
        python -m opc_foundation.document_extraction.cli report --archive-root data/document_extraction --date YYYY-MM-DD
        python -m opc_foundation.document_extraction.cli retry-failed --archive-root data/document_extraction
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from .archiver import DocumentArchiver
from .config import load_config, validate_config
from .health import get_source_health
from .reports import daily_report_filename

app = typer.Typer(
    name="document-extraction",
    help="Document Extraction Foundation CLI",
)


@app.command()
def validate_config(
    config: str = typer.Option(..., "--config", "-c", help="配置文件路径"),
) -> None:
    """验证配置文件是否有效。

    参数：
        config: 配置文件路径
    """
    config_path = Path(config)

    try:
        cfg = load_config(config_path)
    except FileNotFoundError:
        typer.echo(f"❌ 配置文件不存在: {config}", err=True)
        raise typer.Exit(1)
    except Exception as exc:
        typer.echo(f"❌ 配置加载失败: {exc}", err=True)
        raise typer.Exit(1)

    # 验证配置
    errors = validate_config(cfg)

    if errors:
        typer.echo("❌ 配置验证失败:")
        for error in errors:
            typer.echo(f"  - {error}")
        raise typer.Exit(1)

    typer.echo("✅ 配置验证通过")
    typer.echo(f"  - archive_root: {cfg.archive_root}")
    typer.echo(f"  - sources: {len(cfg.sources)}")
    for source in cfg.sources:
        enabled_str = "enabled" if source.enabled else "disabled"
        typer.echo(f"    - [{source.source_id}] {source.source_name} ({enabled_str})")


@app.command()
def dry_run(
    config: str = typer.Option(..., "--config", "-c", help="配置文件路径"),
) -> None:
    """试运行模式（不写归档）。

    参数：
        config: 配置文件路径
    """
    config_path = Path(config)

    try:
        cfg = load_config(config_path)
    except Exception as exc:
        typer.echo(f"❌ 配置加载失败: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo("🔍 试运行模式（不会写入归档）...")

    archiver = DocumentArchiver(cfg)
    result = archiver.run(mode="dry-run")

    _print_run_result(result)


@app.command()
def run(
    config: str = typer.Option(..., "--config", "-c", help="配置文件路径"),
) -> None:
    """正式运行模式。

    参数：
        config: 配置文件路径
    """
    config_path = Path(config)

    try:
        cfg = load_config(config_path)
    except Exception as exc:
        typer.echo(f"❌ 配置加载失败: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo("🚀 开始运行...")

    archiver = DocumentArchiver(cfg)
    result = archiver.run(mode="run")

    _print_run_result(result)

    if result.report_path:
        typer.echo(f"\n📄 报告已生成: {result.report_path}")


@app.command()
def source_health(
    archive_root: str = typer.Option(
        ...,
        "--archive-root",
        help="归档根目录",
    ),
    format: str = typer.Option("text", "--format", "-f", help="输出格式 (text/json)"),
    source_id: str | None = typer.Option(None, "--source-id", help="查看特定源的状态"),
) -> None:
    """查看源健康状态。

    参数：
        archive_root: 归档根目录
        format:       输出格式
        source_id:    源 ID（可选）
    """
    archive_path = Path(archive_root)

    if not archive_path.exists():
        typer.echo(f"❌ 归档目录不存在: {archive_root}", err=True)
        raise typer.Exit(1)

    health_data = get_source_health(archive_path, source_id)

    if format == "json":
        import json

        if isinstance(health_data, dict):
            output = {k: v.model_dump() for k, v in health_data.items()}
        elif health_data:
            output = health_data.model_dump()
        else:
            output = {}

        typer.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # text 格式
        if isinstance(health_data, dict):
            if not health_data:
                typer.echo("暂无健康数据")
                return

            typer.echo("## Source Health")
            typer.echo("")
            for sid, health in health_data.items():
                _print_health_text(health)
        elif health_data:
            _print_health_text(health_data)
        else:
            typer.echo("未找到指定源的健康数据")


@app.command()
def report(
    archive_root: str = typer.Option(
        ...,
        "--archive-root",
        help="归档根目录",
    ),
    date: str | None = typer.Option(None, "--date", "-d", help="日期 YYYY-MM-DD"),
) -> None:
    """查看或生成日报。

    参数：
        archive_root: 归档根目录
        date:         日期（可选，默认今天）
    """
    archive_path = Path(archive_root)

    if not archive_path.exists():
        typer.echo(f"❌ 归档目录不存在: {archive_root}", err=True)
        raise typer.Exit(1)

    # 确定日期
    from ..run.time_utils import utcnow_iso

    if date is None:
        date = utcnow_iso()[:10]

    report_filename = f"{date}_document_extraction_report.md"
    report_path = archive_path / "reports" / report_filename

    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        typer.echo(content)
    else:
        typer.echo(f"❌ 报告不存在: {report_path}", err=True)
        typer.echo("请先运行一次归档生成报告")


@app.command()
def retry_failed(
    archive_root: str = typer.Option(
        ...,
        "--archive-root",
        help="归档根目录",
    ),
    config: str | None = typer.Option(None, "--config", "-c", help="配置文件路径（可选）"),
) -> None:
    """重试失败队列中的文档。

    参数：
        archive_root: 归档根目录
        config:       配置文件路径（可选，如果不提供则使用默认配置）
    """
    archive_path = Path(archive_root)

    if not archive_path.exists():
        typer.echo(f"❌ 归档目录不存在: {archive_root}", err=True)
        raise typer.Exit(1)

    if config:
        try:
            cfg = load_config(config)
        except Exception as exc:
            typer.echo(f"❌ 配置加载失败: {exc}", err=True)
            raise typer.Exit(1)
    else:
        # 使用默认配置
        from .config import DocumentArchiveConfig, DocumentExtractionDefaults

        cfg = DocumentArchiveConfig(
            archive_root=str(archive_path),
            defaults=DocumentExtractionDefaults(),
            sources=[],
        )

    typer.echo("🔄 重试失败队列...")

    archiver = DocumentArchiver(cfg)
    result = archiver.retry_failed()

    _print_run_result(result)


def _print_run_result(result: Any) -> None:
    """打印运行结果。"""
    typer.echo("")
    typer.echo(f"Run ID: {result.run_id}")
    typer.echo(f"Mode: {result.mode}")
    typer.echo(f"Sources: {result.source_count} (enabled: {result.enabled_source_count})")
    typer.echo(f"Candidates: {result.candidate_count}")
    typer.echo(f"Saved: {result.saved_count}")
    typer.echo(f"Duplicates: {result.duplicate_count}")
    typer.echo(f"Partial: {result.partial_count}")
    typer.echo(f"Failed: {result.failed_count}")
    typer.echo(f"Skipped: {result.skipped_count}")

    if result.warnings:
        typer.echo("")
        typer.echo("Warnings:")
        for warning in result.warnings:
            typer.echo(f"  ⚠️ {warning}")

    if result.exit_code == 0:
        typer.echo("\n✅ 运行成功")
    else:
        typer.echo(f"\n⚠️ 运行完成（有 {result.failed_count} 个失败）")


def _print_health_text(health: Any) -> None:
    """打印健康状态（文本格式）。"""
    status_icon = {
        "healthy": "✅",
        "degraded": "⚠️",
        "failed": "❌",
        "disabled": "⏸️",
        "unknown": "❓",
    }.get(health.status, "❓")

    typer.echo(f"{status_icon} **{health.source_id}** ({health.source_type})")
    typer.echo(f"   Status: {health.status}")
    typer.echo(f"   Checked: {health.checked_at}")

    if health.last_error:
        typer.echo(f"   Last Error: {health.last_error}")

    if health.candidate_count_last_run > 0:
        typer.echo(
            f"   Last Run: candidates={health.candidate_count_last_run}, "
            f"saved={health.saved_count_last_run}, "
            f"failed={health.failed_count_last_run}"
        )
    typer.echo("")


if __name__ == "__main__":
    app()
