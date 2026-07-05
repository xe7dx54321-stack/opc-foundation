"""M3C-6C.1 Low-frequency Observation Harness — data models and validation.

This module defines the observation harness for tracking merck_ir low-frequency
source stability over a 7-day period. It records daily runs, detects navigation
regression, blocking errors, and computes a final observation status.

Observation states:
    pending -> active -> completed_7d | partial_observation | failed

This module does NOT modify trial_v2 allowlist, TRAE scheduling, or production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OBSERVATION_ALLOWED_SOURCES: set[str] = {"merck_ir"}

OBSERVATION_STATUS_VALUES: set[str] = {
    "pending",
    "active",
    "completed_7d",
    "partial_observation",
    "failed",
}

DAY_STATUS_VALUES: set[str] = {
    "success",
    "partial",
    "failed",
    "no_run",
}

TARGET_DAYS: int = 7
MIN_VALID_ITEMS_PER_RUN: int = 3
MAX_CONSECUTIVE_ZERO_ITEM_RUNS: int = 2
MAX_CONSECUTIVE_NAVIGATION_ONLY_RUNS: int = 2
MAX_SAMPLE_ITEMS_RECORDED: int = 5

TIMESTAMP_CONFIDENCE_VALUES: set[str] = {"HIGH", "MEDIUM", "LOW", "NONE"}

# Sensitive keywords
SENSITIVE_KEYWORDS: tuple[str, ...] = (
    "http_proxy=",
    "https_proxy=",
    "all_proxy=",
    "proxy_url=",
    "proxy_host=",
    "proxy_port=",
    "proxy_username=",
    "proxy_password=",
    "cookie:",
    "set-cookie:",
    "authorization:",
    "bearer ",
    "api_key=",
    "secret=",
    "password=",
    "session_id=",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LowFrequencyObservationRun:
    """A single observation run record."""

    source_id: str = "merck_ir"
    run_id: str = ""
    run_date: str = ""  # YYYY-MM-DD
    run_started_at: str = ""
    run_finished_at: str = ""
    mode: str = "dry_run"
    valid_item_count: int = 0
    dated_item_count: int = 0
    missing_date_count: int = 0
    navigation_rejected_count: int = 0
    timestamp_confidence_distribution: dict[str, int] = field(
        default_factory=lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    )
    sample_items: list[dict] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    status: str = "pending"
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "run_id": self.run_id,
            "run_date": self.run_date,
            "run_started_at": self.run_started_at,
            "run_finished_at": self.run_finished_at,
            "mode": self.mode,
            "valid_item_count": self.valid_item_count,
            "dated_item_count": self.dated_item_count,
            "missing_date_count": self.missing_date_count,
            "navigation_rejected_count": self.navigation_rejected_count,
            "timestamp_confidence_distribution": dict(self.timestamp_confidence_distribution),
            "sample_items": list(self.sample_items),
            "risk_flags": list(self.risk_flags),
            "status": self.status,
            "notes": self.notes,
        }


@dataclass
class LowFrequencyObservationDay:
    """A single day's observation summary."""

    date: str = ""  # YYYY-MM-DD
    source_id: str = "merck_ir"
    run_count: int = 0
    best_valid_item_count: int = 0
    best_dated_item_count: int = 0
    had_successful_run: bool = False
    had_navigation_regression: bool = False
    had_blocking_error: bool = False
    status: str = "no_run"  # success / partial / failed / no_run

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "source_id": self.source_id,
            "run_count": self.run_count,
            "best_valid_item_count": self.best_valid_item_count,
            "best_dated_item_count": self.best_dated_item_count,
            "had_successful_run": self.had_successful_run,
            "had_navigation_regression": self.had_navigation_regression,
            "had_blocking_error": self.had_blocking_error,
            "status": self.status,
        }


@dataclass
class LowFrequencyObservationSummary:
    """7-day observation summary."""

    source_id: str = "merck_ir"
    target_days: int = TARGET_DAYS
    observed_days: int = 0
    successful_days: int = 0
    partial_days: int = 0
    failed_days: int = 0
    total_runs: int = 0
    min_valid_items_per_run: int = 0
    max_valid_items_per_run: int = 0
    timestamp_confidence_distribution: dict[str, int] = field(
        default_factory=lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    )
    navigation_regression_count: int = 0
    blocking_error_count: int = 0
    final_observation_status: str = "pending"
    recommended_next_action: str = "continue_observation"
    days: list[LowFrequencyObservationDay] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_days": self.target_days,
            "observed_days": self.observed_days,
            "successful_days": self.successful_days,
            "partial_days": self.partial_days,
            "failed_days": self.failed_days,
            "total_runs": self.total_runs,
            "min_valid_items_per_run": self.min_valid_items_per_run,
            "max_valid_items_per_run": self.max_valid_items_per_run,
            "timestamp_confidence_distribution": dict(self.timestamp_confidence_distribution),
            "navigation_regression_count": self.navigation_regression_count,
            "blocking_error_count": self.blocking_error_count,
            "final_observation_status": self.final_observation_status,
            "recommended_next_action": self.recommended_next_action,
            "days": [d.to_dict() for d in self.days],
        }


@dataclass
class LowFrequencyObservationDecision:
    """Decision for observation status."""

    final_observation_status: str = "pending"
    recommended_next_action: str = "continue_observation"
    can_create_trae_task: bool = False
    risk_flags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Sensitive keyword scanning
# ---------------------------------------------------------------------------


def scan_sensitive_keywords(text: str) -> list[str]:
    """Return a list of sensitive keywords found in *text* (case-insensitive)."""
    if not text:
        return []
    lower = text.lower()
    found: list[str] = []
    for kw in SENSITIVE_KEYWORDS:
        if kw in lower:
            found.append(kw)
    return found


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_observation_run(run: LowFrequencyObservationRun) -> list[str]:
    """Validate an observation run. Returns list of errors (empty = pass)."""
    errors: list[str] = []

    if run.source_id not in OBSERVATION_ALLOWED_SOURCES:
        errors.append(
            f"source_id '{run.source_id}' not in allowed sources: {OBSERVATION_ALLOWED_SOURCES}"
        )

    if run.status not in DAY_STATUS_VALUES and run.status != "pending":
        errors.append(f"invalid run status: {run.status}")

    # Check timestamp_confidence when dated_item_count == 0
    if run.dated_item_count == 0 and run.valid_item_count > 0:
        low_count = run.timestamp_confidence_distribution.get("LOW", 0)
        none_count = run.timestamp_confidence_distribution.get("NONE", 0)
        if low_count == 0 and none_count == 0:
            errors.append(
                "dated_item_count=0 but no LOW/NONE timestamp_confidence entries"
            )

    # Sensitive keyword scan
    for i, item in enumerate(run.sample_items):
        for field_name in ("title", "url", "date_text"):
            val = item.get(field_name, "") if isinstance(item, dict) else ""
            found = scan_sensitive_keywords(val)
            if found:
                errors.append(
                    f"sample_items[{i}].{field_name} contains sensitive keywords: {found}"
                )

    found_notes = scan_sensitive_keywords(run.notes)
    if found_notes:
        errors.append(f"notes contains sensitive keywords: {found_notes}")

    return errors


def validate_observation_summary(summary: LowFrequencyObservationSummary) -> list[str]:
    """Validate an observation summary. Returns list of errors (empty = pass)."""
    errors: list[str] = []

    if summary.source_id not in OBSERVATION_ALLOWED_SOURCES:
        errors.append(
            f"source_id '{summary.source_id}' not in allowed sources"
        )

    if summary.final_observation_status not in OBSERVATION_STATUS_VALUES:
        errors.append(
            f"invalid final_observation_status: {summary.final_observation_status}"
        )

    # completed_7d requires 7 observed days
    if summary.final_observation_status == "completed_7d":
        if summary.observed_days < TARGET_DAYS:
            errors.append(
                f"completed_7d requires {TARGET_DAYS} observed days, got {summary.observed_days}"
            )
        if summary.successful_days < TARGET_DAYS:
            errors.append(
                f"completed_7d requires {TARGET_DAYS} successful days, got {summary.successful_days}"
            )

    # Sensitive keyword scan on days
    for i, day in enumerate(summary.days):
        if day.had_blocking_error and summary.final_observation_status == "completed_7d":
            errors.append(f"day[{i}] has blocking error but status is completed_7d")

    return errors


# ---------------------------------------------------------------------------
# Day status computation
# ---------------------------------------------------------------------------


def compute_day_status(
    runs: list[LowFrequencyObservationRun],
    date: str,
    source_id: str = "merck_ir",
) -> LowFrequencyObservationDay:
    """Compute the status for a single observation day."""
    day_runs = [r for r in runs if r.run_date == date and r.source_id == source_id]

    if not day_runs:
        return LowFrequencyObservationDay(
            date=date,
            source_id=source_id,
            status="no_run",
        )

    day = LowFrequencyObservationDay(
        date=date,
        source_id=source_id,
        run_count=len(day_runs),
    )

    for run in day_runs:
        if run.valid_item_count > day.best_valid_item_count:
            day.best_valid_item_count = run.valid_item_count
        if run.dated_item_count > day.best_dated_item_count:
            day.best_dated_item_count = run.dated_item_count

        # Check for blocking errors
        if any(
            flag in run.risk_flags
            for flag in ("login_required", "paywall_observed", "captcha_or_antibot_observed")
        ):
            day.had_blocking_error = True

        # Check for navigation regression (all items were navigation)
        if run.valid_item_count == 0 and run.navigation_rejected_count > 0:
            day.had_navigation_regression = True

        # Check if run was successful
        if run.valid_item_count >= MIN_VALID_ITEMS_PER_RUN and not day.had_blocking_error:
            day.had_successful_run = True

    # Determine day status
    if day.had_blocking_error:
        day.status = "failed"
    elif day.had_successful_run:
        day.status = "success"
    else:
        day.status = "partial"

    return day


# ---------------------------------------------------------------------------
# Observation summary computation
# ---------------------------------------------------------------------------


def compute_observation_summary(
    runs: list[LowFrequencyObservationRun],
    source_id: str = "merck_ir",
    target_days: int = TARGET_DAYS,
) -> LowFrequencyObservationSummary:
    """Compute a 7-day observation summary from a list of runs."""
    summary = LowFrequencyObservationSummary(
        source_id=source_id,
        target_days=target_days,
    )

    # Get unique dates
    dates = sorted(set(r.run_date for r in runs if r.run_date))
    summary.observed_days = len(dates)
    summary.total_runs = len(runs)

    # Compute day statuses
    for date in dates:
        day = compute_day_status(runs, date, source_id)
        summary.days.append(day)

        if day.status == "success":
            summary.successful_days += 1
        elif day.status == "partial":
            summary.partial_days += 1
        elif day.status == "failed":
            summary.failed_days += 1

        if day.had_navigation_regression:
            summary.navigation_regression_count += 1
        if day.had_blocking_error:
            summary.blocking_error_count += 1

    # Compute min/max valid items
    valid_counts = [r.valid_item_count for r in runs]
    if valid_counts:
        summary.min_valid_items_per_run = min(valid_counts)
        summary.max_valid_items_per_run = max(valid_counts)

    # Aggregate timestamp confidence distribution
    for run in runs:
        for conf, count in run.timestamp_confidence_distribution.items():
            summary.timestamp_confidence_distribution[conf] = (
                summary.timestamp_confidence_distribution.get(conf, 0) + count
            )

    # Determine final status
    if summary.blocking_error_count > 0:
        summary.final_observation_status = "failed"
        summary.recommended_next_action = "investigate_blocking_errors"
    elif summary.observed_days >= target_days and summary.successful_days >= target_days:
        summary.final_observation_status = "completed_7d"
        summary.recommended_next_action = "propose_trae_low_frequency_task"
    elif summary.observed_days > 0:
        summary.final_observation_status = "partial_observation"
        summary.recommended_next_action = "continue_observation"
    else:
        summary.final_observation_status = "pending"
        summary.recommended_next_action = "start_observation"

    return summary


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def is_observation_allowed_source(source_id: str) -> bool:
    """Check if source_id is allowed for observation."""
    return source_id in OBSERVATION_ALLOWED_SOURCES


def now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_date() -> str:
    """Return current UTC date as YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def make_default_observation_run(
    source_id: str = "merck_ir",
) -> LowFrequencyObservationRun:
    """Create a default observation run."""
    return LowFrequencyObservationRun(source_id=source_id)


def make_default_observation_summary(
    source_id: str = "merck_ir",
) -> LowFrequencyObservationSummary:
    """Create a default observation summary."""
    return LowFrequencyObservationSummary(source_id=source_id)
