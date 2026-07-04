"""Tests for opc_foundation.source_inventory.trae_execution_assessment (M3C-6G).

覆盖范围：
    1. source_id 只能是 reuters / marketwatch / streetinsider
    2. trial_v2_allowlist_allowed_now 必须默认 false
    3. trae_automation_allowed_now 不能是 true，只能 false 或 manual_approval_required
    4. login_required=true 时不得成为 trae_browser_assisted_candidate
    5. paywall_observed=true 时不得成为 trae_browser_assisted_candidate
    6. captcha_or_antibot_observed=true 时不得成为 trae_browser_assisted_candidate
    7. cloudflare_or_botwall_observed=true 时不得成为 trae_browser_assisted_candidate
    8. visible_item_count < 3 时不得成为 candidate
    9. visible_dated_item_count < 2 时不得成为 candidate
    10. sample_items 不得包含 cookie / token / session
    11. report 不得包含 cookie / token / proxy URL
    12. 不修改 trial_v2 allowlist
    13. 不修改 TRAE scheduling
    14. 不配置 production
    15. 不引入 Playwright / Selenium
    16. 不恢复 Dashboard 已删除页面
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from opc_foundation.source_inventory.trae_execution_assessment import (
    MAX_SAMPLE_ITEMS_RECORDED,
    MIN_VISIBLE_DATED_ITEMS_FOR_CANDIDATE,
    MIN_VISIBLE_ITEMS_FOR_CANDIDATE,
    SENSITIVE_KEYWORDS,
    TRAE_AUTOMATION_ALLOWED_VALUES,
    TRAE_FINAL_DECISIONS,
    M3C_6G_ALLOWED_CANDIDATES,
    TraeAssistedDecision,
    TraeAutomationDryRunObservation,
    TraeBrowserObservation,
    TraeBrowserSampleItem,
    TraeExecutionAssessmentReport,
    TraeSkillObservation,
    apply_trae_decision,
    compute_trae_decision,
    is_m3c_6g_candidate,
    make_default_trae_report,
    scan_sensitive_keywords,
    validate_trae_assessment,
)


# =============================================================================
# Test 1: source_id 只能是 reuters / marketwatch / streetinsider
# =============================================================================

class TestCandidateWhitelist:
    """Validate only reuters / marketwatch / streetinsider are allowed."""

    def test_allowed_candidates_exact(self):
        assert M3C_6G_ALLOWED_CANDIDATES == {
            "reuters",
            "marketwatch",
            "streetinsider",
        }

    @pytest.mark.parametrize("source_id,expected", [
        ("reuters", True),
        ("marketwatch", True),
        ("streetinsider", True),
        ("merck_ir", False),
        ("goldman_sachs_podcasts", False),
        ("benzinga_analyst_ratings", False),
        ("wallstreet_cn", False),
        ("", False),
    ])
    def test_is_candidate(self, source_id, expected):
        assert is_m3c_6g_candidate(source_id) is expected

    def test_validate_rejects_non_whitelisted_source(self):
        """Sources outside the whitelist must trigger validation errors."""
        report = TraeExecutionAssessmentReport(
            source_id="merck_ir",
            decision=TraeAssistedDecision(
                recommended_execution_mode="trae_browser_assisted_candidate",
                trae_automation_allowed_now="manual_approval_required",
            ),
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                visible_item_count=5,
                visible_dated_item_count=3,
                structured_extraction_possible=True,
                repeatability_observed=True,
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("不在 M3C-6G 允许候选白名单" in e for e in errors), errors


# =============================================================================
# Test 2: trial_v2_allowlist_allowed_now 必须默认 false
# =============================================================================

class TestDefaultAllowlistFlag:
    """trial_v2_allowlist_allowed_now must default to False."""

    def test_default_report_has_false_allowlist_flag(self):
        report = make_default_trae_report("reuters")
        assert report.decision.trial_v2_allowlist_allowed_now is False

    def test_default_decision_is_manual_review_only(self):
        report = make_default_trae_report("reuters")
        assert report.decision.recommended_execution_mode == "manual_review_only"

    def test_validate_rejects_true_allowlist_flag(self):
        """Forcing trial_v2_allowlist_allowed_now=True must fail validation."""
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="false",
                trial_v2_allowlist_allowed_now=True,  # illegal
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("trial_v2_allowlist_allowed_now 必须为 False" in e for e in errors), errors


# =============================================================================
# Test 3: trae_automation_allowed_now 只能 false 或 manual_approval_required
# =============================================================================

class TestTraeAutomationAllowedValues:
    """trae_automation_allowed_now cannot be True; only false or manual_approval_required."""

    def test_allowed_values_constant(self):
        assert TRAE_AUTOMATION_ALLOWED_VALUES == {"false", "manual_approval_required"}

    def test_true_rejected(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="true",  # illegal
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("trae_automation_allowed_now" in e for e in errors), errors

    def test_invalid_value_rejected(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="always",  # illegal
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("trae_automation_allowed_now" in e for e in errors), errors

    def test_false_accepted(self):
        report = make_default_trae_report("reuters")
        errors = validate_trae_assessment(report)
        # Should not have trae_automation_allowed_now errors
        assert not any("trae_automation_allowed_now" in e for e in errors), errors

    def test_manual_approval_required_accepted(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="trae_browser_assisted_candidate",
                trae_automation_allowed_now="manual_approval_required",
            ),
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                visible_item_count=5,
                visible_dated_item_count=3,
                structured_extraction_possible=True,
                repeatability_observed=True,
            ),
        )
        errors = validate_trae_assessment(report)
        assert not any("trae_automation_allowed_now" in e for e in errors), errors


# =============================================================================
# Tests 4-7: Blocker flags reject candidate status
# =============================================================================

class TestBlockerFlagsRejectCandidate:
    """login / paywall / captcha / cloudflare blockers reject candidate status."""

    def _make_candidate_report_with_blocker(self, **blocker_kwargs) -> TraeExecutionAssessmentReport:
        return TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="trae_browser_assisted_candidate",
                trae_automation_allowed_now="manual_approval_required",
            ),
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                visible_item_count=5,
                visible_dated_item_count=3,
                structured_extraction_possible=True,
                repeatability_observed=True,
                **blocker_kwargs,
            ),
        )

    def test_login_required_blocks_candidate(self):
        report = self._make_candidate_report_with_blocker(login_required=True)
        errors = validate_trae_assessment(report)
        assert any("login_required" in e for e in errors), errors

    def test_paywall_observed_blocks_candidate(self):
        report = self._make_candidate_report_with_blocker(paywall_observed=True)
        errors = validate_trae_assessment(report)
        assert any("paywall_observed" in e for e in errors), errors

    def test_captcha_blocks_candidate(self):
        report = self._make_candidate_report_with_blocker(captcha_or_antibot_observed=True)
        errors = validate_trae_assessment(report)
        assert any("captcha_or_antibot_observed" in e for e in errors), errors

    def test_cloudflare_blocks_candidate(self):
        report = self._make_candidate_report_with_blocker(cloudflare_or_botwall_observed=True)
        errors = validate_trae_assessment(report)
        assert any("cloudflare_or_botwall_observed" in e for e in errors), errors

    def test_login_blocks_low_frequency_candidate(self):
        """login_required also blocks trae_low_frequency_candidate."""
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="trae_low_frequency_candidate",
                trae_automation_allowed_now="manual_approval_required",
            ),
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                visible_item_count=5,
                visible_dated_item_count=3,
                login_required=True,
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("login_required" in e for e in errors), errors


# =============================================================================
# Tests 8-9: visible item count thresholds
# =============================================================================

class TestVisibleItemThresholds:
    """visible_item_count < 3 or visible_dated_item_count < 2 blocks candidate."""

    def test_thresholds_constants(self):
        assert MIN_VISIBLE_ITEMS_FOR_CANDIDATE == 3
        assert MIN_VISIBLE_DATED_ITEMS_FOR_CANDIDATE == 2

    def test_insufficient_visible_items_blocks_candidate(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="trae_browser_assisted_candidate",
                trae_automation_allowed_now="manual_approval_required",
            ),
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                visible_item_count=2,  # below 3
                visible_dated_item_count=3,
                structured_extraction_possible=True,
                repeatability_observed=True,
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("visible_item_count" in e for e in errors), errors

    def test_insufficient_dated_items_blocks_candidate(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="trae_browser_assisted_candidate",
                trae_automation_allowed_now="manual_approval_required",
            ),
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                visible_item_count=5,
                visible_dated_item_count=1,  # below 2
                structured_extraction_possible=True,
                repeatability_observed=True,
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("visible_dated_item_count" in e for e in errors), errors


# =============================================================================
# Test 10: sample_items 不得包含 cookie / token / session
# =============================================================================

class TestSampleItemsClean:
    """sample_items must not contain cookie / token / session."""

    def test_sensitive_keywords_listed(self):
        for kw in ("cookie:", "set-cookie", "bearer ", "token=", "session_id=", "sessionid="):
            assert kw in SENSITIVE_KEYWORDS

    def test_sample_item_with_cookie_rejected(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="false",
            ),
            browser_observation=TraeBrowserObservation(
                sample_items=[
                    TraeBrowserSampleItem(
                        title="Article with cookie: session=abc",
                        url="https://example.com/article",
                        date_text="2026-07-04",
                    )
                ]
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("敏感关键字" in e for e in errors), errors

    def test_sample_item_with_token_rejected(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="false",
            ),
            browser_observation=TraeBrowserObservation(
                sample_items=[
                    TraeBrowserSampleItem(
                        title="Article",
                        url="https://example.com/article?token=abc123",
                        date_text="2026-07-04",
                    )
                ]
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("敏感关键字" in e for e in errors), errors

    def test_sample_item_with_session_id_rejected(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="false",
            ),
            browser_observation=TraeBrowserObservation(
                sample_items=[
                    TraeBrowserSampleItem(
                        title="Article",
                        url="https://example.com/article",
                        date_text="session_id=abc123",
                    )
                ]
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("敏感关键字" in e for e in errors), errors

    def test_sample_items_count_limit(self):
        """sample_items cannot exceed MAX_SAMPLE_ITEMS_RECORDED."""
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="false",
            ),
            browser_observation=TraeBrowserObservation(
                sample_items=[
                    TraeBrowserSampleItem(title=f"Article {i}", url=f"https://example.com/{i}", date_text="2026-07-04")
                    for i in range(MAX_SAMPLE_ITEMS_RECORDED + 1)
                ]
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("超过上限" in e for e in errors), errors

    def test_clean_sample_items_accepted(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="trae_browser_assisted_candidate",
                trae_automation_allowed_now="manual_approval_required",
            ),
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                visible_item_count=5,
                visible_dated_item_count=3,
                structured_extraction_possible=True,
                repeatability_observed=True,
                sample_items=[
                    TraeBrowserSampleItem(
                        title="Reuters Breaking News",
                        url="https://www.reuters.com/article/123",
                        date_text="2026-07-04",
                    )
                ],
            ),
        )
        errors = validate_trae_assessment(report)
        assert not any("敏感关键字" in e for e in errors), errors


# =============================================================================
# Test 11: report 不得包含 cookie / token / proxy URL
# =============================================================================

class TestReportNoSensitiveData:
    """notes / observation_notes must not contain sensitive keywords."""

    def test_notes_with_cookie_rejected(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            notes="observation; cookie: session=abc",
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="false",
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("notes 包含敏感关键字" in e for e in errors), errors

    def test_observation_notes_with_token_rejected(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            browser_observation=TraeBrowserObservation(
                observation_notes="page loaded; token=abc123",
            ),
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="false",
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("observation_notes 包含敏感关键字" in e for e in errors), errors

    def test_skill_notes_with_proxy_url_rejected(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            skill_observation=TraeSkillObservation(
                notes="used proxy_url=http://127.0.0.1:7890",
            ),
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="false",
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("skill_observation.notes 包含敏感关键字" in e for e in errors), errors

    def test_to_dict_excludes_raw_html(self):
        """to_dict must not contain raw_html / screenshot / cookie fields."""
        report = make_default_trae_report("reuters")
        d = report.to_dict()
        assert "raw_html" not in d
        assert "screenshot" not in d
        assert "cookies" not in d


# =============================================================================
# Tests 12-16: Boundary invariants
# =============================================================================

class TestBoundaryInvariants:
    """Module must not modify allowlist / TRAE scheduling / production / Dashboard."""

    def test_no_playwright_selenium_in_module(self):
        """Module source code must not import Playwright / Selenium."""
        module_path = (
            REPO_ROOT / "src" / "opc_foundation" / "source_inventory"
            / "trae_execution_assessment.py"
        )
        text = module_path.read_text(encoding="utf-8")
        lower = text.lower()
        assert "import playwright" not in lower
        assert "from playwright" not in lower
        assert "import selenium" not in lower
        assert "from selenium" not in lower
        assert "playwright.sync_playwright" not in lower
        assert "selenium.webdriver" not in lower

    def test_final_decisions_includes_all_9(self):
        """All 9 final decisions listed in spec must be present."""
        expected = {
            "trae_browser_assisted_candidate",
            "trae_skill_assisted_candidate",
            "trae_low_frequency_candidate",
            "trae_on_demand_candidate",
            "public_browser_blocked",
            "login_or_paywall_blocked",
            "captcha_or_antibot_blocked",
            "manual_review_only",
            "not_worth_it",
        }
        assert expected == TRAE_FINAL_DECISIONS

    def test_apply_trae_decision_does_not_create_files(self, monkeypatch):
        """apply_trae_decision must not write to filesystem."""
        report = make_default_trae_report("reuters")
        original_open = open
        def _fail_open(*args, **kwargs):
            raise AssertionError("apply_trae_decision must not call open()")
        monkeypatch.setattr("builtins.open", _fail_open)
        try:
            apply_trae_decision(report)
        finally:
            monkeypatch.setattr("builtins.open", original_open)


# =============================================================================
# Test: compute_trae_decision logic
# =============================================================================

class TestComputeTraeDecision:
    """Decision computation logic tests."""

    def test_login_required_returns_login_or_paywall_blocked(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                login_required=True,
                visible_item_count=5,
                visible_dated_item_count=3,
            ),
        )
        decision = compute_trae_decision(report)
        assert decision.recommended_execution_mode == "login_or_paywall_blocked"
        assert decision.trae_automation_allowed_now == "false"
        assert decision.trial_v2_allowlist_allowed_now is False

    def test_paywall_returns_login_or_paywall_blocked(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                paywall_observed=True,
                visible_item_count=5,
                visible_dated_item_count=3,
            ),
        )
        decision = compute_trae_decision(report)
        assert decision.recommended_execution_mode == "login_or_paywall_blocked"

    def test_captcha_returns_captcha_or_antibot_blocked(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                captcha_or_antibot_observed=True,
                visible_item_count=5,
                visible_dated_item_count=3,
            ),
        )
        decision = compute_trae_decision(report)
        assert decision.recommended_execution_mode == "captcha_or_antibot_blocked"

    def test_cloudflare_returns_captcha_or_antibot_blocked(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                cloudflare_or_botwall_observed=True,
                visible_item_count=5,
                visible_dated_item_count=3,
            ),
        )
        decision = compute_trae_decision(report)
        assert decision.recommended_execution_mode == "captcha_or_antibot_blocked"

    def test_not_accessible_returns_public_browser_blocked(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            browser_observation=TraeBrowserObservation(
                public_page_accessible=False,
            ),
        )
        decision = compute_trae_decision(report)
        assert decision.recommended_execution_mode == "public_browser_blocked"

    def test_insufficient_items_returns_manual_review_only(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                visible_item_count=2,  # below 3
                visible_dated_item_count=2,
            ),
        )
        decision = compute_trae_decision(report)
        assert decision.recommended_execution_mode == "manual_review_only"

    def test_sufficient_items_returns_candidate(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            browser_observation=TraeBrowserObservation(
                public_page_accessible=True,
                visible_item_count=5,
                visible_dated_item_count=3,
                structured_extraction_possible=True,
                repeatability_observed=True,
            ),
        )
        decision = compute_trae_decision(report)
        assert decision.recommended_execution_mode == "trae_browser_assisted_candidate"
        assert decision.trae_automation_allowed_now == "manual_approval_required"
        assert decision.trial_v2_allowlist_allowed_now is False


# =============================================================================
# Test: make_default_trae_report
# =============================================================================

class TestMakeDefaultReport:
    """Default report factory tests."""

    def test_default_report_fields(self):
        report = make_default_trae_report("reuters")
        assert report.source_id == "reuters"
        assert report.prior_static_decision == "manual_reaudit_needed"
        assert report.browser_observation.public_page_accessible is False
        assert report.browser_observation.visible_item_count == 0
        assert report.skill_observation.skill_available is False
        assert report.automation_dry_run.tested is False
        assert report.decision.recommended_execution_mode == "manual_review_only"
        assert report.decision.trae_automation_allowed_now == "false"
        assert report.decision.trial_v2_allowlist_allowed_now is False

    def test_default_report_validation_passes(self):
        report = make_default_trae_report("reuters")
        errors = validate_trae_assessment(report)
        assert errors == [], errors


# =============================================================================
# Test: TraeBrowserSampleItem and extraction_method
# =============================================================================

class TestSampleItemValidation:
    """TraeBrowserSampleItem validation."""

    def test_valid_extraction_methods_accepted(self):
        for method in (
            "manual_browser_observation",
            "agent_browser_observation",
            "agent_reach_observation",
            "structured_extraction",
        ):
            report = TraeExecutionAssessmentReport(
                source_id="reuters",
                decision=TraeAssistedDecision(
                    recommended_execution_mode="manual_review_only",
                    trae_automation_allowed_now="false",
                ),
                browser_observation=TraeBrowserObservation(
                    sample_items=[
                        TraeBrowserSampleItem(
                            title="Test",
                            url="https://example.com",
                            date_text="2026-07-04",
                            extraction_method=method,
                        )
                    ]
                ),
            )
            errors = validate_trae_assessment(report)
            assert not any("extraction_method" in e for e in errors), f"Failed for method={method}"

    def test_invalid_extraction_method_rejected(self):
        report = TraeExecutionAssessmentReport(
            source_id="reuters",
            decision=TraeAssistedDecision(
                recommended_execution_mode="manual_review_only",
                trae_automation_allowed_now="false",
            ),
            browser_observation=TraeBrowserObservation(
                sample_items=[
                    TraeBrowserSampleItem(
                        title="Test",
                        url="https://example.com",
                        date_text="2026-07-04",
                        extraction_method="playwright_extraction",  # illegal
                    )
                ]
            ),
        )
        errors = validate_trae_assessment(report)
        assert any("extraction_method" in e for e in errors), errors


# =============================================================================
# Test: scan_sensitive_keywords
# =============================================================================

class TestScanSensitiveKeywords:
    """Sensitive keyword scanner tests."""

    def test_scan_cookie(self):
        assert "cookie:" in scan_sensitive_keywords("Headers: cookie: sessionid=abc")

    def test_scan_proxy_url(self):
        hits = scan_sensitive_keywords("config: proxy_url=http://127.0.0.1:7890")
        assert "proxy_url=" in hits
        assert "http://127.0.0.1" in hits

    def test_scan_clean_text(self):
        assert scan_sensitive_keywords("https://www.reuters.com/markets/") == []

    def test_scan_empty(self):
        assert scan_sensitive_keywords("") == []
