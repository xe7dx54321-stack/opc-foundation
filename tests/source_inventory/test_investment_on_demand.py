"""Tests for M3C-6E1 Investment On-demand Registry data models."""

from __future__ import annotations

import pytest

from opc_foundation.source_inventory.investment_on_demand import (
    ACCESS_LEVEL_VALUES,
    BaseEvidencePacket,
    DOWNSTREAM_ONLY_SOURCE_TYPES,
    EVIDENCE_STRENGTH_VALUES,
    EvidenceClaimSkeleton,
    FORBIDDEN_INVESTMENT_FIELDS,
    FORBIDDEN_NETWORK_IMPORTS,
    FOUNDATION_ALLOWED_SOURCE_TYPES,
    INVESTMENT_SOURCE_TYPES,
    InvestmentEntity,
    InvestmentQueryPack,
    InvestmentRoutePlan,
    InvestmentSourceRoute,
    InvestmentSourceTaxonomy,
    InvestmentSourceTaxonomyEntry,
    InvestmentTopic,
    OUTPUT_MODE_VALUES,
    OnDemandDryRunResult,
    SENSITIVE_KEYWORDS,
    TIMESTAMP_CONFIDENCE_VALUES,
    TimeWindow,
    compute_evidence_packet_skeletons,
    compute_route_plan,
    run_dry_run,
    scan_sensitive_keywords,
    validate_dry_run_result,
    validate_evidence_packet,
    validate_query_pack,
    validate_route_plan,
)


class TestSourceTaxonomy:
    """Source taxonomy enums and categories."""

    def test_all_source_types_defined(self):
        taxonomy = InvestmentSourceTaxonomy()
        for st in INVESTMENT_SOURCE_TYPES:
            assert taxonomy.get(st) is not None, f"{st} missing from taxonomy"

    def test_foundation_allowed_types(self):
        taxonomy = InvestmentSourceTaxonomy()
        for st in FOUNDATION_ALLOWED_SOURCE_TYPES:
            assert taxonomy.is_foundation_allowed(st) is True

    def test_downstream_only_types(self):
        taxonomy = InvestmentSourceTaxonomy()
        for st in DOWNSTREAM_ONLY_SOURCE_TYPES:
            assert taxonomy.is_foundation_allowed(st) is False

    def test_paid_sellside_research_not_foundation_allowed(self):
        taxonomy = InvestmentSourceTaxonomy()
        assert taxonomy.is_foundation_allowed("sellside_research_paid_or_entitled") is False

    def test_paid_sellside_research_requires_downstream(self):
        taxonomy = InvestmentSourceTaxonomy()
        assert taxonomy.requires_downstream("sellside_research_paid_or_entitled") is True

    def test_market_data_not_foundation_allowed(self):
        taxonomy = InvestmentSourceTaxonomy()
        assert taxonomy.is_foundation_allowed("market_data") is False

    def test_market_data_requires_downstream(self):
        taxonomy = InvestmentSourceTaxonomy()
        assert taxonomy.requires_downstream("market_data") is True

    def test_official_filing_foundation_allowed(self):
        taxonomy = InvestmentSourceTaxonomy()
        assert taxonomy.is_foundation_allowed("official_filing") is True


class TestQueryPackValidation:
    """Query Pack schema validation."""

    def _make_valid_query_pack(self) -> InvestmentQueryPack:
        return InvestmentQueryPack(
            request_id="test_query_001",
            companies=[InvestmentEntity(name="TestCo", tickers=["TST"])],
            industries=["AI"],
            research_questions=["What is the outlook?"],
            output_mode="evidence_packet_skeleton_only",
        )

    def test_valid_query_pack_passes(self):
        qp = self._make_valid_query_pack()
        errors = validate_query_pack(qp)
        assert errors == []

    def test_empty_request_id_fails(self):
        qp = self._make_valid_query_pack()
        qp.request_id = ""
        errors = validate_query_pack(qp)
        assert any("request_id" in e for e in errors)

    def test_production_enabled_fails(self):
        qp = self._make_valid_query_pack()
        qp.production_enabled = True
        errors = validate_query_pack(qp)
        assert any("production_enabled" in e for e in errors)

    def test_performs_real_fetch_fails(self):
        qp = self._make_valid_query_pack()
        qp.performs_real_fetch = True
        errors = validate_query_pack(qp)
        assert any("performs_real_fetch" in e for e in errors)

    def test_affects_trial_v2_allowlist_fails(self):
        qp = self._make_valid_query_pack()
        qp.affects_trial_v2_allowlist = True
        errors = validate_query_pack(qp)
        assert any("affects_trial_v2_allowlist" in e for e in errors)

    def test_affects_trae_scheduling_fails(self):
        qp = self._make_valid_query_pack()
        qp.affects_trae_scheduling = True
        errors = validate_query_pack(qp)
        assert any("affects_trae_scheduling" in e for e in errors)

    def test_no_entities_fails(self):
        qp = self._make_valid_query_pack()
        qp.companies = []
        qp.industries = []
        qp.topics = []
        qp.banks = []
        errors = validate_query_pack(qp)
        assert any("at least one" in e for e in errors)

    def test_invalid_output_mode_fails(self):
        qp = self._make_valid_query_pack()
        qp.output_mode = "invalid_mode"
        errors = validate_query_pack(qp)
        assert any("output_mode" in e for e in errors)

    def test_invalid_preferred_source_type_fails(self):
        qp = self._make_valid_query_pack()
        qp.preferred_source_types = ["invalid_type"]
        errors = validate_query_pack(qp)
        assert any("preferred_source_type" in e for e in errors)

    def test_sensitive_keyword_in_research_question_fails(self):
        qp = self._make_valid_query_pack()
        qp.research_questions = ["What is the api_key=secret123?"]
        errors = validate_query_pack(qp)
        assert any("sensitive" in e for e in errors)


class TestDynamicWatchlistInput:
    """Dynamic watchlist is only input snapshot, not owned by Foundation."""

    def test_watchlist_not_stored_in_foundation(self):
        qp = InvestmentQueryPack(
            request_id="test_watchlist_001",
            companies=[InvestmentEntity(name="TestCo")],
        )
        # Query pack has no watchlist_id field — Foundation does not own watchlist
        assert not hasattr(qp, "watchlist_id")
        assert not hasattr(qp, "watchlist_persistent_storage")

    def test_query_pack_is_snapshot_only(self):
        qp = InvestmentQueryPack(
            request_id="test_snapshot_001",
            companies=[InvestmentEntity(name="TestCo")],
        )
        # No persistence mechanism in query pack
        assert qp.request_id.startswith("test_")
        assert qp.performs_real_fetch is False


class TestRoutePlan:
    """Route plan computation and validation."""

    def _make_valid_query_pack(self) -> InvestmentQueryPack:
        return InvestmentQueryPack(
            request_id="test_route_001",
            companies=[InvestmentEntity(name="NVIDIA", tickers=["NVDA"])],
            industries=["AI optical interconnect"],
            banks=["Goldman Sachs"],
            research_questions=["What is the outlook?"],
        )

    def test_route_plan_generated(self):
        qp = self._make_valid_query_pack()
        plan = compute_route_plan(qp)
        assert plan.request_id == qp.request_id
        assert len(plan.routes) > 0

    def test_route_plan_no_real_fetch(self):
        qp = self._make_valid_query_pack()
        plan = compute_route_plan(qp)
        assert plan.performs_real_fetch is False

    def test_route_plan_production_disabled(self):
        qp = self._make_valid_query_pack()
        plan = compute_route_plan(qp)
        assert plan.production_enabled is False

    def test_route_plan_does_not_affect_trial_v2(self):
        qp = self._make_valid_query_pack()
        plan = compute_route_plan(qp)
        assert plan.affects_trial_v2_allowlist is False

    def test_paid_sellside_skipped(self):
        qp = self._make_valid_query_pack()
        plan = compute_route_plan(qp)
        skipped_types = [r.source_type for r in plan.skipped_routes]
        assert "sellside_research_paid_or_entitled" in skipped_types

    def test_market_data_skipped(self):
        qp = self._make_valid_query_pack()
        plan = compute_route_plan(qp)
        skipped_types = [r.source_type for r in plan.skipped_routes]
        assert "market_data" in skipped_types

    def test_paid_sellside_has_entitlement_flag(self):
        qp = self._make_valid_query_pack()
        plan = compute_route_plan(qp)
        for route in plan.skipped_routes:
            if route.source_type == "sellside_research_paid_or_entitled":
                assert "entitlement_required" in route.risk_flags

    def test_market_data_recommended_action(self):
        qp = self._make_valid_query_pack()
        plan = compute_route_plan(qp)
        for route in plan.skipped_routes:
            if route.source_type == "market_data":
                assert route.recommended_action == "handled_by_th_capital_stock"

    def test_route_plan_validation_passes(self):
        qp = self._make_valid_query_pack()
        plan = compute_route_plan(qp)
        errors = validate_route_plan(plan)
        assert errors == []


class TestEvidencePacket:
    """Base Evidence Packet schema and forbidden fields."""

    def _make_valid_packet(self) -> BaseEvidencePacket:
        return BaseEvidencePacket(
            evidence_id="ev_001",
            request_id="req_001",
            source_type="official_filing",
            source_name="SEC Filing",
            title="Test Filing",
            timestamp_confidence="MEDIUM",
            evidence_strength="strong_direct_disclosure",
            access_level="public",
            cannot_conclude="Cannot conclude investment recommendation from this evidence.",
        )

    def test_valid_packet_passes(self):
        packet = self._make_valid_packet()
        errors = validate_evidence_packet(packet)
        assert errors == []

    def test_forbidden_fields_list(self):
        assert "rating" in FORBIDDEN_INVESTMENT_FIELDS
        assert "target_price" in FORBIDDEN_INVESTMENT_FIELDS
        assert "buy_sell_hold" in FORBIDDEN_INVESTMENT_FIELDS
        assert "investment_recommendation" in FORBIDDEN_INVESTMENT_FIELDS
        assert "position_size" in FORBIDDEN_INVESTMENT_FIELDS
        assert "trade_signal" in FORBIDDEN_INVESTMENT_FIELDS

    def test_packet_to_dict_no_forbidden_fields(self):
        packet = self._make_valid_packet()
        d = packet.to_dict()
        for forbidden in FORBIDDEN_INVESTMENT_FIELDS:
            assert forbidden not in d, f"forbidden field '{forbidden}' in packet dict"

    def test_production_enabled_fails(self):
        packet = self._make_valid_packet()
        packet.production_enabled = True
        errors = validate_evidence_packet(packet)
        assert any("production_enabled" in e for e in errors)

    def test_performs_real_fetch_fails(self):
        packet = self._make_valid_packet()
        packet.performs_real_fetch = True
        errors = validate_evidence_packet(packet)
        assert any("performs_real_fetch" in e for e in errors)

    def test_invalid_source_type_fails(self):
        packet = self._make_valid_packet()
        packet.source_type = "invalid_type"
        errors = validate_evidence_packet(packet)
        assert any("source_type" in e for e in errors)

    def test_paid_sellside_source_fails(self):
        packet = self._make_valid_packet()
        packet.source_type = "sellside_research_paid_or_entitled"
        errors = validate_evidence_packet(packet)
        assert any("not foundation_allowed" in e for e in errors)

    def test_market_data_source_fails(self):
        packet = self._make_valid_packet()
        packet.source_type = "market_data"
        errors = validate_evidence_packet(packet)
        assert any("not foundation_allowed" in e for e in errors)

    def test_missing_cannot_conclude_for_primary_fails(self):
        packet = self._make_valid_packet()
        packet.cannot_conclude = ""
        errors = validate_evidence_packet(packet)
        assert any("cannot_conclude" in e for e in errors)

    def test_non_primary_without_cannot_conclude_ok(self):
        packet = self._make_valid_packet()
        packet.is_primary_source = False
        packet.cannot_conclude = ""
        errors = validate_evidence_packet(packet)
        assert not any("cannot_conclude" in e for e in errors)

    def test_invalid_timestamp_confidence_fails(self):
        packet = self._make_valid_packet()
        packet.timestamp_confidence = "INVALID"
        errors = validate_evidence_packet(packet)
        assert any("timestamp_confidence" in e for e in errors)

    def test_sensitive_keyword_in_title_fails(self):
        packet = self._make_valid_packet()
        packet.title = "Report with api_key=secret123"
        errors = validate_evidence_packet(packet)
        assert any("sensitive" in e for e in errors)


class TestDryRunResult:
    """Dry-run result validation."""

    def _make_valid_query_pack(self) -> InvestmentQueryPack:
        return InvestmentQueryPack(
            request_id="test_dry_001",
            companies=[InvestmentEntity(name="NVIDIA", tickers=["NVDA"])],
            industries=["AI"],
            research_questions=["What is the outlook?"],
        )

    def test_dry_run_produces_result(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        assert result.request_id == qp.request_id

    def test_dry_run_no_real_fetch(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        assert result.performs_real_fetch is False

    def test_dry_run_production_disabled(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        assert result.production_enabled is False

    def test_dry_run_does_not_affect_trial_v2(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        assert result.affects_trial_v2_allowlist is False

    def test_dry_run_does_not_affect_trae_scheduling(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        assert result.affects_trae_scheduling is False

    def test_dry_run_forbidden_fields_absent(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        assert result.forbidden_fields_absent is True

    def test_dry_run_produces_route_plan(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        assert len(result.route_plan.routes) > 0

    def test_dry_run_produces_evidence_skeletons(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        assert len(result.evidence_packet_skeletons) > 0

    def test_dry_run_result_validation_passes(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        errors = validate_dry_run_result(result)
        assert errors == []

    def test_dry_run_evidence_skeletons_no_forbidden_fields(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        for packet in result.evidence_packet_skeletons:
            d = packet.to_dict()
            for forbidden in FORBIDDEN_INVESTMENT_FIELDS:
                assert forbidden not in d

    def test_dry_run_evidence_skeletons_have_cannot_conclude(self):
        qp = self._make_valid_query_pack()
        result = run_dry_run(qp)
        for packet in result.evidence_packet_skeletons:
            assert packet.cannot_conclude != ""


class TestSensitiveKeywords:
    """Sensitive keyword scanning."""

    def test_clean_text_no_findings(self):
        found = scan_sensitive_keywords("normal text without secrets")
        assert found == []

    def test_proxy_url_detected(self):
        found = scan_sensitive_keywords("proxy_url=http://example.com")
        assert "proxy_url=" in found

    def test_cookie_detected(self):
        found = scan_sensitive_keywords("cookie: session=abc123")
        assert "cookie:" in found

    def test_api_key_detected(self):
        found = scan_sensitive_keywords("api_key=abc123")
        assert "api_key=" in found

    def test_empty_text_no_findings(self):
        found = scan_sensitive_keywords("")
        assert found == []


class TestForbiddenNetworkImports:
    """Verify no real network imports in the dry-run module."""

    def test_forbidden_imports_list_not_empty(self):
        assert len(FORBIDDEN_NETWORK_IMPORTS) > 0

    def test_requests_in_forbidden_list(self):
        assert "requests" in FORBIDDEN_NETWORK_IMPORTS

    def test_httpx_in_forbidden_list(self):
        assert "httpx" in FORBIDDEN_NETWORK_IMPORTS

    def test_tavily_in_forbidden_list(self):
        assert "tavily" in FORBIDDEN_NETWORK_IMPORTS

    def test_investment_on_demand_module_no_network_imports(self):
        """The investment_on_demand module must not import requests/httpx/etc."""
        import opc_foundation.source_inventory.investment_on_demand as mod
        module_text = open(mod.__file__, encoding="utf-8").read()
        for imp in ("import requests", "import httpx", "import aiohttp"):
            assert imp not in module_text, f"forbidden import found: {imp}"
