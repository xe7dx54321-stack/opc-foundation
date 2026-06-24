"""Foundation capabilities 配置文件测试。

覆盖：
1. foundation_capabilities.yaml 存在
2. capability_id 唯一
3. track 引用有效
4. docs 路径存在
5. maturity_status 值有效
6. 不包含禁止字段
7. usage registry example 存在
8. usage registry 引用的 capability_id 都存在
9. dashboard 文档存在
10. README 链接 Control Center
11. capability registry 提到 Control Center
12. readiness summary 提到 Control Center
13. dashboard app 可在无 streamlit 时导入
"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.dashboard.loaders import (
    load_capabilities_config,
    load_usage_registry,
    validate_capabilities,
)
from opc_foundation.dashboard.usage import (
    find_unknown_usage_references,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "foundation_capabilities.yaml"
USAGE_PATH = PROJECT_ROOT / "configs" / "capability_usage_registry.example.yaml"

VALID_MATURITY = {
    "production_trial_ready",
    "mvp_ready",
    "degraded",
    "planned",
    "dormant",
    "disabled",
    "failed",
}

PROHIBITED_FIELDS = {
    "affected_tickers",
    "expectation_delta",
    "investment_rating",
    "trade_signal",
    "watchlist",
    "action_decision",
    "recommendation",
    "opportunity_score",
    "risk_score",
    "position_size",
    "target_price",
}


def test_config_exists() -> None:
    """foundation_capabilities.yaml 必须存在。"""
    assert CONFIG_PATH.exists()


def test_capability_ids_unique() -> None:
    """所有 capability_id 必须唯一。"""
    reg = load_capabilities_config(CONFIG_PATH)
    ids = [c.capability_id for c in reg.capabilities]
    assert len(ids) == len(set(ids)), f"重复的 capability_id: {set(ids) - set(set(ids))}"


def test_track_references_valid() -> None:
    """所有 track 引用必须有效。"""
    reg = load_capabilities_config(CONFIG_PATH)
    errors = validate_capabilities(reg)
    assert errors == [], f"校验错误: {errors}"


def test_docs_paths_exist() -> None:
    """所有 docs 路径必须存在。"""
    reg = load_capabilities_config(CONFIG_PATH)
    for cap in reg.capabilities:
        for doc in cap.docs:
            full = PROJECT_ROOT / doc
            assert full.exists(), f"{cap.capability_id} 的文档不存在: {doc}"


def test_maturity_status_valid() -> None:
    """所有 maturity_status 必须是允许值。"""
    reg = load_capabilities_config(CONFIG_PATH)
    for cap in reg.capabilities:
        assert cap.maturity_status in VALID_MATURITY, (
            f"{cap.capability_id} 的 maturity_status 无效: {cap.maturity_status}"
        )


def test_no_prohibited_fields_in_config() -> None:
    """配置文件中不得包含禁止字段。"""
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    content = str(raw)
    for field in PROHIBITED_FIELDS:
        assert field not in content, f"配置文件包含禁止字段: {field}"


def test_usage_registry_exists() -> None:
    """capability_usage_registry.example.yaml 必须存在。"""
    assert USAGE_PATH.exists()


def test_usage_references_valid() -> None:
    """usage registry 引用的 capability_id 必须都存在。"""
    cap_reg = load_capabilities_config(CONFIG_PATH)
    usage_reg = load_usage_registry(USAGE_PATH)
    unknown = find_unknown_usage_references(cap_reg.capabilities, usage_reg)
    assert unknown == [], f"未知引用: {unknown}"


def test_dashboard_docs_exist() -> None:
    """dashboard 文档必须存在。"""
    assert (PROJECT_ROOT / "docs" / "foundation_control_center.md").exists()
    assert (PROJECT_ROOT / "docs" / "foundation_control_center_usage.md").exists()


def test_readme_links_control_center() -> None:
    """README 应链接 Control Center。"""
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "Control Center" in readme or "control_center" in readme


def test_capability_registry_mentions_control_center() -> None:
    """capability registry 应提到 Control Center。"""
    doc = (PROJECT_ROOT / "docs" / "foundation_capability_registry.md").read_text(encoding="utf-8")
    assert "Control Center" in doc or "control_center" in doc


def test_readiness_summary_mentions_control_center() -> None:
    """readiness summary 应提到 Control Center。"""
    doc = (PROJECT_ROOT / "docs" / "foundation_readiness_summary.md").read_text(encoding="utf-8")
    assert "Control Center" in doc or "control_center" in doc


def test_dashboard_app_importable_without_streamlit() -> None:
    """dashboard app 模块应可在无 streamlit 时导入。"""
    # app.py 的 main() 函数会 lazy import streamlit
    # 但模块本身应该可以导入
    import opc_foundation.dashboard.app as app_module
    assert hasattr(app_module, "main")
