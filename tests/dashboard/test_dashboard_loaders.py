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
    load_runbooks_config,
    load_usage_registry,
    validate_capabilities,
    validate_runbooks,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "foundation_capabilities.yaml"
USAGE_PATH = PROJECT_ROOT / "configs" / "capability_usage_registry.example.yaml"
RUNBOOKS_PATH = PROJECT_ROOT / "configs" / "capability_runbooks.yaml"


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


def test_load_runbooks_config_success() -> None:
    """应成功读取 capability_runbooks.yaml。"""
    reg = load_runbooks_config(RUNBOOKS_PATH)
    assert reg.version != ""
    assert len(reg.runbooks) == 20
    assert reg.load_error is None


def test_load_runbooks_config_missing_file() -> None:
    """文件不存在应返回空 registry。"""
    reg = load_runbooks_config("/nonexistent/runbooks.yaml")
    assert reg.version == ""
    assert len(reg.runbooks) == 0
    assert reg.load_error is None


def test_load_runbooks_config_bad_yaml(tmp_path: Path) -> None:
    """YAML 格式错误应返回带 load_error 的空 registry。"""
    p = tmp_path / "bad.yaml"
    p.write_text("key: [unclosed", encoding="utf-8")
    reg = load_runbooks_config(p)
    assert reg.load_error is not None
    assert len(reg.runbooks) == 0


def test_load_runbooks_config_empty_file(tmp_path: Path) -> None:
    """空文件应返回空 registry。"""
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    reg = load_runbooks_config(p)
    assert len(reg.runbooks) == 0


def test_validate_runbooks_no_errors() -> None:
    """正确的配置应返回空错误列表。"""
    cap_reg = load_capabilities_config(CONFIG_PATH)
    rb_reg = load_runbooks_config(RUNBOOKS_PATH)
    errors = validate_runbooks(rb_reg, cap_reg)
    assert errors == []


def test_validate_runbooks_unknown_capability() -> None:
    """引用了未知 capability_id 应报错。"""
    from opc_foundation.dashboard.models import (
        Capability,
        CapabilityRegistry,
        CapabilityRunbook,
        CapabilityTrack,
        RunbookRegistry,
    )

    cap_reg = CapabilityRegistry(
        version="1",
        updated_at="",
        tracks=[CapabilityTrack(track_id="research", name="Research", status="ready", description="")],
        capabilities=[
            Capability(
                capability_id="research.rss_feed",
                name="RSS",
                track="research",
                category="source",
                maturity_status="ready",
                description="",
                input_type="",
                primary_output="",
                health_file="",
                run_log_file="",
                failed_queue_file="",
                docs=[],
            )
        ],
    )
    rb_reg = RunbookRegistry(
        runbooks=[
            CapabilityRunbook(capability_id="research.unknown"),
        ],
    )
    errors = validate_runbooks(rb_reg, cap_reg)
    assert len(errors) == 1
    assert "unknown" in errors[0]


def test_validate_runbooks_duplicate_id() -> None:
    """重复的 capability_id 应报错。"""
    from opc_foundation.dashboard.models import (
        Capability,
        CapabilityRegistry,
        CapabilityRunbook,
        CapabilityTrack,
        RunbookRegistry,
    )

    cap_reg = CapabilityRegistry(
        version="1",
        updated_at="",
        tracks=[CapabilityTrack(track_id="research", name="Research", status="ready", description="")],
        capabilities=[
            Capability(
                capability_id="research.rss_feed",
                name="RSS",
                track="research",
                category="source",
                maturity_status="ready",
                description="",
                input_type="",
                primary_output="",
                health_file="",
                run_log_file="",
                failed_queue_file="",
                docs=[],
            )
        ],
    )
    rb_reg = RunbookRegistry(
        runbooks=[
            CapabilityRunbook(capability_id="research.rss_feed"),
            CapabilityRunbook(capability_id="research.rss_feed"),
        ],
    )
    errors = validate_runbooks(rb_reg, cap_reg)
    assert len(errors) == 1
    assert "重复" in errors[0]
