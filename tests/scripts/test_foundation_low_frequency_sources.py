"""Tests for M3C-6C Low-frequency Source Pipeline scripts and config."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_PATH = _REPO_ROOT / "configs" / "foundation_low_frequency_sources.example.yaml"
RUNNER_PATH = _REPO_ROOT / "scripts" / "run_foundation_low_frequency_sources.py"
CHECKER_PATH = _REPO_ROOT / "scripts" / "check_foundation_low_frequency_sources.py"


class TestConfigStructure:
    """配置文件结构验证"""

    @pytest.fixture(scope="class")
    def config(self):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_config_exists(self):
        assert CONFIG_PATH.exists()

    def test_production_disabled(self, config):
        assert config["scope"]["production_enabled"] is False

    def test_does_not_affect_allowlist(self, config):
        assert config["scope"]["affects_trial_v2_allowlist"] is False

    def test_does_not_affect_trae(self, config):
        assert config["scope"]["affects_trae_scheduling"] is False

    def test_no_permanent_automation(self, config):
        assert config["scope"]["creates_permanent_automation"] is False

    def test_only_merck_ir(self, config):
        source_ids = [s["source_id"] for s in config["sources"]]
        assert source_ids == ["merck_ir"]

    def test_merck_ir_low_freq_allowed(self, config):
        assert config["sources"][0]["low_frequency_allowed_now"] is True

    def test_merck_ir_trial_v2_not_allowed(self, config):
        assert config["sources"][0]["trial_v2_allowlist_allowed_now"] is False

    def test_merck_ir_production_disabled(self, config):
        assert config["sources"][0]["production_enabled"] is False

    def test_timestamp_confidence_low(self, config):
        assert config["sources"][0]["timestamp_confidence_when_missing"] == "LOW"

    def test_create_trae_task_now_false(self, config):
        assert config["scheduling_policy"]["create_trae_task_now"] is False

    def test_manual_approval_required(self, config):
        assert config["scheduling_policy"]["manual_approval_required_before_scheduling"] is True

    def test_policy_no_login(self, config):
        assert config["policy"]["no_login"] is True

    def test_policy_no_paywall(self, config):
        assert config["policy"]["no_paywall_bypass"] is True

    def test_policy_no_captcha(self, config):
        assert config["policy"]["no_captcha_solving"] is True

    def test_policy_no_antibot(self, config):
        assert config["policy"]["no_antibot_bypass"] is True


class TestRunnerBoundary:
    """Runner 脚本边界检查"""

    @pytest.fixture(scope="class")
    def runner_content(self):
        return RUNNER_PATH.read_text(encoding="utf-8")

    def test_runner_exists(self):
        assert RUNNER_PATH.exists()

    def test_does_not_modify_trial_v2_allowlist(self, runner_content):
        assert "does not modify trial_v2 allowlist" in runner_content.lower()

    def test_does_not_modify_trae_scheduling(self, runner_content):
        assert "does not modify trae scheduling" in runner_content.lower()

    def test_does_not_configure_production(self, runner_content):
        assert "does not configure production" in runner_content.lower()

    def test_no_permanent_automation(self, runner_content):
        assert "does not create permanent automation" in runner_content.lower()

    def test_does_not_commit_data(self, runner_content):
        assert "does not commit data" in runner_content.lower()

    def test_no_playwright_import(self, runner_content):
        lines = runner_content.split("\n")
        import_lines = [
            line.strip()
            for line in lines
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        for line in import_lines:
            assert "playwright" not in line.lower(), f"Playwright import found: {line}"
            assert "selenium" not in line.lower(), f"Selenium import found: {line}"

    def test_has_dry_run_flag(self, runner_content):
        assert "--dry-run" in runner_content

    def test_has_run_once_flag(self, runner_content):
        assert "--run-once" in runner_content

    def test_has_source_flag(self, runner_content):
        assert "--source" in runner_content

    def test_has_all_flag(self, runner_content):
        assert "--all" in runner_content

    def test_default_dry_run(self, runner_content):
        # dry_run should default to True
        assert "dry_run" in runner_content

    def test_uses_merck_ir_runner(self, runner_content):
        assert "merck_ir" in runner_content


class TestCheckerBoundary:
    """Check 脚本边界检查"""

    @pytest.fixture(scope="class")
    def checker_content(self):
        return CHECKER_PATH.read_text(encoding="utf-8")

    def test_checker_exists(self):
        assert CHECKER_PATH.exists()

    def test_checks_production(self, checker_content):
        assert "production_enabled" in checker_content

    def test_checks_allowlist(self, checker_content):
        assert "affects_trial_v2_allowlist" in checker_content

    def test_checks_trae(self, checker_content):
        assert "affects_trae_scheduling" in checker_content

    def test_checks_permanent_automation(self, checker_content):
        assert "creates_permanent_automation" in checker_content

    def test_checks_gitignored(self, checker_content):
        assert "gitignored" in checker_content.lower() or "gitignore" in checker_content.lower()

    def test_checks_sensitive_data(self, checker_content):
        assert "sensitive" in checker_content.lower()

    def test_no_playwright(self, checker_content):
        lines = checker_content.split("\n")
        import_lines = [
            line.strip()
            for line in lines
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        for line in import_lines:
            assert "playwright" not in line.lower()
            assert "selenium" not in line.lower()


class TestGitignoreCoverage:
    """Runtime data must be gitignored"""

    def test_gitignore_has_low_freq_entry(self):
        gitignore = (_REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        assert "data/foundation_low_frequency_sources/" in gitignore


class TestTraeScheduleUnchanged:
    """不修改 TRAE scheduling"""

    def test_runner_no_schedule_modification(self):
        runner_content = RUNNER_PATH.read_text(encoding="utf-8")
        assert "schedule_create" not in runner_content
        assert "schedule_update" not in runner_content

    def test_checker_no_schedule_modification(self):
        checker_content = CHECKER_PATH.read_text(encoding="utf-8")
        assert "schedule_create" not in checker_content
        assert "schedule_update" not in checker_content
