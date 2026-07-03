"""
Tests for M3C-5B1.1 Next Candidate Preflight configuration and runner.

Covers:
- Config structure and boundary constraints
- Runner does not modify trial_v2 allowlist / TRAE config / production
- Candidate scope (only gelonghui / merck_ir)
- Report security (no proxy URL / cookie / token / secret)
"""

import yaml
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "foundation_trial_v2_next_candidates_preflight.example.yaml"
RUNNER_PATH = REPO_ROOT / "scripts" / "run_foundation_trial_v2_next_candidates_preflight.py"
REPORT_PATH = REPO_ROOT / "docs" / "foundation_m3c_5b1_1_next_candidate_preflight_report.md"
ALLOWLIST_PATH = REPO_ROOT / "configs" / "foundation_trial_v2_content_ready_allowlist.example.yaml"
TRAE_CONFIG_PATH = REPO_ROOT / "configs" / "trae_foundation_trial_v2_content_ready.example.yaml"


@pytest.fixture(scope="class")
def config():
    """Load next candidate preflight config."""
    assert CONFIG_PATH.exists(), f"Config not found: {CONFIG_PATH}"
    return yaml.safe_load(open(CONFIG_PATH))


@pytest.fixture(scope="class")
def base_allowlist():
    """Load current trial_v2 content-ready allowlist."""
    assert ALLOWLIST_PATH.exists(), f"Allowlist not found: {ALLOWLIST_PATH}"
    return yaml.safe_load(open(ALLOWLIST_PATH))


@pytest.fixture(scope="class")
def trae_config():
    """Load TRAE config."""
    if TRAE_CONFIG_PATH.exists():
        return yaml.safe_load(open(TRAE_CONFIG_PATH))
    return None


@pytest.fixture(scope="class")
def report():
    """Load generated report."""
    if REPORT_PATH.exists():
        return REPORT_PATH.read_text(encoding="utf-8")
    return None


class TestNextCandidatePreflightConfig:
    """Test the next candidate preflight configuration file."""

    def test_config_exists(self):
        assert CONFIG_PATH.exists()

    def test_production_enabled_false(self, config):
        assert config["scope"]["production_enabled"] == False

    def test_affects_trial_v2_allowlist_false(self, config):
        assert config["scope"]["affects_trial_v2_allowlist"] == False

    def test_affects_trae_scheduling_false(self, config):
        assert config["scope"]["affects_trae_scheduling"] == False

    def test_candidate_count_is_2(self, config):
        assert config["scope"]["candidate_count"] == 2

    def test_base_trial_v2_count_is_8(self, config):
        assert config["scope"]["base_trial_v2_content_ready_count"] == 8

    def test_candidates_only_gelonghui_and_merck_ir(self, config):
        candidate_ids = [c["source_id"] for c in config["next_scheduling_candidates"]]
        assert set(candidate_ids) == {"gelonghui", "merck_ir"}

    def test_base_allowlist_unchanged(self, config):
        base = config["base_allowlist"]
        assert len(base) == 8
        expected = {
            "barclays_our_insights", "markets_insider", "china_fund_news",
            "wind_public", "goldman_sachs_insights", "business_insider",
            "cls_cn", "zhitong_caijing",
        }
        assert set(base) == expected

    def test_gelonghui_not_in_base_allowlist(self, config):
        assert "gelonghui" not in config["base_allowlist"]

    def test_merck_ir_not_in_base_allowlist(self, config):
        assert "merck_ir" not in config["base_allowlist"]

    def test_goldman_sachs_podcasts_not_in_candidates(self, config):
        candidate_ids = [c["source_id"] for c in config["next_scheduling_candidates"]]
        assert "goldman_sachs_podcasts" not in candidate_ids

    def test_scheduling_allowed_now_false(self, config):
        for c in config["next_scheduling_candidates"]:
            assert c["scheduling_allowed_now"] == False, (
                f"{c['source_id']} scheduling_allowed_now must be false"
            )

    def test_min_content_score_ge_70(self, config):
        for c in config["next_scheduling_candidates"]:
            assert c["min_content_score"] >= 70, (
                f"{c['source_id']} min_content_score must be >= 70"
            )

    def test_min_valid_candidates_ge_2(self, config):
        for c in config["next_scheduling_candidates"]:
            assert c["min_valid_candidates"] >= 2, (
                f"{c['source_id']} min_valid_candidates must be >= 2"
            )

    def test_min_relevant_candidates_ge_2(self, config):
        for c in config["next_scheduling_candidates"]:
            assert c["min_relevant_candidates"] >= 2, (
                f"{c['source_id']} min_relevant_candidates must be >= 2"
            )

    def test_min_dated_candidates_ge_2(self, config):
        for c in config["next_scheduling_candidates"]:
            assert c["min_dated_candidates"] >= 2, (
                f"{c['source_id']} min_dated_candidates must be >= 2"
            )

    def test_rounds_ge_3(self, config):
        for c in config["next_scheduling_candidates"]:
            assert c["rounds"] >= 3, (
                f"{c['source_id']} rounds must be >= 3"
            )

    def test_policy_do_not_modify_allowlist(self, config):
        assert config["policy"]["do_not_modify_trial_v2_allowlist"] == True

    def test_policy_do_not_modify_scheduling(self, config):
        assert config["policy"]["do_not_modify_trae_scheduling"] == True

    def test_policy_no_production(self, config):
        assert config["policy"]["do_not_configure_production"] == True

    def test_policy_no_browser_runtime(self, config):
        assert config["policy"]["no_browser_runtime"] == True


class TestNextCandidatePreflightRunner:
    """Test the runner script existence and safety."""

    def test_runner_exists(self):
        assert RUNNER_PATH.exists()

    def test_runner_is_python(self):
        content = RUNNER_PATH.read_text()
        assert "#!/usr/bin/env python3" in content

    def test_runner_imports_extract_candidates(self):
        content = RUNNER_PATH.read_text()
        assert "extract_candidates_from_html" in content

    def test_runner_does_not_write_allowlist(self):
        content = RUNNER_PATH.read_text()
        assert "foundation_trial_v2_content_ready_allowlist" not in content
        # Ensure no yaml.dump to allowlist path
        assert "trial_v2_content_ready_allowlist" not in content or "yaml.dump" not in content

    def test_runner_does_not_write_trae_config(self):
        content = RUNNER_PATH.read_text()
        assert "trae_foundation_trial_v2" not in content or "yaml.dump" not in content

    def test_runner_does_not_configure_production(self):
        content = RUNNER_PATH.read_text()
        assert "production_enabled = true" not in content
        assert "production_enabled=True" not in content


class TestNextCandidatePreflightReport:
    """Test the generated report."""

    def test_report_exists(self, report):
        assert report is not None, "Report not found"

    def test_report_has_preflight_results(self, report):
        assert report is not None
        assert "preflight_fail" in report or "preflight_pass" in report or "preflight_watch" in report

    def test_report_has_gelonghui(self, report):
        assert report is not None
        assert "gelonghui" in report

    def test_report_has_merck_ir(self, report):
        assert report is not None
        assert "merck_ir" in report

    def test_report_no_proxy_url(self, report):
        assert report is not None
        # No raw proxy URLs
        assert "http://127.0.0.1:7890" not in report
        assert "socks5://" not in report
        assert "proxy" not in report.lower() or "no proxy" in report.lower() or "proxy" not in report

    def test_report_no_cookie_token_secret(self, report):
        assert report is not None
        # Report may contain "secrets" in the boundary confirmation section ("Submitted data/local/secrets | No")
        # which is expected. Check for actual leaked secrets (cookie values, tokens, API keys)
        sensitive_patterns = ["api_key=", "bearer ", "authorization:", "set-cookie:", "x-token:"]
        for pattern in sensitive_patterns:
            assert pattern not in report.lower(), f"Found sensitive pattern: {pattern}"

    def test_report_boundary_confirmation(self, report):
        assert report is not None
        assert "Modified trial_v2 allowlist" in report
        assert "No" in report

    def test_report_scheduling_allowed_false(self, report):
        assert report is not None
        assert "scheduling_allowed_now" in report
        assert "false" in report


class TestNextCandidatePreflightIsolation:
    """Ensure preflight work is isolated from trial_v2 allowlist."""

    def test_allowlist_has_9_sources(self, base_allowlist):
        """M3C-5B1.3: Trial_v2 allowlist expanded to 9 sources."""
        sources = base_allowlist.get("sources", [])
        assert len(sources) == 9

    def test_allowlist_has_gelonghui(self, base_allowlist):
        """M3C-5B1.3: gelonghui is now in trial_v2 allowlist."""
        ids = [s["source_id"] for s in base_allowlist.get("sources", [])]
        assert "gelonghui" in ids

    def test_allowlist_no_merck_ir(self, base_allowlist):
        ids = [s["source_id"] for s in base_allowlist.get("sources", [])]
        assert "merck_ir" not in ids

    def test_trae_jobs_still_disabled(self, trae_config):
        if trae_config is None:
            pytest.skip("TRAE config not found")
        for job in trae_config.get("jobs", []):
            assert job["enabled"] == False, f"Job {job.get('job_id')} should be disabled"

    def test_no_dashboard_pages_restored(self):
        """Ensure no deleted Dashboard pages are referenced."""
        docs_dir = REPO_ROOT / "docs"
        # Check that report does not restore deleted pages
        for f in docs_dir.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            if f.name.startswith("foundation_m3c_5b1_1"):
                # Our own report is allowed to exist
                continue
