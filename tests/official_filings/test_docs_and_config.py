"""测试文档存在性和 example config 合规性。"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# 仓库根目录（往上找 opc-foundation 仓库）
REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
CONFIGS_DIR = REPO_ROOT / "configs"


# ---------------------------------------------------------------------------
# Example Config 检查
# ---------------------------------------------------------------------------


def test_example_config_exists() -> None:
    """official_filings.example.yaml 存在。"""
    config_path = CONFIGS_DIR / "official_filings.example.yaml"
    assert config_path.exists(), f"缺少 example config: {config_path}"


def test_example_config_all_disabled() -> None:
    """example config 中所有 source 都是 enabled=false。"""
    config_path = CONFIGS_DIR / "official_filings.example.yaml"
    if not config_path.exists():
        pytest.skip("example config 不存在")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    sources = config.get("sources", [])
    assert len(sources) >= 3, "example config 至少应有 3 个 source（SEC/CNINFO/HKEX）"

    for src in sources:
        assert src.get("enabled") is False, (
            f"example config 中 source [{src.get('source_id')}] 不应启用"
        )


def test_example_config_contains_three_source_types() -> None:
    """example config 包含三种 source type。"""
    config_path = CONFIGS_DIR / "official_filings.example.yaml"
    if not config_path.exists():
        pytest.skip("example config 不存在")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    source_types = {s.get("source_type") for s in config.get("sources", [])}
    assert "sec_edgar" in source_types
    assert "cninfo_announcement" in source_types
    assert "hkex_announcement" in source_types


def test_example_config_has_no_secrets() -> None:
    """example config 中不包含 secrets 相关字段。"""
    config_path = CONFIGS_DIR / "official_filings.example.yaml"
    if not config_path.exists():
        pytest.skip("example config 不存在")

    content = config_path.read_text(encoding="utf-8").lower()
    # 不应包含密码、token、cookie、api_key 等
    assert "password" not in content
    assert "token" not in content
    assert "cookie" not in content
    assert "api_key" not in content
    assert "secret" not in content


# ---------------------------------------------------------------------------
# 文档检查
# ---------------------------------------------------------------------------


def test_foundation_doc_exists() -> None:
    """official_filing_foundation.md 存在。"""
    doc_path = DOCS_DIR / "official_filing_foundation.md"
    assert doc_path.exists(), f"缺少 foundation 文档: {doc_path}"


def test_production_run_doc_exists() -> None:
    """official_filing_production_run.md 存在。"""
    doc_path = DOCS_DIR / "official_filing_production_run.md"
    assert doc_path.exists(), f"缺少 production run 文档: {doc_path}"


def test_foundation_doc_mentions_three_sources() -> None:
    """foundation 文档提到了三个 source type。"""
    doc_path = DOCS_DIR / "official_filing_foundation.md"
    if not doc_path.exists():
        pytest.skip("foundation doc 不存在")

    content = doc_path.read_text(encoding="utf-8")
    assert "SEC EDGAR" in content or "sec_edgar" in content
    assert "CNINFO" in content or "cninfo_announcement" in content
    assert "HKEX" in content or "hkex_announcement" in content


def test_foundation_doc_mentions_no_investment_judgment() -> None:
    """foundation 文档明确说明不做投资判断。"""
    doc_path = DOCS_DIR / "official_filing_foundation.md"
    if not doc_path.exists():
        pytest.skip("foundation doc 不存在")

    content = doc_path.read_text(encoding="utf-8")
    assert "不做投资判断" in content or "不提供投资建议" in content


def test_foundation_doc_mentions_downstream_contract() -> None:
    """foundation 文档提到了下游消费契约。"""
    doc_path = DOCS_DIR / "official_filing_foundation.md"
    if not doc_path.exists():
        pytest.skip("foundation doc 不存在")

    content = doc_path.read_text(encoding="utf-8")
    assert "下游" in content or "downstream" in content or "消费" in content


# ---------------------------------------------------------------------------
# .gitignore 检查
# ---------------------------------------------------------------------------


def test_gitignore_contains_official_filings_data() -> None:
    """.gitignore 中包含 official_filings 数据目录。"""
    gitignore_path = REPO_ROOT / ".gitignore"
    if not gitignore_path.exists():
        pytest.skip(".gitignore 不存在")

    content = gitignore_path.read_text(encoding="utf-8")
    assert "data/official_filings/" in content


def test_gitignore_contains_local_configs() -> None:
    """.gitignore 中包含 local config。"""
    gitignore_path = REPO_ROOT / ".gitignore"
    if not gitignore_path.exists():
        pytest.skip(".gitignore 不存在")

    content = gitignore_path.read_text(encoding="utf-8")
    assert "official_filings.local.yaml" in content
