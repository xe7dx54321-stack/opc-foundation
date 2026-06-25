"""
Tests for Foundation Operations Scripts.

本测试文件验证 foundation 运维脚本的正确性，包括：
- 所有新增脚本存在
- 已有 wechat/document_extraction 脚本仍存在
- 新增脚本包含 RepoRoot 自动定位逻辑
- 新增脚本设置 PYTHONPATH=src
- 新增脚本不包含 secrets 字样或 API key 示例
"""

from pathlib import Path

import pytest


# ============================================
# Constants
# ============================================

SCRIPTS_DIR = Path("scripts")

# 新增脚本
NEW_SCRIPTS = [
    "run_research_archive.ps1",
    "check_research_archive.ps1",
    "run_official_filings.ps1",
    "check_official_filings.ps1",
    "run_manual_url_archive.ps1",
    "check_foundation_control_center.ps1",
    "check_foundation_daily_status.ps1",
]

# 已有脚本（不得删除）
EXISTING_SCRIPTS = [
    "run_wechat_archive.ps1",
    "check_wechat_archive.ps1",
    "run_document_extraction.ps1",
    "check_document_extraction.ps1",
]


# ============================================
# Script Existence Tests
# ============================================


class TestScriptExistence:
    """脚本存在性测试类。

    验证所有应该存在的脚本都存在。
    """

    @pytest.mark.parametrize("script_name", NEW_SCRIPTS)
    def test_new_scripts_exist(self, script_name: str) -> None:
        """测试所有新增脚本存在。

        Args:
            script_name: 脚本文件名
        """
        script_path = SCRIPTS_DIR / script_name
        assert script_path.exists(), f"Script {script_name} should exist"

    @pytest.mark.parametrize("script_name", EXISTING_SCRIPTS)
    def test_existing_scripts_preserved(self, script_name: str) -> None:
        """测试已有脚本仍然存在。

        验证历史脚本没有被删除。

        Args:
            script_name: 脚本文件名
        """
        script_path = SCRIPTS_DIR / script_name
        assert script_path.exists(), f"Script {script_name} should still exist (not deleted)"


# ============================================
# Script Structure Tests
# ============================================


class TestScriptStructure:
    """脚本结构测试类。

    验证脚本包含必要的结构和逻辑。
    """

    @pytest.mark.parametrize("script_name", NEW_SCRIPTS)
    def test_script_has_reporoot_logic(self, script_name: str) -> None:
        """测试新增脚本包含 RepoRoot 自动定位逻辑。

        验证脚本中有 MyInvocation.MyCommand.Path 和 Split-Path 组合。

        Args:
            script_name: 脚本文件名
        """
        script_path = SCRIPTS_DIR / script_name
        content = script_path.read_text(encoding="utf-8")

        # 检查是否有脚本目录定位
        assert "MyInvocation.MyCommand.Path" in content, \
            f"{script_name} should have script path detection"
        # 检查是否有 RepoRoot 变量
        assert "RepoRoot" in content or "ScriptDir" in content, \
            f"{script_name} should have RepoRoot or ScriptDir variable"
        # 检查是否有 Set-Location
        assert "Set-Location" in content, \
            f"{script_name} should Set-Location to repo root"

    @pytest.mark.parametrize("script_name", NEW_SCRIPTS)
    def test_script_sets_pythonpath(self, script_name: str) -> None:
        """测试新增脚本设置 PYTHONPATH=src。

        验证脚本设置了 PYTHONPATH 环境变量指向 src 目录。

        Args:
            script_name: 脚本文件名
        """
        script_path = SCRIPTS_DIR / script_name
        content = script_path.read_text(encoding="utf-8")

        assert "PYTHONPATH" in content, \
            f"{script_name} should set PYTHONPATH"
        assert "src" in content, \
            f"{script_name} should set PYTHONPATH to include src"

    @pytest.mark.parametrize("script_name", NEW_SCRIPTS)
    def test_script_no_hardcoded_secrets(self, script_name: str) -> None:
        """测试新增脚本不包含 secrets 或 API key 示例。

        验证脚本中没有硬编码的密钥、token、API key 等。

        Args:
            script_name: 脚本文件名
        """
        script_path = SCRIPTS_DIR / script_name
        content = script_path.read_text(encoding="utf-8").lower()

        # 检查常见的密钥关键词
        secret_patterns = [
            "api_key",
            "apikey",
            "secret_key",
            "secretkey",
            "access_token",
            "accesstoken",
        ]

        for pattern in secret_patterns:
            # 允许注释中提到这些词，但不允许赋值
            # 简单检查：不出现 = "xxx" 形式的赋值
            lines = content.split("\n")
            for line in lines:
                # 跳过注释行
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # 检查是否有可疑的密钥赋值
                if pattern in stripped and "=" in stripped:
                    # 检查等号后面是否有引号（可能是硬编码值）
                    parts = stripped.split("=", 1)
                    if len(parts) > 1:
                        value_part = parts[1].strip()
                        # 如果值被引号包裹，可能是硬编码
                        if value_part.startswith('"') or value_part.startswith("'"):
                            # 检查是否有实际值（不是空字符串或变量引用）
                            if len(value_part) > 5 and "$" not in value_part[:3]:
                                pytest.fail(f"{script_name} may contain hardcoded secret: {pattern}")

    @pytest.mark.parametrize("script_name", NEW_SCRIPTS)
    def test_script_has_chinese_output(self, script_name: str) -> None:
        """测试新增脚本有中文输出。

        验证脚本包含中文提示信息（不是全英文）。

        Args:
            script_name: 脚本文件名
        """
        script_path = SCRIPTS_DIR / script_name
        content = script_path.read_text(encoding="utf-8")

        # 简单检查：包含中文字符（通过统计非 ASCII 字符）
        non_ascii_count = sum(1 for c in content if ord(c) > 127)
        assert non_ascii_count > 20, \
            f"{script_name} should have Chinese output (found {non_ascii_count} non-ASCII chars)"

    @pytest.mark.parametrize("script_name", NEW_SCRIPTS)
    def test_script_has_exit_statement(self, script_name: str) -> None:
        """测试新增脚本有 exit 语句。

        验证脚本有明确的退出码（不是自然结束）。

        Args:
            script_name: 脚本文件名
        """
        script_path = SCRIPTS_DIR / script_name
        content = script_path.read_text(encoding="utf-8")

        assert "exit " in content or "exit\n" in content or content.rstrip().endswith("exit 0"), \
            f"{script_name} should have exit statement"

    @pytest.mark.parametrize("script_name", NEW_SCRIPTS)
    def test_script_has_erroraction_preference(self, script_name: str) -> None:
        """测试新增脚本设置 ErrorActionPreference。

        验证脚本设置了错误处理偏好。

        Args:
            script_name: 脚本文件名
        """
        script_path = SCRIPTS_DIR / script_name
        content = script_path.read_text(encoding="utf-8")

        assert "ErrorActionPreference" in content, \
            f"{script_name} should set ErrorActionPreference"


# ============================================
# Script Content Tests
# ============================================


class TestScriptContent:
    """脚本内容测试类。

    验证特定脚本的内容是否符合预期。
    """

    def test_run_research_has_mode_param(self) -> None:
        """测试 run_research_archive 有 Mode 参数。

        验证脚本支持 -Mode 参数。
        """
        content = (SCRIPTS_DIR / "run_research_archive.ps1").read_text(encoding="utf-8")
        assert "[string]$Mode" in content, "run_research_archive should have Mode parameter"

    def test_run_research_supports_validate_or_dryrun(self) -> None:
        """测试 run_research_archive 支持 dry-run 或 validate-config。

        验证脚本至少支持 dry-run 模式。
        """
        content = (SCRIPTS_DIR / "run_research_archive.ps1").read_text(encoding="utf-8")
        assert "dry-run" in content, "run_research_archive should support dry-run mode"

    def test_check_research_does_not_run_scraping(self) -> None:
        """测试 check_research_archive 不运行采集。

        验证 check 脚本不包含 run 命令，只做检查。
        """
        content = (SCRIPTS_DIR / "check_research_archive.ps1").read_text(encoding="utf-8")
        # 不应该有 cli run 命令
        assert "cli run" not in content.lower(), \
            "check_research_archive should not run scraping"

    def test_check_control_center_no_streamlit_run(self) -> None:
        """测试 check_foundation_control_center 不启动 Streamlit。

        验证 Control Center 检查脚本不启动 Streamlit。
        """
        content = (SCRIPTS_DIR / "check_foundation_control_center.ps1").read_text(encoding="utf-8")
        assert "streamlit run" not in content.lower(), \
            "check_foundation_control_center should not start Streamlit"

    def test_check_daily_status_writes_report(self) -> None:
        """测试 check_foundation_daily_status 写报告。

        验证每日状态脚本会生成报告文件。
        """
        content = (SCRIPTS_DIR / "check_foundation_daily_status.ps1").read_text(encoding="utf-8")
        assert "daily_status_" in content or "报告" in content, \
            "check_foundation_daily_status should generate daily report"

    def test_manual_url_no_panic_when_empty(self) -> None:
        """测试 run_manual_url_archive 在无 URL 时正常退出。

        验证脚本在没有待处理 URL 时正常退出，不报错。
        """
        content = (SCRIPTS_DIR / "run_manual_url_archive.ps1").read_text(encoding="utf-8")
        assert "无待处理" in content or "等待人工触发" in content, \
            "run_manual_url_archive should handle empty queue gracefully"

    def test_run_official_filings_has_mode_param(self) -> None:
        """测试 run_official_filings 有 Mode 参数。

        验证脚本支持 -Mode 参数。
        """
        content = (SCRIPTS_DIR / "run_official_filings.ps1").read_text(encoding="utf-8")
        assert "[string]$Mode" in content, "run_official_filings should have Mode parameter"
