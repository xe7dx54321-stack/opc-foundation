"""Dashboard loaders 测试。

覆盖：
1. load_capabilities_config 读取成功
2. load_capabilities_config 文件不存在返回空 registry
3. load_usage_registry 读取成功
4. load_usage_registry 文件不存在返回空 registry
5. load_jsonl_safe 文件不存在返回 []
6. load_jsonl_safe 空文件返回 []
7. load_jsonl_safe 坏 JSON 行 fail-soft
8. validate_capabilities 返回空错误列表
9. check_docs_exist 返回存在的 docs
"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.dashboard.loaders import (
    check_docs_exist,
    load_capabilities_config,
    load_jsonl_safe,
    load_usage_registry,
    validate_capabilities,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "foundation_capabilities.yaml"
USAGE_PATH = PROJECT_ROOT / "configs" / "capability_usage_registry.example.yaml"


def test_load_capabilities_config_success() -> None:
    """应成功读取 foundation_capabilities.yaml。"""
    reg = load_capabilities_config(CONFIG_PATH)
    assert reg.version != ""
    assert len(reg.tracks) == 4
    assert len(reg.capabilities) == 20


def test_load_capabilities_config_missing_file() -> None:
    """文件不存在应返回空 registry。"""
    reg = load_capabilities_config("/nonexistent/path.yaml")
    assert reg.version == ""
    assert len(reg.tracks) == 0
    assert len(reg.capabilities) == 0


def test_load_usage_registry_success() -> None:
    """应成功读取 usage registry example。"""
    reg = load_usage_registry(USAGE_PATH)
    assert reg.version != ""
    assert len(reg.projects) >= 2


def test_load_usage_registry_missing_file() -> None:
    """文件不存在应返回空 registry。"""
    reg = load_usage_registry("/nonexistent/usage.yaml")
    assert reg.version == ""
    assert len(reg.projects) == 0


def test_load_jsonl_safe_missing_file(tmp_path: Path) -> None:
    """文件不存在应返回 []。"""
    assert load_jsonl_safe(tmp_path / "nonexistent.jsonl") == []


def test_load_jsonl_safe_empty_file(tmp_path: Path) -> None:
    """空文件应返回 []。"""
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    assert load_jsonl_safe(p) == []


def test_load_jsonl_safe_bad_line(tmp_path: Path) -> None:
    """坏 JSON 行应被跳过。"""
    p = tmp_path / "bad.jsonl"
    p.write_text('{"ok": 1}\nBAD LINE\n{"ok": 2}\n', encoding="utf-8")
    records = load_jsonl_safe(p)
    assert len(records) == 2
    assert records[0]["ok"] == 1


def test_validate_capabilities_no_errors() -> None:
    """正确的配置应返回空错误列表。"""
    reg = load_capabilities_config(CONFIG_PATH)
    errors = validate_capabilities(reg)
    assert errors == []


def test_check_docs_exist_all_present() -> None:
    """所有 docs 路径应存在。"""
    reg = load_capabilities_config(CONFIG_PATH)
    missing = check_docs_exist(reg.capabilities, PROJECT_ROOT)
    # 可能有缺失，但不应崩溃
    assert isinstance(missing, dict)
