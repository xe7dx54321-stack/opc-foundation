#!/usr/bin/env python3
"""M3C-6C Low-frequency Source Pipeline runner.

This script runs low-frequency source checks for the low-frequency pipeline.
Currently only merck_ir is supported as a sample source.

Usage:
    python scripts/run_foundation_low_frequency_sources.py --source merck_ir --dry-run
    python scripts/run_foundation_low_frequency_sources.py --source merck_ir --run-once
    python scripts/run_foundation_low_frequency_sources.py --all --dry-run

Constraints:
    - Only processes sources in the low-frequency allowed set (currently merck_ir)
    - Does NOT modify trial_v2 allowlist
    - Does NOT modify TRAE scheduling
    - Does NOT configure production
    - Does NOT create permanent automation tasks
    - Does NOT commit data/
    - Does NOT save raw HTML
    - Does NOT download PDFs
    - Does NOT introduce Playwright/Selenium
    - Does NOT record proxy URL / cookie / token / secret
    - date_text missing -> fallback to discovered_at, timestamp_confidence=LOW
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from opc_foundation.source_inventory.low_frequency_sources import (  # noqa: E402
    LOW_FREQ_ALLOWED_SOURCES,
    MAX_SAMPLE_ITEMS_RECORDED,
    MIN_VALID_ITEMS_FOR_LOW_FREQ,
    LowFrequencyItem,
    LowFrequencyRunResult,
    apply_low_frequency_decision,
    is_low_frequency_allowed_source,
    is_rejected_navigation_title,
    now_iso,
    validate_low_frequency_run_result,
)

# Runtime data directory (gitignored)
RUNTIME_DATA_DIR = _REPO_ROOT / "data" / "foundation_low_frequency_sources"


def _import_merck_ir_runner():
    """Import the merck_ir dedicated preflight runner functions."""
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))
    import run_m3c_6f1_merck_ir_dedicated_preflight as merck_runner
    return merck_runner


def run_merck_ir_low_frequency(dry_run: bool = True) -> LowFrequencyRunResult:
    """Run merck_ir as a low-frequency source check.

    Reuses the M3C-6F.1 dedicated preflight extraction logic but wraps results
    in LowFrequencyItem objects with discovered_at / timestamp_confidence.
    """
    merck_runner = _import_merck_ir_runner()

    # Run the merck_ir dedicated preflight
    merck_result = merck_runner.run_merck_ir_dedicated_preflight(discover_only=False)

    # Build LowFrequencyRunResult
    result = LowFrequencyRunResult(
        source_id="merck_ir",
        run_mode="dry_run" if dry_run else "run_once",
    )

    result.valid_item_count = merck_result.valid_item_count
    result.dated_item_count = merck_result.dated_item_count
    result.navigation_rejected_count = merck_result.rejected_navigation_count

    # Convert sample items to LowFrequencyItem
    discovered_at = now_iso()
    observed_at = discovered_at

    for item in merck_result.sample_items[:MAX_SAMPLE_ITEMS_RECORDED]:
        is_nav = is_rejected_navigation_title(item.title)

        if item.date_text:
            timestamp_confidence = "MEDIUM"
            date_missing_reason = ""
        else:
            timestamp_confidence = "LOW"
            date_missing_reason = "date not extractable from listing page HTML"

        result.sample_items.append(
            LowFrequencyItem(
                source_id="merck_ir",
                title=item.title,
                url=item.url,
                entry_type=item.entry_type,
                date_text=item.date_text,
                discovered_at=discovered_at,
                observed_at=observed_at,
                timestamp_confidence=timestamp_confidence,
                date_missing_reason=date_missing_reason,
                is_navigation=is_nav,
                is_valid_item=not is_nav,
            )
        )

    # Count missing dates
    result.missing_date_count = result.valid_item_count - result.dated_item_count

    # Timestamp confidence distribution
    result.timestamp_confidence_distribution = {
        "HIGH": 0,
        "MEDIUM": result.dated_item_count,
        "LOW": result.missing_date_count,
        "NONE": 0,
    }

    # Apply decision
    apply_low_frequency_decision(result)

    if dry_run:
        result.notes = (
            f"Dry-run: merck_ir has {result.valid_item_count} valid items, "
            f"{result.dated_item_count} dated items. "
            "No runtime data written."
        )
    else:
        result.notes = (
            f"Run-once: merck_ir has {result.valid_item_count} valid items, "
            f"{result.dated_item_count} dated items. "
            "Runtime data written to data/foundation_low_frequency_sources/."
        )

    return result


def generate_markdown_report(result: LowFrequencyRunResult) -> str:
    """Generate a markdown summary for a low-frequency run."""
    lines: list[str] = []
    lines.append("# Low-frequency Source Run Report")
    lines.append("")
    lines.append(f"- **Generated at:** {now_iso()}")
    lines.append(f"- **Source:** {result.source_id}")
    lines.append(f"- **Run mode:** {result.run_mode}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| field | value |")
    lines.append("|---|---|")
    lines.append(f"| valid_item_count | {result.valid_item_count} |")
    lines.append(f"| dated_item_count | {result.dated_item_count} |")
    lines.append(f"| missing_date_count | {result.missing_date_count} |")
    lines.append(f"| navigation_rejected_count | {result.navigation_rejected_count} |")
    lines.append(f"| recommended_frequency | {result.recommended_frequency} |")
    lines.append(f"| low_frequency_allowed_now | {result.low_frequency_allowed_now} |")
    lines.append(f"| trial_v2_allowlist_allowed_now | {result.trial_v2_allowlist_allowed_now} |")
    lines.append(f"| production_enabled | {result.production_enabled} |")
    lines.append(f"| next_action | {result.next_action} |")
    lines.append(f"| risk_flags | {', '.join(result.risk_flags) if result.risk_flags else 'none'} |")
    lines.append("")

    lines.append("## Timestamp Confidence Distribution")
    lines.append("")
    lines.append("| confidence | count |")
    lines.append("|---|---:|")
    for conf in ("HIGH", "MEDIUM", "LOW", "NONE"):
        lines.append(
            f"| {conf} | {result.timestamp_confidence_distribution.get(conf, 0)} |"
        )
    lines.append("")

    if result.sample_items:
        lines.append("## Sample Items")
        lines.append("")
        lines.append("| title | url | date_text | discovered_at | timestamp_confidence |")
        lines.append("|---|---|---|---|---|")
        for item in result.sample_items:
            lines.append(
                f"| {item.title} | {item.url} | {item.date_text or '-'} | "
                f"{item.discovered_at} | {item.timestamp_confidence} |"
            )
        lines.append("")

    lines.append("## Boundary Compliance")
    lines.append("")
    lines.append("- Does NOT modify trial_v2 allowlist: yes")
    lines.append("- Does NOT modify TRAE scheduling: yes")
    lines.append("- Does NOT configure production: yes")
    lines.append("- Does NOT create permanent automation: yes")
    lines.append("- Does NOT commit data/local/secrets: yes")
    lines.append("- Does NOT commit proxy URL/cookie/token: yes")
    lines.append("- Does NOT commit raw HTML/screenshot: yes")
    lines.append("- Does NOT introduce Playwright/Selenium: yes")
    lines.append("- Does NOT restore deleted Dashboard pages: yes")
    lines.append("- Does NOT create tag: yes")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="M3C-6C Low-frequency Source Pipeline runner"
    )
    parser.add_argument(
        "--source",
        default="merck_ir",
        help="Source ID to run (currently only merck_ir is allowed)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all allowed low-frequency sources",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry-run mode (default): do not write runtime data",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run-once mode: write runtime data (gitignored, not committed)",
    )
    args = parser.parse_args()

    # Determine mode
    dry_run = not args.run_once

    # Determine sources
    if args.all:
        sources = sorted(LOW_FREQ_ALLOWED_SOURCES)
    else:
        sources = [args.source]

    # Validate sources
    for source_id in sources:
        if not is_low_frequency_allowed_source(source_id):
            print(f"ERROR: source '{source_id}' is not in allowed low-frequency sources: "
                  f"{LOW_FREQ_ALLOWED_SOURCES}")
            return 1

    print(f"Running low-frequency pipeline for sources: {sources}")
    print(f"  Mode: {'dry_run' if dry_run else 'run_once'}")

    all_results: list[LowFrequencyRunResult] = []

    for source_id in sources:
        print(f"\n--- {source_id} ---")
        if source_id == "merck_ir":
            result = run_merck_ir_low_frequency(dry_run=dry_run)
        else:
            print(f"  ERROR: no runner implemented for '{source_id}'")
            return 1

        # Validate
        errors = validate_low_frequency_run_result(result)
        if errors:
            print("  VALIDATION ERRORS:")
            for err in errors:
                print(f"    - {err}")
            return 1

        print(f"  -> valid_items={result.valid_item_count}, "
              f"dated={result.dated_item_count}, "
              f"missing_date={result.missing_date_count}, "
              f"freq={result.recommended_frequency}, "
              f"low_freq_allowed={result.low_frequency_allowed_now}")

        all_results.append(result)

    # Write runtime data for run-once mode
    if not dry_run:
        RUNTIME_DATA_DIR.mkdir(parents=True, exist_ok=True)
        for result in all_results:
            md_report = generate_markdown_report(result)
            md_path = RUNTIME_DATA_DIR / f"{result.source_id}_low_freq_report.md"
            md_path.write_text(md_report, encoding="utf-8")

            json_dict = {
                "batch_name": "foundation_low_frequency_sources",
                "generated_at": now_iso(),
                "result": result.to_dict(),
            }
            json_path = RUNTIME_DATA_DIR / f"{result.source_id}_low_freq_summary.json"
            json_path.write_text(
                json.dumps(json_dict, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"  Runtime data written to {json_path}")

    print("\nLow-frequency pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
