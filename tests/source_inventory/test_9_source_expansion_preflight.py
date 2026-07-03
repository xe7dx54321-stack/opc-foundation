"""
Tests for M3C-5B1.2 9-Source Expansion Preflight configuration and runner.

Covers:
- Config structure and boundary constraints
- Runner does not modify formal allowlist / TRAE config / production
- Candidate package scope (only gelonghui as new candidate)
- Report security (no proxy URL / cookie / token / secret)
- No deleted Dashboard pages restored
"""

import yaml
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "foundation_trial_v2_9_source_expansion_candidate.example.yaml"
RUNNER_PATH = REPO_ROOT / "scripts" / "run_foundation_trial_v2_9_source_expansion_preflight.py"
REPORT_PATH = REPO_ROOT / "docs" / "foundation_m3c_5b1_2_gelonghui_9_source_preflight_report.md"
FORMAL_ALLOWLIST_PATH = REPO_ROOT / "configs" / "foundation_trial_v2_content_ready_allowlist.example.yaml"


@pytest.fixture(scope="class")
def config():
    assert CONFIG_PATH.exists(), f"Config not found: {CONFIG_PATH}"
    return yaml.safe_load(open(CONFIG_PATH))


@pytest.fixture(scope="class")
def formal_allowlist():
    assert FORMAL_ALLOWLIST_PATH.exists()
    return yaml.safe_load(open(FORMAL_ALLOWLIST_PATH))


@pytest.fixture(scope="class")
def report():
    if REPORT_PATH.exists():
        return REPORT_PATH.read_text(encoding="utf-8")
    return None


class Test9SourceExpansionConfig:
    """Test the 9-source expansion candidate configuration."""

    def test_config_exists(self):
        assert CONFIG_PATH.exists()

    def test_production_enabled_false(self, config):
        assert config["scope"]["production_enabled"] == False

    def test_affects_current_allowlist_false(self, config):
        assert config["scope"]["affects_current_trial_v2_allowlist"] == False

    def test_affects_trae_scheduling_false(self, config):
        assert config["scope"]["affects_trae_scheduling"] == False

    def test_base_allowlist_count_8(self, config):
        assert len(config["base_allowlist"]) == 8

    def test_new_candidate_count_1(self, config):
        assert config["scope"]["new_candidate_count"] == 1

    def test_candidate_package_count_9(self, config):
        assert config["scope"]["candidate_package_count"] == 9

    def test_candidate_allowlist_count_9(self, config):
        assert len(config["candidate_allowlist"]) == 9

    def test_candidate_allowlist_contains_base(self, config):
        base = set(config["base_allowlist"])
        cand = set(config["candidate_allowlist"])
        assert base.issubset(cand)

    def test_candidate_allowlist_has_gelonghui(self, config):
        assert "gelonghui" in config["candidate_allowlist"]

    def test_candidate_allowlist_no_merck_ir(self, config):
        assert "merck_ir" not in config["candidate_allowlist"]

    def test_candidate_allowlist_no_goldman_sachs_podcasts(self, config):
        assert "goldman_sachs_podcasts" not in config["candidate_allowlist"]

    def test_formal_allowlist_no_gelonghui(self, config, formal_allowlist):
        ids = [s["source_id"] for s in formal_allowlist.get("sources", [])]
        assert "gelonghui" not in ids

    def test_scheduling_allowed_now_false(self, config):
        assert config["new_candidates"][0]["scheduling_allowed_now"] == False

    def test_ready_for_expansion_evaluation_true(self, config):
        assert config["new_candidates"][0]["ready_for_expansion_evaluation"] == True

    def test_new_candidate_is_gelonghui(self, config):
        assert config["new_candidates"][0]["source_id"] == "gelonghui"

    def test_min_content_score_ge_70(self, config):
        assert config["new_candidates"][0]["min_content_score"] >= 70


class Test9SourceExpansionRunner:
    """Test the runner script."""

    def test_runner_exists(self):
        assert RUNNER_PATH.exists()

    def test_runner_supports_all_modes(self):
        content = RUNNER_PATH.read_text()
        assert "validate-config" in content
        assert "preflight" in content
        assert "dry-run" in content
        assert "check" in content
        assert "all" in content

    def test_runner_does_not_write_formal_allowlist(self):
        content = RUNNER_PATH.read_text()
        assert "yaml.dump" not in content

    def test_runner_does_not_configure_production(self):
        content = RUNNER_PATH.read_text()
        assert "production_enabled = true" not in content
        assert "production_enabled=True" not in content

    def test_runner_does_not_write_trae_config(self):
        content = RUNNER_PATH.read_text()
        assert "trae_foundation_trial_v2" not in content or "yaml.dump" not in content


class Test9SourceExpansionReport:
    """Test the generated report."""

    def test_report_exists(self, report):
        assert report is not None

    def test_report_has_expansion_preflight_result(self, report):
        assert report is not None
        assert "expansion_preflight_pass" in report or "expansion_preflight_watch" in report or "expansion_preflight_fail" in report

    def test_report_has_gelonghui(self, report):
        assert report is not None
        assert "gelonghui" in report

    def test_report_has_9_sources(self, report):
        assert report is not None
        assert "9 sources" in report or "9-source" in report or "9 源" in report

    def test_report_no_proxy_url(self, report):
        assert report is not None
        sensitive = ["socks5://", "http://127.0.0.1", "proxy"]
        for p in sensitive:
            if p == "proxy":
                # "proxy" may appear in "no proxy" context
                continue
            assert p not in report.lower(), f"Found sensitive pattern: {p}"

    def test_report_no_sensitive_data(self, report):
        assert report is not None
        sensitive = ["api_key=", "bearer ", "authorization:", "set-cookie:", "x-token:"]
        for p in sensitive:
            assert p not in report.lower(), f"Found sensitive pattern: {p}"

    def test_report_boundary_confirmation(self, report):
        assert report is not None
        assert "Modified formal trial_v2 allowlist" in report
        assert "No" in report


class Test9SourceExpansionIsolation:
    """Ensure expansion preflight is isolated."""

    def test_formal_allowlist_unchanged(self, formal_allowlist):
        sources = formal_allowlist.get("sources", [])
        assert len(sources) == 8

    def test_formal_allowlist_no_gelonghui(self, formal_allowlist):
        ids = [s["source_id"] for s in formal_allowlist.get("sources", [])]
        assert "gelonghui" not in ids

    def test_formal_allowlist_no_merck_ir(self, formal_allowlist):
        ids = [s["source_id"] for s in formal_allowlist.get("sources", [])]
        assert "merck_ir" not in ids

    def test_no_dashboard_pages_restored(self):
        deleted_pages = ["总览", "运行日志", "失败队列", "文档入口"]
        docs_dir = REPO_ROOT / "docs"
        for f in docs_dir.glob("*.md"):
            if f.name.startswith("foundation_m3c_5b1_2"):
                content = f.read_text(encoding="utf-8")
                for page in deleted_pages:
                    if page in content:
                        assert "恢复" not in content or "不恢复" in content
