"""M3C-6C Low-frequency Source Pipeline — data models and validation.

This module defines the data structures for the low-frequency source pipeline,
which is the second source layer alongside trial_v2 high-frequency sources.

Key distinctions:
    - trial_v2_high_frequency: 9 sources, daily 3 batches, requires stable
      dated items, strict quality bar.
    - low_frequency_sources: daily/weekly/event-driven, accepts missing
      date_text with discovered_at fallback, timestamp_confidence=LOW.
    - on_demand_sources: triggered by topic/ticker/keyword (future, not
      implemented in this stage).

merck_ir is the first sample low-frequency source (M3C-6F.1 validated 15 valid
IR items, 0 dated items).

This module does NOT modify trial_v2 allowlist, TRAE scheduling, or production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOW_FREQ_ALLOWED_SOURCES: set[str] = {"merck_ir"}

LOW_FREQ_FINAL_DECISIONS: set[str] = {
    "low_frequency_active",
    "low_frequency_candidate",
    "manual_review_only",
    "blocked_or_backlog",
    "not_eligible_for_low_frequency",
}

MIN_VALID_ITEMS_FOR_LOW_FREQ: int = 3
MAX_SAMPLE_ITEMS_RECORDED: int = 5

TIMESTAMP_CONFIDENCE_VALUES: set[str] = {"HIGH", "MEDIUM", "LOW", "NONE"}

# Navigation page titles that must be rejected (case-insensitive substring).
LOW_FREQ_REJECT_TITLE_PATTERNS: tuple[str, ...] = (
    "who we are",
    "what we do",
    "sustainability",
    "careers",
    "about us",
    "company overview",
    "skip to content",
    "skip to main",
    "areas of innovation",
    "see full agenda",
    "icons /",
    "microphonewebcast",
    "back to top",
    "menu",
    "close",
    "search",
)

# Sensitive keywords that must never appear in any field.
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
class LowFrequencySourceConfig:
    """Configuration for a single low-frequency source."""

    source_id: str = ""
    source_layer: str = "low_frequency_candidate"
    expected_value: str = "medium"
    prior_stage: str = ""
    prior_valid_items: int = 0
    prior_dated_items: int = 0
    preferred_frequency: str = "daily_or_weekly"
    recommended_initial_frequency: str = "weekly"
    date_text_required: bool = False
    timestamp_confidence_when_missing: str = "LOW"
    trial_v2_allowlist_allowed_now: bool = False
    low_frequency_allowed_now: bool = True
    production_enabled: bool = False
    notes: str = ""


@dataclass
class LowFrequencyItem:
    """A single extracted low-frequency item."""

    source_id: str = ""
    title: str = ""
    url: str = ""
    entry_type: str = "investor_news"
    date_text: str = ""
    discovered_at: str = ""
    observed_at: str = ""
    timestamp_confidence: str = "LOW"
    date_missing_reason: str = ""
    is_navigation: bool = False
    is_valid_item: bool = True
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class LowFrequencyDecision:
    """Decision for a low-frequency source run."""

    recommended_frequency: str = "weekly"
    low_frequency_allowed_now: bool = True
    trial_v2_allowlist_allowed_now: bool = False
    production_enabled: bool = False
    next_action: str = "evaluate_low_frequency_schedule"
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class LowFrequencyRunResult:
    """Full result of a low-frequency source run."""

    source_id: str = ""
    run_mode: str = "dry_run"  # dry_run or run_once
    valid_item_count: int = 0
    dated_item_count: int = 0
    missing_date_count: int = 0
    navigation_rejected_count: int = 0
    timestamp_confidence_distribution: dict[str, int] = field(
        default_factory=lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    )
    sample_items: list[LowFrequencyItem] = field(default_factory=list)
    recommended_frequency: str = "weekly"
    low_frequency_allowed_now: bool = True
    trial_v2_allowlist_allowed_now: bool = False
    production_enabled: bool = False
    next_action: str = "evaluate_low_frequency_schedule"
    risk_flags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "run_mode": self.run_mode,
            "valid_item_count": self.valid_item_count,
            "dated_item_count": self.dated_item_count,
            "missing_date_count": self.missing_date_count,
            "navigation_rejected_count": self.navigation_rejected_count,
            "timestamp_confidence_distribution": dict(
                self.timestamp_confidence_distribution
            ),
            "sample_items": [
                {
                    "source_id": s.source_id,
                    "title": s.title,
                    "url": s.url,
                    "entry_type": s.entry_type,
                    "date_text": s.date_text,
                    "discovered_at": s.discovered_at,
                    "observed_at": s.observed_at,
                    "timestamp_confidence": s.timestamp_confidence,
                    "date_missing_reason": s.date_missing_reason,
                    "is_navigation": s.is_navigation,
                    "is_valid_item": s.is_valid_item,
                    "risk_flags": list(s.risk_flags),
                }
                for s in self.sample_items
            ],
            "recommended_frequency": self.recommended_frequency,
            "low_frequency_allowed_now": self.low_frequency_allowed_now,
            "trial_v2_allowlist_allowed_now": self.trial_v2_allowlist_allowed_now,
            "production_enabled": self.production_enabled,
            "next_action": self.next_action,
            "risk_flags": list(self.risk_flags),
            "notes": self.notes,
        }


@dataclass
class LowFrequencySchedulingProposal:
    """A TRAE task proposal for a low-frequency source (not a real task)."""

    source_id: str = ""
    proposed_frequency: str = "weekly"
    proposed_command: str = ""
    create_trae_task_now: bool = False
    manual_approval_required: bool = True
    production_enabled: bool = False
    affects_trial_v2_allowlist: bool = False
    affects_trae_scheduling: bool = False
    rationale: str = ""


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


def validate_low_frequency_run_result(
    result: LowFrequencyRunResult,
) -> list[str]:
    """Validate a low-frequency run result.

    Returns a list of error strings (empty list = pass).
    """
    errors: list[str] = []

    # source_id must be in allowed set
    if result.source_id not in LOW_FREQ_ALLOWED_SOURCES:
        errors.append(
            f"source_id '{result.source_id}' is not in allowed low-frequency sources: "
            f"{LOW_FREQ_ALLOWED_SOURCES}"
        )

    # trial_v2_allowlist_allowed_now must be False
    if result.trial_v2_allowlist_allowed_now:
        errors.append("trial_v2_allowlist_allowed_now must be False")

    # production_enabled must be False
    if result.production_enabled:
        errors.append("production_enabled must be False")

    # If valid_item_count < 3, should not be low_frequency_active
    if (
        result.valid_item_count < MIN_VALID_ITEMS_FOR_LOW_FREQ
        and result.low_frequency_allowed_now
        and result.next_action != "manual_review"
    ):
        errors.append(
            f"valid_item_count {result.valid_item_count} < {MIN_VALID_ITEMS_FOR_LOW_FREQ} "
            f"but low_frequency_allowed_now is True"
        )

    # If dated_item_count == 0, timestamp_confidence should have LOW entries
    if result.dated_item_count == 0:
        low_count = result.timestamp_confidence_distribution.get("LOW", 0)
        none_count = result.timestamp_confidence_distribution.get("NONE", 0)
        if low_count == 0 and none_count == 0:
            errors.append(
                "dated_item_count=0 but no LOW/NONE timestamp_confidence entries"
            )

    # sample_items count
    if len(result.sample_items) > MAX_SAMPLE_ITEMS_RECORDED:
        errors.append(
            f"sample_items count {len(result.sample_items)} exceeds max "
            f"{MAX_SAMPLE_ITEMS_RECORDED}"
        )

    # Sensitive keyword scan on sample items
    for i, item in enumerate(result.sample_items):
        for field_name in ("title", "url", "date_text", "date_missing_reason"):
            val = getattr(item, field_name, "")
            found = scan_sensitive_keywords(val)
            if found:
                errors.append(
                    f"sample_items[{i}].{field_name} contains sensitive keywords: {found}"
                )

    # Sensitive keyword scan on notes
    found_notes = scan_sensitive_keywords(result.notes)
    if found_notes:
        errors.append(f"notes contains sensitive keywords: {found_notes}")

    # Navigation items must be rejected
    for i, item in enumerate(result.sample_items):
        if item.is_navigation and item.is_valid_item:
            errors.append(
                f"sample_items[{i}] is navigation but is_valid_item=True"
            )

    return errors


# ---------------------------------------------------------------------------
# Decision computation
# ---------------------------------------------------------------------------


def compute_low_frequency_decision(
    result: LowFrequencyRunResult,
) -> LowFrequencyDecision:
    """Compute the recommended frequency and decision for a low-frequency run.

    Decision rules:
        1. valid_item_count >= 3 -> low_frequency_active or low_frequency_candidate
        2. valid_item_count < 3 -> manual_review_only
        3. dated_item_count >= 2 -> can consider higher frequency (daily)
        4. dated_item_count == 0 -> weekly with timestamp_confidence=LOW
    """
    risk_flags: list[str] = []

    if result.valid_item_count < MIN_VALID_ITEMS_FOR_LOW_FREQ:
        risk_flags.append("insufficient_valid_items")
        return LowFrequencyDecision(
            recommended_frequency="manual_review",
            low_frequency_allowed_now=False,
            trial_v2_allowlist_allowed_now=False,
            production_enabled=False,
            next_action="manual_review",
            risk_flags=risk_flags,
        )

    # Has enough items for low-frequency
    if result.dated_item_count >= 2:
        return LowFrequencyDecision(
            recommended_frequency="daily",
            low_frequency_allowed_now=True,
            trial_v2_allowlist_allowed_now=False,
            production_enabled=False,
            next_action="evaluate_daily_low_frequency",
            risk_flags=[],
        )

    # dated_item_count < 2 -> weekly
    if result.dated_item_count == 0:
        risk_flags.append("no_dated_items_timestamp_confidence_LOW")
    else:
        risk_flags.append("insufficient_dated_items")

    return LowFrequencyDecision(
        recommended_frequency="weekly",
        low_frequency_allowed_now=True,
        trial_v2_allowlist_allowed_now=False,
        production_enabled=False,
        next_action="evaluate_weekly_low_frequency",
        risk_flags=risk_flags,
    )


def apply_low_frequency_decision(
    result: LowFrequencyRunResult,
) -> LowFrequencyRunResult:
    """Compute and apply the decision to *result* (in-place)."""
    decision = compute_low_frequency_decision(result)
    result.recommended_frequency = decision.recommended_frequency
    result.low_frequency_allowed_now = decision.low_frequency_allowed_now
    result.trial_v2_allowlist_allowed_now = decision.trial_v2_allowlist_allowed_now
    result.production_enabled = decision.production_enabled
    result.next_action = decision.next_action
    result.risk_flags = decision.risk_flags
    return result


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def is_low_frequency_allowed_source(source_id: str) -> bool:
    """Check if source_id is in the allowed low-frequency sources set."""
    return source_id in LOW_FREQ_ALLOWED_SOURCES


def make_default_low_frequency_result(
    source_id: str = "merck_ir",
) -> LowFrequencyRunResult:
    """Create a default LowFrequencyRunResult."""
    return LowFrequencyRunResult(source_id=source_id)


def is_rejected_navigation_title(title: str) -> bool:
    """Check if a title matches a rejected navigation pattern."""
    if not title:
        return True
    lower = title.lower().strip()
    for pattern in LOW_FREQ_REJECT_TITLE_PATTERNS:
        if pattern in lower:
            return True
    return False


def make_default_scheduling_proposal(
    source_id: str = "merck_ir",
) -> LowFrequencySchedulingProposal:
    """Create a default TRAE scheduling proposal (not a real task)."""
    return LowFrequencySchedulingProposal(
        source_id=source_id,
        proposed_frequency="weekly",
        proposed_command=(
            f"python scripts/run_foundation_low_frequency_sources.py "
            f"--source {source_id} --run-once"
        ),
        create_trae_task_now=False,
        manual_approval_required=True,
        production_enabled=False,
        affects_trial_v2_allowlist=False,
        affects_trae_scheduling=False,
        rationale=(
            f"{source_id} has valid IR content but dated_item_count=0; "
            "low-frequency weekly observation with timestamp_confidence=LOW."
        ),
    )


def now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
