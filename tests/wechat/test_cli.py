"""CLI 命令的最小测试（不会访问真实网络）。"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from opc_foundation.wechat.cli import app


runner = CliRunner()


def _make_config_yaml(tmp_path: Path) -> Path:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        f"""
archive_root: {tmp_path / 'archive'}
defaults:
  fetch_timeout_seconds: 5
  max_articles_per_account: 5
  download_images: false
  save_html: true
  save_markdown: true
  user_agent: test-bot
accounts:
  - account_name: "示例公众号A"
    account_id: "example_a"
    source_type: "rss"
    feed_url: "http://localhost:8000/feed/example_a.xml"
    enabled: true
""".strip(),
        encoding="utf-8",
    )
    return cfg_path


def test_dry_run(tmp_path: Path):
    cfg = _make_config_yaml(tmp_path)
    result = runner.invoke(app, ["dry-run", "--config", str(cfg)])
    assert result.exit_code == 0, (result.stdout, result.stderr)
    # 应该输出"发现候选"等中文摘要
    assert "发现候选" in result.stdout or "候选文章" in result.stdout or "监控账号" in result.stdout


def test_report_without_config(tmp_path: Path):
    root = tmp_path / "archive"
    (root / "index").mkdir(parents=True)
    # 写入一条 fake articles.jsonl 含失败/saved 各一个
    (root / "index" / "articles.jsonl").write_text(
        json.dumps({"title": "a", "status": "saved", "url": "http://x/", "canonical_url": "http://x/"}, ensure_ascii=False)
        + "\n"
        + json.dumps({"title": "b", "status": "failed", "url": "http://y/", "canonical_url": "http://y/"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["report", "--archive-root", str(root)])
    assert result.exit_code == 0
    assert (root / "reports").exists()


def test_bad_config_path(tmp_path: Path):
    result = runner.invoke(app, ["run", "--config", str(tmp_path / "no.yaml")])
    assert result.exit_code in (1, 2, 3)
