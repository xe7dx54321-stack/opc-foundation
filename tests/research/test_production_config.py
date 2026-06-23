"""Phase 2F 测试：production config 校验。

覆盖：
    1. production example config 能 validate
    2. production example config 所有 source enabled=false
    3. local config path 被 .gitignore 覆盖
    4. production config 包含 source_groups
    5. production config 包含 production 元信息
    6. 不出现业务字段
"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.config.loader import load_yaml_config
from opc_foundation.research.config import load_research_config, validate_research_config


# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_EXAMPLE = PROJECT_ROOT / "configs" / "research_sources.production.example.yaml"
EXAMPLE_CONFIG = PROJECT_ROOT / "configs" / "research_sources.example.yaml"
GITIGNORE = PROJECT_ROOT / ".gitignore"


# ---------------------------------------------------------------------------
# 1. production example config 能 validate
# ---------------------------------------------------------------------------


def test_production_example_config_can_validate() -> None:
    """production example config 必须能通过 validate_research_config。"""
    config = load_research_config(str(PRODUCTION_EXAMPLE))
    errors = validate_research_config(config)
    assert errors == [], f"production example config 校验失败: {errors}"


# ---------------------------------------------------------------------------
# 2. production example config 所有 source enabled=false
# ---------------------------------------------------------------------------


def test_production_example_config_all_disabled() -> None:
    """production example config 中所有 source 必须 enabled=false。"""
    config_dict = load_yaml_config(str(PRODUCTION_EXAMPLE))
    sources = config_dict.get("sources", [])
    assert len(sources) > 0, "production example config 应该至少有一个 source"
    for src in sources:
        assert src.get("enabled") is False, (
            f"source [{src.get('source_id')}] 必须 enabled=false，"
            f"实际为 {src.get('enabled')}"
        )


# ---------------------------------------------------------------------------
# 3. local config path 被 .gitignore 覆盖
# ---------------------------------------------------------------------------


def test_gitignore_covers_local_configs() -> None:
    """.gitignore 必须覆盖 local config 文件。"""
    content = GITIGNORE.read_text(encoding="utf-8")
    assert "configs/research_sources.local.yaml" in content, (
        ".gitignore 必须包含 configs/research_sources.local.yaml"
    )
    assert "configs/research_sources.production.local.yaml" in content, (
        ".gitignore 必须包含 configs/research_sources.production.local.yaml"
    )
    assert "data/research_archive/" in content, (
        ".gitignore 必须包含 data/research_archive/"
    )


# ---------------------------------------------------------------------------
# 4. production config 包含 source_groups
# ---------------------------------------------------------------------------


def test_production_config_has_source_groups() -> None:
    """production config 必须包含 source_groups 分组说明。"""
    config_dict = load_yaml_config(str(PRODUCTION_EXAMPLE))
    source_groups = config_dict.get("source_groups")
    assert source_groups is not None, "production config 必须包含 source_groups"
    assert isinstance(source_groups, dict), "source_groups 必须是 dict"
    # 至少包含 5 个分组
    expected_groups = {
        "official_public_research",
        "podcast_transcript",
        "conference_transcript",
        "analyst_action",
        "media_mention",
    }
    for group in expected_groups:
        assert group in source_groups, f"source_groups 缺少 {group}"


# ---------------------------------------------------------------------------
# 5. production config 包含 production 元信息
# ---------------------------------------------------------------------------


def test_production_config_has_production_meta() -> None:
    """production config 必须包含 production 元信息。"""
    config_dict = load_yaml_config(str(PRODUCTION_EXAMPLE))
    production = config_dict.get("production")
    assert production is not None, "production config 必须包含 production 元信息"
    assert production.get("schedule_hint") == "daily"
    assert production.get("owner_project") == "opc-foundation"
    assert production.get("downstream_contract") == "index/documents.jsonl"
    assert production.get("local_config_path") == "configs/research_sources.production.local.yaml"


# ---------------------------------------------------------------------------
# 6. production config 不包含真实 URL
# ---------------------------------------------------------------------------


def test_production_config_uses_example_com() -> None:
    """production example config 中所有 URL 必须使用 example.com。"""
    config_dict = load_yaml_config(str(PRODUCTION_EXAMPLE))
    sources = config_dict.get("sources", [])
    for src in sources:
        url = src.get("url", "")
        base_url = src.get("base_url", "")
        assert "example.com" in url, (
            f"source [{src.get('source_id')}] url 必须使用 example.com，实际为 {url}"
        )
        assert "example.com" in base_url, (
            f"source [{src.get('source_id')}] base_url 必须使用 example.com，实际为 {base_url}"
        )


# ---------------------------------------------------------------------------
# 7. production config 不包含 secrets
# ---------------------------------------------------------------------------


def test_production_config_no_secrets() -> None:
    """production example config 的 source 配置不能包含 cookie/token/API key。"""
    config_dict = load_yaml_config(str(PRODUCTION_EXAMPLE))
    sources = config_dict.get("sources", [])
    forbidden = ["cookie", "token", "api_key", "apikey", "password", "secret"]
    for src in sources:
        # 把 source dict 转成字符串检查（不包含注释）
        src_str = str(src).lower()
        for word in forbidden:
            assert word not in src_str, (
                f"source [{src.get('source_id')}] 配置不能包含 {word}"
            )


# ---------------------------------------------------------------------------
# 8. production config 不包含业务判断字段
# ---------------------------------------------------------------------------


def test_production_config_no_business_fields() -> None:
    """production example config 的 source 配置不能包含投研判断字段。"""
    config_dict = load_yaml_config(str(PRODUCTION_EXAMPLE))
    sources = config_dict.get("sources", [])
    forbidden = [
        "affected_tickers",
        "expectation_delta",
        "investment_rating",
        "trade_signal",
        "watchlist",
        "action_decision",
        "recommendation",
    ]
    for src in sources:
        src_str = str(src).lower()
        for word in forbidden:
            assert word not in src_str, (
                f"source [{src.get('source_id')}] 配置不能包含 {word}"
            )


# ---------------------------------------------------------------------------
# 9. production config 覆盖所有已实现 source_type
# ---------------------------------------------------------------------------


def test_production_config_covers_all_source_types() -> None:
    """production example config 应覆盖所有已实现的 source_type。"""
    config_dict = load_yaml_config(str(PRODUCTION_EXAMPLE))
    sources = config_dict.get("sources", [])
    source_types = {src.get("source_type") for src in sources}
    expected_types = {
        "official_public_research",
        "podcast_transcript",
        "conference_transcript",
        "analyst_action",
        "media_mention",
    }
    for st in expected_types:
        assert st in source_types, f"production example config 缺少 source_type: {st}"


# ---------------------------------------------------------------------------
# 10. production scripts 存在
# ---------------------------------------------------------------------------


def test_run_script_exists() -> None:
    """scripts/run_research_archive.ps1 必须存在。"""
    script = PROJECT_ROOT / "scripts" / "run_research_archive.ps1"
    assert script.exists(), f"脚本不存在: {script}"


def test_check_script_exists() -> None:
    """scripts/check_research_archive.ps1 必须存在。"""
    script = PROJECT_ROOT / "scripts" / "check_research_archive.ps1"
    assert script.exists(), f"脚本不存在: {script}"


# ---------------------------------------------------------------------------
# 11. production docs 存在
# ---------------------------------------------------------------------------


def test_production_run_doc_exists() -> None:
    """docs/research_source_production_run.md 必须存在。"""
    doc = PROJECT_ROOT / "docs" / "research_source_production_run.md"
    assert doc.exists(), f"文档不存在: {doc}"
