#!/usr/bin/env python3
"""
OPC Foundation M3C-6F Proxy Retry Batch Runner
================================================

Independent proxy retry batch for merck_ir / yahoo_finance / the_fly to
determine if inaccessibility is due to local network / DNS / TLS issues.
Tests both direct and proxy-env modes and compares results.

Boundaries:
    - Does NOT modify trial_v2 allowlist
    - Does NOT modify TRAE scheduling
    - Does NOT configure production
    - Does NOT commit data / secrets / cookies / raw HTML / screenshots
    - Does NOT record or output real proxy URL values
    - Does NOT bypass login / paywall / captcha / Cloudflare
    - Does NOT introduce Playwright / Selenium into repo
    - Does NOT restore deleted Dashboard pages

Usage:
    python scripts/run_m3c_6f_proxy_retry_batch.py --source merck_ir --mode direct
    python scripts/run_m3c_6f_proxy_retry_batch.py --source merck_ir --mode proxy-env
    python scripts/run_m3c_6f_proxy_retry_batch.py --all --mode direct
    python scripts/run_m3c_6f_proxy_retry_batch.py --all --mode proxy-env
    python scripts/run_m3c_6f_proxy_retry_batch.py --all --mode both

Author: OPC Foundation
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import yaml

repo_root = Path(__file__).resolve().parent.parent
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from opc_foundation.source_inventory.proxy_retry_assessment import (
    M3C_6F_ALLOWED_CANDIDATES,
    MAX_SAMPLE_ITEMS_RECORDED,
    ProxyRetryAttempt,
    ProxyRetryBatchReport,
    ProxyRetrySampleItem,
    ProxyRetrySourceResult,
    apply_proxy_retry_decision,
    check_proxy_env_configured,
    is_m3c_6f_candidate,
    make_default_proxy_result,
    validate_proxy_retry_result,
)


DEFAULT_CONFIG = "configs/foundation_m3c_6f_proxy_retry_batch.example.yaml"
DEFAULT_REPORT = "docs/foundation_m3c_6f_proxy_retry_batch_report.md"
DEFAULT_OUTPUT_DIR = "data/foundation_m3c_6f_proxy_retry_batch"

DEFAULT_USER_AGENT = (
    "OPC-Foundation-M3C-6F-ProxyRetry/1.0 "
    "(+https://github.com/xe7dx54321-stack/opc-foundation)"
)

LOGIN_BLOCKER_HINTS = (
    "please sign in to continue", "please log in to continue",
    "you must be logged in", "sign in to access", "log in to access",
    "login required", "authentication required",
)
PAYWALL_HINTS = (
    "subscribe to read", "this content is for subscribers",
    "paywall", "premium content only", "subscribe to continue reading",
    "you have reached your article limit",
)
CAPTCHA_HINTS = (
    "captcha", "recaptcha", "hcaptcha", "are you a human", "verify you are human",
    "please complete the security check",
)
ANTIBOT_HINTS = (
    "cloudflare", "cf-ray", "cf-mitigated", "datadome",
    "checking your browser before accessing",
    "attention required! | cloudflare",
)


def _safe_get(obj: dict, key: str, default: Any = "") -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else default


def classify_risk_flags(page_text: str, http_status: int = 200) -> list[str]:
    flags: list[str] = []
    lower = page_text.lower()
    if http_status == 403:
        flags.append("blocked_403")
    if http_status == 0:
        flags.append("network_failure")
    if any(h in lower for h in LOGIN_BLOCKER_HINTS):
        flags.append("login_required_hint")
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
    if not text:
        return ""
    m = re.search(r"\b(20\d{2})[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12][0-9]|3[01])\b", text)
    if m:
        return m.group(0)
    m = re.search(r"\b(\d+)\s*(minute|hour|day|week|month|year)s?\s*ago\b", text, re.IGNORECASE)
    if m:
        return m.group(0)
    m = re.search(r"\d+\s*(分钟|小时|天|周|月|年)前", text)
    if m:
        return m.group(0)
    m = re.search(r"\b(0?[1-9]|1[0-2])-(0?[1-9]|[12][0-9]|3[01])\s+\d{2}:\d{2}\b", text)
    if m:
        return m.group(0)
    return ""


def extract_sample_items(html: str, base_url: str, max_items: int = 10) -> list[ProxyRetrySampleItem]:
    if not html:
        return []
    items: list[ProxyRetrySampleItem] = []
    seen_urls: set[str] = set()

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
        lower_href = raw_href.lower()
        if any(seg in lower_href for seg in (
            "/login", "/signin", "/signup", "/register", "/subscribe",
            "/privacy", "/terms", "/contact", "/about", "javascript:",
        )):
            continue
        if full_url in seen_urls:
            continue
        raw_title = match.group(2)
        title = re.sub(r"<[^>]+>", " ", raw_title)
        title = re.sub(r"\s+", " ", title).strip()
        if not title or len(title) < 8:
            continue
        start = max(0, match.start() - 100)
        end = min(len(html), match.end() + 100)
        window = html[start:end]
        date_text = extract_date_text(window)

        seen_urls.add(full_url)
        items.append(ProxyRetrySampleItem(
            title=title[:200],
            url=full_url,
            date_text=date_text,
            extraction_method="html_parsing",
        ))

    return items


def _sanitize_error_message(error: Exception) -> str:
    msg = str(error)
    msg = re.sub(r'http[s]?://[^\s]+', '[redacted_url]', msg)
    msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b', '[redacted_ip]', msg)
    if len(msg) > 300:
        msg = msg[:300] + "..."
    return msg


def run_single_attempt(
    source: dict,
    mode: str,
    timeout: int = 20,
) -> ProxyRetryAttempt:
    attempt = ProxyRetryAttempt(mode=mode)

    try:
        import httpx
    except ImportError:
        attempt.status = "not_tested"
        attempt.error_type = "unknown"
        attempt.error_message = "httpx not installed"
        attempt.notes = "httpx library not available; network test skipped"
        return attempt

    test_urls = source.get("test_urls", []) or [source.get("inventory_url", "")]
    url = test_urls[0] if test_urls else ""

    if not url:
        attempt.status = "not_tested"
        attempt.error_type = "unknown"
        attempt.error_message = "no test URL configured"
        return attempt

    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    }

    proxy_env_configured = check_proxy_env_configured()

    if mode == "proxy-env" and not proxy_env_configured:
        attempt.status = "not_configured"
        attempt.error_type = "proxy_not_configured"
        attempt.error_message = "proxy environment variables not configured"
        attempt.notes = "No proxy env vars detected; proxy-env test skipped"
        return attempt

    client_kwargs: dict[str, Any] = {
        "timeout": timeout,
        "follow_redirects": True,
        "verify": True,
    }

    if mode == "direct":
        client_kwargs["proxy"] = None
        for env_var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            os.environ.pop(env_var, None)

    try:
        with httpx.Client(**client_kwargs) as client:
            resp = client.get(url, headers=headers)
            http_status = resp.status_code
            html = resp.text or ""
            content_type = resp.headers.get("content-type", "")
            content_length = len(resp.content)
    except httpx.ConnectTimeout as e:
        attempt.status = "timeout"
        attempt.error_type = "timeout_connect"
        attempt.error_message = _sanitize_error_message(e)
        attempt.timeout_observed = True
        attempt.risk_flags.append("connect_timeout")
        return attempt
    except httpx.ReadTimeout as e:
        attempt.status = "timeout"
        attempt.error_type = "timeout_read"
        attempt.error_message = _sanitize_error_message(e)
        attempt.timeout_observed = True
        attempt.risk_flags.append("read_timeout")
        return attempt
    except httpx.ConnectError as e:
        msg_lower = str(e).lower()
        if "dns" in msg_lower or "name or service not known" in msg_lower:
            attempt.status = "dns_error"
            attempt.error_type = "dns_resolution"
            attempt.dns_error_observed = True
            attempt.risk_flags.append("dns_error")
        elif "connection refused" in msg_lower:
            attempt.status = "connection_error"
            attempt.error_type = "connection_refused"
            attempt.risk_flags.append("connection_refused")
        elif "connection reset" in msg_lower:
            attempt.status = "connection_error"
            attempt.error_type = "connection_reset"
            attempt.risk_flags.append("connection_reset")
        else:
            attempt.status = "connection_error"
            attempt.error_type = "unknown"
            attempt.risk_flags.append("connection_error")
        attempt.error_message = _sanitize_error_message(e)
        return attempt
    except httpx.TLSError as e:
        attempt.status = "tls_error"
        msg_lower = str(e).lower()
        if "certificate" in msg_lower or "ssl" in msg_lower:
            attempt.error_type = "tls_certificate"
        else:
            attempt.error_type = "tls_handshake"
        attempt.tls_error_observed = True
        attempt.error_message = _sanitize_error_message(e)
        attempt.risk_flags.append("tls_error")
        return attempt
    except Exception as e:
        attempt.status = "connection_error"
        attempt.error_type = "unknown"
        attempt.error_message = _sanitize_error_message(e)
        attempt.risk_flags.append("unknown_error")
        return attempt

    attempt.http_status = http_status
    attempt.content_type = content_type
    attempt.content_length = content_length

    if http_status >= 400:
        attempt.status = "http_error"
        if 400 <= http_status < 500:
            attempt.error_type = "http_4xx"
        else:
            attempt.error_type = "http_5xx"
        attempt.risk_flags.append(f"http_{http_status}")
    else:
        attempt.status = "success"
        attempt.error_type = "none"

    risk_flags = classify_risk_flags(html, http_status)
    attempt.risk_flags.extend(risk_flags)

    lower_html = html.lower()
    if any(h in lower_html for h in LOGIN_BLOCKER_HINTS):
        attempt.login_required = True
    if any(h in lower_html for h in PAYWALL_HINTS):
        attempt.paywall_observed = True
    if any(h in lower_html for h in CAPTCHA_HINTS):
        attempt.captcha_or_antibot_observed = True
    if any(h in lower_html for h in ANTIBOT_HINTS):
        attempt.cloudflare_or_botwall_observed = True
        attempt.captcha_or_antibot_observed = True

    if attempt.status == "success":
        all_items = extract_sample_items(html, url, max_items=20)
        dated_items = [i for i in all_items if i.date_text]
        attempt.valid_item_count = len(all_items)
        attempt.dated_item_count = len(dated_items)
        attempt.sample_items = all_items[:MAX_SAMPLE_ITEMS_RECORDED]

    if attempt.status == "success" and attempt.valid_item_count == 0:
        attempt.risk_flags.append("no_extractable_items")

    return attempt


def run_proxy_retry_for_source(
    source: dict,
    config: dict,
    mode: str = "both",
) -> ProxyRetrySourceResult:
    source_id = source.get("source_id", "")
    result = make_default_proxy_result(source_id)
    result.prior_status = source.get("prior_status", "tls_or_proxy_backlog")
    result.prior_score = source.get("prior_score", 0)

    result.proxy_env_configured = check_proxy_env_configured()

    network_cfg = _safe_get(config, "network_modes", {}) or {}
    timeout = 20

    if mode in ("direct", "both"):
        result.direct_attempt = run_single_attempt(source, "direct", timeout=timeout)

    if mode in ("proxy-env", "both"):
        result.proxy_env_attempt = run_single_attempt(source, "proxy-env", timeout=timeout)

    apply_proxy_retry_decision(result)

    return result


def load_config(config_path: str) -> dict:
    path = repo_root / config_path
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_source_by_id(config: dict, source_id: str) -> Optional[dict]:
    candidates = _safe_get(config, "candidates", []) or []
    for src in candidates:
        if src.get("source_id") == source_id:
            return src
    return None


def get_git_info() -> tuple[str, str]:
    try:
        import subprocess
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return branch, commit
    except Exception:
        return "unknown", "unknown"


def build_batch_report(
    config: dict,
    results: list[ProxyRetrySourceResult],
    mode: str,
) -> ProxyRetryBatchReport:
    branch, commit = get_git_info()
    scope = _safe_get(config, "scope", {}) or {}
    report = ProxyRetryBatchReport(
        batch_name=scope.get("name", "m3c_6f_proxy_retry_batch"),
        base_commit=commit,
        branch=branch,
        m3c_6g_merge_commit="",
        trial_v2_source_count=scope.get("base_trial_v2_content_ready_count", 9),
        proxy_env_configured=check_proxy_env_configured(),
        sources=results,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return report


def generate_markdown_report(report: ProxyRetryBatchReport) -> str:
    lines: list[str] = []
    lines.append("# OPC Foundation M3C-6F Proxy Retry Batch Report")
    lines.append("")
    lines.append(f"- **Generated at:** {report.generated_at}")
    lines.append(f"- **Branch:** {report.branch}")
    lines.append(f"- **Base commit:** {report.base_commit}")
    lines.append(f"- **Trial v2 source count:** {report.trial_v2_source_count}")
    lines.append(f"- **Proxy env configured:** {report.proxy_env_configured}")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- **Candidate count:** {len(report.sources)}")
    lines.append("- **Candidate sources:** " + ", ".join(s.source_id for s in report.sources))
    lines.append("")
    lines.append("## Summary Table")
    lines.append("")
    lines.append("| source_id | direct_status | proxy_status | http_status | error_type | valid_items | dated_items | decision |")
    lines.append("|---|---|---|---|---|---:|---:|---|")
    for s in report.sources:
        best = _best_attempt(s)
        lines.append(
            f"| {s.source_id} | {s.direct_attempt.status} | {s.proxy_env_attempt.status} "
            f"| {best.http_status} | {best.error_type} | {best.valid_item_count} "
            f"| {best.dated_item_count} | {s.decision.recommended_execution_mode} |"
        )
    lines.append("")
    lines.append("## Sample Items")
    lines.append("")
    for s in report.sources:
        best = _best_attempt(s)
        lines.append(f"### {s.source_id}")
        lines.append("")
        if best.sample_items:
            lines.append("| title | url | date_text |")
            lines.append("|---|---|---|")
            for item in best.sample_items:
                safe_title = item.title.replace("|", "\\|")
                lines.append(f"| {safe_title} | {item.url} | {item.date_text} |")
        else:
            lines.append("_No sample items extracted_")
        lines.append("")
    lines.append("## Decisions")
    lines.append("")
    lines.append("| source_id | recommended_execution_mode | trial_v2_allowlist_allowed_now | low_frequency_allowed_now | on_demand_allowed_now | next_action |")
    lines.append("|---|---|---|---|---|---|")
    for s in report.sources:
        lines.append(
            f"| {s.source_id} | {s.decision.recommended_execution_mode} "
            f"| {s.decision.trial_v2_allowlist_allowed_now} "
            f"| {s.decision.low_frequency_allowed_now} "
            f"| {s.decision.on_demand_allowed_now} "
            f"| {s.decision.next_action} |"
        )
    lines.append("")
    lines.append("## Boundary Compliance")
    lines.append("")
    lines.append("- Does NOT modify trial_v2 allowlist: yes")
    lines.append("- Does NOT modify TRAE scheduling: yes")
    lines.append("- Does NOT configure production: yes")
    lines.append("- Does NOT commit data/local/secrets: yes")
    lines.append("- Does NOT commit proxy URL: yes")
    lines.append("- Does NOT commit cookie/token: yes")
    lines.append("- Does NOT commit raw HTML: yes")
    lines.append("- Does NOT commit screenshot: yes")
    lines.append("- Does NOT introduce Playwright/Selenium: yes")
    lines.append("- Does NOT restore deleted Dashboard pages: yes")
    lines.append("- Does NOT create tag: yes")
    lines.append("")
    return "\n".join(lines)


def _best_attempt(result: ProxyRetrySourceResult) -> ProxyRetryAttempt:
    attempts = [result.proxy_env_attempt, result.direct_attempt]
    success_attempts = [a for a in attempts if a.status == "success"]
    if success_attempts:
        return max(success_attempts, key=lambda a: a.valid_item_count)
    http_attempts = [a for a in attempts if a.status == "http_error" and a.http_status > 0]
    if http_attempts:
        return http_attempts[0]
    return result.direct_attempt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OPC Foundation M3C-6F Proxy Retry Batch Runner",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Single source ID to test (merck_ir / yahoo_finance / the_fly)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all 3 candidate sources",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="both",
        choices=["direct", "proxy-env", "both"],
        help="Network mode to test (default: both)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=DEFAULT_CONFIG,
        help=f"Path to config file (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for runtime data (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=DEFAULT_REPORT,
        help=f"Path to markdown report output (default: {DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output JSON summary",
    )

    args = parser.parse_args()

    if not args.source and not args.all:
        print("ERROR: must specify --source <id> or --all", file=sys.stderr)
        return 1

    config = load_config(args.config)
    scope = _safe_get(config, "scope", {}) or {}

    if scope.get("production_enabled", False):
        print("ERROR: config production_enabled must be false", file=sys.stderr)
        return 1

    source_ids: list[str] = []
    if args.source:
        if not is_m3c_6f_candidate(args.source):
            print(
                f"ERROR: source_id {args.source!r} not in M3C-6F candidates: "
                f"{sorted(M3C_6F_ALLOWED_CANDIDATES)}",
                file=sys.stderr,
            )
            return 1
        source_ids = [args.source]
    else:
        source_ids = sorted(M3C_6F_ALLOWED_CANDIDATES)

    results: list[ProxyRetrySourceResult] = []
    all_errors: list[str] = []

    for sid in source_ids:
        src = find_source_by_id(config, sid)
        if not src:
            print(f"WARNING: source {sid} not found in config, using defaults", file=sys.stderr)
            src = {"source_id": sid}

        print(f"Running proxy retry for {sid} (mode={args.mode})...", file=sys.stderr)
        result = run_proxy_retry_for_source(src, config, mode=args.mode)

        errors = validate_proxy_retry_result(result)
        if errors:
            print(f"  Validation errors for {sid}:", file=sys.stderr)
            for e in errors:
                print(f"    - {e}", file=sys.stderr)
            all_errors.extend([f"{sid}: {e}" for e in errors])

        results.append(result)

        best = _best_attempt(result)
        print(
            f"  -> decision={result.decision.recommended_execution_mode}, "
            f"best_status={best.status}, http={best.http_status}, "
            f"items={best.valid_item_count}, dated={best.dated_item_count}",
            file=sys.stderr,
        )

    batch_report = build_batch_report(config, results, mode=args.mode)

    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "proxy_retry_batch_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(batch_report.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"JSON summary written to {json_path}", file=sys.stderr)

    md_content = generate_markdown_report(batch_report)
    report_path = repo_root / args.report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Markdown report written to {report_path}", file=sys.stderr)

    if all_errors:
        print(f"\nValidation completed with {len(all_errors)} error(s):", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("\nProxy retry batch completed successfully.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
