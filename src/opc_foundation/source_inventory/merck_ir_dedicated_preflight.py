"""M3C-6F.1 Merck IR Dedicated Extraction Preflight — data models and validation.

This module provides the data structures and decision logic for the M3C-6F.1
stage, which focuses exclusively on merck_ir. The goal is to determine whether
merck_ir can recover its M3C-5B1 content_ready status (score 90) by using the
correct IR entry points instead of the generic homepage crawl that failed in
M3C-6F.

Key constraints (enforced by validation):
    - Only merck_ir is allowed as source_id.
    - trial_v2_allowlist_allowed_now is always False.
    - Navigation page titles (Who we are, What we do, etc.) must be rejected.
    - login / paywall / captcha / anti-bot observations block scheduled_candidate.
    - valid_item_count >= 3 and dated_item_count >= 2 required for scheduled.
    - No sensitive data (proxy URL, cookie, token, secret) in any field.

This module does NOT modify trial_v2 allowlist, TRAE scheduling, or production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

M3C_6F1_ALLOWED_SOURCE: str = "merck_ir"

MERCK_IR_FINAL_DECISIONS: set[str] = {
    "scheduled_candidate_round_2",
    "low_frequency_candidate",
    "on_demand_candidate",
    "manual_review_only",
    "blocked_or_backlog",
    "login_or_paywall_blocked",
    "captcha_or_antibot_blocked",
}

SCHEDULED_ROUND_2_ELIGIBLE: set[str] = {"scheduled_candidate_round_2"}

MIN_VALID_ITEMS_FOR_SCHEDULED: int = 3
MIN_DATED_ITEMS_FOR_SCHEDULED: int = 2
MAX_SAMPLE_ITEMS_RECORDED: int = 5

TARGET_ENTRY_TYPES: set[str] = {
    "investor_news",
    "press_releases",
    "news_releases",
    "events_presentations",
    "rss_atom",
    "sitemap_investor_urls",
    "json_ld_metadata",
    "homepage_discovery",
}

# Navigation page titles that must be rejected (case-insensitive substring).
REJECT_TITLE_PATTERNS: tuple[str, ...] = (
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
    "news releases",
    "events & presentations",
    "financial information",
    "sec filings",
    "stock information",
    "investor resources",
    "investors overview",
    "investors",
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
class MerckIrCandidateUrl:
    """A candidate URL discovered during IR entry-point discovery."""

    url: str = ""
    entry_type: str = "homepage_discovery"
    source: str = ""  # where this URL was found (e.g. "homepage", "sitemap", "rss")


@dataclass
class MerckIrExtractionItem:
    """A single extracted IR item (news, event, press release, etc.)."""

    title: str = ""
    url: str = ""
    date_text: str = ""
    entry_type: str = "investor_news"
    extraction_method: str = "html_parsing"


@dataclass
class MerckIrDedicatedDecision:
    """Decision for a merck_ir dedicated preflight result."""

    recommended_execution_mode: str = "manual_review_only"
    trial_v2_allowlist_allowed_now: bool = False
    next_action: str = "manual_content_extraction_review"
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class MerckIrDedicatedPreflightResult:
    """Full result of a merck_ir dedicated extraction preflight."""

    source_id: str = "merck_ir"
    entry_url: str = ""
    entry_type: str = "investor_news"
    http_status: int = 0
    content_type: str = ""
    candidate_url_count: int = 0
    valid_item_count: int = 0
    dated_item_count: int = 0
    rejected_navigation_count: int = 0
    sample_items: list[MerckIrExtractionItem] = field(default_factory=list)
    rss_or_feed_found: bool = False
    sitemap_investor_url_count: int = 0
    json_ld_item_count: int = 0
    login_required: bool = False
    paywall_observed: bool = False
    captcha_or_antibot_observed: bool = False
    recommended_execution_mode: str = "manual_review_only"
    trial_v2_allowlist_allowed_now: bool = False
    next_action: str = "manual_content_extraction_review"
    risk_flags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "entry_url": self.entry_url,
            "entry_type": self.entry_type,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "candidate_url_count": self.candidate_url_count,
            "valid_item_count": self.valid_item_count,
            "dated_item_count": self.dated_item_count,
            "rejected_navigation_count": self.rejected_navigation_count,
            "sample_items": [
                {
                    "title": s.title,
                    "url": s.url,
                    "date_text": s.date_text,
                    "entry_type": s.entry_type,
                    "extraction_method": s.extraction_method,
                }
                for s in self.sample_items
            ],
            "rss_or_feed_found": self.rss_or_feed_found,
            "sitemap_investor_url_count": self.sitemap_investor_url_count,
            "json_ld_item_count": self.json_ld_item_count,
            "login_required": self.login_required,
            "paywall_observed": self.paywall_observed,
            "captcha_or_antibot_observed": self.captcha_or_antibot_observed,
            "recommended_execution_mode": self.recommended_execution_mode,
            "trial_v2_allowlist_allowed_now": self.trial_v2_allowlist_allowed_now,
            "next_action": self.next_action,
            "risk_flags": list(self.risk_flags),
            "notes": self.notes,
        }


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


def validate_merck_ir_preflight_result(
    result: MerckIrDedicatedPreflightResult,
) -> list[str]:
    """Validate a merck_ir dedicated preflight result.

    Returns a list of error strings (empty list = pass).
    """
    errors: list[str] = []

    # source_id must be merck_ir
    if result.source_id != M3C_6F1_ALLOWED_SOURCE:
        errors.append(
            f"source_id must be '{M3C_6F1_ALLOWED_SOURCE}', got '{result.source_id}'"
        )

    # trial_v2_allowlist_allowed_now must be False
    if result.trial_v2_allowlist_allowed_now:
        errors.append("trial_v2_allowlist_allowed_now must be False")

    # recommended_execution_mode must be a known value
    if result.recommended_execution_mode not in MERCK_IR_FINAL_DECISIONS:
        errors.append(
            f"recommended_execution_mode '{result.recommended_execution_mode}' "
            f"is not a valid decision"
        )

    # If login/paywall/captcha, must not be scheduled_candidate_round_2
    if result.login_required and result.recommended_execution_mode == "scheduled_candidate_round_2":
        errors.append("login_required=True cannot be scheduled_candidate_round_2")
    if result.paywall_observed and result.recommended_execution_mode == "scheduled_candidate_round_2":
        errors.append("paywall_observed=True cannot be scheduled_candidate_round_2")
    if result.captcha_or_antibot_observed and result.recommended_execution_mode == "scheduled_candidate_round_2":
        errors.append("captcha_or_antibot_observed=True cannot be scheduled_candidate_round_2")

    # valid_item_count / dated_item_count requirements for scheduled
    if result.recommended_execution_mode == "scheduled_candidate_round_2":
        if result.valid_item_count < MIN_VALID_ITEMS_FOR_SCHEDULED:
            errors.append(
                f"valid_item_count {result.valid_item_count} < {MIN_VALID_ITEMS_FOR_SCHEDULED} "
                f"for scheduled_candidate_round_2"
            )
        if result.dated_item_count < MIN_DATED_ITEMS_FOR_SCHEDULED:
            errors.append(
                f"dated_item_count {result.dated_item_count} < {MIN_DATED_ITEMS_FOR_SCHEDULED} "
                f"for scheduled_candidate_round_2"
            )

    # sample_items count
    if len(result.sample_items) > MAX_SAMPLE_ITEMS_RECORDED:
        errors.append(
            f"sample_items count {len(result.sample_items)} exceeds max {MAX_SAMPLE_ITEMS_RECORDED}"
        )

    # Sensitive keyword scan on sample items
    for i, item in enumerate(result.sample_items):
        for field_name in ("title", "url", "date_text"):
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

    return errors


# ---------------------------------------------------------------------------
# Decision computation
# ---------------------------------------------------------------------------


def compute_merck_ir_decision(
    result: MerckIrDedicatedPreflightResult,
) -> MerckIrDedicatedDecision:
    """Compute the recommended execution mode for a merck_ir preflight result.

    Decision rules (in priority order):
        1. login_required or paywall_observed -> login_or_paywall_blocked
        2. captcha_or_antibot_observed -> captcha_or_antibot_blocked
        3. http_status == 0 -> blocked_or_backlog
        4. valid_item_count >= 3 and dated_item_count >= 2 -> scheduled_candidate_round_2
        5. valid_item_count >= 1 -> low_frequency_candidate (if items but not enough/dated)
        6. otherwise -> manual_review_only
    """
    risk_flags: list[str] = []

    # 1. login / paywall
    if result.login_required or result.paywall_observed:
        if result.login_required:
            risk_flags.append("login_required")
        if result.paywall_observed:
            risk_flags.append("paywall_observed")
        return MerckIrDedicatedDecision(
            recommended_execution_mode="login_or_paywall_blocked",
            trial_v2_allowlist_allowed_now=False,
            next_action="exclude_from_automation",
            risk_flags=risk_flags,
        )

    # 2. captcha / anti-bot
    if result.captcha_or_antibot_observed:
        risk_flags.append("captcha_or_antibot_observed")
        return MerckIrDedicatedDecision(
            recommended_execution_mode="captcha_or_antibot_blocked",
            trial_v2_allowlist_allowed_now=False,
            next_action="exclude_from_automation",
            risk_flags=risk_flags,
        )

    # 3. unreachable
    if result.http_status == 0:
        risk_flags.append("unreachable")
        return MerckIrDedicatedDecision(
            recommended_execution_mode="blocked_or_backlog",
            trial_v2_allowlist_allowed_now=False,
            next_action="retry_with_network_troubleshooting",
            risk_flags=risk_flags,
        )

    # 4. scheduled_candidate_round_2
    if (
        result.valid_item_count >= MIN_VALID_ITEMS_FOR_SCHEDULED
        and result.dated_item_count >= MIN_DATED_ITEMS_FOR_SCHEDULED
    ):
        return MerckIrDedicatedDecision(
            recommended_execution_mode="scheduled_candidate_round_2",
            trial_v2_allowlist_allowed_now=False,
            next_action="propose_10_source_preflight",
            risk_flags=[],
        )

    # 5. low_frequency_candidate (some items but not enough for scheduled)
    if result.valid_item_count >= 1:
        if result.dated_item_count < MIN_DATED_ITEMS_FOR_SCHEDULED:
            risk_flags.append("insufficient_dated_items")
        return MerckIrDedicatedDecision(
            recommended_execution_mode="low_frequency_candidate",
            trial_v2_allowlist_allowed_now=False,
            next_action="evaluate_low_frequency_schedule",
            risk_flags=risk_flags,
        )

    # 6. manual_review_only
    if result.valid_item_count == 0:
        risk_flags.append("no_valid_items_extracted")
    return MerckIrDedicatedDecision(
        recommended_execution_mode="manual_review_only",
        trial_v2_allowlist_allowed_now=False,
        next_action="manual_content_extraction_review",
        risk_flags=risk_flags,
    )


def apply_merck_ir_decision(
    result: MerckIrDedicatedPreflightResult,
) -> MerckIrDedicatedPreflightResult:
    """Compute and apply the decision to *result* (in-place)."""
    decision = compute_merck_ir_decision(result)
    result.recommended_execution_mode = decision.recommended_execution_mode
    result.trial_v2_allowlist_allowed_now = decision.trial_v2_allowlist_allowed_now
    result.next_action = decision.next_action
    result.risk_flags = decision.risk_flags
    return result


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def is_merck_ir_source(source_id: str) -> bool:
    """Check if source_id is merck_ir."""
    return source_id == M3C_6F1_ALLOWED_SOURCE


def make_default_merck_ir_result() -> MerckIrDedicatedPreflightResult:
    """Create a default MerckIrDedicatedPreflightResult."""
    return MerckIrDedicatedPreflightResult()


def is_rejected_navigation_title(title: str) -> bool:
    """Check if a title matches a rejected navigation pattern."""
    if not title:
        return True
    lower = title.lower().strip()
    for pattern in REJECT_TITLE_PATTERNS:
        if pattern in lower:
            return True
    return False


def make_batch_report_dict(
    result: MerckIrDedicatedPreflightResult,
    *,
    base_commit: str = "",
    branch: str = "",
    merge_6f_commit: str = "",
    trial_v2_source_count: int = 9,
) -> dict:
    """Build a JSON-serializable batch report dict."""
    return {
        "batch_name": "m3c_6f1_merck_ir_dedicated_preflight",
        "base_commit": base_commit,
        "branch": branch,
        "m3c_6f_merge_commit": merge_6f_commit,
        "trial_v2_source_count": trial_v2_source_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": result.to_dict(),
    }
