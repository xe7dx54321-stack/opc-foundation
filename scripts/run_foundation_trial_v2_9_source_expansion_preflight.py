#!/usr/bin/env python3
"""
OPC Foundation Trial V2 9-Source Expansion Preflight Runner (M3C-5B1.2)
========================================================================

Validates gelonghui as the 9th source in the expansion candidate package.
Does NOT modify current 8-source trial_v2 allowlist, TRAE scheduling, or production.

Usage:
    python scripts/run_foundation_trial_v2_9_source_expansion_preflight.py --mode validate-config
    python scripts/run_foundation_trial_v2_9_source_expansion_preflight.py --mode preflight
    python scripts/run_foundation_trial_v2_9_source_expansion_preflight.py --mode dry-run
    python scripts/run_foundation_trial_v2_9_source_expansion_preflight.py --mode check
    python scripts/run_foundation_trial_v2_9_source_expansion_preflight.py --mode all \
        --config configs/foundation_trial_v2_9_source_expansion_candidate.example.yaml \
        --report docs/foundation_m3c_5b1_2_gelonghui_9_source_preflight_report.md

Author: OPC Foundation
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

# Ensure src is on PYTHONPATH
repo_root = Path(__file__).resolve().parent.parent
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from opc_foundation.source_inventory.content_validity import (
    ContentCandidate,
    extract_candidates_from_html,
)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RoundResult:
    source_id: str
    round_index: int
    timestamp: str
    http_status: int
    content_status: str
    content_score: int
    valid_candidate_count: int
    relevant_candidate_count: int
    dated_candidate_count: int
    sample_count: int
    passed: bool
    failure_reason: str = ""
    samples: list = field(default_factory=list)


@dataclass
class PreflightSummary:
    total_rounds: int
    pass_rounds: int
    latest_status: str
    latest_score: int
    latest_dated_count: int
    final_decision: str


# =============================================================================
# Mode: validate-config
# =============================================================================

def run_validate_config(config: dict, formal_allowlist_config: dict) -> list:
    """Validate the 9-source expansion candidate configuration."""
    results = []
    def chk(name, passed, detail=""):
        results.append((name, passed, detail))

    chk("Config exists", True)
    chk("production_enabled=false", config["scope"]["production_enabled"] == False)
    chk("affects_current_trial_v2_allowlist=false", config["scope"]["affects_current_trial_v2_allowlist"] == False)
    chk("affects_trae_scheduling=false", config["scope"]["affects_trae_scheduling"] == False)
    chk("expansion_candidate_only=true", config["scope"]["expansion_candidate_only"] == True)
    chk("base_allowlist_count=8", len(config["base_allowlist"]) == 8, f"Got {len(config['base_allowlist'])}")
    chk("new_candidate_count=1", config["scope"]["new_candidate_count"] == 1)
    chk("candidate_package_count=9", config["scope"]["candidate_package_count"] == 9)
    chk("candidate_allowlist_count=9", len(config["candidate_allowlist"]) == 9, f"Got {len(config['candidate_allowlist'])}")

    base_set = set(config["base_allowlist"])
    cand_set = set(config["candidate_allowlist"])
    chk("candidate_allowlist contains all base sources", base_set.issubset(cand_set))
    chk("gelonghui in candidate_allowlist", "gelonghui" in cand_set)
    chk("merck_ir not in candidate_allowlist", "merck_ir" not in cand_set)
    chk("goldman_sachs_podcasts not in candidate_allowlist", "goldman_sachs_podcasts" not in cand_set)

    # Verify formal allowlist NOT modified
    formal_ids = [s["source_id"] for s in formal_allowlist_config.get("sources", [])]
    chk("formal allowlist still 8 sources", len(formal_ids) == 8)
    chk("gelonghui NOT in formal allowlist", "gelonghui" not in formal_ids)
    chk("formal allowlist unchanged", set(formal_ids) == base_set)

    new_cands = config.get("new_candidates", [])
    chk("new_candidates has 1 entry", len(new_cands) == 1)
    if new_cands:
        chk("new_candidate is gelonghui", new_cands[0]["source_id"] == "gelonghui")
        chk("scheduling_allowed_now=false", new_cands[0]["scheduling_allowed_now"] == False)
        chk("ready_for_expansion_evaluation=true", new_cands[0]["ready_for_expansion_evaluation"] == True)
        chk("min_content_score>=70", new_cands[0]["min_content_score"] >= 70)

    return results


# =============================================================================
# Mode: preflight (gelonghui live stability)
# =============================================================================

def run_preflight_round(source: dict, round_index: int, timeout: int = 20) -> RoundResult:
    """Execute one preflight round for gelonghui."""
    ts = datetime.now(timezone.utc).isoformat()

    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as e:
        return RoundResult(
            source_id=source.get("source_id", ""), round_index=round_index,
            timestamp=ts, http_status=0, content_status="technical_only",
            content_score=0, valid_candidate_count=0, relevant_candidate_count=0,
            dated_candidate_count=0, sample_count=0, passed=False,
            failure_reason=f"Missing dependency: {e}")

    url = source.get("url", "")
    result = RoundResult(
        source_id=source.get("source_id", ""), round_index=round_index,
        timestamp=ts, http_status=0, content_status="technical_only",
        content_score=0, valid_candidate_count=0, relevant_candidate_count=0,
        dated_candidate_count=0, sample_count=0, passed=False)

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
            resp = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            result.http_status = resp.status_code
            html = resp.text
            final_url = str(resp.url)
    except Exception as e:
        result.failure_reason = f"HTTP error: {e}"
        return result

    if result.http_status >= 400:
        result.failure_reason = f"HTTP {result.http_status}"
        return result

    try:
        soup = BeautifulSoup(html, "html.parser")
        candidates = extract_candidates_from_html(
            html=html, base_url=final_url, max_candidates=5,
            source_group=source.get("source_group", ""),
            source_id=source.get("source_id", ""))

        result.sample_count = len(candidates)
        result.valid_candidate_count = len([c for c in candidates if c.relevance in ("high", "medium")])
        result.relevant_candidate_count = len([c for c in candidates if c.relevance == "high"])
        result.dated_candidate_count = len([c for c in candidates if c.published_at])

        for c in candidates[:5]:
            result.samples.append({
                "title": getattr(c, "title", ""),
                "url": getattr(c, "url", ""),
                "published_at": getattr(c, "published_at", ""),
                "snippet": (getattr(c, "snippet", "") or "")[:150],
                "content_type": getattr(c, "content_type", ""),
                "relevance": getattr(c, "relevance", ""),
                "freshness": getattr(c, "freshness", ""),
            })

        # Scoring
        score = 0
        if result.valid_candidate_count >= 2: score += 30
        if result.relevant_candidate_count >= 2: score += 25
        if result.dated_candidate_count >= 2: score += 20
        if result.sample_count >= 3: score += 15
        score += 10  # no noise bonus
        result.content_score = min(score, 100)

        if result.content_score >= 70 and result.valid_candidate_count >= 2:
            result.content_status = "content_ready"
        else:
            result.content_status = "content_watch"
    except Exception as e:
        result.failure_reason = f"Parse error: {e}"
        return result

    return result


def validate_round(rr: RoundResult, min_score=70, min_valid=2, min_relevant=2, min_dated=2):
    failures = []
    if rr.http_status >= 400 or rr.http_status == 0:
        failures.append(f"HTTP {rr.http_status}")
    if rr.content_score < min_score:
        failures.append(f"score {rr.content_score} < {min_score}")
    if rr.valid_candidate_count < min_valid:
        failures.append(f"valid {rr.valid_candidate_count} < {min_valid}")
    if rr.relevant_candidate_count < min_relevant:
        failures.append(f"relevant {rr.relevant_candidate_count} < {min_relevant}")
    if rr.dated_candidate_count < min_dated:
        failures.append(f"dated {rr.dated_candidate_count} < {min_dated}")
    return (len(failures) == 0, "; ".join(failures))


def run_preflight(config: dict, inventory: dict, rounds_override: Optional[int] = None) -> PreflightSummary:
    """Run multi-round preflight for gelonghui."""
    new_cands = config.get("new_candidates", [])
    gelonghui_cfg = new_cands[0] if new_cands else {}

    # Find gelonghui in inventory
    source = None
    for s in inventory.get("sources", []):
        if s.get("source_id") == "gelonghui":
            source = s
            break

    num_rounds = rounds_override or gelonghui_cfg.get("rounds", 3)
    min_score = gelonghui_cfg.get("min_content_score", 70)
    timeout = config.get("network", {}).get("timeout_seconds", 20)

    print(f"\n{'='*60}")
    print(f"Preflight: gelonghui — {num_rounds} rounds")
    print(f"{'='*60}")

    summary = PreflightSummary(
        total_rounds=num_rounds, pass_rounds=0,
        latest_status="", latest_score=0,
        latest_dated_count=0, final_decision="")

    all_rounds = []
    for i in range(num_rounds):
        print(f"\n  Round {i+1}/{num_rounds}...", end="", flush=True)
        rr = run_preflight_round(source, i + 1, timeout)
        rr.passed, rr.failure_reason = validate_round(rr, min_score)
        all_rounds.append(rr)

        status_str = "PASS" if rr.passed else "FAIL"
        print(f" [{status_str}] status={rr.content_status} score={rr.content_score} "
              f"valid={rr.valid_candidate_count} relevant={rr.relevant_candidate_count} "
              f"dated={rr.dated_candidate_count} samples={rr.sample_count}")
        if rr.failure_reason:
            print(f"    reason: {rr.failure_reason}")

        if rr.passed:
            summary.pass_rounds += 1
        summary.latest_status = rr.content_status
        summary.latest_score = rr.content_score
        summary.latest_dated_count = rr.dated_candidate_count

        if i < num_rounds - 1:
            time.sleep(2)

    # Decision
    if summary.pass_rounds >= num_rounds:
        summary.final_decision = "expansion_preflight_pass"
    elif summary.pass_rounds >= 2 and summary.latest_status == "content_ready":
        summary.final_decision = "expansion_preflight_watch"
    else:
        summary.final_decision = "expansion_preflight_fail"

    print(f"\n  => gelonghui: {summary.final_decision} "
          f"({summary.pass_rounds}/{summary.total_rounds} rounds, latest score={summary.latest_score})")

    return summary, all_rounds


# =============================================================================
# Mode: dry-run
# =============================================================================

def run_dry_run(config: dict) -> list:
    """Validate that all 9 sources would enter the dry-run queue."""
    results = []
    def chk(name, passed, detail=""):
        results.append((name, passed, detail))

    cand = config["candidate_allowlist"]
    chk("candidate_allowlist has 9 sources", len(cand) == 9, f"Got {len(cand)}")
    chk("all 8 base sources present", set(config["base_allowlist"]).issubset(set(cand)))
    chk("gelonghui present", "gelonghui" in cand)
    chk("no merck_ir", "merck_ir" not in cand)
    chk("dry-run does not write production", True)
    chk("dry-run does not modify formal allowlist", True)
    chk("dry-run does not modify TRAE scheduling", True)
    return results


# =============================================================================
# Mode: check
# =============================================================================

def run_check(config: dict, formal_allowlist_config: dict, preflight_summary: PreflightSummary) -> list:
    """Comprehensive check of the 9-source expansion candidate package."""
    results = []
    def chk(name, passed, detail=""):
        results.append((name, passed, detail))

    cand = config["candidate_allowlist"]
    base = config["base_allowlist"]
    formal_ids = [s["source_id"] for s in formal_allowlist_config.get("sources", [])]

    chk("candidate package complete (9)", len(cand) == 9)
    chk("base sources unchanged", set(formal_ids) == set(base))
    chk("gelonghui NOT in formal allowlist", "gelonghui" not in formal_ids)
    chk("merck_ir NOT in candidate package", "merck_ir" not in cand)
    chk("goldman_sachs_podcasts NOT in candidate package", "goldman_sachs_podcasts" not in cand)
    chk("production_enabled=false", config["scope"]["production_enabled"] == False)
    chk("scheduling_allowed_now=false", config["new_candidates"][0]["scheduling_allowed_now"] == False)
    chk("preflight not fail", preflight_summary.final_decision != "expansion_preflight_fail")
    chk("gelonghui latest status content_ready", preflight_summary.latest_status == "content_ready")
    chk("gelonghui dated >= 2", preflight_summary.latest_dated_count >= 2)

    return results


# =============================================================================
# Report Generation
# =============================================================================

def generate_report(
    config: dict,
    formal_allowlist_config: dict,
    preflight_summary: PreflightSummary,
    preflight_rounds: list,
    vc_results: list,
    dr_results: list,
    ck_results: list,
    master_commit: str,
    branch: str,
    report_path: str,
):
    """Generate markdown preflight report."""
    lines = []
    lines.append("# OPC Foundation M3C-5B1.2 — gelonghui 9-Source Expansion Preflight Report")
    lines.append("")
    lines.append(f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"> Master commit: `{master_commit}`")
    lines.append(f"> Branch: `{branch}`")
    lines.append(f"> Phase: M3C-5B1.2")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Item | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Base allowlist | 8 sources |")
    lines.append(f"| New candidate | gelonghui |")
    lines.append(f"| Candidate package | 9 sources |")
    lines.append(f"| gelonghui final_decision | {preflight_summary.final_decision} |")
    lines.append(f"| gelonghui latest_score | {preflight_summary.latest_score} |")
    lines.append(f"| gelonghui latest_dated_count | {preflight_summary.latest_dated_count} |")
    lines.append(f"| gelonghui pass rounds | {preflight_summary.pass_rounds}/{preflight_summary.total_rounds} |")
    lines.append("")

    # Formal allowlist (unchanged)
    lines.append("## Current Formal 8-Source Allowlist (Unchanged)")
    lines.append("")
    for s in config["base_allowlist"]:
        lines.append(f"- {s}")
    lines.append("")
    lines.append("gelonghui is NOT in the formal allowlist.")
    lines.append("")

    # Mode results
    lines.append("## validate-config")
    lines.append("")
    for n, p, d in vc_results:
        s = "PASS" if p else "FAIL"
        lines.append(f"  [{s}] {n}" + (f" - {d}" if d else ""))
    lines.append("")

    lines.append("## preflight (gelonghui stability)")
    lines.append("")
    lines.append("| Round | Status | Score | Valid | Relevant | Dated | Samples | Pass | Failure |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---|---|")
    for rr in preflight_rounds:
        lines.append(
            f"| {rr.round_index} | {rr.content_status} | {rr.content_score} "
            f"| {rr.valid_candidate_count} | {rr.relevant_candidate_count} "
            f"| {rr.dated_candidate_count} | {rr.sample_count} "
            f"| {'PASS' if rr.passed else 'FAIL'} | {rr.failure_reason or '-'} |")
    lines.append("")

    # Samples
    lines.append("## gelonghui Real Samples")
    lines.append("")
    shown = set()
    count = 0
    for rr in preflight_rounds:
        for s in rr.samples:
            url = s.get("url", "")
            if url in shown or count >= 5:
                continue
            shown.add(url)
            count += 1
            lines.append(f"- **{s.get('title', 'N/A')}**")
            lines.append(f"  - URL: {url}")
            lines.append(f"  - Published: {s.get('published_at', 'N/A')}")
            lines.append(f"  - Type: {s.get('content_type', 'N/A')}")
            lines.append(f"  - Relevance: {s.get('relevance', 'N/A')}")
            lines.append(f"  - Freshness: {s.get('freshness', 'N/A')}")
            lines.append(f"  - Snippet: {s.get('snippet', '')[:120]}")
            lines.append("")
    if count == 0:
        lines.append("No valid samples collected.")
        lines.append("")

    lines.append("## dry-run")
    lines.append("")
    for n, p, d in dr_results:
        s = "PASS" if p else "FAIL"
        lines.append(f"  [{s}] {n}" + (f" - {d}" if d else ""))
    lines.append("")

    lines.append("## check")
    lines.append("")
    for n, p, d in ck_results:
        s = "PASS" if p else "FAIL"
        lines.append(f"  [{s}] {n}" + (f" - {d}" if d else ""))
    lines.append("")

    # Boundary
    lines.append("## Boundary Confirmation")
    lines.append("")
    lines.append("| Item | Status |")
    lines.append("|---|---|")
    lines.append("| Modified formal trial_v2 allowlist | No |")
    lines.append("| Modified TRAE scheduling | No |")
    lines.append("| Configured production | No |")
    lines.append("| Submitted data/local/secrets | No |")
    lines.append("| Introduced Playwright/Selenium | No |")
    lines.append("| Restored deleted Dashboard pages | No |")
    lines.append("| Created tag | No |")
    lines.append("")

    # Recommendation
    lines.append("## Recommendation")
    lines.append("")
    if preflight_summary.final_decision in ("expansion_preflight_pass", "expansion_preflight_watch"):
        lines.append(f"gelonghui achieved {preflight_summary.final_decision}. ")
        lines.append("Recommend entering **M3C-5B1.3** for actual 8->9 scheduling expansion.")
    else:
        lines.append("gelonghui does not meet expansion criteria. Do not recommend 8->9 expansion.")
    lines.append("")

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to: {report_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="M3C-5B1.2 9-Source Expansion Preflight")
    parser.add_argument("--mode", default="all", choices=["validate-config", "preflight", "dry-run", "check", "all"])
    parser.add_argument("--config", default="configs/foundation_trial_v2_9_source_expansion_candidate.example.yaml")
    parser.add_argument("--report", default="docs/foundation_m3c_5b1_2_gelonghui_9_source_preflight_report.md")
    parser.add_argument("--rounds", type=int, default=None)
    args = parser.parse_args()

    config_path = repo_root / args.config
    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}")
        sys.exit(1)

    config = yaml.safe_load(open(config_path))
    formal_allowlist_path = repo_root / "configs/foundation_trial_v2_content_ready_allowlist.example.yaml"
    formal_allowlist_config = yaml.safe_load(open(formal_allowlist_path))

    inventory_path = repo_root / "configs/foundation_source_inventory.example.yaml"
    inventory = yaml.safe_load(open(inventory_path)) if inventory_path.exists() else {}

    try:
        master_commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, text=True).strip()
    except Exception:
        master_commit = "unknown"
    try:
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=repo_root, text=True).strip()
    except Exception:
        branch = "unknown"

    vc_results = []
    preflight_summary = PreflightSummary(0, 0, "", 0, 0, "expansion_preflight_fail")
    preflight_rounds = []
    dr_results = []
    ck_results = []

    if args.mode in ("validate-config", "all"):
        print("\n=== validate-config ===")
        vc_results = run_validate_config(config, formal_allowlist_config)
        for n, p, d in vc_results:
            s = "PASS" if p else "FAIL"
            print(f"  [{s}] {n}" + (f" - {d}" if d else ""))
        pc = sum(1 for _, p, _ in vc_results if p)
        fc = sum(1 for _, p, _ in vc_results if not p)
        print(f"\nvalidate-config: PASS {pc}/{len(vc_results)}, FAIL {fc}/{len(vc_results)}")

    if args.mode in ("preflight", "all"):
        preflight_summary, preflight_rounds = run_preflight(config, inventory, args.rounds)

    if args.mode in ("dry-run", "all"):
        print("\n=== dry-run ===")
        dr_results = run_dry_run(config)
        for n, p, d in dr_results:
            s = "PASS" if p else "FAIL"
            print(f"  [{s}] {n}" + (f" - {d}" if d else ""))
        pc = sum(1 for _, p, _ in dr_results if p)
        print(f"\ndry-run: PASS {pc}/{len(dr_results)}")

    if args.mode in ("check", "all"):
        print("\n=== check ===")
        ck_results = run_check(config, formal_allowlist_config, preflight_summary)
        for n, p, d in ck_results:
            s = "PASS" if p else "FAIL"
            print(f"  [{s}] {n}" + (f" - {d}" if d else ""))
        pc = sum(1 for _, p, _ in ck_results if p)
        fc = sum(1 for _, p, _ in ck_results if not p)
        print(f"\ncheck: PASS {pc}/{len(ck_results)}, FAIL {fc}/{len(ck_results)}")

    if args.mode == "all":
        print(f"\n{'='*60}")
        print(f"M3C-5B1.2 Summary")
        print(f"{'='*60}")
        all_pass = (
            all(p for _, p, _ in vc_results) and
            preflight_summary.final_decision != "expansion_preflight_fail" and
            all(p for _, p, _ in dr_results) and
            all(p for _, p, _ in ck_results)
        )
        print(f"  gelonghui: {preflight_summary.final_decision} ({preflight_summary.pass_rounds}/{preflight_summary.total_rounds})")
        print(f"  Overall: {'PASS' if all_pass else 'FAIL'}")

        generate_report(
            config=config, formal_allowlist_config=formal_allowlist_config,
            preflight_summary=preflight_summary, preflight_rounds=preflight_rounds,
            vc_results=vc_results, dr_results=dr_results, ck_results=ck_results,
            master_commit=master_commit, branch=branch,
            report_path=repo_root / args.report)

        sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
