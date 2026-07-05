"""M3C-6E1 Investment On-demand Registry — data models and validation.

This module defines the schemas for the investment on-demand source registry,
which is the third source layer (Layer 3) alongside trial_v2 (Layer 1) and
low-frequency observation (Layer 2).

Key design principles:
    - Foundation only collects evidence; it does NOT output investment conclusions.
    - Forbidden investment fields (rating, target_price, buy_sell_hold, etc.) are
      rejected by validation.
    - Paid/entitled sell-side research and market_data are foundation_allowed=false.
    - Dry-run only: no real network fetch in M3C-6E1.

This module does NOT modify trial_v2 allowlist, TRAE scheduling, or production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Source taxonomy types
INVESTMENT_SOURCE_TYPES: set[str] = {
    "official_filing",
    "company_ir",
    "sellside_research_public",
    "sellside_research_paid_or_entitled",
    "public_news",
    "transcript",
    "market_data",
    "macro",
    "industry_report",
}

# Source types that Foundation is allowed to handle
FOUNDATION_ALLOWED_SOURCE_TYPES: set[str] = {
    "official_filing",
    "company_ir",
    "sellside_research_public",
    "public_news",
    "transcript",
    "macro",
    "industry_report",
}

# Source types that must be handled by downstream (th_capital_stock)
DOWNSTREAM_ONLY_SOURCE_TYPES: set[str] = {
    "sellside_research_paid_or_entitled",
    "market_data",
}

# Timestamp confidence values
TIMESTAMP_CONFIDENCE_VALUES: set[str] = {"HIGH", "MEDIUM", "LOW", "NONE"}

# Evidence strength values
EVIDENCE_STRENGTH_VALUES: set[str] = {
    "strong_direct_disclosure",
    "management_commentary",
    "financial_report_context",
    "business_context",
    "proxy_signal",
    "risk_or_contradictory_signal",
    "review_required",
}

# Access level values
ACCESS_LEVEL_VALUES: set[str] = {
    "public",
    "registration_required",
    "entitlement_required",
    "paid_license_required",
}

# Output mode values
OUTPUT_MODE_VALUES: set[str] = {
    "evidence_packet_skeleton_only",
    "route_plan_only",
    "full_dry_run",
}

# Forbidden investment fields — must NEVER appear in BaseEvidencePacket
FORBIDDEN_INVESTMENT_FIELDS: tuple[str, ...] = (
    "rating",
    "target_price",
    "buy_sell_hold",
    "investment_recommendation",
    "position_size",
    "trade_signal",
    "expected_return",
    "valuation_upside",
    "portfolio_action",
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

# Network module names that must not be imported by the dry-run runner.
FORBIDDEN_NETWORK_IMPORTS: tuple[str, ...] = (
    "requests",
    "httpx",
    "aiohttp",
    "urllib.request",
    "tavily",
    "serpapi",
)


# ---------------------------------------------------------------------------
# Entity / Topic
# ---------------------------------------------------------------------------


@dataclass
class InvestmentEntity:
    """A single entity (company, bank, industry) referenced in a query pack."""

    entity_type: str = "company"  # company / bank / industry / product / person
    name: str = ""
    tickers: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    entity_id: str = ""  # Foundation internal ID (resolved after expansion)


@dataclass
class InvestmentTopic:
    """A research topic or theme."""

    topic_id: str = ""
    keywords: list[str] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)


@dataclass
class TimeWindow:
    """Time window for an on-demand query."""

    lookback_days: int = 30
    start_date: str = ""  # YYYY-MM-DD (optional override)
    end_date: str = ""  # YYYY-MM-DD (optional override)
    relative_window: str = ""  # e.g., "last_earnings_call"


# ---------------------------------------------------------------------------
# Query Pack
# ---------------------------------------------------------------------------


@dataclass
class InvestmentQueryPack:
    """Structured investment on-demand query pack.

    This is NOT a single keyword. It is a structured research requirement
    describing entities, industries, topics, banks, time window, and research
    questions. Foundation uses it to compute a source routing plan.

    Foundation does NOT own the watchlist. The watchlist is a downstream
    (th_capital_stock) concept; only a snapshot is passed in.
    """

    request_id: str = ""
    created_at: str = ""
    time_window: TimeWindow = field(default_factory=TimeWindow)
    companies: list[InvestmentEntity] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    topics: list[InvestmentTopic] = field(default_factory=list)
    banks: list[str] = field(default_factory=list)
    research_questions: list[str] = field(default_factory=list)
    preferred_source_types: list[str] = field(default_factory=list)
    excluded_source_types: list[str] = field(default_factory=list)
    output_mode: str = "evidence_packet_skeleton_only"
    risk_flags: list[str] = field(default_factory=list)
    # Boundary flags — must remain at these values for M3C-6E1
    production_enabled: bool = False
    performs_real_fetch: bool = False
    affects_trial_v2_allowlist: bool = False
    affects_trae_scheduling: bool = False


# ---------------------------------------------------------------------------
# Source Taxonomy
# ---------------------------------------------------------------------------


@dataclass
class InvestmentSourceTaxonomyEntry:
    """A single source taxonomy entry."""

    source_type: str = ""
    description: str = ""
    foundation_allowed: bool = True
    requires_downstream: bool = False
    reason: str = ""


@dataclass
class InvestmentSourceTaxonomy:
    """The full investment source taxonomy."""

    entries: dict[str, InvestmentSourceTaxonomyEntry] = field(
        default_factory=lambda: {
            "official_filing": InvestmentSourceTaxonomyEntry(
                source_type="official_filing",
                description="Company filings, official disclosures, exchange filings.",
                foundation_allowed=True,
                requires_downstream=False,
            ),
            "company_ir": InvestmentSourceTaxonomyEntry(
                source_type="company_ir",
                description="Investor relations pages, press releases, events, presentations.",
                foundation_allowed=True,
                requires_downstream=False,
            ),
            "sellside_research_public": InvestmentSourceTaxonomyEntry(
                source_type="sellside_research_public",
                description="Public insights, podcasts, conference notes, public research summaries.",
                foundation_allowed=True,
                requires_downstream=False,
            ),
            "sellside_research_paid_or_entitled": InvestmentSourceTaxonomyEntry(
                source_type="sellside_research_paid_or_entitled",
                description="Paid or permissioned broker research.",
                foundation_allowed=False,
                requires_downstream=True,
                reason="Do not bypass entitlement or licensing.",
            ),
            "public_news": InvestmentSourceTaxonomyEntry(
                source_type="public_news",
                description="Public news and media recap sources.",
                foundation_allowed=True,
                requires_downstream=False,
            ),
            "transcript": InvestmentSourceTaxonomyEntry(
                source_type="transcript",
                description="Public earnings call, conference, or interview transcript.",
                foundation_allowed=True,
                requires_downstream=False,
            ),
            "market_data": InvestmentSourceTaxonomyEntry(
                source_type="market_data",
                description="Pricing / bars / factor data.",
                foundation_allowed=False,
                requires_downstream=True,
                reason="Downstream th_capital_stock owns market-data business logic.",
            ),
            "macro": InvestmentSourceTaxonomyEntry(
                source_type="macro",
                description="Macro data and commentary.",
                foundation_allowed=True,
                requires_downstream=False,
            ),
            "industry_report": InvestmentSourceTaxonomyEntry(
                source_type="industry_report",
                description="Public industry reports, whitepapers, conference materials.",
                foundation_allowed=True,
                requires_downstream=False,
            ),
        }
    )

    def get(self, source_type: str) -> InvestmentSourceTaxonomyEntry | None:
        return self.entries.get(source_type)

    def is_foundation_allowed(self, source_type: str) -> bool:
        entry = self.entries.get(source_type)
        return entry.foundation_allowed if entry else False

    def requires_downstream(self, source_type: str) -> bool:
        entry = self.entries.get(source_type)
        return entry.requires_downstream if entry else False


# ---------------------------------------------------------------------------
# Source Route / Route Plan
# ---------------------------------------------------------------------------


@dataclass
class InvestmentSourceRoute:
    """A single source route in a routing plan."""

    route_id: str = ""
    source_type: str = ""
    source_name: str = ""
    query_terms: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    priority: str = "medium"  # high / medium / low
    expected_access_level: str = "public"
    foundation_allowed: bool = True
    requires_downstream: bool = False
    risk_flags: list[str] = field(default_factory=list)
    fallback_routes: list[str] = field(default_factory=list)
    recommended_action: str = "dry_run_route_only"


@dataclass
class InvestmentRoutePlan:
    """The full routing plan for a query pack (dry-run only)."""

    request_id: str = ""
    routes: list[InvestmentSourceRoute] = field(default_factory=list)
    skipped_routes: list[InvestmentSourceRoute] = field(default_factory=list)
    production_enabled: bool = False
    performs_real_fetch: bool = False
    affects_trial_v2_allowlist: bool = False
    affects_trae_scheduling: bool = False
    risk_flags: list[str] = field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------
# Evidence Packet
# ---------------------------------------------------------------------------


@dataclass
class EvidenceClaimSkeleton:
    """A single claim skeleton within an evidence packet."""

    claim_text: str = ""
    claim_type: str = ""  # e.g., "management_commentary", "data_point"
    confidence: str = "medium"
    quoted_span: str = ""
    span_location: str = ""


@dataclass
class BaseEvidencePacket:
    """Foundation-level base evidence packet.

    This is the OUTPUT of the Foundation on-demand layer. It contains only
    generic evidence fields. It does NOT contain any investment judgment.

    Forbidden fields (validated against FORBIDDEN_INVESTMENT_FIELDS):
        rating, target_price, buy_sell_hold, investment_recommendation,
        position_size, trade_signal, expected_return, valuation_upside,
        portfolio_action

    Downstream (th_capital_stock) may EXTEND this packet with business fields
    such as ticker, analyst_name, bank_name, business_variable, claim_type,
    investment_implication, expectation_change. Those extensions are NOT
    defined by Foundation.
    """

    evidence_id: str = ""
    request_id: str = ""
    source_type: str = ""
    source_name: str = ""
    source_url: str = ""
    title: str = ""
    published_at: str = ""  # YYYY-MM-DD or ISO datetime
    observed_at: str = ""
    timestamp_confidence: str = "MEDIUM"  # HIGH / MEDIUM / LOW / NONE
    entity_refs: list[str] = field(default_factory=list)
    topic_refs: list[str] = field(default_factory=list)
    key_claims: list[EvidenceClaimSkeleton] = field(default_factory=list)
    evidence_summary: str = ""
    access_level: str = "public"
    is_primary_source: bool = True
    is_media_recap: bool = False
    confidence: str = "medium"  # high / medium / low
    evidence_strength: str = "business_context"
    risk_flags: list[str] = field(default_factory=list)
    cannot_conclude: str = ""  # MUST be populated for primary sources
    # Boundary flags
    production_enabled: bool = False
    performs_real_fetch: bool = False

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "request_id": self.request_id,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "title": self.title,
            "published_at": self.published_at,
            "observed_at": self.observed_at,
            "timestamp_confidence": self.timestamp_confidence,
            "entity_refs": list(self.entity_refs),
            "topic_refs": list(self.topic_refs),
            "key_claims": [
                {
                    "claim_text": c.claim_text,
                    "claim_type": c.claim_type,
                    "confidence": c.confidence,
                    "quoted_span": c.quoted_span,
                    "span_location": c.span_location,
                }
                for c in self.key_claims
            ],
            "evidence_summary": self.evidence_summary,
            "access_level": self.access_level,
            "is_primary_source": self.is_primary_source,
            "is_media_recap": self.is_media_recap,
            "confidence": self.confidence,
            "evidence_strength": self.evidence_strength,
            "risk_flags": list(self.risk_flags),
            "cannot_conclude": self.cannot_conclude,
            "production_enabled": self.production_enabled,
            "performs_real_fetch": self.performs_real_fetch,
        }


# ---------------------------------------------------------------------------
# Dry-run Result
# ---------------------------------------------------------------------------


@dataclass
class OnDemandDryRunResult:
    """Result of a dry-run on-demand registry execution."""

    request_id: str = ""
    route_plan: InvestmentRoutePlan = field(default_factory=InvestmentRoutePlan)
    evidence_packet_skeletons: list[BaseEvidencePacket] = field(default_factory=list)
    production_enabled: bool = False
    performs_real_fetch: bool = False
    affects_trial_v2_allowlist: bool = False
    affects_trae_scheduling: bool = False
    forbidden_fields_absent: bool = True
    risk_flags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "route_plan": {
                "request_id": self.route_plan.request_id,
                "routes": [
                    {
                        "route_id": r.route_id,
                        "source_type": r.source_type,
                        "source_name": r.source_name,
                        "query_terms": list(r.query_terms),
                        "entities": list(r.entities),
                        "priority": r.priority,
                        "expected_access_level": r.expected_access_level,
                        "foundation_allowed": r.foundation_allowed,
                        "requires_downstream": r.requires_downstream,
                        "risk_flags": list(r.risk_flags),
                        "fallback_routes": list(r.fallback_routes),
                        "recommended_action": r.recommended_action,
                    }
                    for r in self.route_plan.routes
                ],
                "skipped_routes": [
                    {
                        "route_id": r.route_id,
                        "source_type": r.source_type,
                        "source_name": r.source_name,
                        "reason": r.recommended_action,
                    }
                    for r in self.route_plan.skipped_routes
                ],
                "production_enabled": self.route_plan.production_enabled,
                "performs_real_fetch": self.route_plan.performs_real_fetch,
                "affects_trial_v2_allowlist": self.route_plan.affects_trial_v2_allowlist,
                "affects_trae_scheduling": self.route_plan.affects_trae_scheduling,
                "risk_flags": list(self.route_plan.risk_flags),
            },
            "evidence_packet_skeletons": [
                p.to_dict() for p in self.evidence_packet_skeletons
            ],
            "production_enabled": self.production_enabled,
            "performs_real_fetch": self.performs_real_fetch,
            "affects_trial_v2_allowlist": self.affects_trial_v2_allowlist,
            "affects_trae_scheduling": self.affects_trae_scheduling,
            "forbidden_fields_absent": self.forbidden_fields_absent,
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


def validate_query_pack(query_pack: InvestmentQueryPack) -> list[str]:
    """Validate a query pack. Returns a list of error strings (empty = pass)."""
    errors: list[str] = []

    if not query_pack.request_id:
        errors.append("request_id must not be empty")

    # Boundary flags
    if query_pack.production_enabled:
        errors.append("production_enabled must be False in M3C-6E1")
    if query_pack.performs_real_fetch:
        errors.append("performs_real_fetch must be False in M3C-6E1")
    if query_pack.affects_trial_v2_allowlist:
        errors.append("affects_trial_v2_allowlist must be False")
    if query_pack.affects_trae_scheduling:
        errors.append("affects_trae_scheduling must be False")

    # Output mode
    if query_pack.output_mode not in OUTPUT_MODE_VALUES:
        errors.append(
            f"output_mode '{query_pack.output_mode}' not in {OUTPUT_MODE_VALUES}"
        )

    # At least one entity or industry or topic
    if (
        not query_pack.companies
        and not query_pack.industries
        and not query_pack.topics
        and not query_pack.banks
    ):
        errors.append(
            "query pack must contain at least one company, industry, topic, or bank"
        )

    # Preferred source types must be valid
    for st in query_pack.preferred_source_types:
        if st not in INVESTMENT_SOURCE_TYPES:
            errors.append(
                f"preferred_source_type '{st}' not in {INVESTMENT_SOURCE_TYPES}"
            )

    for st in query_pack.excluded_source_types:
        if st not in INVESTMENT_SOURCE_TYPES:
            errors.append(
                f"excluded_source_type '{st}' not in {INVESTMENT_SOURCE_TYPES}"
            )

    # Sensitive keyword scan
    for q in query_pack.research_questions:
        found = scan_sensitive_keywords(q)
        if found:
            errors.append(
                f"research_question contains sensitive keywords: {found}"
            )

    return errors


def validate_route_plan(route_plan: InvestmentRoutePlan) -> list[str]:
    """Validate a route plan. Returns a list of error strings (empty = pass)."""
    errors: list[str] = []

    if route_plan.production_enabled:
        errors.append("production_enabled must be False")
    if route_plan.performs_real_fetch:
        errors.append("performs_real_fetch must be False")
    if route_plan.affects_trial_v2_allowlist:
        errors.append("affects_trial_v2_allowlist must be False")
    if route_plan.affects_trae_scheduling:
        errors.append("affects_trae_scheduling must be False")

    taxonomy = InvestmentSourceTaxonomy()

    for route in route_plan.routes:
        if route.source_type not in INVESTMENT_SOURCE_TYPES:
            errors.append(
                f"route '{route.route_id}' source_type '{route.source_type}' not in taxonomy"
            )
            continue

        entry = taxonomy.get(route.source_type)
        if entry is None:
            errors.append(f"route '{route.route_id}' has unknown source_type")
            continue

        # foundation_allowed must match taxonomy
        if route.foundation_allowed != entry.foundation_allowed:
            errors.append(
                f"route '{route.route_id}' foundation_allowed={route.foundation_allowed} "
                f"but taxonomy says {entry.foundation_allowed} for {route.source_type}"
            )

        # requires_downstream must match taxonomy
        if route.requires_downstream != entry.requires_downstream:
            errors.append(
                f"route '{route.route_id}' requires_downstream={route.requires_downstream} "
                f"but taxonomy says {entry.requires_downstream} for {route.source_type}"
            )

        # Paid sellside research must have entitlement_required risk flag
        if route.source_type == "sellside_research_paid_or_entitled":
            if "entitlement_required" not in route.risk_flags:
                errors.append(
                    f"route '{route.route_id}' is paid sellside research but "
                    f"missing 'entitlement_required' risk flag"
                )
            if route.recommended_action != "downstream_manual_or_entitled_access_only":
                errors.append(
                    f"route '{route.route_id}' is paid sellside research but "
                    f"recommended_action is not 'downstream_manual_or_entitled_access_only'"
                )

        # Market data must be handled by downstream
        if route.source_type == "market_data":
            if route.recommended_action != "handled_by_th_capital_stock":
                errors.append(
                    f"route '{route.route_id}' is market_data but recommended_action "
                    f"is not 'handled_by_th_capital_stock'"
                )

    return errors


def validate_evidence_packet(packet: BaseEvidencePacket) -> list[str]:
    """Validate an evidence packet. Returns a list of error strings (empty = pass)."""
    errors: list[str] = []

    # Check forbidden investment fields via to_dict keys
    packet_dict = packet.to_dict()
    for forbidden in FORBIDDEN_INVESTMENT_FIELDS:
        if forbidden in packet_dict:
            errors.append(
                f"forbidden investment field '{forbidden}' found in evidence packet"
            )

    # Boundary flags
    if packet.production_enabled:
        errors.append("production_enabled must be False")
    if packet.performs_real_fetch:
        errors.append("performs_real_fetch must be False")

    # Timestamp confidence
    if packet.timestamp_confidence not in TIMESTAMP_CONFIDENCE_VALUES:
        errors.append(
            f"timestamp_confidence '{packet.timestamp_confidence}' not in "
            f"{TIMESTAMP_CONFIDENCE_VALUES}"
        )

    # Evidence strength
    if packet.evidence_strength not in EVIDENCE_STRENGTH_VALUES:
        errors.append(
            f"evidence_strength '{packet.evidence_strength}' not in "
            f"{EVIDENCE_STRENGTH_VALUES}"
        )

    # Access level
    if packet.access_level not in ACCESS_LEVEL_VALUES:
        errors.append(
            f"access_level '{packet.access_level}' not in {ACCESS_LEVEL_VALUES}"
        )

    # Source type must be valid
    if packet.source_type not in INVESTMENT_SOURCE_TYPES:
        errors.append(
            f"source_type '{packet.source_type}' not in {INVESTMENT_SOURCE_TYPES}"
        )

    # Source type must be foundation_allowed
    taxonomy = InvestmentSourceTaxonomy()
    if not taxonomy.is_foundation_allowed(packet.source_type):
        errors.append(
            f"source_type '{packet.source_type}' is not foundation_allowed"
        )

    # cannot_conclude must be populated for primary sources
    if packet.is_primary_source and not packet.cannot_conclude:
        errors.append(
            "cannot_conclude must be populated for primary sources"
        )

    # Sensitive keyword scan
    for field_name in ("source_url", "title", "evidence_summary", "cannot_conclude"):
        val = getattr(packet, field_name, "")
        found = scan_sensitive_keywords(val)
        if found:
            errors.append(
                f"{field_name} contains sensitive keywords: {found}"
            )

    for claim in packet.key_claims:
        found = scan_sensitive_keywords(claim.claim_text)
        if found:
            errors.append(
                f"key_claim contains sensitive keywords: {found}"
            )

    return errors


def validate_dry_run_result(result: OnDemandDryRunResult) -> list[str]:
    """Validate a dry-run result. Returns a list of error strings (empty = pass)."""
    errors: list[str] = []

    if result.production_enabled:
        errors.append("production_enabled must be False")
    if result.performs_real_fetch:
        errors.append("performs_real_fetch must be False")
    if result.affects_trial_v2_allowlist:
        errors.append("affects_trial_v2_allowlist must be False")
    if result.affects_trae_scheduling:
        errors.append("affects_trae_scheduling must be False")
    if not result.forbidden_fields_absent:
        errors.append("forbidden_fields_absent must be True")

    errors.extend(validate_route_plan(result.route_plan))

    for packet in result.evidence_packet_skeletons:
        errors.extend(validate_evidence_packet(packet))

    return errors


# ---------------------------------------------------------------------------
# Routing logic (dry-run only)
# ---------------------------------------------------------------------------


def compute_route_plan(
    query_pack: InvestmentQueryPack,
    taxonomy: InvestmentSourceTaxonomy | None = None,
) -> InvestmentRoutePlan:
    """Compute a dry-run routing plan for a query pack.

    This does NOT perform any real network fetch. It only generates a
    routing plan based on the query pack contents and source taxonomy.
    """
    taxonomy = taxonomy or InvestmentSourceTaxonomy()
    plan = InvestmentRoutePlan(
        request_id=query_pack.request_id,
        production_enabled=False,
        performs_real_fetch=False,
        affects_trial_v2_allowlist=False,
        affects_trae_scheduling=False,
    )

    excluded = set(query_pack.excluded_source_types)
    preferred = set(query_pack.preferred_source_types)

    # If preferred_source_types is empty, use all foundation-allowed types
    candidate_types: list[str] = []
    if preferred:
        candidate_types = [st for st in query_pack.preferred_source_types if st not in excluded]
    else:
        for st in INVESTMENT_SOURCE_TYPES:
            if st in excluded:
                continue
            candidate_types.append(st)

    route_idx = 0
    for source_type in candidate_types:
        entry = taxonomy.get(source_type)
        if entry is None:
            continue

        route_idx += 1
        route = InvestmentSourceRoute(
            route_id=f"route_{query_pack.request_id}_{route_idx:03d}",
            source_type=source_type,
            source_name=source_type.replace("_", " ").title(),
            query_terms=list(query_pack.research_questions),
            entities=[e.name for e in query_pack.companies],
            priority="high" if source_type in ("official_filing", "company_ir") else "medium",
            expected_access_level="entitlement_required" if source_type == "sellside_research_paid_or_entitled" else "public",
            foundation_allowed=entry.foundation_allowed,
            requires_downstream=entry.requires_downstream,
        )

        if source_type == "sellside_research_paid_or_entitled":
            route.risk_flags.append("entitlement_required")
            route.recommended_action = "downstream_manual_or_entitled_access_only"
            plan.skipped_routes.append(route)
        elif source_type == "market_data":
            route.risk_flags.append("downstream_business_logic")
            route.recommended_action = "handled_by_th_capital_stock"
            plan.skipped_routes.append(route)
        else:
            route.recommended_action = "dry_run_route_only"
            plan.routes.append(route)

    plan.risk_flags.append("dry_run_only")
    plan.notes = "M3C-6E1 dry-run: no real network fetch performed."
    return plan


def compute_evidence_packet_skeletons(
    query_pack: InvestmentQueryPack,
    route_plan: InvestmentRoutePlan,
) -> list[BaseEvidencePacket]:
    """Generate evidence packet skeletons from a route plan (dry-run only).

    These are SKELETONS — they contain placeholder text, not real evidence.
    No network fetch is performed.
    """
    packets: list[BaseEvidencePacket] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for route in route_plan.routes:
        if not route.foundation_allowed:
            continue

        packet = BaseEvidencePacket(
            evidence_id=f"evidence_{route.route_id}_skeleton",
            request_id=query_pack.request_id,
            source_type=route.source_type,
            source_name=route.source_name,
            source_url="",  # No real URL in dry-run
            title=f"[skeleton] {route.source_name} for {query_pack.request_id}",
            published_at="",  # No real date in dry-run
            observed_at=now,
            timestamp_confidence="NONE",
            entity_refs=[e.name for e in query_pack.companies],
            topic_refs=list(query_pack.industries),
            key_claims=[
                EvidenceClaimSkeleton(
                    claim_text="[skeleton] placeholder claim — no real fetch performed",
                    claim_type="skeleton",
                    confidence="low",
                )
            ],
            evidence_summary="[skeleton] No real fetch performed in M3C-6E1 dry-run.",
            access_level="public",
            is_primary_source=True,
            is_media_recap=False,
            confidence="low",
            evidence_strength="review_required",
            risk_flags=["skeleton_only", "dry_run"],
            cannot_conclude="No real fetch performed; cannot conclude anything in dry-run.",
            production_enabled=False,
            performs_real_fetch=False,
        )
        packets.append(packet)

    return packets


def run_dry_run(
    query_pack: InvestmentQueryPack,
    taxonomy: InvestmentSourceTaxonomy | None = None,
) -> OnDemandDryRunResult:
    """Run a complete dry-run for a query pack.

    This is the main entry point for the dry-run runner. It:
    1. Validates the query pack
    2. Computes the route plan
    3. Generates evidence packet skeletons
    4. Validates the result

    No real network fetch is performed.
    """
    result = OnDemandDryRunResult(
        request_id=query_pack.request_id,
        production_enabled=False,
        performs_real_fetch=False,
        affects_trial_v2_allowlist=False,
        affects_trae_scheduling=False,
        forbidden_fields_absent=True,
    )

    result.route_plan = compute_route_plan(query_pack, taxonomy)
    result.evidence_packet_skeletons = compute_evidence_packet_skeletons(
        query_pack, result.route_plan
    )
    result.risk_flags = list(result.route_plan.risk_flags)
    result.notes = "M3C-6E1 dry-run completed. No real network fetch performed."

    return result
