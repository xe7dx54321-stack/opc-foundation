"""
微信公众号归档 Live Smoke 包装脚本。

功能说明（小白解读）：
    这个脚本是对 CLI 命令的一个简单包装，提供统一的入口和中文提示。
    实际执行的是 opc_foundation.wechat.cli 中的命令，不新增任何业务逻辑。

用法：
    python scripts/wechat_live_smoke.py dry-run --config configs/wechat_live_smoke.local.yaml
    python scripts/wechat_live_smoke.py run     --config configs/wechat_live_smoke.local.yaml
    python scripts/wechat_live_smoke.py check  --archive-root ./data/wechat_live_smoke_archive
    python scripts/wechat_live_smoke.py report  --archive-root ./data/wechat_live_smoke_archive
    python scripts/wechat_live_smoke.py retry  --archive-root ./data/wechat_live_smoke_archive

check 子命令说明：
    轻量检查归档目录结构，统计已保存的文章数量，输出中文摘要。
    不访问网络，不重新运行抓取。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

app = typer.Typer(help="微信公众号归档 Live Smoke 包装脚本")


@app.command("dry-run")
def cmd_dry_run(config: str) -> None:
    """只读 feed，展示候选文章，不写文件。"""
    from opc_foundation.wechat.cli import app as cli_app
    sys.argv = ["wechat", "dry-run", "--config", config]
    cli_app()


@app.command("run")
def cmd_run(config: str) -> None:
    """完整执行：读 feed、抓正文、保存归档。"""
    from opc_foundation.wechat.cli import app as cli_app
    sys.argv = ["wechat", "run", "--config", config]
    cli_app()


@app.command("report")
def cmd_report(
    archive_root: str = typer.Option(..., "--archive-root", help="归档根目录"),
    date: str | None = typer.Option(None, "--date", help="指定日期（YYYY-MM-DD）"),
) -> None:
    """生成日报（默认今天，或 --date YYYY-MM-DD 指定日期）。"""
    from opc_foundation.wechat.cli import app as cli_app
    args = ["wechat", "report", "--archive-root", archive_root]
    if date:
        args.extend(["--date", date])
    sys.argv = args
    cli_app()


@app.command("retry")
def cmd_retry(archive_root: str) -> None:
    """重试 failed_queue.jsonl 中的失败文章。"""
    from opc_foundation.wechat.cli import app as cli_app
    sys.argv = ["wechat", "retry-failed", "--archive-root", archive_root]
    cli_app()


@app.command("check")
def cmd_check(
    archive_root: str = typer.Option(..., "--archive-root", help="归档根目录"),
) -> None:
    """轻量检查归档目录结构和统计信息（不访问网络）。"""
    root = Path(archive_root)
    if not root.exists():
        typer.echo(f"[错误] 归档目录不存在：{archive_root}", err=True)
        raise typer.Exit(code=1)

    typer.echo("")
    typer.echo(f"📁 归档根目录：{archive_root}")
    typer.echo("")

    # 1) 目录结构检查
    typer.echo("--- 目录结构检查 ---")
    checks = {
        "index/articles.jsonl": root / "index" / "articles.jsonl",
        "state/seen_articles.sqlite": root / "state" / "seen_articles.sqlite",
        "state/run_log.jsonl": root / "state" / "run_log.jsonl",
        "reports/": root / "reports",
    }
    all_ok = True
    for name, path in checks.items():
        if name.endswith("/"):
            ok = path.is_dir()
        else:
            ok = path.exists()
        symbol = "✅" if ok else "❌"
        typer.echo(f"  {symbol} {name}")
        if not ok:
            all_ok = False

    typer.echo("")

    # 2) 统计 articles.jsonl
    index_path = root / "index" / "articles.jsonl"
    saved = failed = partial = 0
    canonical_urls: set[str] = set()
    if index_path.exists():
        with open(index_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    status = data.get("status", "saved")
                    if status == "saved":
                        saved += 1
                    elif status == "failed":
                        failed += 1
                    elif status == "partial":
                        partial += 1
                    url = data.get("canonical_url", "")
                    if url:
                        canonical_urls.add(url)
                except Exception:
                    pass

    typer.echo("--- articles.jsonl 统计 ---")
    typer.echo(f"  总记录数：{saved + failed + partial}")
    typer.echo(f"  ✅ 成功保存：{saved} 篇")
    typer.echo(f"  ⚠️  部分保存：{partial} 篇")
    typer.echo(f"  ❌ 失败：{failed} 篇")
    typer.echo(f"  🔗 唯一 URL 数：{len(canonical_urls)}")
    typer.echo("")

    # 3) 检查 articles/ 目录
    articles_dir = root / "articles"
    article_dirs = []
    if articles_dir.exists():
        for y in articles_dir.rglob("*"):
            if y.is_dir() and (y / "metadata.json").exists():
                article_dirs.append(y)
    typer.echo("--- articles/ 目录 ---")
    typer.echo(f"  文章目录数：{len(article_dirs)}")
    if article_dirs:
        sample = article_dirs[0]
        typer.echo(f"  示例目录：{sample.relative_to(root)}")
        for fname in ["article.md", "article.html", "metadata.json"]:
            f = sample / fname
            typer.echo(f"    {'✅' if f.exists() else '❌'} {fname}")
    typer.echo("")

    # 4) run_log.jsonl 中的 run_summary
    log_path = root / "state" / "run_log.jsonl"
    if log_path.exists():
        with open(log_path, encoding="utf-8") as fh:
            lines = [json.loads(ln) for ln in fh if ln.strip()]
        summaries = [l for l in lines if l.get("entry_type") == "run_summary"]
        typer.echo("--- run_log.jsonl 运行记录 ---")
        typer.echo(f"  总条目数：{len(lines)}")
        typer.echo(f"  run_summary 条目数：{len(summaries)}")
        if summaries:
            last = summaries[-1]
            typer.echo(f"  最近一次运行：{last.get('started_at', '')} | mode={last.get('mode')} | exit={last.get('exit_code')}")
    typer.echo("")

    if all_ok and saved > 0:
        typer.echo("✅ 归档目录结构正常，已保存文章。")
    elif all_ok:
        typer.echo("⚠️ 目录结构正常，但还没有保存文章（请先运行 run）。")
    else:
        typer.echo("❌ 目录结构不完整，请检查上述 ❌ 项。")
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
