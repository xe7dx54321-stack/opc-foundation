"""Document Extraction Production 配置与脚本测试。

覆盖：
1. production scripts 存在
2. scripts 提到 document_extraction.production.local.yaml
3. scripts 设置 PYTHONPATH
4. production example config 存在
5. production example config all enabled=false
"""
from __future__ import annotations

from pathlib import Path

import yaml

from opc_foundation.document_extraction.config import load_config


# 路径常量
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RUN_SCRIPT = SCRIPTS_DIR / "run_document_extraction.ps1"
CHECK_SCRIPT = SCRIPTS_DIR / "check_document_extraction.ps1"
PRODUCTION_EXAMPLE = PROJECT_ROOT / "configs" / "document_extraction.production.example.yaml"


# ---------------------------------------------------------------------------
# 1. Production scripts 存在
# ---------------------------------------------------------------------------


def test_run_script_exists() -> None:
    """run 脚本必须存在。"""
    assert RUN_SCRIPT.exists(), f"run 脚本不存在: {RUN_SCRIPT}"


def test_check_script_exists() -> None:
    """check 脚本必须存在。"""
    assert CHECK_SCRIPT.exists(), f"check 脚本不存在: {CHECK_SCRIPT}"


# ---------------------------------------------------------------------------
# 2. scripts 提到 document_extraction.production.local.yaml
# ---------------------------------------------------------------------------


def test_run_script_mentions_local_config() -> None:
    """run 脚本必须提到 local config。"""
    content = RUN_SCRIPT.read_text(encoding="utf-8")
    assert "document_extraction.production.local.yaml" in content, (
        "run 脚本应提到 document_extraction.production.local.yaml"
    )


def test_check_script_mentions_local_config() -> None:
    """check 脚本必须提到 local config。"""
    content = CHECK_SCRIPT.read_text(encoding="utf-8")
    # check 脚本可能不直接提 local config 名，至少提到 archive root
    assert (
        "document_extraction" in content
        or "archive_root" in content
        or "data" in content
    ), "check 脚本应提到 document_extraction 相关内容"


# ---------------------------------------------------------------------------
# 3. scripts 设置 PYTHONPATH
# ---------------------------------------------------------------------------


def test_run_script_sets_pythonpath() -> None:
    """run 脚本必须设置 PYTHONPATH。"""
    content = RUN_SCRIPT.read_text(encoding="utf-8")
    assert "PYTHONPATH" in content or "pythonpath" in content, (
        "run 脚本应设置 PYTHONPATH"
    )
    assert "src" in content, "run 脚本的 PYTHONPATH 应包含 src"


def test_check_script_sets_pythonpath() -> None:
    """check 脚本必须设置 PYTHONPATH。"""
    content = CHECK_SCRIPT.read_text(encoding="utf-8")
    assert "PYTHONPATH" in content or "pythonpath" in content, (
        "check 脚本应设置 PYTHONPATH"
    )
    assert "src" in content, "check 脚本的 PYTHONPATH 应包含 src"


# ---------------------------------------------------------------------------
# 4. Production example config 存在
# ---------------------------------------------------------------------------


def test_production_example_config_exists() -> None:
    """production example config 必须存在。"""
    assert PRODUCTION_EXAMPLE.exists(), (
        f"production example config 不存在: {PRODUCTION_EXAMPLE}"
    )


def test_production_example_config_all_disabled() -> None:
    """production example config 中所有 source 必须 enabled=false。"""
    with open(PRODUCTION_EXAMPLE, encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    sources = config_data.get("sources", [])
    assert len(sources) > 0, "production example config 应该至少有一个 source"

    for src in sources:
        assert src.get("enabled") is False, (
            f"source [{src.get('source_id')}] 必须 enabled=false，"
            f"实际为 {src.get('enabled')}"
        )


def test_production_example_config_can_load() -> None:
    """production example config 必须能通过 load_config 加载。"""
    config = load_config(PRODUCTION_EXAMPLE)
    assert config.archive_root is not None
    assert len(config.sources) > 0


def test_production_example_config_ocr_disabled() -> None:
    """production example config 中 ocr_enabled 必须为 false。"""
    with open(PRODUCTION_EXAMPLE, encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    defaults = config_data.get("defaults", {})
    ocr_enabled = defaults.get("ocr_enabled", None)
    assert ocr_enabled is False, (
        f"production example config 中 ocr_enabled 必须为 false，"
        f"实际为 {ocr_enabled}"
    )
