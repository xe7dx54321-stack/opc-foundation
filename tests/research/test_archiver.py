"""测试 research/archiver.py —— 主流程。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors
from opc_foundation.research.config import load_research_config
from opc_foundation.research.models import ResearchArchiveConfig, ResearchDefaults


def _write_config(path: Path, data: dict) -> Path:
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_dry_run_discovers_candidates(
    sample_config_dict: dict,
    tmp_path: Path,
    sample_feed_xml: str,
) -> None:
    """dry-run 能发现候选，不抓正文。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    cfg = load_research_config(cfg_path)

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            feed_content_by_url=lambda url: sample_feed_xml,
        ),
    )
    result = archiver.dry_run()

    assert result.mode == "dry_run"
    assert result.candidate_count > 0
    assert result.saved_count == 0  # dry-run 不抓正文
    assert result.failed_count == 0
    # run_log 写入
    run_log = (Path(cfg.archive_root) / "state" / "run_log.jsonl").read_text(encoding="utf-8")
    assert "run_summary" in run_log


def test_dry_run_skips_disabled_source(
    sample_config_dict: dict,
    tmp_path: Path,
    sample_feed_xml: str,
) -> None:
    """disabled source 不参与。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    cfg = load_research_config(cfg_path)

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            feed_content_by_url=lambda url: sample_feed_xml,
        ),
    )
    result = archiver.dry_run()

    # 4 个 source，1 个 disabled
    assert result.source_count == 4
    assert result.enabled_source_count == 3


def test_dry_run_unsupported_source_type_fail_soft(tmp_path: Path) -> None:
    """未实现的 source_type 标记 skipped，不崩溃。"""
    cfg_data = {
        "archive_root": str(tmp_path / "archive"),
        "sources": [{
            "source_id": "future_type",
            "source_name": "Future",
            "source_type": "podcast_transcript",  # Phase 1 未实现
            "enabled": True,
            "legal_profile": "unknown",
        }],
    }
    cfg_path = _write_config(tmp_path / "config.yaml", cfg_data)
    cfg = load_research_config(cfg_path)

    archiver = ResearchArchiver(cfg)
    result = archiver.dry_run()

    # 不崩溃，标记为 failed/skipped
    assert result.source_count == 1
    assert len(result.warnings) >= 1
    assert any("unsupported" in w or "connector" in w for w in result.warnings)


def test_run_full_flow(
    sample_config_dict: dict,
    tmp_path: Path,
    sample_feed_xml: str,
    sample_article_html: str,
) -> None:
    """完整 run：发现 → 去重 → 抓取 → 抽取 → 归档。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    cfg = load_research_config(cfg_path)

    # 注入 feed 内容和 HTTP HTML
    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            feed_content_by_url=lambda url: sample_feed_xml,
            http_html=lambda url: sample_article_html,
        ),
    )
    result = archiver.run()

    assert result.mode == "run"
    assert result.candidate_count > 0
    # RSS 3 个 + manual 3 个 = 6 个候选（wechat 2 个，但 wechat_archive 走特殊路径）
    # wechat 候选会直接 saved
    assert result.saved_count > 0

    # documents.jsonl 存在
    jsonl_path = Path(cfg.archive_root) / "index" / "documents.jsonl"
    assert jsonl_path.exists()
    lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1

    # documents.latest.jsonl 存在
    latest_path = Path(cfg.archive_root) / "index" / "documents.latest.jsonl"
    assert latest_path.exists()

    # source_health.jsonl 存在
    health_path = Path(cfg.archive_root) / "state" / "source_health.jsonl"
    assert health_path.exists()

    # 日报存在
    assert result.report_path is not None
    assert Path(result.report_path).exists()


def test_run_dedup_skips_seen(
    sample_config_dict: dict,
    tmp_path: Path,
    sample_feed_xml: str,
    sample_article_html: str,
) -> None:
    """重复 run 不重复保存。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    cfg = load_research_config(cfg_path)

    injectors = ResearchInjectors(
        feed_content_by_url=lambda url: sample_feed_xml,
        http_html=lambda url: sample_article_html,
    )
    archiver = ResearchArchiver(cfg, injectors=injectors)

    # 第一次 run
    result1 = archiver.run()
    saved1 = result1.saved_count + result1.partial_count

    # 第二次 run：应该全部 duplicate
    result2 = archiver.run()
    assert result2.duplicate_count > 0
    saved2 = result2.saved_count + result2.partial_count
    # 第二次新保存应该很少甚至 0
    assert saved2 <= saved1


def test_run_single_source_failure_doesnt_crash_others(tmp_path: Path) -> None:
    """单个 source 失败不影响其他 source。"""
    cfg_data = {
        "archive_root": str(tmp_path / "archive"),
        "sources": [
            {
                "source_id": "broken_rss",
                "source_name": "Broken RSS",
                "source_type": "rss_feed",
                "feed_url": "https://nonexistent.example.com/feed.xml",
                "enabled": True,
                "legal_profile": "official_public",
            },
            {
                "source_id": "ok_manual",
                "source_name": "OK Manual",
                "source_type": "manual_url",
                "manual_urls_path": str(tmp_path / "urls.txt"),
                "enabled": True,
                "legal_profile": "user_provided",
            },
        ],
    }
    # 创建 manual url 文件
    (tmp_path / "urls.txt").write_text("https://example.com/article-1\n", encoding="utf-8")

    cfg_path = _write_config(tmp_path / "config.yaml", cfg_data)
    cfg = load_research_config(cfg_path)

    # 不注入 feed，让 broken_rss 失败
    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            http_html=lambda url: "<html><body><article><p>正文内容</p></article></body></html>",
        ),
    )
    result = archiver.run()

    # broken_rss 失败，但 ok_manual 应该能成功
    assert result.source_count == 2
    # 至少有一个 source 失败
    broken_stat = next(s for s in result.source_stats if s["source_id"] == "broken_rss")
    assert broken_stat["status"] == "failed"


def test_retry_failed_empty_queue(temp_archive_root: Path) -> None:
    """空 failed_queue 时 retry-failed 返回空结果。"""
    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(),
        sources=[],
    )
    archiver = ResearchArchiver(cfg)
    result = archiver.retry_failed()

    assert result.mode == "retry_failed"
    assert result.candidate_count == 0
    assert any("failed_queue" in w for w in result.warnings)


def test_run_exit_code_success(
    sample_config_dict: dict,
    tmp_path: Path,
    sample_feed_xml: str,
    sample_article_html: str,
) -> None:
    """全部成功时 exit_code=0。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    cfg = load_research_config(cfg_path)

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            feed_content_by_url=lambda url: sample_feed_xml,
            http_html=lambda url: sample_article_html,
        ),
    )
    result = archiver.run()
    assert result.exit_code == 0


def test_run_writes_run_log_summary(
    sample_config_dict: dict,
    tmp_path: Path,
    sample_feed_xml: str,
    sample_article_html: str,
) -> None:
    """run_log.jsonl 包含 run_summary 记录。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    cfg = load_research_config(cfg_path)

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            feed_content_by_url=lambda url: sample_feed_xml,
            http_html=lambda url: sample_article_html,
        ),
    )
    archiver.run()

    run_log_path = Path(cfg.archive_root) / "state" / "run_log.jsonl"
    records = []
    with open(run_log_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    summaries = [r for r in records if r.get("entry_type") == "run_summary"]
    assert len(summaries) >= 1
    assert summaries[0]["mode"] == "run"
