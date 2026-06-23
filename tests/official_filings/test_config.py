"""测试 official_filings 的配置加载与校验。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from opc_foundation.official_filings.config import (
    FilingConfigError,
    load_filing_config,
    validate_filing_config,
)
from opc_foundation.official_filings.models import FilingArchiveConfig


def _write_yaml(path: Path, content: str) -> None:
    """写 YAML 文件。"""
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# load_filing_config
# ---------------------------------------------------------------------------


def test_load_config_success(sample_config_dict: dict, tmp_path: Path) -> None:
    """能正确加载合法配置。"""
    import yaml

    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(yaml.dump(sample_config_dict, allow_unicode=True), encoding="utf-8")

    cfg = load_filing_config(str(config_path))
    assert isinstance(cfg, FilingArchiveConfig)
    assert len(cfg.sources) == 3
    assert cfg.sources[0].source_id == "test_sec"
    assert cfg.defaults.max_items_per_source == 5


def test_load_config_file_not_found() -> None:
    """文件不存在时抛出 FilingConfigError。"""
    with pytest.raises(FilingConfigError, match="配置文件不存在"):
        load_filing_config("/nonexistent/path/config.yaml")


def test_load_config_missing_archive_root(tmp_path: Path) -> None:
    """缺少 archive_root 时抛出错误。"""
    config_path = tmp_path / "bad.yaml"
    config_path.write_text("sources: []\n", encoding="utf-8")

    with pytest.raises(FilingConfigError, match="archive_root"):
        load_filing_config(str(config_path))


def test_load_config_duplicate_source_id(tmp_path: Path) -> None:
    """source_id 重复时抛出错误。"""
    import yaml

    config = {
        "archive_root": str(tmp_path / "archive"),
        "sources": [
            {"source_id": "dup", "source_name": "A", "source_type": "sec_edgar"},
            {"source_id": "dup", "source_name": "B", "source_type": "sec_edgar"},
        ],
    }
    config_path = tmp_path / "dup.yaml"
    config_path.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")

    with pytest.raises(FilingConfigError, match="source_id 重复"):
        load_filing_config(str(config_path))


def test_load_config_invalid_legal_profile(tmp_path: Path) -> None:
    """legal_profile 不合法时抛出错误。"""
    import yaml

    config = {
        "archive_root": str(tmp_path / "archive"),
        "sources": [
            {
                "source_id": "test",
                "source_name": "Test",
                "source_type": "sec_edgar",
                "legal_profile": "invalid_profile",
            }
        ],
    }
    config_path = tmp_path / "bad.yaml"
    config_path.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")

    with pytest.raises(FilingConfigError, match="legal_profile"):
        load_filing_config(str(config_path))


# ---------------------------------------------------------------------------
# validate_filing_config
# ---------------------------------------------------------------------------


def test_validate_config_valid(sample_config_dict: dict, tmp_path: Path) -> None:
    """合法配置校验通过（返回空列表）。"""
    import yaml

    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(yaml.dump(sample_config_dict, allow_unicode=True), encoding="utf-8")

    cfg = load_filing_config(str(config_path))
    errors = validate_filing_config(cfg)
    assert errors == []


def test_validate_config_example_all_disabled(tmp_path: Path) -> None:
    """example config 所有 source enabled=false 也能通过校验。"""
    import yaml

    config = {
        "archive_root": "./data/official_filings",
        "defaults": {"max_items_per_source": 10},
        "sources": [
            {
                "source_id": "example_sec",
                "source_name": "Example SEC",
                "source_type": "sec_edgar",
                "base_url": "https://www.sec.gov",
                "enabled": False,
                "legal_profile": "official_public",
            },
            {
                "source_id": "example_cninfo",
                "source_name": "Example CNINFO",
                "source_type": "cninfo_announcement",
                "base_url": "https://www.cninfo.com.cn",
                "enabled": False,
                "legal_profile": "official_public",
            },
            {
                "source_id": "example_hkex",
                "source_name": "Example HKEX",
                "source_type": "hkex_announcement",
                "base_url": "https://www.hkexnews.hk",
                "enabled": False,
                "legal_profile": "official_public",
            },
        ],
    }
    config_path = tmp_path / "example.yaml"
    config_path.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")

    cfg = load_filing_config(str(config_path))
    errors = validate_filing_config(cfg)
    assert errors == []
    # 确认所有 source 都是 disabled
    assert all(not s.enabled for s in cfg.sources)
