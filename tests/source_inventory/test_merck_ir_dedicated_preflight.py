"""Tests for M3C-6F.1 Merck IR Dedicated Extraction Preflight data model."""

from __future__ import annotations

import pytest

from opc_foundation.source_inventory.merck_ir_dedicated_preflight import (
    M3C_6F1_ALLOWED_SOURCE,
    MERCK_IR_FINAL_DECISIONS,
    MIN_DATED_ITEMS_FOR_SCHEDULED,
    MIN_VALID_ITEMS_FOR_SCHEDULED,
    REJECT_TITLE_PATTERNS,
    SENSITIVE_KEYWORDS,
    MerckIrCandidateUrl,
    MerckIrDedicatedDecision,
    MerckIrDedicatedPreflightResult,
    MerckIrExtractionItem,
    apply_merck_ir_decision,
    compute_merck_ir_decision,
    is_merck_ir_source,
    is_rejected_navigation_title,
    make_default_merck_ir_result,
    make_batch_report_dict,
    scan_sensitive_keywords,
    validate_merck_ir_preflight_result,
)


class TestSourceIdFixed:
    """source_id 固定为 merck_ir"""

    def test_allowed_source_is_merck_ir(self):
        assert M3C_6F1_ALLOWED_SOURCE == "merck_ir"

    def test_is_merck_ir_source_true(self):
        assert is_merck_ir_source("merck_ir") is True

    def test_is_merck_ir_source_false(self):
        assert is_merck_ir_source("yahoo_finance") is False
        assert is_merck_ir_source("the_fly") is False
        assert is_merck_ir_source("") is False

    def test_default_result_source_id(self):
        result = make_default_merck_ir_result()
        assert result.source_id == "merck_ir"

    def test_non_merck_ir_rejected(self):
        result = make_default_merck_ir_result()
        result.source_id = "yahoo_finance"
        errors = validate_merck_ir_preflight_result(result)
        assert any("must be 'merck_ir'" in e for e in errors)


class TestNavigationReject:
    """导航标题必须被 reject"""

    @pytest.mark.parametrize("title", [p for p in REJECT_TITLE_PATTERNS])
    def test_reject_patterns(self, title):
        assert is_rejected_navigation_title(title) is True

    def test_reject_who_we_are(self):
        assert is_rejected_navigation_title("Who we are") is True

    def test_reject_what_we_do(self):
        assert is_rejected_navigation_title("What we do") is True

    def test_reject_sustainability(self):
        assert is_rejected_navigation_title("Sustainability") is True

    def test_reject_careers(self):
        assert is_rejected_navigation_title("Careers at Merck") is True

    def test_reject_skip_to_content(self):
        assert is_rejected_navigation_title("Skip to content") is True

    def test_accept_real_ir_title(self):
        assert is_rejected_navigation_title("Q3 2026 Earnings Call") is False

    def test_accept_conference_title(self):
        assert is_rejected_navigation_title(
            "47th Annual Goldman Sachs Global Healthcare Conference"
        ) is False

    def test_reject_empty_title(self):
        assert is_rejected_navigation_title("") is True


class TestScheduledCandidateRules:
    """scheduled_candidate_round_2 判定规则"""

    def _make_passing_result(self) -> MerckIrDedicatedPreflightResult:
        return MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=MIN_VALID_ITEMS_FOR_SCHEDULED,
            dated_item_count=MIN_DATED_ITEMS_FOR_SCHEDULED,
            sample_items=[
                MerckIrExtractionItem(
                    title="Q3 2026 Earnings Call",
                    url="https://www.merck.com/events/q3-2026-earnings-call/",
                    date_text="2026-07-15",
                    entry_type="events_presentations",
                ),
                MerckIrExtractionItem(
                    title="Q2 2026 Earnings Call",
                    url="https://www.merck.com/events/q2-2026-earnings-call/",
                    date_text="2026-04-15",
                    entry_type="events_presentations",
                ),
            ],
        )

    def test_sufficient_items_passes(self):
        result = self._make_passing_result()
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode == "scheduled_candidate_round_2"
        assert result.trial_v2_allowlist_allowed_now is False
        assert result.next_action == "propose_10_source_preflight"

    def test_insufficient_valid_items_fails(self):
        result = self._make_passing_result()
        result.valid_item_count = 2
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode != "scheduled_candidate_round_2"

    def test_insufficient_dated_items_fails(self):
        result = self._make_passing_result()
        result.dated_item_count = 1
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode != "scheduled_candidate_round_2"

    def test_dated_zero_fails(self):
        result = self._make_passing_result()
        result.dated_item_count = 0
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode != "scheduled_candidate_round_2"


class TestLoginPaywallCaptcha:
    """login/paywall/captcha 阻断"""

    def test_login_required_blocks_scheduled(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=5,
            dated_item_count=3,
            login_required=True,
        )
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode == "login_or_paywall_blocked"

    def test_paywall_blocks_scheduled(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=5,
            dated_item_count=3,
            paywall_observed=True,
        )
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode == "login_or_paywall_blocked"

    def test_captcha_blocks_scheduled(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=5,
            dated_item_count=3,
            captcha_or_antibot_observed=True,
        )
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode == "captcha_or_antibot_blocked"

    def test_validation_rejects_login_with_scheduled(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=5,
            dated_item_count=3,
            login_required=True,
            recommended_execution_mode="scheduled_candidate_round_2",
        )
        errors = validate_merck_ir_preflight_result(result)
        assert any("login_required" in e for e in errors)

    def test_validation_rejects_paywall_with_scheduled(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=5,
            dated_item_count=3,
            paywall_observed=True,
            recommended_execution_mode="scheduled_candidate_round_2",
        )
        errors = validate_merck_ir_preflight_result(result)
        assert any("paywall_observed" in e for e in errors)

    def test_validation_rejects_captcha_with_scheduled(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=5,
            dated_item_count=3,
            captcha_or_antibot_observed=True,
            recommended_execution_mode="scheduled_candidate_round_2",
        )
        errors = validate_merck_ir_preflight_result(result)
        assert any("captcha_or_antibot_observed" in e for e in errors)


class TestAllowlistFlag:
    """trial_v2_allowlist_allowed_now 默认 false"""

    def test_default_is_false(self):
        result = make_default_merck_ir_result()
        assert result.trial_v2_allowlist_allowed_now is False

    def test_scheduled_still_false(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=5,
            dated_item_count=3,
        )
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode == "scheduled_candidate_round_2"
        assert result.trial_v2_allowlist_allowed_now is False

    def test_validation_rejects_true(self):
        result = make_default_merck_ir_result()
        result.trial_v2_allowlist_allowed_now = True
        errors = validate_merck_ir_preflight_result(result)
        assert any("must be False" in e for e in errors)


class TestSensitiveKeywords:
    """report 不包含 cookie / token / proxy URL / secret"""

    def test_scan_finds_proxy_url(self):
        found = scan_sensitive_keywords("http_proxy=http://1.2.3.4:8080")
        assert len(found) > 0

    def test_scan_finds_cookie(self):
        found = scan_sensitive_keywords("cookie: session=abc123")
        assert len(found) > 0

    def test_scan_finds_authorization(self):
        found = scan_sensitive_keywords("authorization: bearer xyz")
        assert len(found) > 0

    def test_scan_clean_text(self):
        found = scan_sensitive_keywords("Q3 2026 Earnings Call")
        assert len(found) == 0

    def test_validation_rejects_sensitive_in_notes(self):
        result = make_default_merck_ir_result()
        result.notes = "http_proxy=http://1.2.3.4:8080"
        errors = validate_merck_ir_preflight_result(result)
        assert any("sensitive" in e.lower() for e in errors)

    def test_validation_rejects_sensitive_in_sample_title(self):
        result = make_default_merck_ir_result()
        result.sample_items = [
            MerckIrExtractionItem(title="cookie: secret data", url="https://example.com"),
        ]
        errors = validate_merck_ir_preflight_result(result)
        assert any("sensitive" in e.lower() for e in errors)


class TestLowFrequencyCandidate:
    """low_frequency_candidate 判定"""

    def test_items_but_no_dates(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=5,
            dated_item_count=0,
        )
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode == "low_frequency_candidate"

    def test_items_but_insufficient_dates(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=5,
            dated_item_count=1,
        )
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode == "low_frequency_candidate"


class TestManualReview:
    """manual_review_only 判定"""

    def test_no_items(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=200,
            valid_item_count=0,
            dated_item_count=0,
        )
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode == "manual_review_only"


class TestBlockedBacklog:
    """blocked_or_backlog 判定"""

    def test_http_zero(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            http_status=0,
        )
        apply_merck_ir_decision(result)
        assert result.recommended_execution_mode == "blocked_or_backlog"


class TestToDict:
    """to_dict 方法"""

    def test_to_dict_has_required_fields(self):
        result = make_default_merck_ir_result()
        d = result.to_dict()
        for key in (
            "source_id", "entry_url", "entry_type", "http_status",
            "valid_item_count", "dated_item_count", "rejected_navigation_count",
            "sample_items", "recommended_execution_mode",
            "trial_v2_allowlist_allowed_now", "next_action", "risk_flags",
        ):
            assert key in d

    def test_to_dict_sample_items(self):
        result = MerckIrDedicatedPreflightResult(
            source_id="merck_ir",
            sample_items=[
                MerckIrExtractionItem(title="Test", url="https://example.com"),
            ],
        )
        d = result.to_dict()
        assert len(d["sample_items"]) == 1
        assert d["sample_items"][0]["title"] == "Test"


class TestBatchReport:
    """make_batch_report_dict"""

    def test_batch_report_structure(self):
        result = make_default_merck_ir_result()
        d = make_batch_report_dict(result, base_commit="abc", branch="test")
        assert d["batch_name"] == "m3c_6f1_merck_ir_dedicated_preflight"
        assert d["base_commit"] == "abc"
        assert d["branch"] == "test"
        assert "result" in d
        assert "generated_at" in d


class TestValidDecisions:
    """所有决策值必须是合法的"""

    def test_all_decisions_in_set(self):
        for decision in (
            "scheduled_candidate_round_2",
            "low_frequency_candidate",
            "on_demand_candidate",
            "manual_review_only",
            "blocked_or_backlog",
            "login_or_paywall_blocked",
            "captcha_or_antibot_blocked",
        ):
            assert decision in MERCK_IR_FINAL_DECISIONS

    def test_invalid_decision_rejected(self):
        result = make_default_merck_ir_result()
        result.recommended_execution_mode = "invalid_decision"
        errors = validate_merck_ir_preflight_result(result)
        assert any("not a valid decision" in e for e in errors)
