"""Tests for M3C-6C.1 Low-frequency Observation Harness data model."""

from __future__ import annotations

import pytest

from opc_foundation.source_inventory.low_frequency_observation import (
    DAY_STATUS_VALUES,
    MIN_VALID_ITEMS_PER_RUN,
    OBSERVATION_ALLOWED_SOURCES,
    OBSERVATION_STATUS_VALUES,
    SENSITIVE_KEYWORDS,
    TARGET_DAYS,
    LowFrequencyObservationDay,
    LowFrequencyObservationDecision,
    LowFrequencyObservationRun,
    LowFrequencyObservationSummary,
    compute_day_status,
    compute_observation_summary,
    is_observation_allowed_source,
    make_default_observation_run,
    make_default_observation_summary,
    now_iso,
    scan_sensitive_keywords,
    today_date,
    validate_observation_run,
    validate_observation_summary,
)


class TestAllowedSources:
    """observation config 只允许 merck_ir"""

    def test_merck_ir_allowed(self):
        assert "merck_ir" in OBSERVATION_ALLOWED_SOURCES

    def test_yahoo_finance_not_allowed(self):
        assert "yahoo_finance" not in OBSERVATION_ALLOWED_SOURCES

    def test_is_allowed_true(self):
        assert is_observation_allowed_source("merck_ir") is True

    def test_is_allowed_false(self):
        assert is_observation_allowed_source("yahoo_finance") is False

    def test_non_allowed_rejected(self):
        run = make_default_observation_run("yahoo_finance")
        errors = validate_observation_run(run)
        assert any("not in allowed" in e for e in errors)


class TestTargetDays:
    """target_days=7"""

    def test_target_days_is_7(self):
        assert TARGET_DAYS == 7

    def test_summary_default_target_7(self):
        summary = make_default_observation_summary()
        assert summary.target_days == TARGET_DAYS


class TestObservationStatus:
    """pending / active / completed_7d / partial_observation / failed 状态合法"""

    def test_all_statuses_in_set(self):
        for s in ("pending", "active", "completed_7d", "partial_observation", "failed"):
            assert s in OBSERVATION_STATUS_VALUES

    def test_invalid_status_rejected(self):
        summary = make_default_observation_summary()
        summary.final_observation_status = "invalid"
        errors = validate_observation_summary(summary)
        assert any("invalid" in e.lower() for e in errors)


class TestAllowlistFlags:
    """trial_v2_allowlist_allowed_now=false, low_frequency_allowed_now=true"""

    def test_default_run_source_merck_ir(self):
        run = make_default_observation_run()
        assert run.source_id == "merck_ir"


class TestCompletedSevenDays:
    """observed_days < 7 时不得 completed_7d"""

    def _make_runs(self, num_days: int, valid: int = 5) -> list[LowFrequencyObservationRun]:
        runs = []
        for i in range(num_days):
            runs.append(LowFrequencyObservationRun(
                source_id="merck_ir",
                run_date=f"2026-07-{i+1:02d}",
                valid_item_count=valid,
                dated_item_count=0,
                missing_date_count=valid,
                timestamp_confidence_distribution={"HIGH": 0, "MEDIUM": 0, "LOW": valid, "NONE": 0},
                status="success",
            ))
        return runs

    def test_seven_days_completes(self):
        runs = self._make_runs(7)
        summary = compute_observation_summary(runs)
        assert summary.final_observation_status == "completed_7d"

    def test_six_days_partial(self):
        runs = self._make_runs(6)
        summary = compute_observation_summary(runs)
        assert summary.final_observation_status == "partial_observation"

    def test_zero_days_pending(self):
        summary = compute_observation_summary([])
        assert summary.final_observation_status == "pending"

    def test_completed_with_missing_days_rejected(self):
        summary = make_default_observation_summary()
        summary.final_observation_status = "completed_7d"
        summary.observed_days = 3
        summary.successful_days = 3
        errors = validate_observation_summary(summary)
        assert any("requires 7 observed days" in e for e in errors)


class TestDayStatus:
    """每天缺 run 时不得 completed_7d; valid < 3 不得 success"""

    def test_no_run_day_status(self):
        day = compute_day_status([], "2026-07-01")
        assert day.status == "no_run"

    def test_success_day(self):
        run = LowFrequencyObservationRun(
            source_id="merck_ir",
            run_date="2026-07-01",
            valid_item_count=5,
            status="success",
        )
        day = compute_day_status([run], "2026-07-01")
        assert day.status == "success"
        assert day.best_valid_item_count == 5

    def test_partial_day_low_items(self):
        run = LowFrequencyObservationRun(
            source_id="merck_ir",
            run_date="2026-07-01",
            valid_item_count=2,
            status="partial",
        )
        day = compute_day_status([run], "2026-07-01")
        assert day.status == "partial"

    def test_failed_day_blocking_error(self):
        run = LowFrequencyObservationRun(
            source_id="merck_ir",
            run_date="2026-07-01",
            valid_item_count=5,
            risk_flags=["login_required"],
        )
        day = compute_day_status([run], "2026-07-01")
        assert day.status == "failed"
        assert day.had_blocking_error is True


class TestTimestampConfidence:
    """date_text 缺失时必须 timestamp_confidence=LOW"""

    def test_dated_zero_requires_low(self):
        run = LowFrequencyObservationRun(
            source_id="merck_ir",
            valid_item_count=5,
            dated_item_count=0,
            timestamp_confidence_distribution={"HIGH": 5, "MEDIUM": 0, "LOW": 0, "NONE": 0},
        )
        errors = validate_observation_run(run)
        assert any("no LOW/NONE" in e for e in errors)

    def test_dated_zero_with_low_passes(self):
        run = LowFrequencyObservationRun(
            source_id="merck_ir",
            valid_item_count=5,
            dated_item_count=0,
            timestamp_confidence_distribution={"HIGH": 0, "MEDIUM": 0, "LOW": 5, "NONE": 0},
        )
        errors = validate_observation_run(run)
        assert not any("no LOW/NONE" in e for e in errors)


class TestNavigationRegression:
    """连续 navigation-only run 必须 failed"""

    def test_navigation_regression_detected(self):
        run = LowFrequencyObservationRun(
            source_id="merck_ir",
            run_date="2026-07-01",
            valid_item_count=0,
            navigation_rejected_count=10,
        )
        day = compute_day_status([run], "2026-07-01")
        assert day.had_navigation_regression is True


class TestBlockingErrors:
    """login / paywall / captcha / anti-bot 必须 failed"""

    @pytest.mark.parametrize("flag", ["login_required", "paywall_observed", "captcha_or_antibot_observed"])
    def test_blocking_flag_causes_failed_day(self, flag):
        run = LowFrequencyObservationRun(
            source_id="merck_ir",
            run_date="2026-07-01",
            valid_item_count=5,
            risk_flags=[flag],
        )
        day = compute_day_status([run], "2026-07-01")
        assert day.status == "failed"

    def test_blocking_error_fails_summary(self):
        runs = [
            LowFrequencyObservationRun(
                source_id="merck_ir",
                run_date=f"2026-07-{i+1:02d}",
                valid_item_count=5,
                risk_flags=["login_required"],
            )
            for i in range(7)
        ]
        summary = compute_observation_summary(runs)
        assert summary.final_observation_status == "failed"


class TestSensitiveKeywords:
    """report 不包含 cookie / token / proxy URL / secret"""

    def test_scan_finds_proxy(self):
        found = scan_sensitive_keywords("http_proxy=http://1.2.3.4:8080")
        assert len(found) > 0

    def test_scan_finds_cookie(self):
        found = scan_sensitive_keywords("cookie: session=abc")
        assert len(found) > 0

    def test_scan_clean(self):
        found = scan_sensitive_keywords("Q3 2026 Earnings Call")
        assert len(found) == 0

    def test_validation_rejects_sensitive_in_notes(self):
        run = make_default_observation_run()
        run.notes = "http_proxy=http://1.2.3.4:8080"
        errors = validate_observation_run(run)
        assert any("sensitive" in e.lower() for e in errors)

    def test_validation_rejects_sensitive_in_sample(self):
        run = make_default_observation_run()
        run.sample_items = [{"title": "cookie: secret", "url": "https://example.com"}]
        errors = validate_observation_run(run)
        assert any("sensitive" in e.lower() for e in errors)


class TestSummaryToDict:
    """to_dict 方法"""

    def test_summary_to_dict(self):
        summary = make_default_observation_summary()
        d = summary.to_dict()
        for key in (
            "source_id", "target_days", "observed_days", "successful_days",
            "partial_days", "failed_days", "total_runs",
            "final_observation_status", "recommended_next_action", "days",
        ):
            assert key in d

    def test_run_to_dict(self):
        run = make_default_observation_run()
        d = run.to_dict()
        for key in (
            "source_id", "run_id", "run_date", "valid_item_count",
            "dated_item_count", "timestamp_confidence_distribution",
            "status", "notes",
        ):
            assert key in d


class TestNowIso:
    """now_iso returns valid ISO string"""

    def test_format(self):
        ts = now_iso()
        assert "T" in ts
        assert ts.endswith("Z")

    def test_today_date(self):
        d = today_date()
        assert len(d) == 10
        assert "-" in d
