#!/usr/bin/env python3
"""M3C-6C.1 Low-frequency Observation Harness runner.

Runs merck_ir low-frequency observation, stores daily run records, and
generates 7-day observation summaries.

Usage:
    python scripts/run_foundation_low_frequency_observation.py --source merck_ir --dry-run
    python scripts/run_foundation_low_frequency_observation.py --source merck_ir --run-once
    python scripts/run_foundation_low_frequency_observation.py --source merck_ir --summarize

Constraints:
    - Only processes merck_ir
    - Does NOT modify trial_v2 allowlist
    - Does NOT modify TRAE scheduling
    - Does NOT configure production
    - Does NOT create permanent automation tasks
    - Does NOT commit data/
    - Does NOT save raw HTML
    - Does NOT introduce Playwright/Selenium
    - Does NOT record proxy URL / cookie / token / secret
    - date_text missing -> discovered_at fallback, timestamp_confidence=LOW
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from opc_foundation.source_inventory.low_frequency_observation import (  # noqa: E402
    OBSERVATION_ALLOWED_SOURCES,
    LowFrequencyObservationRun,
    compute_observation_summary,
    is_observation_allowed_source,
    now_iso,
    today_date,
    validate_observation_run,
    validate_observation_summary,
)

RUNTIME_DATA_DIR = _REPO_ROOT / "data" / "foundation_low_frequency_observation"


def _import_low_freq_runner():
    """Import the low-frequency runner."""
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))
    import run_foundation_low_frequency_sources as lf_runner
    return lf_runner


def run_observation(dry_run: bool = True, source_id: str = "merck_ir") -> LowFrequencyObservationRun:
    """Run a single observation for merck_ir."""
    lf_runner = _import_low_freq_runner()

    # Run the low-frequency source check
    lf_result = lf_runner.run_merck_ir_low_frequency(dry_run=dry_run)

    # Build observation run record
    run = LowFrequencyObservationRun(
        source_id=source_id,
        run_id=str(uuid.uuid4())[:8],
        run_date=today_date(),
        run_started_at=now_iso(),
        run_finished_at=now_iso(),
        mode="dry_run" if dry_run else "run_once",
        valid_item_count=lf_result.valid_item_count,
        dated_item_count=lf_result.dated_item_count,
        missing_date_count=lf_result.missing_date_count,
        navigation_rejected_count=lf_result.navigation_rejected_count,
        timestamp_confidence_distribution=dict(lf_result.timestamp_confidence_distribution),
        risk_flags=list(lf_result.risk_flags),
    )

    # Convert sample items to dicts
    run.sample_items = [
        {
            "title": item.title,
            "url": item.url,
            "date_text": item.date_text,
            "discovered_at": item.discovered_at,
            "timestamp_confidence": item.timestamp_confidence,
            "entry_type": item.entry_type,
        }
        for item in lf_result.sample_items
    ]

    # Determine run status
    if lf_result.valid_item_count >= 3:
        run.status = "success"
    elif lf_result.valid_item_count > 0:
        run.status = "partial"
    else:
        run.status = "failed"

    run.notes = lf_result.notes

    return run


def save_run(run: LowFrequencyObservationRun) -> Path:
    """Save a run record to runtime data."""
    RUNTIME_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{run.run_date}_{run.run_id}.json"
    filepath = RUNTIME_DATA_DIR / filename
    filepath.write_text(
        json.dumps(run.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return filepath


def load_all_runs(source_id: str = "merck_ir") -> list[LowFrequencyObservationRun]:
    """Load all run records from runtime data."""
    runs: list[LowFrequencyObservationRun] = []
    if not RUNTIME_DATA_DIR.exists():
        return runs

    for filepath in sorted(RUNTIME_DATA_DIR.glob("*.json")):
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            run = LowFrequencyObservationRun(
                source_id=data.get("source_id", "merck_ir"),
                run_id=data.get("run_id", ""),
                run_date=data.get("run_date", ""),
                run_started_at=data.get("run_started_at", ""),
                run_finished_at=data.get("run_finished_at", ""),
                mode=data.get("mode", "run_once"),
                valid_item_count=data.get("valid_item_count", 0),
                dated_item_count=data.get("dated_item_count", 0),
                missing_date_count=data.get("missing_date_count", 0),
                navigation_rejected_count=data.get("navigation_rejected_count", 0),
                timestamp_confidence_distribution=data.get(
                    "timestamp_confidence_distribution",
                    {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0},
                ),
                sample_items=data.get("sample_items", []),
                risk_flags=data.get("risk_flags", []),
                status=data.get("status", "pending"),
                notes=data.get("notes", ""),
            )
            if run.source_id == source_id:
                runs.append(run)
        except Exception:
            continue

    return runs


def generate_summary_markdown(summary) -> str:
    """Generate markdown summary."""
    lines: list[str] = []
    lines.append("# Low-frequency Observation Summary")
    lines.append("")
    lines.append(f"- **Generated at:** {now_iso()}")
    lines.append(f"- **Source:** {summary.source_id}")
    lines.append(f"- **Target days:** {summary.target_days}")
    lines.append(f"- **Observed days:** {summary.observed_days}")
    lines.append(f"- **Successful days:** {summary.successful_days}")
    lines.append(f"- **Partial days:** {summary.partial_days}")
    lines.append(f"- **Failed days:** {summary.failed_days}")
    lines.append(f"- **Total runs:** {summary.total_runs}")
    lines.append(f"- **Min valid items per run:** {summary.min_valid_items_per_run}")
    lines.append(f"- **Max valid items per run:** {summary.max_valid_items_per_run}")
    lines.append(f"- **Navigation regression count:** {summary.navigation_regression_count}")
    lines.append(f"- **Blocking error count:** {summary.blocking_error_count}")
    lines.append(f"- **Final observation status:** {summary.final_observation_status}")
    lines.append(f"- **Recommended next action:** {summary.recommended_next_action}")
    lines.append("")

    lines.append("## Timestamp Confidence Distribution")
    lines.append("")
    lines.append("| confidence | count |")
    lines.append("|---|---:|")
    for conf in ("HIGH", "MEDIUM", "LOW", "NONE"):
        lines.append(
            f"| {conf} | {summary.timestamp_confidence_distribution.get(conf, 0)} |"
        )
    lines.append("")

    if summary.days:
        lines.append("## Daily Status")
        lines.append("")
        lines.append("| date | status | runs | best_valid | best_dated | nav_regression | blocking_error |")
        lines.append("|---|---|---:|---:|---:|---|---|")
        for day in summary.days:
            lines.append(
                f"| {day.date} | {day.status} | {day.run_count} | "
                f"{day.best_valid_item_count} | {day.best_dated_item_count} | "
                f"{day.had_navigation_regression} | {day.had_blocking_error} |"
            )
        lines.append("")

    lines.append("## Boundary Compliance")
    lines.append("")
    lines.append("- Does NOT modify trial_v2 allowlist: yes")
    lines.append("- Does NOT modify TRAE scheduling: yes")
    lines.append("- Does NOT configure production: yes")
    lines.append("- Does NOT create permanent automation: yes")
    lines.append("- Does NOT commit data/local/secrets: yes")
    lines.append("- Does NOT introduce Playwright/Selenium: yes")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="M3C-6C.1 Low-frequency Observation Harness runner"
    )
    parser.add_argument(
        "--source",
        default="merck_ir",
        help="Source ID to observe (currently only merck_ir)",
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
        help="Run-once mode: write runtime data (gitignored)",
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Summarize existing runtime data",
    )
    args = parser.parse_args()

    source_id = args.source

    if not is_observation_allowed_source(source_id):
        print(f"ERROR: source '{source_id}' not allowed for observation")
        return 1

    if args.summarize:
        print(f"Summarizing observation data for {source_id}...")
        runs = load_all_runs(source_id)
        summary = compute_observation_summary(runs, source_id=source_id)

        errors = validate_observation_summary(summary)
        if errors:
            print("VALIDATION ERRORS:")
            for e in errors:
                print(f"  - {e}")
            return 1

        md = generate_summary_markdown(summary)
        print(md)

        # Write summary to runtime data
        RUNTIME_DATA_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = RUNTIME_DATA_DIR / f"{source_id}_observation_summary.json"
        summary_path.write_text(
            json.dumps(summary.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nSummary written to {summary_path}")
        return 0

    dry_run = not args.run_once
    print(f"Running observation for {source_id} (mode={'dry_run' if dry_run else 'run_once'})...")

    run = run_observation(dry_run=dry_run, source_id=source_id)

    errors = validate_observation_run(run)
    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"  -> status={run.status}, valid={run.valid_item_count}, "
          f"dated={run.dated_item_count}, missing_date={run.missing_date_count}")

    if not dry_run:
        filepath = save_run(run)
        print(f"  Runtime data written to {filepath}")
    else:
        print("  Dry-run: no runtime data written")

    # Show sample items
    if run.sample_items:
        print("\n  Sample items:")
        for item in run.sample_items[:5]:
            print(f"    - {item.get('title', '')} | {item.get('timestamp_confidence', '')}")

    print("\nObservation run completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
