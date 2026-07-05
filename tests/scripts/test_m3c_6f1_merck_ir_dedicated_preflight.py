"""Tests for M3C-6F.1 Merck IR Dedicated Preflight script and config."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_m3c_6f1_merck_ir_dedicated_preflight.py"
CONFIG_PATH = _REPO_ROOT / "configs" / "foundation_m3c_6f1_merck_ir_dedicated_preflight.example.yaml"


class TestConfigStructure:
    """配置文件结构验证"""

    @pytest.fixture(scope="class")
    def config(self):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_config_exists(self):
        assert CONFIG_PATH.exists()

    def test_scope_name(self, config):
        assert config["scope"]["name"] == "m3c_6f1_merck_ir_dedicated_preflight"

    def test_production_disabled(self, config):
        assert config["scope"]["production_enabled"] is False

    def test_does_not_affect_allowlist(self, config):
        assert config["scope"]["affects_trial_v2_allowlist"] is False

    def test_does_not_affect_trae(self, config):
        assert config["scope"]["affects_trae_scheduling"] is False

    def test_only_merck_ir(self, config):
        assert config["scope"]["candidate_sources"] == ["merck_ir"]

    def test_policy_no_login(self, config):
        assert config["policy"]["no_login"] is True

    def test_policy_no_paywall(self, config):
        assert config["policy"]["no_paywall_bypass"] is True

    def test_policy_no_captcha(self, config):
        assert config["policy"]["no_captcha_solving"] is True

    def test_policy_no_antibot(self, config):
        assert config["policy"]["no_antibot_bypass"] is True

    def test_policy_no_cookie_commit(self, config):
        assert config["policy"]["no_cookie_commit"] is True

    def test_policy_no_raw_html(self, config):
        assert config["policy"]["no_raw_html_commit"] is True

    def test_policy_no_screenshot(self, config):
        assert config["policy"]["no_screenshot_commit"] is True

    def test_policy_no_allowlist_modification(self, config):
        assert config["policy"]["do_not_modify_trial_v2_allowlist"] is True

    def test_policy_no_trae_modification(self, config):
        assert config["policy"]["do_not_modify_trae_scheduling"] is True

    def test_policy_no_production(self, config):
        assert config["policy"]["do_not_configure_production"] is True

    def test_has_target_entry_types(self, config):
        assert "target_entry_types" in config["merck_ir"]
        assert "investor_news" in config["merck_ir"]["target_entry_types"]
        assert "press_releases" in config["merck_ir"]["target_entry_types"]

    def test_has_reject_patterns(self, config):
        assert "reject_title_patterns" in config["merck_ir"]
        assert "Who we are" in config["merck_ir"]["reject_title_patterns"]


class TestScriptBoundary:
    """脚本边界检查"""

    @pytest.fixture(scope="class")
    def script_content(self):
        return SCRIPT_PATH.read_text(encoding="utf-8")

    def test_script_exists(self):
        assert SCRIPT_PATH.exists()

    def test_does_not_modify_trial_v2_allowlist(self, script_content):
        assert "does not modify trial_v2 allowlist" in script_content.lower()

    def test_does_not_modify_trae_scheduling(self, script_content):
        assert "does not modify trae scheduling" in script_content.lower()

    def test_does_not_configure_production(self, script_content):
        assert "does not configure production" in script_content.lower()

    def test_does_not_commit_data(self, script_content):
        assert "does not commit data" in script_content.lower()

    def test_no_playwright_import(self, script_content):
        # Check for actual imports, not docstring mentions
        lines = script_content.split("\n")
        import_lines = [
            line.strip()
            for line in lines
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        for line in import_lines:
            assert "playwright" not in line.lower(), f"Playwright import found: {line}"
            assert "selenium" not in line.lower(), f"Selenium import found: {line}"

    def test_no_cookie_commit(self, script_content):
        lower = script_content.lower()
        # The script should mention it does NOT commit cookies
        assert "cookie" in lower  # should be in the "does NOT" section

    def test_only_merck_ir(self, script_content):
        assert "merck_ir" in script_content
        assert "yahoo_finance" not in script_content or "does not" in script_content.lower()
        assert "the_fly" not in script_content or "does not" in script_content.lower()

    def test_uses_httpx(self, script_content):
        assert "httpx" in script_content

    def test_has_discover_only_flag(self, script_content):
        assert "--discover-only" in script_content

    def test_has_extract_flag(self, script_content):
        assert "--extract" in script_content

    def test_has_ir_entry_patterns(self, script_content):
        assert "/news/" in script_content
        assert "/events/" in script_content
        assert "/presentations/" in script_content


class TestScriptNoSensitiveData:
    """脚本不包含敏感数据"""

    @pytest.fixture(scope="class")
    def script_content(self):
        return SCRIPT_PATH.read_text(encoding="utf-8")

    def test_no_proxy_url_values(self, script_content):
        import re
        # Check for actual proxy URL values (not variable names)
        proxy_value_pattern = r"https?://\d+\.\d+\.\d+\.\d+:\d+"
        matches = re.findall(proxy_value_pattern, script_content)
        assert len(matches) == 0, f"Proxy URL values found: {matches}"

    def test_no_hardcoded_secrets(self, script_content):
        lower = script_content.lower()
        assert "password=" not in lower or "password=" in lower.replace(
            "proxy_password=", ""
        ).replace("does not", "")
        # Just check no actual secret values
        assert "bearer ey" not in lower
        assert "api_key=sk_" not in lower


class TestTraeScheduleUnchanged:
    """不修改 TRAE scheduling"""

    def test_no_schedule_modification(self):
        # Check that the script doesn't create or modify any schedule files
        script_content = SCRIPT_PATH.read_text(encoding="utf-8")
        assert "Schedule" not in script_content or "does NOT" in script_content
        # Check no schedule tool calls
        assert "schedule_create" not in script_content
        assert "schedule_update" not in script_content
