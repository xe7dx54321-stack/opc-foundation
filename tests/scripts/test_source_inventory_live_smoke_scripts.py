"""测试 source inventory live smoke 的 PowerShell 脚本。

功能说明（小白解读）：
    测试 run 和 check 脚本文件是否存在、包含必要内容。
    不真实运行 PowerShell（那样太慢了），只做静态检查。
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


class TestSourceInventoryScripts:
    """测试 live smoke 相关脚本。"""

    def test_run_script_exists(self) -> None:
        """测试 run 脚本存在。"""
        script_path = SCRIPTS_DIR / "run_source_inventory_live_smoke.ps1"
        assert script_path.exists(), f"Script not found: {script_path}"

    def test_check_script_exists(self) -> None:
        """测试 check 脚本存在。"""
        script_path = SCRIPTS_DIR / "check_source_inventory_live_smoke.ps1"
        assert script_path.exists(), f"Script not found: {script_path}"

    def test_run_script_has_repo_root_auto_locate(self) -> None:
        """测试 run 脚本包含 RepoRoot 自动定位。"""
        script_path = SCRIPTS_DIR / "run_source_inventory_live_smoke.ps1"
        content = script_path.read_text(encoding="utf-8")
        assert "RepoRoot" in content
        assert "Split-Path" in content

    def test_run_script_sets_pythonpath(self) -> None:
        """测试 run 脚本设置了 PYTHONPATH=src。"""
        script_path = SCRIPTS_DIR / "run_source_inventory_live_smoke.ps1"
        content = script_path.read_text(encoding="utf-8")
        assert "PYTHONPATH" in content
        assert "src" in content

    def test_run_script_has_validate_config_mode(self) -> None:
        """测试 run 脚本支持 validate-config 模式。"""
        script_path = SCRIPTS_DIR / "run_source_inventory_live_smoke.ps1"
        content = script_path.read_text(encoding="utf-8")
        assert "validate-config" in content

    def test_run_script_has_dry_run_mode(self) -> None:
        """测试 run 脚本支持 dry-run 模式。"""
        script_path = SCRIPTS_DIR / "run_source_inventory_live_smoke.ps1"
        content = script_path.read_text(encoding="utf-8")
        assert "dry-run" in content

    def test_run_script_has_run_mode(self) -> None:
        """测试 run 脚本支持 run 模式。"""
        script_path = SCRIPTS_DIR / "run_source_inventory_live_smoke.ps1"
        content = script_path.read_text(encoding="utf-8")
        assert '"run"' in content or "'run'" in content

    def test_run_script_has_report_mode(self) -> None:
        """测试 run 脚本支持 report 模式。"""
        script_path = SCRIPTS_DIR / "run_source_inventory_live_smoke.ps1"
        content = script_path.read_text(encoding="utf-8")
        assert "report" in content

    def test_check_script_has_repo_root(self) -> None:
        """测试 check 脚本包含 RepoRoot 定位。"""
        script_path = SCRIPTS_DIR / "check_source_inventory_live_smoke.ps1"
        content = script_path.read_text(encoding="utf-8")
        assert "RepoRoot" in content
        assert "PYTHONPATH" in content
