#!/usr/bin/env python3
"""M3C-6E1 Investment On-demand Registry dry-run runner.

Generates a routing plan and evidence packet skeletons from a query pack.
This is a DRY-RUN ONLY runner — no real network fetch is performed.

Usage:
    python scripts/run_investment_on_demand_registry.py --example --dry-run
    python scripts/run_investment_on_demand_registry.py --query-pack configs/foundation_investment_on_demand_registry.example.yaml --dry-run

Constraints:
    - Dry-run only: no real network fetch
    - Does NOT call search APIs (Tavily/Bing/Google/Brave)
    - Does NOT download web pages or PDFs
    - Does NOT modify trial_v2 allowlist
    - Does NOT modify TRAE scheduling
    - Does NOT modify merck_ir observation task
    - Does NOT configure production
    - Does NOT output investment ratings / target prices / trade signals
    - Does NOT commit data/
    - Does NOT record proxy URL / cookie / token / secret
    - Does NOT introduce Playwright/Selenium
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from opc_foundation.source_inventory.investment_on_demand import (  # noqa: E402
    InvestmentEntity,
    InvestmentQueryPack,
    InvestmentSourceTaxonomy,
    TimeWindow,
    run_dry_run,
    validate_query_pack,
    validate_dry_run_result,
    FORBIDDEN_INVESTMENT_FIELDS,
    FORBIDDEN_NETWORK_IMPORTS,
)

EXAMPLE_CONFIG = _REPO_ROOT / "configs" / "foundation_investment_on_demand_registry.example.yaml"


def _fail_closed(msg: str) -> None:
    """Fail-closed: print error and exit with non-zero."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _check_no_network_imports() -> list[str]:
    """Verify this runner script source does not import forbidden network modules.

    Checks the SOURCE CODE of this script, not whether the modules are
    importable in the environment (they may be installed but unused).
    """
    runner_source = Path(__file__).read_text(encoding="utf-8")
    found: list[str] = []
    for name in FORBIDDEN_NETWORK_IMPORTS:
        # Check for both "import <name>" and "from <name>"
        if f"import {name}" in runner_source or f"from {name}" in runner_source:
            found.append(name)
    return found


def _load_example_query_pack() -> InvestmentQueryPack:
    """Load the example query pack from the example config (manual parse)."""
    return InvestmentQueryPack(
        request_id="example_ai_optical_interconnect",
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        time_window=TimeWindow(lookback_days=30),
        companies=[
            InvestmentEntity(
                entity_type="company",
                name="NVIDIA",
                tickers=["NVDA"],
            ),
            InvestmentEntity(
                entity_type="company",
                name="Broadcom",
                tickers=["AVGO"],
            ),
        ],
        industries=[
            "AI optical interconnect",
            "silicon photonics",
            "optical circuit switching",
            "AI data center networking",
        ],
        banks=["Goldman Sachs", "Morgan Stanley", "J.P. Morgan"],
        research_questions=[
            "What are top sell-side views on AI data center networking demand?",
            "What changed in optical interconnect expectations?",
        ],
        output_mode="evidence_packet_skeleton_only",
    )


def _load_query_pack_from_yaml(path: str) -> InvestmentQueryPack:
    """Load a query pack from a YAML config file (manual parse)."""
    config_path = Path(path)
    if not config_path.exists():
        _fail_closed(f"Query pack config not found: {path}")

    text = config_path.read_text(encoding="utf-8")

    # Simple YAML parse for the example structure (avoid yaml dependency)
    # We look for the example_query_pack section
    request_id = ""
    lookback_days = 30
    companies: list[InvestmentEntity] = []
    industries: list[str] = []
    banks: list[str] = []
    research_questions: list[str] = []
    output_mode = "evidence_packet_skeleton_only"

    in_example_section = False
    in_companies = False
    in_industries = False
    in_banks = False
    in_research_questions = False
    current_company: dict | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("example_query_pack:"):
            in_example_section = True
            continue
        if not in_example_section:
            continue
        if stripped.startswith("request_id:"):
            request_id = stripped.split(":", 1)[1].strip().strip('"')
        elif stripped.startswith("lookback_days:"):
            lookback_days = int(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("output_mode:"):
            output_mode = stripped.split(":", 1)[1].strip().strip('"')
        elif stripped == "companies:":
            in_companies = True
            in_industries = False
            in_banks = False
            in_research_questions = False
        elif stripped == "industries:":
            in_industries = True
            in_companies = False
            in_banks = False
            in_research_questions = False
        elif stripped == "banks:":
            in_banks = True
            in_companies = False
            in_industries = False
            in_research_questions = False
        elif stripped == "research_questions:":
            in_research_questions = True
            in_companies = False
            in_industries = False
            in_banks = False
        elif stripped.startswith("- ") and in_industries:
            industries.append(stripped[2:].strip().strip('"'))
        elif stripped.startswith("- ") and in_banks:
            banks.append(stripped[2:].strip().strip('"'))
        elif stripped.startswith("- ") and in_research_questions:
            research_questions.append(stripped[2:].strip().strip('"'))
        elif stripped.startswith("- name:") and in_companies:
            if current_company:
                companies.append(InvestmentEntity(
                    entity_type="company",
                    name=current_company.get("name", ""),
                    tickers=current_company.get("tickers", []),
                ))
            current_company = {"name": stripped.split(":", 1)[1].strip().strip('"')}
        elif stripped.startswith("tickers:") and current_company is not None:
            ticker_str = stripped.split(":", 1)[1].strip()
            current_company["tickers"] = [
                t.strip().strip('"').strip("[")
                for t in ticker_str.split(",")
                if t.strip()
            ]

    if current_company:
        companies.append(InvestmentEntity(
            entity_type="company",
            name=current_company.get("name", ""),
            tickers=current_company.get("tickers", []),
        ))

    return InvestmentQueryPack(
        request_id=request_id or "loaded_from_yaml",
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        time_window=TimeWindow(lookback_days=lookback_days),
        companies=companies,
        industries=industries,
        banks=banks,
        research_questions=research_questions,
        output_mode=output_mode,
    )


def generate_markdown_summary(result) -> str:
    """Generate a markdown summary of the dry-run result."""
    lines = [
        "# M3C-6E1 Investment On-demand Registry Dry-run Summary",
        "",
        f"- **request_id**: {result.request_id}",
        f"- **production_enabled**: {result.production_enabled}",
        f"- **performs_real_fetch**: {result.performs_real_fetch}",
        f"- **affects_trial_v2_allowlist**: {result.affects_trial_v2_allowlist}",
        f"- **affects_trae_scheduling**: {result.affects_trae_scheduling}",
        f"- **forbidden_fields_absent**: {result.forbidden_fields_absent}",
        f"- **route_count**: {len(result.route_plan.routes)}",
        f"- **skipped_route_count**: {len(result.route_plan.skipped_routes)}",
        f"- **evidence_packet_skeleton_count**: {len(result.evidence_packet_skeletons)}",
        f"- **risk_flags**: {', '.join(result.risk_flags) if result.risk_flags else 'none'}",
        "",
        "## Route Plan",
        "",
        "| route_id | source_type | priority | foundation_allowed | recommended_action |",
        "|---|---|---|---|---|",
    ]
    for route in result.route_plan.routes:
        lines.append(
            f"| {route.route_id} | {route.source_type} | {route.priority} | "
            f"{route.foundation_allowed} | {route.recommended_action} |"
        )
    for route in result.route_plan.skipped_routes:
        lines.append(
            f"| {route.route_id} | {route.source_type} | {route.priority} | "
            f"{route.foundation_allowed} | {route.recommended_action} |"
        )
    lines.append("")
    lines.append("## Evidence Packet Skeletons")
    lines.append("")
    for packet in result.evidence_packet_skeletons:
        lines.append(f"### {packet.evidence_id}")
        lines.append(f"- **source_type**: {packet.source_type}")
        lines.append(f"- **title**: {packet.title}")
        lines.append(f"- **timestamp_confidence**: {packet.timestamp_confidence}")
        lines.append(f"- **cannot_conclude**: {packet.cannot_conclude}")
        lines.append("")
    lines.append("## Boundary Check")
    lines.append("")
    lines.append(f"- No forbidden investment fields: {result.forbidden_fields_absent}")
    lines.append(f"- Forbidden fields checked: {', '.join(FORBIDDEN_INVESTMENT_FIELDS)}")
    lines.append(f"- No real network fetch: {not result.performs_real_fetch}")
    lines.append(f"- Production disabled: {not result.production_enabled}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="M3C-6E1 Investment On-demand Registry dry-run runner"
    )
    parser.add_argument(
        "--example",
        action="store_true",
        help="Use the built-in example query pack",
    )
    parser.add_argument(
        "--query-pack",
        type=str,
        default="",
        help="Path to a query pack YAML config file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (only mode supported in M3C-6E1)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="(UNSUPPORTED) Attempt real fetch — will fail-closed",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output file path for JSON result (optional)",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Also output markdown summary",
    )
    args = parser.parse_args()

    # Fail-closed for real run attempts
    if args.run:
        _fail_closed("real fetch is not supported in M3C-6E1")

    # Require either --example or --query-pack
    if not args.example and not args.query_pack:
        parser.error("must specify --example or --query-pack")

    # Verify no network modules imported
    network_found = _check_no_network_imports()
    if network_found:
        _fail_closed(
            f"forbidden network modules imported: {network_found}. "
            f"M3C-6E1 must not import {FORBIDDEN_NETWORK_IMPORTS}"
        )

    # Load query pack
    if args.example:
        query_pack = _load_example_query_pack()
    else:
        query_pack = _load_query_pack_from_yaml(args.query_pack)

    # Validate query pack
    errors = validate_query_pack(query_pack)
    if errors:
        _fail_closed(f"query pack validation failed: {errors}")

    # Run dry-run
    result = run_dry_run(query_pack)

    # Validate result
    result_errors = validate_dry_run_result(result)
    if result_errors:
        _fail_closed(f"dry-run result validation failed: {result_errors}")

    # Output
    result_json = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
    print(result_json)

    if args.markdown:
        print("\n---\n")
        print(generate_markdown_summary(result))

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(result_json, encoding="utf-8")
        print(f"\nResult written to: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
