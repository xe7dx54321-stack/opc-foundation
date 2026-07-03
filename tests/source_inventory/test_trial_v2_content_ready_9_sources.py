"""
Tests for M3C-5B1.3 trial_v2 content-ready 9-source expansion.

Covers:
- Formal allowlist has 9 sources
- gelonghui is the 9th source
- Original 8 sources preserved
- merck_ir and goldman_sachs_podcasts excluded
- production_enabled=false
- TRAE scheduling unchanged
"""

import yaml
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALLOWLIST_PATH = REPO_ROOT / "configs" / "foundation_trial_v2_content_ready_allowlist.example.yaml"
TRAE_CONFIG_PATH = REPO_ROOT / "configs" / "trae_foundation_trial_v2_content_ready.example.yaml"
NEXT_CANDIDATE_CONFIG = REPO_ROOT / "configs" / "foundation_trial_v2_next_candidates_preflight.example.yaml"
EXPANSION_CONFIG = REPO_ROOT / "configs" / "foundation_trial_v2_9_source_expansion_candidate.example.yaml"


@pytest.fixture(scope="class")
def allowlist():
    assert ALLOWLIST_PATH.exists()
    return yaml.safe_load(open(ALLOWLIST_PATH))


@pytest.fixture(scope="class")
def trae_config():
    if TRAE_CONFIG_PATH.exists():
        return yaml.safe_load(open(TRAEE_CONFIG_PATH))
    return None


class TestTrialV2ContentReady9Sources:
    """Test the formal trial_v2 content-ready allowlist has 9 sources."""

    def test_allowlist_exists(self):
        assert ALLOWLIST_PATH.exists()

    def test_source_count_is_9(self, allowlist):
        sources = allowlist.get("sources", [])
        assert len(sources) == 9, f"Expected 9 sources, got {len(sources)}"

    def test_expected_source_count_is_9(self, allowlist):
        assert allowlist["scope"]["expected_source_count"] == 9

    def test_all_content_ready(self, allowlist):
        sources = allowlist.get("sources", [])
        assert all(s["content_status"] == "content_ready" for s in sources)

    def test_original_8_sources_preserved(self, allowlist):
        ids = [s["source_id"] for s in allowlist.get("sources", [])]
        expected_8 = {
            "barclays_our_insights", "markets_insider", "china_fund_news",
            "wind_public", "goldman_sachs_insights", "business_insider",
            "cls_cn", "zhitong_caijing",
        }
        assert expected_8.issubset(set(ids)), f"Missing original 8 sources: {expected_8 - set(ids)}"

    def test_gelonghui_is_9th_source(self, allowlist):
        ids = [s["source_id"] for s in allowlist.get("sources", [])]
        assert "gelonghui" in ids

    def test_gelonghui_content_score_100(self, allowlist):
        gel = next((s for s in allowlist.get("sources", []) if s["source_id"] == "gelonghui"), None)
        assert gel is not None
        assert gel["content_score"] == 100

    def test_gelonghui_scheduling_candidate(self, allowlist):
        gel = next((s for s in allowlist.get("sources", []) if s["source_id"] == "gelonghui"), None)
        assert gel is not None
        assert gel["scheduling_candidate"] == True

    def test_merck_ir_not_in_allowlist(self, allowlist):
        ids = [s["source_id"] for s in allowlist.get("sources", [])]
        assert "merck_ir" not in ids

    def test_goldman_sachs_podcasts_not_in_allowlist(self, allowlist):
        ids = [s["source_id"] for s in allowlist.get("sources", [])]
        assert "goldman_sachs_podcasts" not in ids

    def test_no_blocked_sources(self, allowlist):
        blocked = {
            "merck_ir", "benzinga_analyst_ratings", "bofa_global_research",
            "texas_instruments_ir", "briefing_com_upgrades", "wallstreet_cn",
            "goldman_sachs_reports", "goldman_sachs_top_of_mind",
            "goldman_sachs_research", "goldman_sachs_podcasts",
        }
        ids = [s["source_id"] for s in allowlist.get("sources", [])]
        found = set(ids) & blocked
        assert not found, f"Found blocked sources in allowlist: {found}"

    def test_production_enabled_false(self, allowlist):
        assert allowlist["scope"]["production_enabled"] == False

    def test_trae_scheduling_enabled_false(self, allowlist):
        assert allowlist["scope"]["trae_scheduling_enabled"] == False

    def test_command_only_required(self, allowlist):
        assert allowlist["scope"]["command_only_required"] == True


class TestExpansionConfigIsolation:
    """Ensure expansion candidate config does not affect formal allowlist."""

    def test_next_candidate_config_exists(self):
        assert NEXT_CANDIDATE_CONFIG.exists()

    def test_next_candidate_config_scheduling_false(self):
        cfg = yaml.safe_load(open(NEXT_CANDIDATE_CONFIG))
        assert cfg["scope"]["affects_trial_v2_allowlist"] == False

    def test_expansion_config_exists(self):
        assert EXPANSION_CONFIG.exists()

    def test_expansion_config_affects_allowlist_false(self):
        cfg = yaml.safe_load(open(EXPANSION_CONFIG))
        assert cfg["scope"]["affects_current_trial_v2_allowlist"] == False


class Test9SourceRunRecords:
    """Test that the manual run produced 9 records."""

    def test_source_health_has_9_new_records(self):
        idx_dir = REPO_ROOT / "data" / "foundation_trial_v2_content_ready" / "index"
        sh = idx_dir / "source_health.jsonl"
        if not sh.exists():
            pytest.skip("No source_health.jsonl yet")
        lines = sh.read_text().strip().split("\n")
        assert len([l for l in lines if l.strip()]) >= 9, "Expected at least 9 source_health records"

    def test_run_log_has_9_new_records(self):
        idx_dir = REPO_ROOT / "data" / "foundation_trial_v2_content_ready" / "index"
        rl = idx_dir / "run_log.jsonl"
        if not rl.exists():
            pytest.skip("No run_log.jsonl yet")
        lines = rl.read_text().strip().split("\n")
        assert len([l for l in lines if l.strip()]) >= 9, "Expected at least 9 run_log records"

    def test_failed_queue_empty(self):
        idx_dir = REPO_ROOT / "data" / "foundation_trial_v2_content_ready" / "index"
        fq = idx_dir / "failed_queue.jsonl"
        if fq.exists():
            assert fq.stat().st_size == 0, "failed_queue should be empty"
