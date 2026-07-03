#!/usr/bin/env python3
"""
OPC Foundation Trial V2 Next Candidates Preflight Runner (M3C-5B1.1)
========================================================================

Independent preflight for gelonghui / merck_ir as next_scheduling_candidate.
Does NOT modify trial_v2 allowlist, TRAE scheduling, or production.

Usage:
    python scripts/run_foundation_trial_v2_next_candidates_preflight.py
    python scripts/run_foundation_trial_v2_next_candidates_preflight.py \
        --config configs/foundation_trial_v2_next_candidates_preflight.example.yaml \
        --rounds 3 \
        --report docs/foundation_m3c_5b1_1_next_candidate_preflight_report.md

Author: OPC Foundation
"""

import argparse
import json
import os
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
    ContentAuditResult,
    ContentValidityAuditor,
    extract_candidates_from_html,
)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RoundResult:
    """Single round preflight result for one source."""
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
    noise_flags: list = field(default_factory=list)
    samples: list = field(default_factory=list)


@dataclass
class SourcePreflightResult:
    """Aggregate preflight result for one source across all rounds."""
    source_id: str
    source_name: str
    total_rounds: int
    pass_rounds: int
    latest_status: str
    latest_score: int
    final_decision: str  # preflight_pass | preflight_watch | preflight_fail
    consecutive_failures: int
    rounds: list = field(default_factory=list)
    failure_reasons: list = field(default_factory=list)


# =============================================================================
# Helpers
# =============================================================================

NOISE_FILTER_TERMS = {
    "login", "register", "download app", "app download", "advertisement",
    "privacy policy", "disclaimer", "contact us", "search", "navigation",
    "terms of service", "cookie settings", "sign in", "create account",
}

MERCK_VALID_CONTENT = {
    "earnings", "investor", "webcast", "quarterly", "results", "presentation",
    "press release", "fda", "approval", "announcement", "financial",
    "sec filing", "annual report", "dividend", "guidance", "pipeline",
}

GELONGHUI_VALID_CONTENT = {
    "港股", "A股", "美股", "宏观", "财经", "市场", "股市", "基金",
    "研报", "策略", "行业", "板块", "涨跌", "新股", "ipo",
}


def classify_noise_flags(page_text: str, http_status: int = 200) -> list:
    """Lightweight noise flag classification (mirrors content_validity module)."""
    flags = []
    lower = page_text.lower()
    if http_status == 403:
        flags.append("blocked_403")
    if http_status == 0:
        flags.append("network_failure")
    if "login" in lower and "password" in lower:
        flags.append("login_page")
    if "cookie" in lower and "consent" in lower:
        flags.append("cookie_consent")
    if len(page_text.strip()) < 200:
        flags.append("empty_page")
    return flags


def validate_round(
    round_result: RoundResult,
    min_score: int,
    min_valid: int,
    min_relevant: int,
    min_dated: int,
) -> tuple[bool, str]:
    """Check if a single round passes preflight criteria."""
    failures = []
    if round_result.http_status >= 400 or round_result.http_status == 0:
        failures.append(f"HTTP {round_result.http_status}")
    if round_result.content_score < min_score:
        failures.append(f"score {round_result.content_score} < {min_score}")
    if round_result.valid_candidate_count < min_valid:
        failures.append(f"valid {round_result.valid_candidate_count} < {min_valid}")
    if round_result.relevant_candidate_count < min_relevant:
        failures.append(f"relevant {round_result.relevant_candidate_count} < {min_relevant}")
    if round_result.dated_candidate_count < min_dated:
        failures.append(f"dated {round_result.dated_candidate_count} < {min_dated}")
    return (len(failures) == 0, "; ".join(failures))


def classify_source_decision(result: SourcePreflightResult) -> str:
    """
    Classify source-level preflight decision:
    - preflight_pass: 3/3 rounds pass, or 2/3 + latest pass
    - preflight_watch: 2/3 pass but with some instability
    - preflight_fail: < 2/3 pass or consecutive timeout/403/empty
    """
    if result.consecutive_failures >= 2:
        return "preflight_fail"
    if result.total_rounds == 0:
        return "preflight_fail"
    pass_rate = result.pass_rounds / result.total_rounds
    if pass_rate >= 1.0:
        return "preflight_pass"
    if pass_rate >= 2 / 3 and result.latest_status == "content_ready":
        return "preflight_watch"
    if pass_rate >= 2 / 3:
        return "preflight_watch"
    return "preflight_fail"


# =============================================================================
# Preflight Runner
# =============================================================================

def run_single_preflight_round(
    source: dict,
    round_index: int,
    min_candidates: int = 5,
    timeout: int = 20,
) -> RoundResult:
    """Execute one preflight round for a single source using existing audit module."""
    ts = datetime.now(timezone.utc).isoformat()

    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as e:
        return RoundResult(
            source_id=source.get("source_id", ""),
            round_index=round_index,
            timestamp=ts,
            http_status=0,
            content_status="technical_only",
            content_score=0,
            valid_candidate_count=0,
            relevant_candidate_count=0,
            dated_candidate_count=0,
            sample_count=0,
            passed=False,
            failure_reason=f"Missing dependency: {e}",
        )

    url = source.get("url", "")
    source_id = source.get("source_id", "")

    result = RoundResult(
        source_id=source_id,
        round_index=round_index,
        timestamp=ts,
        http_status=0,
        content_status="technical_only",
        content_score=0,
        valid_candidate_count=0,
        relevant_candidate_count=0,
        dated_candidate_count=0,
        sample_count=0,
        passed=False,
        failure_reason="",
    )

    # HTTP fetch
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
            resp = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            })
            result.http_status = resp.status_code
            html = resp.text
            final_url = str(resp.url)
    except Exception as e:
        result.http_status = 0
        result.failure_reason = f"HTTP error: {e}"
        result.content_status = "technical_only"
        return result

    if result.http_status >= 400:
        result.failure_reason = f"HTTP {result.http_status}"
        result.content_status = "technical_only"
        return result

    # Parse and extract candidates
    try:
        soup = BeautifulSoup(html, "html.parser")
        full_page_text = soup.get_text(separator=" ", strip=True)
        result.noise_flags = classify_noise_flags(full_page_text, result.http_status)

        candidates = extract_candidates_from_html(
            html=html,
            base_url=final_url,
            max_candidates=min_candidates,
            source_group=source.get("source_group", ""),
            source_id=source_id,
        )

        result.sample_count = len(candidates)
        result.valid_candidate_count = len([c for c in candidates if c.relevance in ("high", "medium")])
        result.relevant_candidate_count = len([c for c in candidates if c.relevance == "high"])
        result.dated_candidate_count = len([c for c in candidates if c.published_at or c.freshness == "fresh"])

        # Collect samples
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

        # Scoring (mirrors content_validity module logic)
        score = 0
        if result.valid_candidate_count >= 2:
            score += 30
        if result.relevant_candidate_count >= 2:
            score += 25
        if result.dated_candidate_count >= 2:
            score += 20
        if result.sample_count >= 3:
            score += 15
        if not any("blocked" in f or "login" in f for f in result.noise_flags):
            score += 10
        result.content_score = min(score, 100)

        # Status classification
        if result.content_score >= 70 and result.valid_candidate_count >= 2:
            result.content_status = "content_ready"
        elif result.content_score >= 45 and result.valid_candidate_count >= 1:
            result.content_status = "content_watch"
        elif result.http_status == 403 or "blocked" in str(result.noise_flags):
            result.content_status = "technical_only"
        else:
            result.content_status = "content_reject"

    except Exception as e:
        result.failure_reason = f"Parse error: {e}"
        return result

    return result


def run_source_preflight(
    source: dict,
    config: dict,
    rounds_override: Optional[int] = None,
) -> SourcePreflightResult:
    """Run multiple preflight rounds for a single source."""
    source_id = source.get("source_id", "")
    source_name = source.get("source_name", "")

    # Get thresholds from config
    candidate_cfg = None
    for c in config.get("next_scheduling_candidates", []):
        if c.get("source_id") == source_id:
            candidate_cfg = c
            break

    if candidate_cfg is None:
        return SourcePreflightResult(
            source_id=source_id,
            source_name=source_name,
            total_rounds=0,
            pass_rounds=0,
            latest_status="content_reject",
            latest_score=0,
            final_decision="preflight_fail",
            consecutive_failures=0,
            failure_reasons=["Source not found in candidate config"],
        )

    num_rounds = rounds_override or candidate_cfg.get("rounds", 3)
    min_score = candidate_cfg.get("min_content_score", 70)
    min_valid = candidate_cfg.get("min_valid_candidates", 2)
    min_relevant = candidate_cfg.get("min_relevant_candidates", 2)
    min_dated = candidate_cfg.get("min_dated_candidates", 2)
    max_candidates = config.get("scope", {}).get("max_candidates", 5)
    timeout = config.get("network", {}).get("timeout_seconds", 20)

    agg = SourcePreflightResult(
        source_id=source_id,
        source_name=source_name,
        total_rounds=num_rounds,
        pass_rounds=0,
        latest_status="",
        latest_score=0,
        final_decision="",
        consecutive_failures=0,
    )

    print(f"\n{'='*60}")
    print(f"Preflight: {source_name} ({source_id}) — {num_rounds} rounds")
    print(f"{'='*60}")

    for i in range(num_rounds):
        print(f"\n  Round {i+1}/{num_rounds}...", end="", flush=True)
        rr = run_single_preflight_round(
            source=source,
            round_index=i + 1,
            min_candidates=max_candidates,
            timeout=timeout,
        )
        rr.passed, rr.failure_reason = validate_round(
            rr, min_score, min_valid, min_relevant, min_dated,
        )
        agg.rounds.append(rr)

        status_str = "PASS" if rr.passed else "FAIL"
        print(f" [{status_str}] status={rr.content_status} score={rr.content_score} "
              f"valid={rr.valid_candidate_count} relevant={rr.relevant_candidate_count} "
              f"dated={rr.dated_candidate_count} samples={rr.sample_count}")
        if rr.failure_reason:
            print(f"    reason: {rr.failure_reason}")
            agg.failure_reasons.append(rr.failure_reason)

        if rr.passed:
            agg.pass_rounds += 1
            agg.consecutive_failures = 0
        else:
            agg.consecutive_failures += 1

        agg.latest_status = rr.content_status
        agg.latest_score = rr.content_score

        # Delay between rounds (avoid hammering)
        if i < num_rounds - 1:
            time.sleep(2)

    agg.final_decision = classify_source_decision(agg)
    print(f"\n  => {source_id}: {agg.final_decision} "
          f"({agg.pass_rounds}/{agg.total_rounds} rounds passed, latest score={agg.latest_score})")

    return agg


def generate_preflight_report(
    results: list[SourcePreflightResult],
    config: dict,
    master_commit: str,
    branch: str,
    report_path: str,
):
    """Generate markdown preflight report."""
    lines = []
    lines.append(f"# OPC Foundation M3C-5B1.1 — Next Candidate Preflight Report")
    lines.append("")
    lines.append(f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"> Master commit: `{master_commit}`")
    lines.append(f"> Branch: `{branch}`")
    lines.append(f"> Phase: M3C-5B1.1")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| source_id | source_name | rounds | pass_rounds | latest_status | latest_score | final_decision |")
    lines.append("|---|---|---:|---:|---|---:|---|")
    for r in results:
        lines.append(
            f"| {r.source_id} | {r.source_name} | {r.total_rounds} | {r.pass_rounds} "
            f"| {r.latest_status} | {r.latest_score} | {r.final_decision} |"
        )
    lines.append("")

    # Base allowlist
    base = config.get("base_allowlist", [])
    lines.append("## Base 8-Source Allowlist (Unchanged)")
    lines.append("")
    for s in base:
        lines.append(f"- {s}")
    lines.append("")

    # Detailed results per source
    for agg in results:
        lines.append(f"## Preflight: {agg.source_name} ({agg.source_id})")
        lines.append("")
        lines.append(f"**Final decision: {agg.final_decision}**")
        lines.append(f"- Total rounds: {agg.total_rounds}")
        lines.append(f"- Pass rounds: {agg.pass_rounds}")
        lines.append(f"- Latest status: {agg.latest_status}")
        lines.append(f"- Latest score: {agg.latest_score}")
        lines.append(f"- Consecutive failures: {agg.consecutive_failures}")
        if agg.failure_reasons:
            lines.append(f"- Failure reasons: {'; '.join(agg.failure_reasons[:5])}")
        lines.append("")

        # Per-round details
        lines.append("### Round Details")
        lines.append("")
        lines.append("| Round | Status | Score | HTTP | Valid | Relevant | Dated | Samples | Pass | Failure Reason |")
        lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---|---|")
        for rr in agg.rounds:
            lines.append(
                f"| {rr.round_index} | {rr.content_status} | {rr.content_score} "
                f"| {rr.http_status} | {rr.valid_candidate_count} | {rr.relevant_candidate_count} "
                f"| {rr.dated_candidate_count} | {rr.sample_count} "
                f"| {'PASS' if rr.passed else 'FAIL'} | {rr.failure_reason or '-'} |"
            )
        lines.append("")

        # Samples
        lines.append("### Real Samples")
        lines.append("")
        # Collect all samples from all rounds
        all_samples = []
        for rr in agg.rounds:
            for s in rr.samples:
                if s.get("url") and s["url"] not in [x.get("url") for x in all_samples]:
                    all_samples.append(s)
        # Show up to 5 unique samples
        shown_urls = set()
        count = 0
        for s in all_samples:
            if count >= 5:
                break
            url = s.get("url", "")
            if url in shown_urls:
                continue
            shown_urls.add(url)
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

    # Risk assessment
    lines.append("## Risk Assessment")
    lines.append("")
    for agg in results:
        lines.append(f"### {agg.source_id}")
        lines.append("")
        if agg.final_decision == "preflight_pass":
            lines.append("No significant risk identified. Source meets content_ready criteria consistently.")
        elif agg.final_decision == "preflight_watch":
            lines.append(f"Minor instability detected. Failure reasons: {'; '.join(agg.failure_reasons[:5])}")
        else:
            lines.append(f"Source does not meet criteria. Reasons: {'; '.join(agg.failure_reasons[:5])}")
        lines.append("")

    # Boundary confirmation
    lines.append("## Boundary Confirmation")
    lines.append("")
    lines.append("| Item | Status |")
    lines.append("|---|---|")
    lines.append("| Modified trial_v2 allowlist | No |")
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
    all_pass = all(r.final_decision in ("preflight_pass", "preflight_watch") for r in results)
    if all_pass:
        lines.append("Both candidates meet minimum preflight criteria. ")
        lines.append("Recommend entering **M3C-5B1.2** evaluation for 8 -> 10 expansion readiness assessment.")
    else:
        failed = [r.source_id for r in results if r.final_decision == "preflight_fail"]
        lines.append(f"Candidates not ready for expansion: {', '.join(failed)}. ")
        lines.append("Do not recommend 8 -> 10 expansion at this time.")
    lines.append("")

    # Write
    report_dir = Path(report_path).parent
    report_dir.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to: {report_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="M3C-5B1.1 Next Candidate Preflight Runner"
    )
    parser.add_argument(
        "--config",
        default="configs/foundation_trial_v2_next_candidates_preflight.example.yaml",
        help="Path to preflight config",
    )
    parser.add_argument("--rounds", type=int, default=None, help="Override rounds per source")
    parser.add_argument(
        "--report",
        default="docs/foundation_m3c_5b1_1_next_candidate_preflight_report.md",
        help="Output report path",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Filter to specific source(s), e.g. --source gelonghui. Comma-separated for multiple.",
    )
    args = parser.parse_args()

    config_path = repo_root / args.config
    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}")
        sys.exit(1)

    config = yaml.safe_load(open(config_path))

    # Validate scope
    assert config["scope"]["production_enabled"] == False, "production_enabled must be false"
    assert config["scope"]["affects_trial_v2_allowlist"] == False, "must not affect allowlist"
    assert config["scope"]["affects_trae_scheduling"] == False, "must not affect scheduling"

    # Get source inventory for URLs
    inventory_path = repo_root / "configs" / "foundation_source_inventory.example.yaml"
    inventory = yaml.safe_load(open(inventory_path)) if inventory_path.exists() else {}
    all_sources = inventory.get("sources", [])

    # Get master commit
    import subprocess
    try:
        master_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root, text=True
        ).strip()
    except Exception:
        master_commit = "unknown"

    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=repo_root, text=True
        ).strip()
    except Exception:
        branch = "unknown"

    # Run preflight for each candidate
    results = []

    # Apply --source filter if specified
    source_filter = None
    if args.source:
        source_filter = set(s.strip() for s in args.source.split(","))
        print(f"Source filter: {source_filter}")

    for candidate_cfg in config.get("next_scheduling_candidates", []):
        source_id = candidate_cfg.get("source_id")

        # Skip if --source filter is active and source not in filter
        if source_filter and source_id not in source_filter:
            print(f"Skipping {source_id} (not in --source filter)")
            continue
        # Find source in inventory
        source = None
        for s in all_sources:
            if s.get("source_id") == source_id:
                source = s
                break
        if source is None:
            print(f"WARNING: {source_id} not found in inventory, using minimal config")
            source = {
                "source_id": source_id,
                "source_name": candidate_cfg.get("source_name", source_id),
                "url": candidate_cfg.get("url", ""),
                "source_group": "",
            }

        agg = run_source_preflight(source, config, rounds_override=args.rounds)
        results.append(agg)

    # Generate report
    generate_preflight_report(
        results=results,
        config=config,
        master_commit=master_commit,
        branch=branch,
        report_path=repo_root / args.report,
    )

    # Print summary
    print(f"\n{'='*60}")
    print(f"M3C-5B1.1 Preflight Summary")
    print(f"{'='*60}")
    all_pass = True
    for r in results:
        print(f"  {r.source_id}: {r.final_decision} "
              f"({r.pass_rounds}/{r.total_rounds} rounds, latest score={r.latest_score})")
        if r.final_decision == "preflight_fail":
            all_pass = False
    print(f"\n  Overall: {'PASS' if all_pass else 'FAIL'}")
    print(f"  Report: {args.report}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
