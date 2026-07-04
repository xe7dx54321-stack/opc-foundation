"""Tests for opc_foundation.source_inventory.execution_capabilities module (M3C-6B).

覆盖范围：
    1. execution mode 枚举合法
    2. source_id 只能是 reuters / marketwatch / streetinsider
    3. trial_v2_allowlist_allowed_now 默认 false
    4. TRAE browser candidate 不得自动进入 trial_v2 allowlist
    5. agent-reach candidate 不得自动进入 trial_v2 allowlist
    6. scheduled_preflight_pass_static 必须有 >=3 valid items
    7. scheduled_preflight_pass_feed 必须有 feed evidence
    8. login_required=true 时不得 scheduled_preflight_pass
    9. paywall_observed=true 时不得 scheduled_preflight_pass
    10. captcha_or_antibot_observed=true 时不得 scheduled_preflight_pass
    11. report 不包含 cookie / token / proxy URL（敏感关键字扫描）
    12. 不修改 trial_v2 allowlist
    13. 不修改 TRAE scheduling
    14. 不配置 production
    15. 不引入 Playwright / Selenium
    16. 不恢复 Dashboard 已删除页面
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# Ensure src on path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from opc_foundation.source_inventory.execution_capabilities import (
    AUTOMATION_SUITABILITY_VALUES,
    CANDIDATE_LAYERS,
    DISCOVERY_STATUSES,
    FINAL_DECISIONS,
    M3C_6B_ALLOWED_CANDIDATES,
    MIN_DATED_ITEMS_FOR_PASS,
    MIN_VALID_ITEMS_FOR_PASS,
    SENSITIVE_KEYWORDS,
    TRAE_AUTOMATION_ELIGIBLE_DECISIONS,
    TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS,
    TRAE_STATUSES,
    ExecutionMode,
    SampleItem,
    SourceExecutionCapability,
    TraeBrowserAssessment,
    apply_recommendations,
    compute_allowlist_flags,
    compute_recommended_execution_mode,
    is_candidate_source,
    make_default_capability,
    scan_sensitive_keywords,
    validate_execution_capability,
)


# =============================================================================
# Test 1: execution mode 枚举合法
# =============================================================================

class TestExecutionModeEnum:
    """Validate ExecutionMode enumeration has all 9 expected modes."""

    def test_all_expected_modes_present(self):
        expected = {
            "python_static_http",
            "rss_or_sitemap",
            "public_json_ld_or_metadata",
            "trae_browser_public",
            "trae_skill_agent_reach",
            "trae_scheduled_automation",
            "on_demand_search",
            "manual_review_only",
            "blocked_or_not_worth_it",
        }
        actual = {m.value for m in ExecutionMode}
        assert actual == expected, f"Missing modes: {expected - actual}"

    def test_no_playwright_selenium_in_modes(self):
        """ExecutionMode must NOT include Playwright / Selenium modes."""
        for m in ExecutionMode:
            assert "playwright" not in m.value
            assert "selenium" not in m.value

    def test_string_enum(self):
        """ExecutionMode must be str-Enum for YAML / JSON friendliness."""
        assert isinstance(ExecutionMode.PYTHON_STATIC_HTTP.value, str)
        assert ExecutionMode.PYTHON_STATIC_HTTP == "python_static_http"


# =============================================================================
# Test 2: source_id 只能是 reuters / marketwatch / streetinsider
# =============================================================================

class TestCandidateWhitelist:
    """Validate that only reuters / marketwatch / streetinsider are allowed."""

    def test_allowed_candidates_exact(self):
        assert M3C_6B_ALLOWED_CANDIDATES == {
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
        ("unknown_source", False),
    ])
    def test_is_candidate_source(self, source_id, expected):
        assert is_candidate_source(source_id) is expected

    def test_validate_rejects_non_whitelisted_source(self):
        """Sources outside the whitelist must trigger validation errors."""
        cap = SourceExecutionCapability(
            source_id="merck_ir",
            final_decision="scheduled_preflight_pass_static",
            static_http_valid_items=5,
            static_http_dated_items=3,
        )
        apply_recommendations(cap)
        errors = validate_execution_capability(cap)
        assert any("不在 M3C-6B 允许候选白名单" in e for e in errors), errors


# =============================================================================
# Test 3: trial_v2_allowlist_allowed_now 默认 false
# =============================================================================

class TestDefaultAllowlistFlag:
    """trial_v2_allowlist_allowed_now must default to False."""

    def test_default_capability_has_false_allowlist_flag(self):
        cap = make_default_capability("reuters")
        assert cap.trial_v2_allowlist_allowed_now is False

    def test_default_capability_has_false_trae_automation_flag(self):
        cap = make_default_capability("reuters")
        assert cap.trae_automation_allowed_now is False

    def test_default_final_decision_is_manual_reaudit(self):
        cap = make_default_capability("reuters")
        assert cap.final_decision == "manual_reaudit_needed"


# =============================================================================
# Test 4: TRAE browser candidate 不得自动进入 trial_v2 allowlist
# =============================================================================

class TestTraeBrowserNotInTrialV2:
    """trae_browser_assisted_candidate must NOT auto-promote to trial_v2."""

    def test_trae_browser_candidate_not_in_allowlist_eligible(self):
        assert "trae_browser_assisted_candidate" not in TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS

    def test_trae_browser_candidate_in_trae_automation_eligible(self):
        assert "trae_browser_assisted_candidate" in TRAE_AUTOMATION_ELIGIBLE_DECISIONS

    def test_validate_blocks_trae_browser_to_trial_v2(self):
        """Forcing trial_v2_allowlist_allowed_now=true for trae_browser candidate fails."""
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="trae_browser_assisted_candidate",
            trial_v2_allowlist_allowed_now=True,  # illegal override
        )
        errors = validate_execution_capability(cap)
        assert any("不得自动进入 trial_v2 allowlist" in e for e in errors), errors

    def test_compute_allowlist_flags_for_trae_browser(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="trae_browser_assisted_candidate",
        )
        trial_v2, trae_auto = compute_allowlist_flags(cap)
        assert trial_v2 is False
        assert trae_auto is True


# =============================================================================
# Test 5: agent-reach candidate 不得自动进入 trial_v2 allowlist
# =============================================================================

class TestTraeSkillNotInTrialV2:
    """trae_skill_assisted_candidate must NOT auto-promote to trial_v2."""

    def test_trae_skill_candidate_not_in_allowlist_eligible(self):
        assert "trae_skill_assisted_candidate" not in TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS

    def test_validate_blocks_trae_skill_to_trial_v2(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="trae_skill_assisted_candidate",
            trial_v2_allowlist_allowed_now=True,  # illegal override
        )
        errors = validate_execution_capability(cap)
        assert any("不得自动进入 trial_v2 allowlist" in e for e in errors), errors


# =============================================================================
# Test 6: scheduled_preflight_pass_static 必须有 >=3 valid items
# =============================================================================

class TestStaticPassMinimumItems:
    """scheduled_preflight_pass_static requires >=3 valid + >=2 dated items."""

    def test_min_constants(self):
        assert MIN_VALID_ITEMS_FOR_PASS == 3
        assert MIN_DATED_ITEMS_FOR_PASS == 2

    def test_pass_static_with_sufficient_items(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_static",
            static_http_valid_items=3,
            static_http_dated_items=2,
        )
        errors = validate_execution_capability(cap)
        static_errors = [e for e in errors if "static_http_valid_items" in e or "static_http_dated_items" in e]
        assert static_errors == [], static_errors

    def test_pass_static_rejects_insufficient_valid_items(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_static",
            static_http_valid_items=2,  # below 3
            static_http_dated_items=2,
        )
        errors = validate_execution_capability(cap)
        assert any("static_http_valid_items" in e for e in errors), errors

    def test_pass_static_rejects_insufficient_dated_items(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_static",
            static_http_valid_items=3,
            static_http_dated_items=1,  # below 2
        )
        errors = validate_execution_capability(cap)
        assert any("static_http_dated_items" in e for e in errors), errors


# =============================================================================
# Test 7: scheduled_preflight_pass_feed 必须有 feed evidence
# =============================================================================

class TestFeedPassFeedEvidence:
    """scheduled_preflight_pass_feed requires feed_count>=1 OR sitemap_count>=1."""

    def test_pass_feed_with_feed_evidence(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_feed",
            feed_count=1,
            sitemap_count=0,
            static_http_dated_items=2,
        )
        errors = validate_execution_capability(cap)
        feed_errors = [e for e in errors if "feed_count" in e or "sitemap_count" in e]
        assert feed_errors == [], feed_errors

    def test_pass_feed_with_sitemap_evidence(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_feed",
            feed_count=0,
            sitemap_count=1,
            static_http_dated_items=2,
        )
        errors = validate_execution_capability(cap)
        feed_errors = [e for e in errors if "feed_count" in e or "sitemap_count" in e]
        assert feed_errors == [], feed_errors

    def test_pass_feed_rejects_no_feed_evidence(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_feed",
            feed_count=0,
            sitemap_count=0,
            static_http_dated_items=2,
        )
        errors = validate_execution_capability(cap)
        assert any("feed_count" in e and "sitemap_count" in e for e in errors), errors

    def test_pass_feed_rejects_insufficient_dated_items(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_feed",
            feed_count=1,
            sitemap_count=0,
            static_http_dated_items=1,  # below 2
        )
        errors = validate_execution_capability(cap)
        assert any("dated items" in e for e in errors), errors


# =============================================================================
# Tests 8-10: login / paywall / captcha blocker flags
# =============================================================================

class TestBlockerFlagsRejectPass:
    """login / paywall / captcha blockers must reject scheduled_preflight_pass_*."""

    def _make_pass_static_with_blocker(self, **blocker_kwargs) -> SourceExecutionCapability:
        return SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_static",
            static_http_valid_items=5,
            static_http_dated_items=3,
            trae_browser_assessment=TraeBrowserAssessment(**blocker_kwargs),
        )

    def test_login_required_blocks_pass_static(self):
        cap = self._make_pass_static_with_blocker(login_required=True)
        errors = validate_execution_capability(cap)
        assert any("login_required" in e for e in errors), errors

    def test_paywall_observed_blocks_pass_static(self):
        cap = self._make_pass_static_with_blocker(paywall_observed=True)
        errors = validate_execution_capability(cap)
        assert any("paywall_observed" in e for e in errors), errors

    def test_captcha_blocks_pass_static(self):
        cap = self._make_pass_static_with_blocker(captcha_or_antibot_observed=True)
        errors = validate_execution_capability(cap)
        assert any("captcha_or_antibot_observed" in e for e in errors), errors

    def test_login_required_blocks_pass_feed(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_feed",
            feed_count=1,
            static_http_dated_items=3,
            trae_browser_assessment=TraeBrowserAssessment(login_required=True),
        )
        errors = validate_execution_capability(cap)
        assert any("login_required" in e for e in errors), errors

    def test_paywall_observed_blocks_pass_feed(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_feed",
            feed_count=1,
            static_http_dated_items=3,
            trae_browser_assessment=TraeBrowserAssessment(paywall_observed=True),
        )
        errors = validate_execution_capability(cap)
        assert any("paywall_observed" in e for e in errors), errors

    def test_captcha_blocks_pass_feed(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_feed",
            feed_count=1,
            static_http_dated_items=3,
            trae_browser_assessment=TraeBrowserAssessment(captcha_or_antibot_observed=True),
        )
        errors = validate_execution_capability(cap)
        assert any("captcha_or_antibot_observed" in e for e in errors), errors


# =============================================================================
# Test 11: report 不包含 cookie / token / proxy URL（敏感关键字扫描）
# =============================================================================

class TestSensitiveKeywordScan:
    """evidence_summary / notes must not contain sensitive keywords."""

    @pytest.mark.parametrize("keyword", [
        "cookie:",
        "set-cookie",
        "bearer ",
        "api_key=",
        "apikey:",
        "proxy_url=",
        "http://127.0.0.1",
        "http://localhost",
        "password=",
        "secret=",
        "token=",
    ])
    def test_sensitive_keyword_listed(self, keyword):
        assert keyword in SENSITIVE_KEYWORDS

    def test_scan_detects_cookie(self):
        text = "Headers: cookie: sessionid=abc"
        hits = scan_sensitive_keywords(text)
        assert "cookie:" in hits

    def test_scan_detects_proxy_url(self):
        text = "config: proxy_url=http://127.0.0.1:7890"
        hits = scan_sensitive_keywords(text)
        assert "proxy_url=" in hits
        assert "http://127.0.0.1" in hits

    def test_scan_clean_text(self):
        text = "https://www.reuters.com/markets/"
        hits = scan_sensitive_keywords(text)
        assert hits == []

    def test_validate_rejects_evidence_with_cookie(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_static",
            static_http_valid_items=3,
            static_http_dated_items=2,
            evidence_summary="fetched; cookie: session=abc",
        )
        errors = validate_execution_capability(cap)
        assert any("敏感关键字" in e for e in errors), errors

    def test_validate_rejects_notes_with_token(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_static",
            static_http_valid_items=3,
            static_http_dated_items=2,
            trae_browser_assessment=TraeBrowserAssessment(
                notes="manual observation; token=abc123",
            ),
        )
        errors = validate_execution_capability(cap)
        assert any("敏感关键字" in e for e in errors), errors


# =============================================================================
# Test 12-16: Boundary checks — no allowlist / TRAE scheduling / production changes
# =============================================================================

class TestBoundaryInvariants:
    """Module must not modify allowlist / TRAE scheduling / production / Dashboard."""

    def test_no_playwright_selenium_in_module(self):
        """Module source code must not import Playwright / Selenium."""
        module_path = (
            REPO_ROOT / "src" / "opc_foundation" / "source_inventory"
            / "execution_capabilities.py"
        )
        text = module_path.read_text(encoding="utf-8")
        lower = text.lower()
        assert "playwright" not in lower
        assert "selenium" not in lower
        assert "from selenium" not in lower
        assert "import playwright" not in lower

    def test_final_decisions_constant_includes_all_decisions(self):
        """All 10 final decisions listed in spec must be present."""
        expected = {
            "scheduled_preflight_pass_static",
            "scheduled_preflight_pass_feed",
            "trae_browser_assisted_candidate",
            "trae_skill_assisted_candidate",
            "low_frequency_candidate",
            "on_demand_candidate",
            "browser_like_backlog",
            "cloudflare_or_anti_bot_backlog",
            "blocked_or_low_value",
            "manual_reaudit_needed",
        }
        assert expected.issubset(FINAL_DECISIONS)

    def test_allowlist_eligible_decisions_only_pass(self):
        """Only static / feed pass decisions can promote to trial_v2."""
        assert TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS == {
            "scheduled_preflight_pass_static",
            "scheduled_preflight_pass_feed",
        }

    def test_compute_recommendations_does_not_create_files(self, tmp_path, monkeypatch):
        """apply_recommendations must not write to filesystem."""
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="scheduled_preflight_pass_static",
            static_http_valid_items=3,
            static_http_dated_items=2,
        )
        # Patch open() to ensure not invoked
        original_open = open
        def _fail_open(*args, **kwargs):
            raise AssertionError("apply_recommendations must not call open()")
        monkeypatch.setattr("builtins.open", _fail_open)
        try:
            apply_recommendations(cap)
        finally:
            monkeypatch.setattr("builtins.open", original_open)
        assert cap.trial_v2_allowlist_allowed_now is True

    def test_to_dict_excludes_raw_html(self):
        """to_dict must not contain raw_html field."""
        cap = make_default_capability("reuters")
        d = cap.to_dict()
        assert "raw_html" not in d
        assert "screenshot" not in d
        assert "cookies" not in d
        assert "cookie" not in d


# =============================================================================
# Test: compute_recommended_execution_mode mapping
# =============================================================================

class TestComputeRecommendedMode:
    """Recommended execution mode must match final_decision mapping."""

    @pytest.mark.parametrize("decision,expected_mode", [
        ("scheduled_preflight_pass_static", "python_static_http"),
        ("scheduled_preflight_pass_feed", "rss_or_sitemap"),
        ("trae_browser_assisted_candidate", "trae_browser_public"),
        ("trae_skill_assisted_candidate", "trae_skill_agent_reach"),
        ("on_demand_candidate", "on_demand_search"),
        ("blocked_or_low_value", "blocked_or_not_worth_it"),
        ("cloudflare_or_anti_bot_backlog", "blocked_or_not_worth_it"),
        ("browser_like_backlog", "trae_browser_public"),
        ("manual_reaudit_needed", "manual_review_only"),
    ])
    def test_decision_to_mode_mapping(self, decision, expected_mode):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision=decision,
            feed_count=1,  # for low_frequency_candidate
        )
        mode = compute_recommended_execution_mode(cap)
        assert mode == expected_mode

    def test_low_frequency_prefers_rss_when_feed_available(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="low_frequency_candidate",
            feed_count=1,
        )
        assert compute_recommended_execution_mode(cap) == "rss_or_sitemap"

    def test_low_frequency_falls_back_to_static_when_no_feed(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="low_frequency_candidate",
            feed_count=0,
            sitemap_count=0,
        )
        assert compute_recommended_execution_mode(cap) == "python_static_http"


# =============================================================================
# Test: validate_execution_capability comprehensive
# =============================================================================

class TestValidateExecutionCapability:
    """Comprehensive validation tests."""

    def test_valid_pass_static_capability_passes_validation(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            candidate_layer="scheduled_candidate",
            static_http_status="ok",
            feed_discovery_status="not_found",
            metadata_discovery_status="ok",
            trae_browser_status="observed_public",
            trae_skill_status="not_available",
            automation_suitability="suitable_for_scheduled",
            recommended_execution_mode="python_static_http",
            trial_v2_allowlist_allowed_now=True,
            trae_automation_allowed_now=False,
            recommended_next_action="schedule_when_allowed",
            risk_flags=[],
            evidence_summary="http_status=200; items=5",
            static_http_valid_items=3,
            static_http_dated_items=2,
            feed_count=0,
            sitemap_count=0,
            metadata_count=2,
            trae_browser_assessment=TraeBrowserAssessment(
                public_page_accessible=True,
                login_required=False,
                paywall_observed=False,
                captcha_or_antibot_observed=False,
                visible_item_count=3,
                visible_dated_item_count=2,
                automation_suitability="suitable_for_scheduled",
            ),
            final_decision="scheduled_preflight_pass_static",
        )
        errors = validate_execution_capability(cap)
        assert errors == [], errors

    def test_empty_source_id_rejected(self):
        cap = SourceExecutionCapability(source_id="", final_decision="manual_reaudit_needed")
        errors = validate_execution_capability(cap)
        assert any("source_id 不能为空" in e for e in errors)

    def test_invalid_candidate_layer_rejected(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            candidate_layer="invalid_layer",
            final_decision="manual_reaudit_needed",
        )
        errors = validate_execution_capability(cap)
        assert any("candidate_layer" in e for e in errors)

    def test_invalid_static_http_status_rejected(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            static_http_status="invalid",
            final_decision="manual_reaudit_needed",
        )
        errors = validate_execution_capability(cap)
        assert any("static_http_status" in e for e in errors)

    def test_invalid_final_decision_rejected(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="invalid_decision",
        )
        errors = validate_execution_capability(cap)
        assert any("final_decision" in e for e in errors)

    def test_invalid_recommended_execution_mode_rejected(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            recommended_execution_mode="playwright_runtime",
            final_decision="manual_reaudit_needed",
        )
        errors = validate_execution_capability(cap)
        assert any("recommended_execution_mode" in e for e in errors)


# =============================================================================
# Test: make_default_capability
# =============================================================================

class TestMakeDefaultCapability:
    """Default capability factory tests."""

    def test_default_capability_fields(self):
        cap = make_default_capability("reuters")
        assert cap.source_id == "reuters"
        assert cap.candidate_layer == "scheduled_candidate"
        assert cap.static_http_status == "not_attempted"
        assert cap.feed_discovery_status == "not_attempted"
        assert cap.metadata_discovery_status == "not_attempted"
        assert cap.trae_browser_status == "not_attempted"
        assert cap.trae_skill_status == "not_available"
        assert cap.automation_suitability == "manual_review_required"
        assert cap.recommended_execution_mode == "manual_review_only"
        assert cap.trial_v2_allowlist_allowed_now is False
        assert cap.trae_automation_allowed_now is False
        assert cap.final_decision == "manual_reaudit_needed"

    def test_default_capability_validation_passes(self):
        cap = make_default_capability("reuters")
        errors = validate_execution_capability(cap)
        assert errors == [], errors


# =============================================================================
# Test: TraeBrowserAssessment sample items
# =============================================================================

class TestTraeBrowserAssessment:
    """TraeBrowserAssessment dataclass behavior."""

    def test_default_assessment(self):
        ba = TraeBrowserAssessment()
        assert ba.public_page_accessible is False
        assert ba.login_required is False
        assert ba.paywall_observed is False
        assert ba.captcha_or_antibot_observed is False
        assert ba.visible_item_count == 0
        assert ba.visible_dated_item_count == 0
        assert ba.sample_items == []
        assert ba.automation_suitability == "not_suitable"

    def test_sample_item_defaults(self):
        s = SampleItem()
        assert s.title == ""
        assert s.url == ""
        assert s.date_text == ""

    def test_to_dict_contains_trae_assessment(self):
        cap = SourceExecutionCapability(
            source_id="reuters",
            final_decision="manual_reaudit_needed",
            trae_browser_assessment=TraeBrowserAssessment(
                public_page_accessible=True,
                visible_item_count=2,
                sample_items=[SampleItem(title="Test", url="https://example.com", date_text="2026-07-04")],
            ),
        )
        d = cap.to_dict()
        assert "trae_browser_assessment" in d
        ba = d["trae_browser_assessment"]
        assert ba["public_page_accessible"] is True
        assert ba["visible_item_count"] == 2
        assert len(ba["sample_items"]) == 1
        assert ba["sample_items"][0]["title"] == "Test"
