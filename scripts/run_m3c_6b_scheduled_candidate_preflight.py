#!/usr/bin/env python3
"""
OPC Foundation M3C-6B Scheduled Candidate Preflight Runner
==========================================================

Independent preflight for reuters / marketwatch / streetinsider as
scheduled_candidate. Includes TRAE execution capability assessment
(browser / skill / automation design only — does NOT create permanent tasks).

Boundaries:
    - Does NOT modify trial_v2 allowlist
    - Does NOT modify TRAE scheduling
    - Does NOT configure production
    - Does NOT commit data / secrets / cookies / raw HTML / screenshots
    - Does NOT bypass login / paywall / captcha / Cloudflare
    - Does NOT introduce Playwright / Selenium into repo
    - Does NOT restore deleted Dashboard pages

Usage:
    python scripts/run_m3c_6b_scheduled_candidate_preflight.py --source reuters
    python scripts/run_m3c_6b_scheduled_candidate_preflight.py --source marketwatch
    python scripts/run_m3c_6b_scheduled_candidate_preflight.py --source streetinsider
    python scripts/run_m3c_6b_scheduled_candidate_preflight.py --all

Author: OPC Foundation
"""

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import yaml

# Ensure src is on PYTHONPATH
repo_root = Path(__file__).resolve().parent.parent
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from opc_foundation.source_inventory.execution_capabilities import (
    ExecutionMode,
    M3C_6B_ALLOWED_CANDIDATES,
    SampleItem,
    SourceExecutionCapability,
    TraeBrowserAssessment,
    TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS,
    TRAE_AUTOMATION_ELIGIBLE_DECISIONS,
    apply_recommendations,
    compute_allowlist_flags,
    compute_recommended_execution_mode,
    is_candidate_source,
    make_default_capability,
    scan_sensitive_keywords,
    validate_execution_capability,
)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_CONFIG = "configs/foundation_m3c_6b_scheduled_candidate_preflight.example.yaml"
DEFAULT_REPORT = "docs/foundation_m3c_6b_scheduled_candidate_preflight_report.md"

DEFAULT_USER_AGENT = (
    "OPC-Foundation-M3C-6B-Preflight/1.0 "
    "(+https://github.com/xe7dx54321-stack/opc-foundation)"
)

# Common feed / sitemap path candidates to probe (relative URLs).
FEED_CANDIDATES = (
    "/rss",
    "/rss.xml",
    "/feed",
    "/feed.xml",
    "/atom.xml",
    "/feeds/news.xml",
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/news-sitemap.xml",
)

# Patterns suggesting a login page or paywall
LOGIN_HINTS = ("sign in", "log in", "login", "sign-in", "create account", "subscribe to continue")
PAYWALL_HINTS = ("subscribe to read", "this content is for subscribers", "paywall", "premium content", "subscribe now")
CAPTCHA_HINTS = ("captcha", "recaptcha", "hcaptcha", "are you a human", "verify you are human")
ANTIBOT_HINTS = ("cloudflare", "access denied", "checking your browser", "cf-ray", "cf-mitigated")


# =============================================================================
# Helpers
# =============================================================================

def _safe_get(obj: dict, key: str, default: Any = "") -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else default


def classify_noise_flags(page_text: str, http_status: int = 200) -> list[str]:
    """Lightweight noise / risk flag classification."""
    flags: list[str] = []
    lower = page_text.lower()
    if http_status == 403:
        flags.append("blocked_403")
    if http_status == 0:
        flags.append("network_failure")
    if any(h in lower for h in LOGIN_HINTS):
        flags.append("login_page_hint")
    if any(h in lower for h in PAYWALL_HINTS):
        flags.append("paywall_hint")
    if any(h in lower for h in CAPTCHA_HINTS):
        flags.append("captcha_hint")
    if any(h in lower for h in ANTIBOT_HINTS):
        flags.append("antibot_hint")
    if len(page_text.strip()) < 200:
        flags.append("empty_page")
    return flags


def extract_date_text(text: str) -> str:
    """Try to extract a date or relative-time string from a snippet."""
    if not text:
        return ""
    # ISO date
    m = re.search(r"\b(20\d{2})[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12][0-9]|3[01])\b", text)
    if m:
        return m.group(0)
    # Relative time (English)
    m = re.search(r"\b(\d+)\s*(minute|hour|day|week|month|year)s?\s*ago\b", text, re.IGNORECASE)
    if m:
        return m.group(0)
    # Chinese relative time
    m = re.search(r"\d+\s*(分钟|小时|天|周|月|年)前", text)
    if m:
        return m.group(0)
    # MM-DD HH:mm
    m = re.search(r"\b(0?[1-9]|1[0-2])-(0?[1-9]|[12][0-9]|3[01])\s+\d{2}:\d{2}\b", text)
    if m:
        return m.group(0)
    return ""


def extract_links_with_dates(html: str, base_url: str, max_items: int = 10) -> list[SampleItem]:
    """Extract candidate anchor items with date hints from HTML.

    Uses a simple regex-based approach to avoid depending on heavy HTML parsing
    in the script layer. We pull <a href="..."> tags with surrounding text that
    may include a date or relative time.
    """
    if not html:
        return []
    items: list[SampleItem] = []
    seen_urls: set[str] = set()

    # Anchor pattern with optional title text
    anchor_re = re.compile(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )

    for match in anchor_re.finditer(html):
        if len(items) >= max_items:
            break
        raw_href = match.group(1).strip()
        if not raw_href or raw_href.startswith("#"):
            continue
        if raw_href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        try:
            full_url = urljoin(base_url, raw_href)
        except Exception:
            continue
        # Skip nav / footer / login links
        lower_href = raw_href.lower()
        if any(seg in lower_href for seg in (
            "/login", "/signin", "/signup", "/register", "/subscribe",
            "/privacy", "/terms", "/contact", "/about", "javascript:",
        )):
            continue
        if full_url in seen_urls:
            continue
        # Title: strip HTML tags
        raw_title = match.group(2)
        title = re.sub(r"<[^>]+>", " ", raw_title)
        title = re.sub(r"\s+", " ", title).strip()
        if not title or len(title) < 8:
            continue
        # Date: look in a 200-char window around the match
        start = max(0, match.start() - 100)
        end = min(len(html), match.end() + 100)
        window = html[start:end]
        date_text = extract_date_text(window)

        seen_urls.add(full_url)
        items.append(SampleItem(title=title[:200], url=full_url, date_text=date_text))

    return items


def extract_metadata_signals(html: str) -> dict[str, Any]:
    """Detect JSON-LD, OpenGraph, and basic metadata presence."""
    signals: dict[str, Any] = {
        "json_ld_count": 0,
        "opengraph_count": 0,
        "canonical_url": "",
    }
    if not html:
        return signals
    # JSON-LD blocks
    signals["json_ld_count"] = len(re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>',
        html, re.IGNORECASE,
    ))
    # OpenGraph meta tags
    signals["opengraph_count"] = len(re.findall(
        r'<meta[^>]+property=["\']og:[^"\']+["\']',
        html, re.IGNORECASE,
    ))
    # Canonical link
    m = re.search(
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if m:
        signals["canonical_url"] = m.group(1)
    return signals


def probe_feed(client: Any, base_url: str, timeout: int = 10) -> tuple[int, int, list[str]]:
    """Probe common feed / sitemap paths.

    Returns (feed_count, sitemap_count, found_paths).
    """
    feed_count = 0
    sitemap_count = 0
    found_paths: list[str] = []
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    for rel in FEED_CANDIDATES:
        url = origin + rel
        try:
            resp = client.get(url, timeout=timeout)
        except Exception:
            continue
        if resp.status_code >= 400:
            continue
        ctype = (resp.headers.get("content-type") or "").lower()
        body = resp.text[:5000].lower()
        if "sitemap" in rel:
            if resp.status_code == 200 and (
                "xml" in ctype or "<urlset" in body or "<sitemapindex" in body
            ):
                sitemap_count += 1
                found_paths.append(rel)
        else:
            if resp.status_code == 200 and (
                "xml" in ctype or "<rss" in body or "<feed" in body or "<channel>" in body
            ):
                feed_count += 1
                found_paths.append(rel)
    return feed_count, sitemap_count, found_paths


# =============================================================================
# Static HTTP Preflight
# =============================================================================

def run_static_http_preflight(
    source: dict,
    config: dict,
) -> tuple[SourceExecutionCapability, str]:
    """Run static HTTP / feed / metadata preflight for a single source.

    Returns (capability, raw_summary_for_report).
    """
    source_id = source.get("source_id", "")
    cap = make_default_capability(source_id)

    # Optional httpx import (kept optional so unit tests can run without network)
    try:
        import httpx  # type: ignore
        HAS_HTTPX = True
    except ImportError:
        HAS_HTTPX = False

    network_cfg = config.get("network", {}) or {}
    timeout = int(network_cfg.get("timeout_seconds", 20))
    ua = network_cfg.get("user_agent", DEFAULT_USER_AGENT)

    url = source.get("url", "")
    if not url:
        cap.static_http_status = "error"
        cap.evidence_summary = "missing url in source config"
        return cap, "missing url"

    if not HAS_HTTPX:
        cap.static_http_status = "not_attempted"
        cap.evidence_summary = "httpx not installed; static HTTP preflight skipped"
        return cap, "httpx unavailable"

    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    }

    # 1) Static HTTP GET
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
            resp = client.get(url, headers=headers)
            http_status = resp.status_code
            html = resp.text or ""
            final_url = str(resp.url)
            content_type = (resp.headers.get("content-type") or "").lower()
    except Exception as e:
        cap.static_http_status = "error"
        cap.evidence_summary = f"HTTP error: {e}"
        cap.risk_flags.append("network_failure")
        return cap, f"HTTP error: {e}"

    if http_status == 0:
        cap.static_http_status = "error"
        cap.risk_flags.append("network_failure")
        cap.evidence_summary = "network failure (http_status=0)"
        return cap, "network failure"

    if http_status == 403:
        cap.static_http_status = "blocked"
        cap.risk_flags.append("blocked_403")
        cap.evidence_summary = f"HTTP 403 from {url}"
        return cap, "HTTP 403"

    if http_status >= 400:
        cap.static_http_status = "error"
        cap.risk_flags.append(f"http_{http_status}")
        cap.evidence_summary = f"HTTP {http_status} from {url}"
        return cap, f"HTTP {http_status}"

    # 2) Noise / risk flags
    noise_flags = classify_noise_flags(html, http_status)
    cap.risk_flags.extend(noise_flags)

    # 3) Extract candidate items
    items = extract_links_with_dates(html, final_url, max_items=15)
    cap.static_http_valid_items = len(items)
    cap.static_http_dated_items = len([i for i in items if i.date_text])

    # 4) Static HTTP status determination
    if cap.static_http_valid_items >= 3 and not any(
        f in noise_flags for f in ("blocked_403", "login_page_hint", "paywall_hint", "captcha_hint")
    ):
        cap.static_http_status = "ok"
    elif cap.static_http_valid_items >= 1:
        cap.static_http_status = "ok_with_noise"
    elif any(f in noise_flags for f in ("login_page_hint", "paywall_hint", "captcha_hint")):
        cap.static_http_status = "blocked"
    else:
        cap.static_http_status = "ok_with_noise"

    # 5) Feed / sitemap discovery
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
            feed_count, sitemap_count, found_paths = probe_feed(client, url, timeout=timeout)
    except Exception:
        feed_count, sitemap_count, found_paths = 0, 0, []

    cap.feed_count = feed_count
    cap.sitemap_count = sitemap_count
    if feed_count > 0 or sitemap_count > 0:
        cap.feed_discovery_status = "ok"
    else:
        cap.feed_discovery_status = "not_found"

    # 6) Metadata signals
    md_signals = extract_metadata_signals(html)
    cap.metadata_count = md_signals.get("json_ld_count", 0) + md_signals.get("opengraph_count", 0)
    if cap.metadata_count > 0:
        cap.metadata_discovery_status = "ok"
    else:
        cap.metadata_discovery_status = "not_found"

    # 7) Build evidence summary (no raw HTML, no cookies, no tokens)
    evidence_parts = [
        f"http_status={http_status}",
        f"content_type={content_type}",
        f"valid_items={cap.static_http_valid_items}",
        f"dated_items={cap.static_http_dated_items}",
        f"feed_count={cap.feed_count}",
        f"sitemap_count={cap.sitemap_count}",
        f"metadata_count={cap.metadata_count}",
        f"found_feed_paths={','.join(found_paths) if found_paths else 'none'}",
        f"noise_flags={','.join(noise_flags) if noise_flags else 'none'}",
        f"sample_titles={' | '.join(i.title[:60] for i in items[:3]) if items else 'none'}",
    ]
    cap.evidence_summary = "; ".join(evidence_parts)

    # 8) Final decision logic (static / feed path)
    has_blocker_flag = any(
        f in cap.risk_flags for f in ("blocked_403", "login_page_hint", "paywall_hint", "captcha_hint", "antibot_hint")
    )

    if has_blocker_flag:
        # Cannot pass static preflight if login/paywall/captcha/antibot present
        cap.final_decision = "manual_reaudit_needed"
        cap.trae_browser_assessment = TraeBrowserAssessment(
            public_page_accessible=(http_status == 200),
            login_required=("login_page_hint" in cap.risk_flags),
            paywall_observed=("paywall_hint" in cap.risk_flags),
            captcha_or_antibot_observed=(
                "captcha_hint" in cap.risk_flags or "antibot_hint" in cap.risk_flags
            ),
            visible_item_count=cap.static_http_valid_items,
            visible_dated_item_count=cap.static_http_dated_items,
            sample_items=items[:5],
            automation_suitability="not_suitable",
            notes="Static preflight detected blocker hints; needs TRAE browser manual review",
        )
        cap.trae_browser_status = "observed_login_required" if "login_page_hint" in cap.risk_flags else (
            "observed_paywall" if "paywall_hint" in cap.risk_flags else (
                "observed_antibot" if "antibot_hint" in cap.risk_flags else (
                    "observed_public" if http_status == 200 else "error"
                )
            )
        )
    elif cap.feed_count > 0 or cap.sitemap_count > 0:
        # Has feed evidence
        if cap.static_http_dated_items >= 2 or cap.feed_count > 0:
            cap.final_decision = "scheduled_preflight_pass_feed"
        else:
            cap.final_decision = "manual_reaudit_needed"
        cap.trae_browser_assessment = TraeBrowserAssessment(
            public_page_accessible=True,
            login_required=False,
            paywall_observed=False,
            captcha_or_antibot_observed=False,
            visible_item_count=cap.static_http_valid_items,
            visible_dated_item_count=cap.static_http_dated_items,
            sample_items=items[:5],
            automation_suitability="suitable_for_scheduled",
            notes="Feed/sitemap discovered; suitable for scheduled",
        )
        cap.trae_browser_status = "observed_public"
    elif cap.static_http_valid_items >= 3 and cap.static_http_dated_items >= 2:
        # Static HTTP path passes
        cap.final_decision = "scheduled_preflight_pass_static"
        cap.trae_browser_assessment = TraeBrowserAssessment(
            public_page_accessible=True,
            login_required=False,
            paywall_observed=False,
            captcha_or_antibot_observed=False,
            visible_item_count=cap.static_http_valid_items,
            visible_dated_item_count=cap.static_http_dated_items,
            sample_items=items[:5],
            automation_suitability="suitable_for_scheduled",
            notes="Static HTTP path yields valid+dated items; no TRAE browser needed",
        )
        cap.trae_browser_status = "observed_public"
    elif cap.static_http_valid_items >= 1:
        # Some items but not enough dated -> low frequency
        cap.final_decision = "low_frequency_candidate"
        cap.trae_browser_assessment = TraeBrowserAssessment(
            public_page_accessible=True,
            login_required=False,
            paywall_observed=False,
            captcha_or_antibot_observed=False,
            visible_item_count=cap.static_http_valid_items,
            visible_dated_item_count=cap.static_http_dated_items,
            sample_items=items[:5],
            automation_suitability="suitable_for_low_frequency",
            notes="Insufficient dated items; suitable for low-frequency observation",
        )
        cap.trae_browser_status = "observed_public"
    else:
        # No items but no blocker -> needs manual reaudit
        cap.final_decision = "manual_reaudit_needed"
        cap.trae_browser_assessment = TraeBrowserAssessment(
            public_page_accessible=(http_status == 200),
            login_required=False,
            paywall_observed=False,
            captcha_or_antibot_observed=False,
            visible_item_count=0,
            visible_dated_item_count=0,
            sample_items=[],
            automation_suitability="manual_review_required",
            notes="No candidate items extracted; needs manual review",
        )
        cap.trae_browser_status = "observed_public" if http_status == 200 else "error"

    # TRAE skill: design-only — not available by default in repo runtime
    cap.trae_skill_status = "not_available"

    # Apply recommendations
    apply_recommendations(cap)

    # Build human-readable summary
    summary = (
        f"http={http_status}, items={cap.static_http_valid_items}, "
        f"dated={cap.static_http_dated_items}, feed={cap.feed_count}, "
        f"sitemap={cap.sitemap_count}, metadata={cap.metadata_count}, "
        f"decision={cap.final_decision}"
    )
    return cap, summary


# =============================================================================
# Report generation
# =============================================================================

def generate_preflight_report(
    capabilities: list[SourceExecutionCapability],
    config: dict,
    master_commit: str,
    branch: str,
    report_path: Path,
) -> None:
    """Generate markdown preflight report."""
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append("# OPC Foundation M3C-6B — Scheduled Candidate Preflight Report")
    lines.append("")
    lines.append(f"> Generated: {now}")
    lines.append(f"> Master commit: `{master_commit}`")
    lines.append(f"> Branch: `{branch}`")
    lines.append(f"> Phase: M3C-6B")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("### Execution Baseline")
    lines.append("")
    base = config.get("base_allowlist", [])
    lines.append(f"- base trial_v2 source_count: {len(base)}")
    lines.append(f"- production_enabled: {config.get('scope', {}).get('production_enabled', False)}")
    lines.append(f"- affects_trial_v2_allowlist: {config.get('scope', {}).get('affects_trial_v2_allowlist', False)}")
    lines.append(f"- affects_trae_scheduling: {config.get('scope', {}).get('affects_trae_scheduling', False)}")
    lines.append("")
    lines.append("### Candidate Sources (M3C-6B)")
    lines.append("")
    for c in config.get("candidates", []):
        lines.append(f"- {c.get('source_id')}: {c.get('source_name')} ({c.get('expected_value')} value)")
    lines.append("")

    # Preflight table
    lines.append("### Static / Feed Preflight Result")
    lines.append("")
    lines.append("| source_id | static_http | feed/sitemap | metadata | valid_items | dated_items | risk_flags | decision |")
    lines.append("|---|---|---|---|---:|---:|---|---|")
    for cap in capabilities:
        flags_str = ", ".join(cap.risk_flags) if cap.risk_flags else "-"
        lines.append(
            f"| {cap.source_id} | {cap.static_http_status} | "
            f"feed={cap.feed_count}/sitemap={cap.sitemap_count} | "
            f"{cap.metadata_discovery_status} ({cap.metadata_count}) | "
            f"{cap.static_http_valid_items} | {cap.static_http_dated_items} | "
            f"{flags_str} | {cap.final_decision} |"
        )
    lines.append("")

    # TRAE Browser / Skill assessment
    lines.append("### TRAE Browser / Skill Assessment")
    lines.append("")
    lines.append("| source_id | trae_browser_status | public_page_accessible | login_required | paywall_observed | captcha_or_antibot | visible_items | trae_skill_status | automation_suitability |")
    lines.append("|---|---|---|---|---|---|---:|---|---|")
    for cap in capabilities:
        ba = cap.trae_browser_assessment
        lines.append(
            f"| {cap.source_id} | {cap.trae_browser_status} | "
            f"{ba.public_page_accessible} | {ba.login_required} | "
            f"{ba.paywall_observed} | {ba.captcha_or_antibot_observed} | "
            f"{ba.visible_item_count} | {cap.trae_skill_status} | "
            f"{cap.automation_suitability} |"
        )
    lines.append("")

    # Final decision
    lines.append("### Final Decision")
    lines.append("")
    lines.append("| source_id | recommended_execution_mode | trial_v2_allowlist_allowed_now | trae_automation_allowed_now | next_action |")
    lines.append("|---|---|---|---|---|")
    for cap in capabilities:
        lines.append(
            f"| {cap.source_id} | {cap.recommended_execution_mode} | "
            f"{cap.trial_v2_allowlist_allowed_now} | {cap.trae_automation_allowed_now} | "
            f"{cap.recommended_next_action} |"
        )
    lines.append("")

    # Per-source details
    for cap in capabilities:
        lines.append(f"## Detail: {cap.source_id}")
        lines.append("")
        lines.append(f"**Final decision**: `{cap.final_decision}`")
        lines.append(f"- candidate_layer: {cap.candidate_layer}")
        lines.append(f"- static_http_status: {cap.static_http_status}")
        lines.append(f"- feed_discovery_status: {cap.feed_discovery_status} (feed_count={cap.feed_count}, sitemap_count={cap.sitemap_count})")
        lines.append(f"- metadata_discovery_status: {cap.metadata_discovery_status} (metadata_count={cap.metadata_count})")
        lines.append(f"- trae_browser_status: {cap.trae_browser_status}")
        lines.append(f"- trae_skill_status: {cap.trae_skill_status}")
        lines.append(f"- automation_suitability: {cap.automation_suitability}")
        lines.append(f"- recommended_execution_mode: {cap.recommended_execution_mode}")
        lines.append(f"- trial_v2_allowlist_allowed_now: {cap.trial_v2_allowlist_allowed_now}")
        lines.append(f"- trae_automation_allowed_now: {cap.trae_automation_allowed_now}")
        lines.append(f"- risk_flags: {cap.risk_flags}")
        lines.append("")
        lines.append("### Evidence Summary")
        lines.append("")
        lines.append("```")
        lines.append(cap.evidence_summary or "(none)")
        lines.append("```")
        lines.append("")
        # TRAE browser samples
        ba = cap.trae_browser_assessment
        if ba.sample_items:
            lines.append("### Sample Items (TRAE Browser Assessment)")
            lines.append("")
            lines.append("| # | title | url | date_text |")
            lines.append("|---:|---|---|---|")
            for i, s in enumerate(ba.sample_items[:5], start=1):
                lines.append(f"| {i} | {s.title[:80]} | {s.url[:80]} | {s.date_text or '-'} |")
            lines.append("")

    # Categorization
    lines.append("## Allowlist Categorization")
    lines.append("")
    trial_v2_pass = [c.source_id for c in capabilities if c.trial_v2_allowlist_allowed_now]
    trae_only = [c.source_id for c in capabilities if c.trae_automation_allowed_now and not c.trial_v2_allowlist_allowed_now]
    low_freq = [c.source_id for c in capabilities if c.final_decision == "low_frequency_candidate"]
    on_demand = [c.source_id for c in capabilities if c.final_decision == "on_demand_candidate"]
    backlog = [c.source_id for c in capabilities if c.final_decision in (
        "browser_like_backlog", "cloudflare_or_anti_bot_backlog", "blocked_or_low_value"
    )]
    manual = [c.source_id for c in capabilities if c.final_decision == "manual_reaudit_needed"]
    lines.append(f"- 可进入 Python trial_v2 preflight 的源: {', '.join(trial_v2_pass) or 'none'}")
    lines.append(f"- 只能进入 TRAE-assisted 的源: {', '.join(trae_only) or 'none'}")
    lines.append(f"- 应降级 low_frequency 的源: {', '.join(low_freq) or 'none'}")
    lines.append(f"- 应进入 on_demand 的源: {', '.join(on_demand) or 'none'}")
    lines.append(f"- 应进入 browser_like / anti-bot backlog 的源: {', '.join(backlog) or 'none'}")
    lines.append(f"- 需要人工 reaudit 的源: {', '.join(manual) or 'none'}")
    lines.append("")

    # Boundary confirmation
    lines.append("## Boundary Confirmation")
    lines.append("")
    lines.append("| Item | Status |")
    lines.append("|---|---|")
    lines.append("| Modified TRAE scheduling | No |")
    lines.append("| Modified TRAE local config | No |")
    lines.append("| Modified trial_v2 allowlist | No |")
    lines.append("| Configured production | No |")
    lines.append("| Submitted data/local/secrets | No |")
    lines.append("| Introduced Playwright/Selenium | No |")
    lines.append("| Submitted raw HTML / screenshot / cookies | No |")
    lines.append("| Restored deleted Dashboard pages | No |")
    lines.append("| Created tag | No |")
    lines.append("")

    # Recommendation
    lines.append("## Recommendation")
    lines.append("")
    if trial_v2_pass:
        lines.append(
            f"Source(s) ready for next-batch trial_v2 allowlist preflight: "
            f"{', '.join(trial_v2_pass)}."
        )
    else:
        lines.append(
            "No source meets scheduled_preflight_pass_static / _feed criteria this round."
        )
    if trae_only:
        lines.append(
            f"Source(s) suitable for TRAE-assisted automation (manual approval required): "
            f"{', '.join(trae_only)}."
        )
    lines.append("")

    # Write
    report_dir = report_path.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to: {report_path}")


# =============================================================================
# Main
# =============================================================================

def get_source_from_config(config: dict, source_id: str) -> Optional[dict]:
    """Find a candidate source entry from config by source_id."""
    for c in config.get("candidates", []):
        if c.get("source_id") == source_id:
            return c
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="M3C-6B Scheduled Candidate Preflight Runner"
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="Path to preflight config",
    )
    parser.add_argument(
        "--report",
        default=DEFAULT_REPORT,
        help="Output report path",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Filter to specific source (reuters / marketwatch / streetinsider). Comma-separated.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run preflight for all 3 candidates",
    )
    args = parser.parse_args()

    config_path = repo_root / args.config
    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}")
        return 1

    with open(config_path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    # Validate scope
    scope = config.get("scope", {})
    assert scope.get("production_enabled") is False, "production_enabled must be false"
    assert scope.get("affects_trial_v2_allowlist") is False, "must not affect allowlist"
    assert scope.get("affects_trae_scheduling") is False, "must not affect scheduling"

    # Determine target sources
    candidate_sources = scope.get("candidate_sources", [])
    if args.all:
        target_sources = list(candidate_sources)
    elif args.source:
        requested = set(s.strip() for s in args.source.split(","))
        invalid = requested - M3C_6B_ALLOWED_CANDIDATES
        if invalid:
            print(f"ERROR: --source contains invalid ids: {invalid}")
            print(f"Allowed candidates: {sorted(M3C_6B_ALLOWED_CANDIDATES)}")
            return 1
        target_sources = [s for s in candidate_sources if s in requested]
    else:
        print("ERROR: must specify --source <id> or --all")
        return 1

    # Get master commit + branch
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

    print(f"M3C-6B Preflight: branch={branch}, commit={master_commit}")
    print(f"Target sources: {target_sources}")
    print(f"Base allowlist: {config.get('base_allowlist', [])}")
    print()

    capabilities: list[SourceExecutionCapability] = []

    for source_id in target_sources:
        source_cfg = get_source_from_config(config, source_id) or {"source_id": source_id}
        print(f"=== Preflight: {source_id} ===")
        cap, summary = run_static_http_preflight(source_cfg, config)
        # Validate capability (will surface rule violations)
        errors = validate_execution_capability(cap)
        if errors:
            print(f"  WARNING: validation errors: {errors}")
        print(f"  {summary}")
        print(f"  final_decision: {cap.final_decision}")
        print(f"  trial_v2_allowlist_allowed_now: {cap.trial_v2_allowlist_allowed_now}")
        print(f"  trae_automation_allowed_now: {cap.trae_automation_allowed_now}")
        print()
        capabilities.append(cap)
        # Small delay between sources to be polite
        time.sleep(1)

    # Generate report
    generate_preflight_report(
        capabilities=capabilities,
        config=config,
        master_commit=master_commit,
        branch=branch,
        report_path=repo_root / args.report,
    )

    # Print summary
    print(f"{'='*60}")
    print(f"M3C-6B Preflight Summary")
    print(f"{'='*60}")
    all_pass = True
    for c in capabilities:
        status = "PASS" if c.trial_v2_allowlist_allowed_now else (
            "TRAE-ONLY" if c.trae_automation_allowed_now else "NO-PASS"
        )
        print(f"  {c.source_id}: {status} ({c.final_decision})")
        if not c.trial_v2_allowlist_allowed_now:
            all_pass = False
    print(f"\n  Overall trial_v2 preflight pass: {all_pass}")
    print(f"  Report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
