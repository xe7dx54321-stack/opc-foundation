"""Tests for M3C-6C Low-frequency Source Pipeline data model."""

from __future__ import annotations

import pytest

from opc_foundation.source_inventory.low_frequency_sources import (
    LOW_FREQ_ALLOWED_SOURCES,
    LOW_FREQ_FINAL_DECISIONS,
    LOW_FREQ_REJECT_TITLE_PATTERNS,
    MAX_SAMPLE_ITEMS_RECORDED,
    MIN_VALID_ITEMS_FOR_LOW_FREQ,
    SENSITIVE_KEYWORDS,
    LowFrequencyDecision,
    LowFrequencyItem,
    LowFrequencyRunResult,
    LowFrequencySchedulingProposal,
    LowFrequencySourceConfig,
    apply_low_frequency_decision,
    compute_low_frequency_decision,
    is_low_frequency_allowed_source,
    is_rejected_navigation_title,
    make_default_low_frequency_result,
    make_default_scheduling_proposal,
    now_iso,
    scan_sensitive_keywords,
    validate_low_frequency_run_result,
)


class TestAllowedSources:
    """当前 low-frequency config 只允许 merck_ir"""

    def test_merck_ir_in_allowed(self):
        assert "merck_ir" in LOW_FREQ_ALLOWED_SOURCES

    def test_yahoo_finance_not_allowed(self):
        assert "yahoo_finance" not in LOW_FREQ_ALLOWED_SOURCES

    def test_the_fly_not_allowed(self):
        assert "the_fly" not in LOW_FREQ_ALLOWED_SOURCES

    def test_is_low_frequency_allowed_source_true(self):
        assert is_low_frequency_allowed_source("merck_ir") is True

    def test_is_low_frequency_allowed_source_false(self):
        assert is_low_frequency_allowed_source("yahoo_finance") is False

    def test_default_result_source_id(self):
        result = make_default_low_frequency_result()
        assert result.source_id == "merck_ir"

    def test_non_allowed_source_rejected(self):
        result = make_default_low_frequency_result("yahoo_finance")
        errors = validate_low_frequency_run_result(result)
        assert any("not in allowed" in e for e in errors)


class TestAllowlistFlags:
    """trial_v2_allowlist_allowed_now=false, low_frequency_allowed_now=true"""

    def test_default_trial_v2_false(self):
        result = make_default_low_frequency_result()
        assert result.trial_v2_allowlist_allowed_now is False

    def test_default_low_freq_true(self):
        result = make_default_low_frequency_result()
        assert result.low_frequency_allowed_now is True

    def test_default_production_false(self):
        result = make_default_low_frequency_result()
        assert result.production_enabled is False

    def test_validation_rejects_trial_v2_true(self):
        result = make_default_low_frequency_result()
        result.trial_v2_allowlist_allowed_now = True
        errors = validate_low_frequency_run_result(result)
        assert any("must be False" in e for e in errors)

    def test_validation_rejects_production_true(self):
        result = make_default_low_frequency_result()
        result.production_enabled = True
        errors = validate_low_frequency_run_result(result)
        assert any("production_enabled" in e for e in errors)


class TestTimestampConfidence:
    """date_text 缺失时 timestamp_confidence=LOW"""

    def test_dated_zero_has_low_confidence(self):
        result = make_default_low_frequency_result()
        result.valid_item_count = 5
        result.dated_item_count = 0
        result.timestamp_confidence_distribution = {
            "HIGH": 0, "MEDIUM": 0, "LOW": 5, "NONE": 0
        }
        apply_low_frequency_decision(result)
        assert result.recommended_frequency == "weekly"

    def test_dated_zero_without_low_fails(self):
        result = make_default_low_frequency_result()
        result.valid_item_count = 5
        result.dated_item_count = 0
        result.timestamp_confidence_distribution = {
            "HIGH": 5, "MEDIUM": 0, "LOW": 0, "NONE": 0
        }
        errors = validate_low_frequency_run_result(result)
        assert any("no LOW/NONE" in e for e in errors)

    def test_dated_two_has_daily(self):
        result = make_default_low_frequency_result()
        result.valid_item_count = 5
        result.dated_item_count = 2
        result.timestamp_confidence_distribution = {
            "HIGH": 0, "MEDIUM": 2, "LOW": 3, "NONE": 0
        }
        apply_low_frequency_decision(result)
        assert result.recommended_frequency == "daily"


class TestValidItemCount:
    """valid_item_count >= 3 可以 low_frequency"""

    def test_sufficient_items(self):
        result = make_default_low_frequency_result()
        result.valid_item_count = 3
        result.dated_item_count = 0
        result.timestamp_confidence_distribution = {
            "HIGH": 0, "MEDIUM": 0, "LOW": 3, "NONE": 0
        }
        apply_low_frequency_decision(result)
        assert result.low_frequency_allowed_now is True

    def test_insufficient_items_fails(self):
        result = make_default_low_frequency_result()
        result.valid_item_count = 2
        result.dated_item_count = 0
        result.timestamp_confidence_distribution = {
            "HIGH": 0, "MEDIUM": 0, "LOW": 2, "NONE": 0
        }
        apply_low_frequency_decision(result)
        assert result.low_frequency_allowed_now is False
        assert result.recommended_frequency == "manual_review"


class TestDatedItemsHighFreq:
    """dated_item_count=0 不得 high-frequency scheduled"""

    def test_dated_zero_not_high_freq(self):
        result = make_default_low_frequency_result()
        result.valid_item_count = 5
        result.dated_item_count = 0
        result.timestamp_confidence_distribution = {
            "HIGH": 0, "MEDIUM": 0, "LOW": 5, "NONE": 0
        }
        apply_low_frequency_decision(result)
        assert result.recommended_frequency != "daily"
        assert result.trial_v2_allowlist_allowed_now is False


class TestNavigationReject:
    """navigation items 必须 reject"""

    @pytest.mark.parametrize("title", list(LOW_FREQ_REJECT_TITLE_PATTERNS))
    def test_reject_patterns(self, title):
        assert is_rejected_navigation_title(title) is True

    def test_reject_who_we_are(self):
        assert is_rejected_navigation_title("Who we are") is True

    def test_accept_real_ir_title(self):
        assert is_rejected_navigation_title("Q3 2026 Earnings Call") is False

    def test_reject_empty(self):
        assert is_rejected_navigation_title("") is True

    def test_navigation_item_must_not_be_valid(self):
        result = make_default_low_frequency_result()
        result.valid_item_count = 5
        result.dated_item_count = 0
        result.timestamp_confidence_distribution = {
            "HIGH": 0, "MEDIUM": 0, "LOW": 5, "NONE": 0
        }
        result.sample_items = [
            LowFrequencyItem(
                title="Who we are",
                url="https://example.com",
                is_navigation=True,
                is_valid_item=True,  # this is an error
            ),
        ]
        errors = validate_low_frequency_run_result(result)
        assert any("is navigation but is_valid_item" in e for e in errors)


class TestSensitiveKeywords:
    """report 不包含 cookie / token / proxy URL / secret"""

    def test_scan_finds_proxy_url(self):
        found = scan_sensitive_keywords("http_proxy=http://1.2.3.4:8080")
        assert len(found) > 0

    def test_scan_finds_cookie(self):
        found = scan_sensitive_keywords("cookie: session=abc")
        assert len(found) > 0

    def test_scan_clean_text(self):
        found = scan_sensitive_keywords("Q3 2026 Earnings Call")
        assert len(found) == 0

    def test_validation_rejects_sensitive_in_notes(self):
        result = make_default_low_frequency_result()
        result.notes = "http_proxy=http://1.2.3.4:8080"
        errors = validate_low_frequency_run_result(result)
        assert any("sensitive" in e.lower() for e in errors)

    def test_validation_rejects_sensitive_in_sample(self):
        result = make_default_low_frequency_result()
        result.sample_items = [
            LowFrequencyItem(title="cookie: secret", url="https://example.com"),
        ]
        errors = validate_low_frequency_run_result(result)
        assert any("sensitive" in e.lower() for e in errors)


class TestSampleItemsLimit:
    """sample_items 不超过 5"""

    def test_too_many_samples_rejected(self):
        result = make_default_low_frequency_result()
        result.sample_items = [
            LowFrequencyItem(title=f"Item {i}", url=f"https://example.com/{i}")
            for i in range(MAX_SAMPLE_ITEMS_RECORDED + 1)
        ]
        errors = validate_low_frequency_run_result(result)
        assert any("exceeds max" in e for e in errors)


class TestSchedulingProposal:
    """TRAE scheduling proposal 不创建真实任务"""

    def test_default_proposal_no_task(self):
        proposal = make_default_scheduling_proposal()
        assert proposal.create_trae_task_now is False
        assert proposal.manual_approval_required is True
        assert proposal.production_enabled is False
        assert proposal.affects_trial_v2_allowlist is False
        assert proposal.affects_trae_scheduling is False

    def test_proposal_has_command(self):
        proposal = make_default_scheduling_proposal("merck_ir")
        assert "run_foundation_low_frequency_sources" in proposal.proposed_command
        assert "merck_ir" in proposal.proposed_command


class TestToDict:
    """to_dict 方法"""

    def test_to_dict_has_required_fields(self):
        result = make_default_low_frequency_result()
        d = result.to_dict()
        for key in (
            "source_id", "run_mode", "valid_item_count", "dated_item_count",
            "missing_date_count", "timestamp_confidence_distribution",
            "sample_items", "recommended_frequency",
            "low_frequency_allowed_now", "trial_v2_allowlist_allowed_now",
            "production_enabled", "next_action", "risk_flags", "notes",
        ):
            assert key in d


class TestNowIso:
    """now_iso returns valid ISO string"""

    def test_now_iso_format(self):
        ts = now_iso()
        assert "T" in ts
        assert ts.endswith("Z")
