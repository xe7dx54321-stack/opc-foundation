"""命令行入口。

用法：
    python -m opc_foundation.wechat.cli run --config configs/wechat_accounts.example.yaml
    python -m opc_foundation.wechat.cli dry-run --config ...
    python -m opc_foundation.wechat.cli retry-failed --archive-root ./data/wechat_archive
    python -m opc_foundation.wechat.cli report --archive-root ./data/wechat_archive

说明：
    exit code：0 成功，1 配置错误，2 部分失败，3 严重错误。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

try:
    import typer
except ImportError:  # pragma: no cover - 仅当仓库里已有 typer
    sys.stderr.write("缺少 typer 依赖，请先安装：pip install typer\n")
    raise

from .archiver import WeChatArchiver
from .config import WeChatConfigError, load_wechat_config
from .models import WeChatArchiveRunResult


app = typer.Typer(help="微信公众号文章归档 CLI")


def _print_summary(result: WeChatArchiveRunResult) -> None:
    """把运行摘要打印到终端（全中文）。"""

    typer.echo("")
    typer.echo(f"运行 ID：{result.run_id}")
    typer.echo(f"开始：{result.started_at}")
    typer.echo(f"结束：{result.ended_at}")
    typer.echo(f"监控账号：{result.total_accounts} 个")
    typer.echo(f"发现候选：{result.total_candidates} 篇")
    typer.echo(f"新文章：{result.total_new_articles} 篇")
    typer.echo(f"成功保存：{result.total_saved} 篇")
    typer.echo(f"部分保存：{result.total_partial} 篇")
    typer.echo(f"失败：{result.total_failed} 篇")
    typer.echo(f"重复跳过：{result.total_duplicate} 篇")
    if result.warnings:
        typer.echo("")
        typer.echo(f"本次运行警告 {len(result.warnings)} 条：")
        for w in result.warnings[:10]:
            typer.echo(f"  - {w}")
        if len(result.warnings) > 10:
            typer.echo(f"  ... 其余 {len(result.warnings) - 10} 条省略，详见 run_log.jsonl")
    typer.echo("")
    if result.reports:
        typer.echo("生成的报告：")
        for r in result.reports:
            typer.echo(f"  - {r}")


@app.command("run")
def cmd_run(
    config: str = typer.Option(..., "--config", help="账号配置 yaml"),
    archive_root: Optional[str] = typer.Option(
        None, "--archive-root", help="覆盖配置中的 archive_root"
    ),
) -> None:
    """读取配置，执行一次完整的归档流程。"""

    try:
        cfg = load_wechat_config(config)
    except WeChatConfigError as exc:
        typer.echo(f"[配置错误] {exc}", err=True)
        raise typer.Exit(code=1)
    except FileNotFoundError as exc:
        typer.echo(f"[配置错误] 文件未找到: {exc}", err=True)
        raise typer.Exit(code=1)

    if archive_root:
        cfg.archive_root = archive_root
        # 同时更新 raw 中的值
        cfg.raw["archive_root"] = archive_root

    archiver = WeChatArchiver(cfg)
    result = archiver.run()
    _print_summary(result)
    from .archiver import _run_exit_code
    raise typer.Exit(code=_run_exit_code(result))


@app.command("dry-run")
def cmd_dry_run(
    config: str = typer.Option(..., "--config", help="账号配置 yaml"),
) -> None:
    """只读取 feed 并展示候选文章，不抓取正文，不写入归档目录。"""

    try:
        cfg = load_wechat_config(config)
    except WeChatConfigError as exc:
        typer.echo(f"[配置错误] {exc}", err=True)
        raise typer.Exit(code=1)
    except FileNotFoundError as exc:
        typer.echo(f"[配置错误] 文件未找到: {exc}", err=True)
        raise typer.Exit(code=1)

    archiver = WeChatArchiver(cfg)
    result = archiver.dry_run()
    _print_summary(result)

    if result.warnings:
        # dry-run 里 warning 也算部分失败（exit 2 太重，这里用 0 让脚本不报错）
        pass
    return None


@app.command("retry-failed")
def cmd_retry_failed(
    archive_root: str = typer.Option(
        ...,
        "--archive-root",
        help="归档根目录（包含 state/failed_queue.jsonl）",
    ),
) -> None:
    """读取 failed_queue.jsonl，重试失败文章。"""

    from .models import WeChatArchiveConfig, WeChatDefaults

    # 我们没有完整的配置文件也能跑：使用最小配置创建 archiver
    # 这里新建一个最小配置，允许用户再去读 state 内容
    root = Path(archive_root)
    if not (root / "state").is_dir():
        typer.echo(f"[错误] 未在 {root} 中找到 state/ 目录", err=True)
        raise typer.Exit(code=1)

    cfg = WeChatArchiveConfig(
        archive_root=str(root),
        defaults=WeChatDefaults(),
        accounts=[],
    )
    archiver = WeChatArchiver(cfg)
    result = archiver.retry_failed()
    _print_summary(result)
    # exit code 复用 archiver 内部计算逻辑
    from .archiver import _run_exit_code
    raise typer.Exit(code=_run_exit_code(result))


@app.command("report")
def cmd_report(
    archive_root: str = typer.Option(
        ..., "--archive-root", help="归档根目录"),
    date: Optional[str] = typer.Option(
        None,
        "--date",
        help="指定日期（YYYY-MM-DD），不指定则默认今天。过滤 articles.jsonl 中 captured_at 为该日期的文章。",
    ),
    config: Optional[str] = typer.Option(None, "--config", help="可选的配置 yaml（有账号名时便于展示）"),
) -> None:
    """基于现有归档目录生成一份统计报告（不访问网络）。

    默认只统计当天新增的文章（按 captured_at 过滤），避免把历史文章都算成当天新增。
    使用 --date YYYY-MM-DD 可以查看任意一天的报告。
    """

    from datetime import date as _date, datetime
    from .reports import build_daily_capture_report
    from .storage import load_failed_queue
    from ..run.time_utils import utcnow_iso

    # 确定目标日期
    if date:
        target_date = date[:10]
    else:
        target_date = utcnow_iso()[:10]

    root = Path(archive_root)

    accounts_count = 0
    try:
        if config:
            cfg = load_wechat_config(config)
            accounts_count = len(cfg.accounts)
    except Exception:
        pass

    index_path = root / "index" / "articles.jsonl"
    total_today = 0
    saved_today = 0
    failed_today = 0
    partial_today = 0
    saved_articles_today = []
    failed_articles_today = []

    if index_path.exists():
        import json
        with open(index_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                # 按 captured_at 日期过滤
                captured = (data.get("captured_at") or "")[:10]
                if captured != target_date:
                    continue
                total_today += 1
                status = data.get("status") or "saved"
                if status == "saved":
                    saved_today += 1
                    from .models import ArchivedArticle
                    saved_articles_today.append(ArchivedArticle(**data))
                elif status == "failed":
                    failed_today += 1
                    from .models import FailedArticle
                    failed_articles_today.append(FailedArticle(**data))
                elif status == "partial":
                    partial_today += 1

    # 只展示当天失败队列中的条目（按 failed_at 过滤）
    all_failed = load_failed_queue(root / "state" / "failed_queue.jsonl")
    failed_queue_today = [f for f in all_failed if (f.failed_at or "")[:10] == target_date]

    started_at = target_date + "T00:00:00+08:00"
    ended_at = utcnow_iso()
    result = WeChatArchiveRunResult(
        run_id="report_" + target_date,
        started_at=started_at,
        ended_at=ended_at,
        total_accounts=accounts_count,
        total_candidates=total_today,
        total_new_articles=total_today,
        total_saved=saved_today,
        total_partial=partial_today,
        total_failed=failed_today,
        total_duplicate=0,
        archive_root=str(root),
        saved_articles=saved_articles_today,
        failed_articles=failed_queue_today,
        reports=[],
    )
    report_text = build_daily_capture_report(result)
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"daily_capture_{target_date}_manual.md"
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report_text)

    typer.echo(f"已生成报告（日期：{target_date}）：{report_path}")
    typer.echo(f"今日新增：{total_today} 篇（成功 {saved_today}，部分 {partial_today}，失败 {failed_today}）")
    if failed_queue_today:
        typer.echo(f"失败队列（当日）：{len(failed_queue_today)} 条待重试")
    if all_failed and not failed_queue_today:
        typer.echo(f"失败队列总计：{len(all_failed)} 条（无今日新增）")
    return None


def main() -> None:
    app()


if __name__ == "__main__":
    main()
