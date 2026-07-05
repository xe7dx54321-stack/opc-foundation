"""Tests for M3C-6F Proxy Retry Batch configuration and script.

覆盖范围：
    1. source_id 只能是 merck_ir / yahoo_finance / the_fly
    2. trial_v2_allowlist_allowed_now 默认 false（已在模型测试覆盖）
    3. captcha / login / paywall blockers（已在模型测试覆盖）
    4. valid / dated item 阈值（已在模型测试覆盖）
    5. 配置文件遵循边界规则
    6. proxy-env 模式不得打印真实代理 URL
    7. proxy-env 未配置时不得失败
    8. 不修改 trial_v2 allowlist
    9. 不修改 TRAE scheduling
    10. 不配置 production
    11. 不引入 Playwright / Selenium
    12. 不恢复 Dashboard 已删除页面
    13. 报告不包含 cookie / token / proxy URL / secret
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from opc_foundation.source_inventory.proxy_retry_assessment import (
    M3C_6F_ALLOWED_CANDIDATES,
    SENSITIVE_KEYWORDS,
    scan_sensitive_keywords,
)

CONFIG_PATH = (
    REPO_ROOT
    / "configs"
    / "foundation_m3c_6f_proxy_retry_batch.example.yaml"
)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "foundation_m3c_6f_proxy_retry_batch_report.md"
)
SCRIPT_PATH = (
    REPO_ROOT
    / "scripts"
    / "run_m3c_6f_proxy_retry_batch.py"
)


# =============================================================================
# Test 1: Config file exists and follows boundary rules
# =============================================================================

class TestConfigBoundaries:
    """Validate M3C-6F example config follows all boundary rules."""

    def test_config_exists(self):
        assert CONFIG_PATH.exists()

    def test_config_is_valid_yaml(self):
        content = CONFIG_PATH.read_text()
        data = yaml.safe_load(content)
        assert isinstance(data, dict)

    def test_production_enabled_is_false(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        scope = data.get("scope", {})
        assert scope.get("production_enabled") is False

    def test_affects_trial_v2_allowlist_is_false(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        scope = data.get("scope", {})
        assert scope.get("affects_trial_v2_allowlist") is False

    def test_affects_trae_scheduling_is_false(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        scope = data.get("scope", {})
        assert scope.get("affects_trae_scheduling") is False

    def test_candidate_sources_only_3(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        scope = data.get("scope", {})
        candidates = scope.get("candidate_sources", [])
        assert len(candidates) == 3
        assert set(candidates) == M3C_6F_ALLOWED_CANDIDATES

    def test_candidates_section_matches(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        candidates = data.get("candidates", [])
        assert len(candidates) == 3
        source_ids = {c.get("source_id") for c in candidates}
        assert source_ids == M3C_6F_ALLOWED_CANDIDATES

    def test_policy_no_login_bypass(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        policy = data.get("policy", {})
        assert policy.get("no_login") is True

    def test_policy_no_paywall_bypass(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        policy = data.get("policy", {})
        assert policy.get("no_paywall_bypass") is True

    def test_policy_no_captcha_solving(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        policy = data.get("policy", {})
        assert policy.get("no_captcha_solving") is True

    def test_policy_no_cloudflare_bypass(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        policy = data.get("policy", {})
        assert policy.get("no_cloudflare_bypass") is True

    def test_policy_no_antibot_bypass(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        policy = data.get("policy", {})
        assert policy.get("no_antibot_bypass") is True

    def test_disallowed_promotions(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        disallowed = data.get("disallowed_promotions", {})
        assert disallowed.get("promote_to_trial_v2_allowlist") is True
        assert disallowed.get("promote_to_production") is True
        assert disallowed.get("create_trae_scheduled_task") is True

    def test_proxy_env_only_environment_variables(self):
        data = yaml.safe_load(CONFIG_PATH.read_text())
        network_modes = data.get("network_modes", {})
        proxy_env = network_modes.get("proxy_env", {})
        assert proxy_env.get("source") == "environment_variables_only"
        assert proxy_env.get("commit_values") is False

    def test_config_no_real_proxy_values(self):
        """Config must only document env var names, not actual proxy URLs."""
        content = CONFIG_PATH.read_text().lower()
        for pattern in (
            "http://127.0.0.1:",
            "http://localhost:",
            "socks5://",
            "192.168.",
            "10.0.",
        ):
            assert pattern not in content, f"Found proxy pattern '{pattern}' in config"


# =============================================================================
# Test 2: Script boundary compliance
# =============================================================================

class TestScriptBoundaries:
    """Validate the proxy retry script follows boundary rules."""

    def test_script_exists(self):
        assert SCRIPT_PATH.exists()

    def test_script_no_playwright_import(self):
        content = SCRIPT_PATH.read_text().lower()
        lines = content.splitlines()
        code_lines = [l for l in lines if not l.strip().startswith("#") and '"""' not in l]
        code_content = "\n".join(code_lines)
        assert "import playwright" not in code_content
        assert "from playwright" not in code_content
        assert "import selenium" not in code_content
        assert "from selenium" not in code_content

    def test_script_does_not_modify_allowlist(self):
        """Script must not write to trial_v2 allowlist configs."""
        content = SCRIPT_PATH.read_text()
        assert "foundation_trial_v2_content_ready_allowlist" not in content
        assert "foundation_trial_v2_allowlist.example.yaml" not in content
        assert "do_not_modify_trial_v2_allowlist" in content.lower() or "does not modify trial_v2 allowlist" in content.lower()

    def test_script_sanitizes_error_messages(self):
        """Script must sanitize error messages to not leak proxy URLs."""
        content = SCRIPT_PATH.read_text()
        assert "_sanitize_error_message" in content

    def test_script_has_proxy_not_configured_mode(self):
        """Script must handle proxy not configured gracefully."""
        content = SCRIPT_PATH.read_text()
        assert "not_configured" in content
        assert "proxy_not_configured" in content

    def test_script_checks_proxy_env(self):
        content = SCRIPT_PATH.read_text()
        assert "check_proxy_env_configured" in content


# =============================================================================
# Test 3: Script CLI behavior
# =============================================================================

class TestScriptCli:
    """Test CLI argument handling and basic execution."""

    def test_script_help_runs(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "--source" in result.stdout
        assert "--mode" in result.stdout
        assert "--all" in result.stdout

    def test_script_rejects_invalid_source(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--source", "invalid_source"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0
        assert "not in M3C-6F" in result.stderr or "ERROR" in result.stderr

    def test_script_accepts_valid_source(self):
        """Test that script accepts valid source (may need network)."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--source", "merck_ir", "--mode", "direct"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )
        assert result.returncode == 0


# =============================================================================
# Test 4: Report security
# =============================================================================

class TestReportSecurity:
    """Validate report doc does not contain sensitive data."""

    @pytest.fixture(scope="class")
    def report_content(self):
        if not REPORT_PATH.exists():
            pytest.skip("report not generated yet")
        return REPORT_PATH.read_text()

    def test_report_no_proxy_urls(self, report_content):
        lower = report_content.lower()
        patterns = (
            "proxy_url=",
            "http_proxy=",
            "https_proxy=",
            "all_proxy=",
        )
        for pat in patterns:
            assert pat not in lower, f"Found sensitive pattern '{pat}' in report"

    def test_report_no_cookie_token(self, report_content):
        lower = report_content.lower()
        patterns = (
            "set-cookie",
            "cookie:",
            "bearer ",
            "api_key=",
            "token=",
            "secret=",
        )
        for pat in patterns:
            assert pat not in lower, f"Found sensitive pattern '{pat}' in report"

    def test_report_no_raw_html(self, report_content):
        assert "<html" not in report_content.lower()
        assert "<script" not in report_content.lower()

    def test_report_mentions_boundary_compliance(self, report_content):
        assert "Does NOT modify trial_v2 allowlist" in report_content
        assert "Does NOT modify TRAE scheduling" in report_content
        assert "Does NOT configure production" in report_content


# =============================================================================
# Test 5: No forbidden modifications
# =============================================================================

class TestNoForbiddenModifications:
    """Validate that trial_v2 allowlist and TRAE scheduling are unchanged."""

    def test_trial_v2_content_ready_allowlist_unchanged(self):
        """trial_v2 content_ready allowlist must still have 9 sources."""
        allowlist_path = REPO_ROOT / "configs/foundation_trial_v2_content_ready_allowlist.example.yaml"
        if not allowlist_path.exists():
            pytest.skip("allowlist config not found")
        data = yaml.safe_load(allowlist_path.read_text())
        sources = data.get("sources", [])
        assert len(sources) == 9

    def test_trae_schedule_unchanged(self):
        """TRAE schedule must still have command_only=true and enabled=false."""
        schedule_path = REPO_ROOT / "configs/trae_foundation_trial_v2_content_ready.example.yaml"
        if not schedule_path.exists():
            pytest.skip("schedule config not found")
        data = yaml.safe_load(schedule_path.read_text())
        scope = data.get("scope", {})
        assert scope.get("command_only", False) is True
        assert scope.get("production_enabled", False) is False
        jobs = data.get("jobs", [])
        for job in jobs:
            assert job.get("enabled", False) is False
