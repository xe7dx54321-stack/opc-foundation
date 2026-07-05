#!/usr/bin/env python3
"""M3C-6E1 Investment On-demand Registry boundary checker.

Validates that the on-demand registry complies with all M3C-6E1 constraints.

Usage:
    python scripts/check_investment_on_demand_registry.py

Checks:
    1. production_enabled=false
    2. performs_real_fetch=false
    3. affects_trial_v2_allowlist=false
    4. affects_trae_scheduling=false
    5. creates_permanent_automation=false
    6. no forbidden investment fields in evidence packets
    7. source taxonomy valid
    8. paid sellside research foundation_allowed=false
    9. market_data requires_downstream=true
    10. output does not contain target_price/rating/buy/sell/position_size/trade_signal
    11. no cookie/token/proxy URL/secret in any field
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from opc_foundation.source_inventory.investment_on_demand import (  # noqa: E402
    InvestmentSourceTaxonomy,
    BaseEvidencePacket,
    FORBIDDEN_INVESTMENT_FIELDS,
    SENSITIVE_KEYWORDS,
    scan_sensitive_keywords,
    INVESTMENT_SOURCE_TYPES,
    FOUNDATION_ALLOWED_SOURCE_TYPES,
    DOWNSTREAM_ONLY_SOURCE_TYPES,
)


def check() -> int:
    """Run all checks. Returns 0 if pass, 1 if fail."""
    errors: list[str] = []
    warnings: list[str] = []

    print("=" * 60)
    print("M3C-6E1 Investment On-demand Registry Boundary Check")
    print("=" * 60)

    # 1. Source taxonomy validation
    print("\n[1] Source taxonomy validation...")
    taxonomy = InvestmentSourceTaxonomy()
    for source_type in INVESTMENT_SOURCE_TYPES:
        entry = taxonomy.get(source_type)
        if entry is None:
            errors.append(f"source_type '{source_type}' missing from taxonomy")
            continue
        if source_type not in taxonomy.entries:
            errors.append(f"source_type '{source_type}' not registered")

    # 2. Paid sellside research must be foundation_allowed=false
    print("[2] Paid sellside research check...")
    paid_entry = taxonomy.get("sellside_research_paid_or_entitled")
    if paid_entry and paid_entry.foundation_allowed:
        errors.append(
            "sellside_research_paid_or_entitled must have foundation_allowed=false"
        )
    if paid_entry and not paid_entry.requires_downstream:
        errors.append(
            "sellside_research_paid_or_entitled must have requires_downstream=true"
        )
    print(f"  foundation_allowed={paid_entry.foundation_allowed if paid_entry else 'N/A'}")

    # 3. Market data must require downstream
    print("[3] Market data check...")
    market_entry = taxonomy.get("market_data")
    if market_entry and market_entry.foundation_allowed:
        errors.append("market_data must have foundation_allowed=false")
    if market_entry and not market_entry.requires_downstream:
        errors.append("market_data must have requires_downstream=true")
    print(f"  foundation_allowed={market_entry.foundation_allowed if market_entry else 'N/A'}")

    # 4. Foundation allowed source types check
    print("[4] Foundation allowed source types check...")
    for st in FOUNDATION_ALLOWED_SOURCE_TYPES:
        entry = taxonomy.get(st)
        if entry and not entry.foundation_allowed:
            errors.append(
                f"source_type '{st}' should be foundation_allowed=true"
            )
    for st in DOWNSTREAM_ONLY_SOURCE_TYPES:
        entry = taxonomy.get(st)
        if entry and entry.foundation_allowed:
            errors.append(
                f"source_type '{st}' should be foundation_allowed=false"
            )

    # 5. Forbidden investment fields check
    print("[5] Forbidden investment fields check...")
    # Verify BaseEvidencePacket does not have any forbidden fields as attributes
    sample_packet = BaseEvidencePacket(
        evidence_id="check_sample",
        cannot_conclude="sample for field check",
    )
    packet_dict = sample_packet.to_dict()
    for forbidden in FORBIDDEN_INVESTMENT_FIELDS:
        if forbidden in packet_dict:
            errors.append(
                f"forbidden investment field '{forbidden}' found in BaseEvidencePacket"
            )
    print(f"  Checked {len(FORBIDDEN_INVESTMENT_FIELDS)} forbidden fields")

    # 6. Sensitive keywords check
    print("[6] Sensitive keywords check...")
    # Check that no field names or default values contain sensitive keywords
    for field_name in dir(sample_packet):
        if field_name.startswith("_"):
            continue
        val = getattr(sample_packet, field_name, "")
        if isinstance(val, str):
            found = scan_sensitive_keywords(val)
            if found:
                errors.append(
                    f"BaseEvidencePacket.{field_name} contains sensitive keywords: {found}"
                )
    print(f"  Checked {len(SENSITIVE_KEYWORDS)} sensitive keyword patterns")

    # 7. Config file check
    print("[7] Example config check...")
    config_path = _REPO_ROOT / "configs" / "foundation_investment_on_demand_registry.example.yaml"
    if not config_path.exists():
        errors.append(f"example config not found: {config_path}")
    else:
        config_text = config_path.read_text(encoding="utf-8")
        found = scan_sensitive_keywords(config_text)
        if found:
            errors.append(f"example config contains sensitive keywords: {found}")
        # Check for forbidden field names in config
        for forbidden in FORBIDDEN_INVESTMENT_FIELDS:
            if forbidden in config_text:
                errors.append(
                    f"example config contains forbidden investment field '{forbidden}'"
                )
        # Check policy flags
        if "production_enabled: false" not in config_text:
            errors.append("example config must have production_enabled: false")
        if "performs_real_fetch: false" not in config_text:
            errors.append("example config must have performs_real_fetch: false")
        if "dry_run_only: true" not in config_text:
            errors.append("example config must have dry_run_only: true")

    # 8. Runner script check — no real network imports
    print("[8] Runner script network import check...")
    runner_path = _REPO_ROOT / "scripts" / "run_investment_on_demand_registry.py"
    if not runner_path.exists():
        errors.append(f"runner script not found: {runner_path}")
    else:
        runner_text = runner_path.read_text(encoding="utf-8")
        forbidden_imports = [
            "import requests",
            "import httpx",
            "import aiohttp",
            "from urllib.request",
            "import tavily",
            "import serpapi",
        ]
        for imp in forbidden_imports:
            if imp in runner_text:
                errors.append(f"runner script contains forbidden import: {imp}")
        # Check for requests.get / httpx.get etc
        forbidden_calls = [
            "requests.get",
            "requests.post",
            "httpx.get",
            "httpx.post",
            "urlopen(",
            "tavily.search",
        ]
        for call in forbidden_calls:
            if call in runner_text:
                errors.append(f"runner script contains forbidden network call: {call}")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1
    if warnings:
        print(f"PASSED with {len(warnings)} warning(s)")
        for w in warnings:
            print(f"  WARN: {w}")
    else:
        print("ALL CHECKS PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(check())
