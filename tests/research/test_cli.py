"""测试 research/cli.py —— CLI 命令。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from opc_foundation.research.cli import app


runner = CliRunner()


def _write_config(path: Path, data: dict) -> Path:
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_validate_config_ok(sample_config_dict: dict, tmp_path: Path) -> None:
    """validate-config 成功。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    result = runner.invoke(app, ["validate-config", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "配置校验通过" in result.output


def test_validate_config_missing_file(tmp_path: Path) -> None:
    """validate-config 文件不存在时 exit_code=1。"""
    result = runner.invoke(
        app,
        ["validate-config", "--config", str(tmp_path / "nonexistent.yaml")],
    )
    assert result.exit_code == 1


def test_validate_config_invalid(tmp_path: Path) -> None:
    """validate-config 配置不合法时 exit_code=1。"""
    cfg_path = _write_config(tmp_path / "config.yaml", {
        "archive_root": str(tmp_path / "archive"),
        "sources": [{
            "source_id": "s1",
            "source_name": "S1",
            "source_type": "rss_feed",  # 缺 feed_url
            "enabled": True,
        }],
    })
    result = runner.invoke(app, ["validate-config", "--config", str(cfg_path)])
    assert result.exit_code == 1


def test_dry_run_via_cli(
    sample_config_dict: dict,
    tmp_path: Path,
    sample_feed_xml: str,
) -> None:
    """dry-run 命令能执行。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    result = runner.invoke(app, ["dry-run", "--config", str(cfg_path)])
    # dry-run 应该成功（exit_code 0）
    assert result.exit_code == 0
    assert "运行 ID" in result.output


def test_run_via_cli(
    sample_config_dict: dict,
    tmp_path: Path,
    sample_feed_xml: str,
    sample_article_html: str,
) -> None:
    """run 命令能完整执行。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    result = runner.invoke(app, ["run", "--config", str(cfg_path)])
    # 因为 CLI 没有注入 fetcher，真实 HTTP 会失败，但流程应该跑完
    # exit_code 可能是 0 或 2（部分失败）
    assert result.exit_code in (0, 2)
    assert "运行 ID" in result.output


def test_source_health_empty(temp_archive_root: Path) -> None:
    """source-health 空归档目录。"""
    result = runner.invoke(
        app,
        ["source-health", "--archive-root", str(temp_archive_root)],
    )
    assert result.exit_code == 0
    assert "暂无" in result.output


def test_source_health_with_records(
    sample_config_dict: dict,
    tmp_path: Path,
    sample_feed_xml: str,
    sample_article_html: str,
) -> None:
    """source-health 有记录时输出表格。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    # 先跑一次 dry-run 生成 source_health
    runner.invoke(app, ["dry-run", "--config", str(cfg_path)])

    archive_root = sample_config_dict["archive_root"]
    result = runner.invoke(
        app,
        ["source-health", "--archive-root", archive_root],
    )
    assert result.exit_code == 0
    assert "Source Health" in result.output


def test_retry_failed_empty_via_cli(temp_archive_root: Path) -> None:
    """retry-failed 空队列。"""
    result = runner.invoke(
        app,
        ["retry-failed", "--archive-root", str(temp_archive_root)],
    )
    assert result.exit_code == 0
    assert "failed_queue" in result.output or "无可重试" in result.output


def test_report_no_run_log(temp_archive_root: Path) -> None:
    """report 命令在无 run_log 时报错。"""
    result = runner.invoke(
        app,
        ["report", "--archive-root", str(temp_archive_root), "--date", "2026-01-15"],
    )
    assert result.exit_code == 1


def test_report_with_run_log(
    sample_config_dict: dict,
    tmp_path: Path,
    sample_feed_xml: str,
    sample_article_html: str,
) -> None:
    """report 命令能生成日报。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    # 先跑一次 dry-run 生成 run_log
    runner.invoke(app, ["dry-run", "--config", str(cfg_path)])

    archive_root = sample_config_dict["archive_root"]
    # 用今天日期
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    result = runner.invoke(
        app,
        ["report", "--archive-root", archive_root, "--date", today],
    )
    assert result.exit_code == 0
    assert "日报已生成" in result.output
