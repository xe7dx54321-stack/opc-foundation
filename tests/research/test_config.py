"""测试 research/config.py —— 配置加载与校验。"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from opc_foundation.research.config import (
    ResearchConfigError,
    load_research_config,
    validate_research_config,
)


def _write_config(path: Path, data: dict) -> Path:
    """把 dict 写成 yaml 文件。"""
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_load_config_basic(sample_config_dict: dict, tmp_path: Path) -> None:
    """能加载完整配置。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    cfg = load_research_config(cfg_path)

    assert cfg.archive_root == sample_config_dict["archive_root"]
    assert len(cfg.sources) == 4
    assert cfg.defaults.fetch_timeout_seconds == 10
    assert cfg.defaults.max_items_per_source == 5


def test_load_config_missing_file(tmp_path: Path) -> None:
    """文件不存在时报错。"""
    with pytest.raises(ResearchConfigError):
        load_research_config(tmp_path / "nonexistent.yaml")


def test_load_config_missing_archive_root(tmp_path: Path) -> None:
    """缺少 archive_root 字段时报错。"""
    cfg_path = _write_config(tmp_path / "config.yaml", {"sources": []})
    with pytest.raises(ResearchConfigError, match="archive_root"):
        load_research_config(cfg_path)


def test_load_config_duplicate_source_id(sample_config_dict: dict, tmp_path: Path) -> None:
    """source_id 重复时报错。"""
    sample_config_dict["sources"][1]["source_id"] = "rss_test"
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    with pytest.raises(ResearchConfigError, match="source_id 重复"):
        load_research_config(cfg_path)


def test_load_config_invalid_legal_profile(sample_config_dict: dict, tmp_path: Path) -> None:
    """legal_profile 不合法时报错。"""
    sample_config_dict["sources"][0]["legal_profile"] = "invalid_profile"
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    with pytest.raises(ResearchConfigError, match="legal_profile"):
        load_research_config(cfg_path)


def test_validate_config_ok(sample_config_dict: dict, tmp_path: Path) -> None:
    """完整配置校验通过。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    cfg = load_research_config(cfg_path)
    errors = validate_research_config(cfg)
    assert errors == []


def test_validate_config_missing_feed_url(tmp_path: Path) -> None:
    """rss_feed 缺少 feed_url 时校验失败。"""
    cfg_path = _write_config(tmp_path / "config.yaml", {
        "archive_root": str(tmp_path / "archive"),
        "sources": [{
            "source_id": "rss_no_url",
            "source_name": "RSS No URL",
            "source_type": "rss_feed",
            "enabled": True,
        }],
    })
    cfg = load_research_config(cfg_path)
    errors = validate_research_config(cfg)
    assert any("feed_url" in e for e in errors)


def test_validate_config_unknown_source_type(tmp_path: Path) -> None:
    """未知 source_type 校验失败。"""
    cfg_path = _write_config(tmp_path / "config.yaml", {
        "archive_root": str(tmp_path / "archive"),
        "sources": [{
            "source_id": "unknown_type",
            "source_name": "Unknown",
            "source_type": "totally_unknown",
            "enabled": True,
        }],
    })
    cfg = load_research_config(cfg_path)
    errors = validate_research_config(cfg)
    assert any("source_type 未知" in e for e in errors)


def test_load_config_disabled_source_preserved(sample_config_dict: dict, tmp_path: Path) -> None:
    """disabled source 也会被加载（只是运行时跳过）。"""
    cfg_path = _write_config(tmp_path / "config.yaml", sample_config_dict)
    cfg = load_research_config(cfg_path)
    disabled = [s for s in cfg.sources if not s.enabled]
    assert len(disabled) == 1
    assert disabled[0].source_id == "disabled_source"
