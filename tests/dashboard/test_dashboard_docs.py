"""Dashboard docs hub 测试。

覆盖：
1. collect_docs_from_capabilities 返回去重的 docs 列表
2. collect_core_docs 返回核心文档列表
"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.dashboard.docs import (
    collect_core_docs,
    collect_docs_from_capabilities,
)
from opc_foundation.dashboard.loaders import load_capabilities_config
from opc_foundation.dashboard.models import Capability

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "foundation_capabilities.yaml"


def test_collect_docs_from_capabilities() -> None:
    """应返回去重的文档列表。"""
    reg = load_capabilities_config(CONFIG_PATH)
    docs = collect_docs_from_capabilities(reg.capabilities)
    # 应该有多个文档
    assert len(docs) > 0
    # 不应有重复
    assert len(docs) == len(set(docs))


def test_collect_docs_dedup() -> None:
    """相同文档路径应去重。"""
    caps = [
        Capability(
            capability_id="c1", name="C1", track="research",
            category="research_source", maturity_status="production_trial_ready",
            description="", input_type="", primary_output="",
            health_file="", run_log_file="", failed_queue_file="",
            docs=["docs/a.md", "docs/b.md"],
        ),
        Capability(
            capability_id="c2", name="C2", track="research",
            category="research_source", maturity_status="production_trial_ready",
            description="", input_type="", primary_output="",
            health_file="", run_log_file="", failed_queue_file="",
            docs=["docs/b.md", "docs/c.md"],
        ),
    ]
    docs = collect_docs_from_capabilities(caps)
    assert docs == ["docs/a.md", "docs/b.md", "docs/c.md"]


def test_collect_core_docs() -> None:
    """应返回存在的核心文档列表。"""
    docs = collect_core_docs(PROJECT_ROOT)
    # 至少应该有几个核心文档存在
    assert len(docs) > 0
    # 检查每个文档确实存在
    for doc in docs:
        assert (PROJECT_ROOT / doc).exists()


def test_collect_core_docs_includes_registry() -> None:
    """核心文档应包含 capability registry。"""
    docs = collect_core_docs(PROJECT_ROOT)
    assert "docs/foundation_capability_registry.md" in docs
    assert "docs/foundation_readiness_summary.md" in docs
    assert "docs/runtime_foundation.md" in docs
