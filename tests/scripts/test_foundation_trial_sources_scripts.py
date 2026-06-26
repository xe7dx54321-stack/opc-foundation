"""PowerShell 脚本测试。

功能说明（小白解读）：
    测试 PowerShell 脚本存在性和基本参数。
    注意：这些测试不执行 PowerShell，只检查脚本内容。
"""

import pytest
from pathlib import Path


class TestRunScript:
    """测试 run_foundation_trial_sources.ps1。"""

    def test_script_exists(self):
        """run_foundation_trial_sources.ps1 应该存在。"""
        script_path = Path("scripts/run_foundation_trial_sources.ps1")
        assert script_path.exists(), f"Script not found: {script_path}"

    def test_has_validate_config_mode(self):
        """脚本应该支持 validate-config 模式。"""
        content = Path("scripts/run_foundation_trial_sources.ps1").read_text(encoding="utf-8")
        assert "validate-config" in content

    def test_has_dry_run_mode(self):
        """脚本应该支持 dry-run 模式。"""
        content = Path("scripts/run_foundation_trial_sources.ps1").read_text(encoding="utf-8")
        assert "dry-run" in content

    def test_has_run_mode(self):
        """脚本应该支持 run 模式。"""
        content = Path("scripts/run_foundation_trial_sources.ps1").read_text(encoding="utf-8")
        assert 'Mode = "run"' in content or "$Mode" in content

    def test_has_proxy_parameter(self):
        """脚本应该支持 -Proxy 参数。"""
        content = Path("scripts/run_foundation_trial_sources.ps1").read_text(encoding="utf-8")
        assert "$Proxy" in content

    def test_sets_pythonpath(self):
        """脚本应该设置 PYTHONPATH。"""
        content = Path("scripts/run_foundation_trial_sources.ps1").read_text(encoding="utf-8")
        assert "PYTHONPATH" in content

    def test_auto_locates_repo_root(self):
        """脚本应该自动定位 RepoRoot。"""
        content = Path("scripts/run_foundation_trial_sources.ps1").read_text(encoding="utf-8")
        assert ".git" in content
        assert "Get-RepoRoot" in content or "Set-Location" in content

    def test_no_proxy_full_url_in_output(self):
        """脚本不应该在输出中显示完整代理地址。"""
        content = Path("scripts/run_foundation_trial_sources.ps1").read_text(encoding="utf-8")
        # 代理地址应该在 $Proxy 参数中，不应该硬编码在 Write-Host 里
        lines_with_proxy = [l for l in content.split('\n') if 'Proxy' in l and 'Write-Host' in l]
        # 如果有输出代理信息，应该是模糊的（不包含完整端口）
        for line in lines_with_proxy:
            # 检查是不是打印了完整地址（应该打印 "[configured]" 或类似占位符）
            if 'Write-Host' in line and '$Proxy' in line:
                # 好的情况：打印占位符或不打印
                # 不好的情况：直接打印 $Proxy 完整值到日志
                assert 'configured' in line.lower() or 'enabled' in line.lower(), \
                    f"Script may expose full proxy URL: {line.strip()}"


class TestCheckScript:
    """测试 check_foundation_trial_sources.ps1。"""

    def test_script_exists(self):
        """check_foundation_trial_sources.ps1 应该存在。"""
        script_path = Path("scripts/check_foundation_trial_sources.ps1")
        assert script_path.exists(), f"Script not found: {script_path}"

    def test_checks_allowlist(self):
        """脚本应该检查 allowlist 完整性。"""
        content = Path("scripts/check_foundation_trial_sources.ps1").read_text(encoding="utf-8")
        assert "allowlist" in content.lower()
        assert "foundation_trial_source_allowlist" in content

    def test_checks_source_count(self):
        """脚本应该从配置文件读取 source 数量（动态，不是硬编码）。"""
        content = Path("scripts/check_foundation_trial_sources.ps1").read_text(encoding="utf-8")
        # Should read from config instead of hardcoded number
        assert "trial_scope" in content and "source_count" in content
        # Should not hardcode "16" as the expected count
        assert "expected_count = data" in content

    def test_checks_no_blocked_sources(self):
        """脚本应该检查不含 blocked sources。"""
        content = Path("scripts/check_foundation_trial_sources.ps1").read_text(encoding="utf-8")
        assert "blocked" in content.lower()
