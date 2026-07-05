#!/usr/bin/env python3
"""M3C-6F.1 Merck IR Dedicated Extraction Preflight script.

This script performs a dedicated IR extraction preflight for merck_ir only.
It discovers IR entry points (news, events, press releases, RSS, sitemap,
JSON-LD) from the Merck investor relations page and extracts real IR content
items — NOT generic homepage navigation links.

Usage:
    python scripts/run_m3c_6f1_merck_ir_dedicated_preflight.py
    python scripts/run_m3c_6f1_merck_ir_dedicated_preflight.py --discover-only
    python scripts/run_m3c_6f1_merck_ir_dedicated_preflight.py --extract

Constraints:
    - Only processes merck_ir
    - Does NOT modify trial_v2 allowlist
    - Does NOT modify TRAE scheduling
    - Does NOT configure production
    - Does NOT commit data/
    - Does NOT save raw HTML
    - Does NOT download PDFs
    - Does NOT introduce Playwright/Selenium
    - Does NOT record proxy URL / cookie / token / secret

Full pytest must pass: 0 failed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Ensure src is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from opc_foundation.source_inventory.merck_ir_dedicated_preflight import (  # noqa: E402
    MAX_SAMPLE_ITEMS_RECORDED,
    MIN_DATED_ITEMS_FOR_SCHEDULED,
    MIN_VALID_ITEMS_FOR_SCHEDULED,
    REJECT_TITLE_PATTERNS,
    MerckIrCandidateUrl,
    MerckIrDedicatedPreflightResult,
    MerckIrExtractionItem,
    apply_merck_ir_decision,
    is_merck_ir_source,
    is_rejected_navigation_title,
    make_batch_report_dict,
    validate_merck_ir_preflight_result,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MERCK_IR_BASE_URL = "https://www.merck.com/investor-relations/"
MERCK_IR_NEWS_URL = "https://www.merck.com/news/"
MERCK_IR_EVENTS_URL = "https://www.merck.com/events/"
MERCK_IR_PRESENTATIONS_URL = "https://www.merck.com/investor-relations/presentations/"

# Link patterns for IR content (M3C-5B1 validated selectors)
IR_LINK_PATTERNS = [
    "/news/",
    "/events/",
    "/presentations/",
    "/press-release",
    "/news-releases",
    "/investor-relations/",
]

# Date patterns for extraction
DATE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b",
    r"\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
]

# Login / paywall / captcha blocker hints
# These must be specific enough to avoid false positives from footer/nav text.
LOGIN_BLOCKER_HINTS = (
    "login required",
    "please sign in to continue",
    "you must be logged in",
    "sign in to access",
    "authentication required",
)

PAYWALL_HINTS = (
    "subscription required to read",
    "subscribe to read this article",
    "premium content is locked",
    "upgrade to read full article",
    "this content is for subscribers only",
    "you have reached your free article limit",
)

CAPTCHA_HINTS = (
    "recaptcha",
    "hcaptcha",
    "turnstile challenge",
    "datadome challenge",
    "cloudflare challenge",
    "please verify you are human",
    "checking your browser before accessing",
)

# Runtime data directory (gitignored)
RUNTIME_DATA_DIR = (
    _REPO_ROOT / "data" / "foundation_m3c_6f1_merck_ir_dedicated_preflight"
)


# ---------------------------------------------------------------------------
# Simple HTML parser for link extraction
# ---------------------------------------------------------------------------


class MerckIRLinkParser(HTMLParser):
    """Extract IR-relevant links and text from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []  # (href, text)
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self._json_ld_blocks: list[str] = []
        self._in_script_jsonld = False
        self._script_buffer: list[str] = []

    @property
    def json_ld_blocks(self) -> list[str]:
        return self._json_ld_blocks

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = None
            for attr_name, attr_val in attrs:
                if attr_name == "href" and attr_val:
                    href = attr_val
                    break
            if href:
                self._current_href = href
                self._current_text = []
        elif tag == "script":
            attrs_dict = dict(attrs)
            script_type = attrs_dict.get("type", "")
            if "application/ld+json" in script_type:
                self._in_script_jsonld = True
                self._script_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href is not None:
            text = " ".join(self._current_text).strip()
            if text:
                self.links.append((self._current_href, text))
            self._current_href = None
            self._current_text = []
        elif tag == "script" and self._in_script_jsonld:
            block = "".join(self._script_buffer).strip()
            if block:
                self._json_ld_blocks.append(block)
            self._in_script_jsonld = False
            self._script_buffer = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)
        if self._in_script_jsonld:
            self._script_buffer.append(data)


class MerckIRContentParser(HTMLParser):
    """Extract structured content from IR pages — news, events, etc."""

    def __init__(self) -> None:
        super().__init__()
        self.items: list[dict[str, str]] = []
        self._current_tag: str | None = None
        self._current_attrs: dict[str, str] = {}
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self._date_context: str = ""
        self._all_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._current_tag = tag
        self._current_attrs = dict(attrs)
        if tag == "a":
            href = self._current_attrs.get("href")
            if href:
                self._current_href = href
                self._current_text = []
        elif tag in ("time",):
            datetime_attr = self._current_attrs.get("datetime", "")
            if datetime_attr:
                self._date_context = datetime_attr

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href is not None:
            text = " ".join(self._current_text).strip()
            if text and len(text) > 10:
                self.items.append({
                    "title": text,
                    "url": self._current_href,
                    "date_text": self._date_context,
                })
            self._current_href = None
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)
        self._all_text.append(data)


# ---------------------------------------------------------------------------
# Network fetching
# ---------------------------------------------------------------------------


def fetch_url(url: str, timeout: int = 15) -> tuple[int, str, str, str]:
    """Fetch a URL and return (http_status, content_type, content, error_type).

    Uses httpx (consistent with M3C-6F proxy retry script).
    Does NOT use proxy unless environment variables are set.
    Does NOT record proxy URL values.
    """
    try:
        import httpx
    except ImportError:
        return 0, "", "", "httpx_not_available"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, verify=True) as client:
            resp = client.get(url, headers=headers)
            return resp.status_code, resp.headers.get("content-type", ""), resp.text or "", "none"
    except httpx.ConnectTimeout:
        return 0, "", "", "timeout"
    except httpx.ReadTimeout:
        return 0, "", "", "timeout"
    except httpx.ConnectError as e:
        msg_lower = str(e).lower()
        if "ssl" in msg_lower or "certificate" in msg_lower:
            return 0, "", "", "tls_error"
        if "dns" in msg_lower or "name or service" in msg_lower:
            return 0, "", "", "dns_error"
        return 0, "", "", "connection_error"
    except Exception:
        return 0, "", "", "unknown"


def check_blocker_hints(html: str) -> tuple[bool, bool, bool]:
    """Check for login, paywall, captcha hints in HTML."""
    lower = html.lower()
    login_found = any(h in lower for h in LOGIN_BLOCKER_HINTS)
    paywall_found = any(h in lower for h in PAYWALL_HINTS)
    captcha_found = any(h in lower for h in CAPTCHA_HINTS)
    return login_found, paywall_found, captcha_found


# ---------------------------------------------------------------------------
# IR entry-point discovery
# ---------------------------------------------------------------------------


def discover_ir_entry_points(
    base_url: str = MERCK_IR_BASE_URL,
) -> list[MerckIrCandidateUrl]:
    """Discover IR entry points from the Merck investor relations page."""
    candidates: list[MerckIrCandidateUrl] = []
    status, content_type, html, error_type = fetch_url(base_url)
    if status != 200 or not html:
        return candidates

    parser = MerckIRLinkParser()
    parser.feed(html)

    seen_urls: set[str] = set()
    for href, text in parser.links:
        full_url = urljoin(base_url, href)
        if full_url in seen_urls:
            continue
        parsed = urlparse(full_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if "merck.com" not in parsed.netloc:
            continue

        # Classify entry type
        path_lower = parsed.path.lower()
        entry_type = "homepage_discovery"
        if "/news" in path_lower:
            entry_type = "investor_news"
        elif "/press-release" in path_lower or "/press_releases" in path_lower:
            entry_type = "press_releases"
        elif "/news-release" in path_lower:
            entry_type = "news_releases"
        elif "/event" in path_lower:
            entry_type = "events_presentations"
        elif "/presentation" in path_lower:
            entry_type = "events_presentations"
        elif "/investor" in path_lower:
            entry_type = "investor_news"

        # Skip navigation pages
        if is_rejected_navigation_title(text):
            continue

        seen_urls.add(full_url)
        candidates.append(
            MerckIrCandidateUrl(
                url=full_url,
                entry_type=entry_type,
                source="homepage",
            )
        )

    # Also try well-known IR URLs
    well_known = [
        (MERCK_IR_NEWS_URL, "investor_news"),
        (MERCK_IR_EVENTS_URL, "events_presentations"),
        (MERCK_IR_PRESENTATIONS_URL, "events_presentations"),
    ]
    for url, etype in well_known:
        if url not in seen_urls:
            candidates.append(
                MerckIrCandidateUrl(url=url, entry_type=etype, source="well_known")
            )

    # Check for RSS/Atom feeds
    feed_patterns = [
        r'href="([^"]*feed[^"]*)"[^>]*type="application/rss',
        r'href="([^"]*rss[^"]*)"[^>]*type="application/rss',
        r'href="([^"]*atom[^"]*)"[^>]*type="application/atom',
        r'<link[^>]*rel="alternate"[^>]*type="application/rss\+xml"[^>]*href="([^"]*)"',
    ]
    for pattern in feed_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            feed_url = urljoin(base_url, match)
            if feed_url not in seen_urls:
                seen_urls.add(feed_url)
                candidates.append(
                    MerckIrCandidateUrl(url=feed_url, entry_type="rss_atom", source="html_link")
                )

    # Check for JSON-LD
    json_ld_count = len(parser.json_ld_blocks)

    return candidates, json_ld_count  # type: ignore


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------


def extract_ir_items(
    entry_url: str,
    entry_type: str,
    max_items: int = 20,
) -> list[MerckIrExtractionItem]:
    """Extract IR content items from a specific entry URL.

    Only extracts links whose URL path contains IR-relevant patterns
    (/news/, /events/, /presentations/, /press-release/, /news-releases/).
    This avoids picking up generic navigation links.
    """
    status, content_type, html, error_type = fetch_url(entry_url)
    if status != 200 or not html:
        return []

    parser = MerckIRContentParser()
    parser.feed(html)

    # M3C-5B1 validated path patterns
    ir_path_patterns = (
        "/news/",
        "/events/",
        "/presentations/",
        "/press-release",
        "/news-releases",
        "/news-release",
    )

    items: list[MerckIrExtractionItem] = []
    seen_urls: set[str] = set()

    for raw_item in parser.items:
        title = raw_item.get("title", "").strip()
        url = raw_item.get("url", "").strip()
        date_text = raw_item.get("date_text", "").strip()

        if not title or not url:
            continue
        if is_rejected_navigation_title(title):
            continue
        if len(title) < 15:  # M3C-5B1 used > 15 for news links
            continue

        full_url = urljoin(entry_url, url)
        if full_url in seen_urls:
            continue
        parsed = urlparse(full_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if "merck.com" not in parsed.netloc:
            continue

        # Only accept IR-relevant URL paths
        path_lower = parsed.path.lower()
        if not any(pattern in path_lower for pattern in ir_path_patterns):
            continue

        # Try to extract date from title if not in <time> tag
        if not date_text:
            for pattern in DATE_PATTERNS:
                match = re.search(pattern, title, re.IGNORECASE)
                if match:
                    date_text = match.group(0)
                    break

        # Try to extract date from URL path (e.g. /news/2024-01-15/...)
        if not date_text:
            url_date_match = re.search(r"/(\d{4}-\d{2}-\d{2})/", path_lower)
            if url_date_match:
                date_text = url_date_match.group(1)

        # Try to extract date from the raw HTML near the link
        if not date_text:
            # Look for date patterns in the HTML around the URL
            url_escaped = re.escape(url)
            # Find the link in HTML, then look for dates within 500 chars after
            link_pos = html.find(url)
            if link_pos >= 0:
                nearby_html = html[link_pos:link_pos + 500]
                for pattern in DATE_PATTERNS:
                    match = re.search(pattern, nearby_html, re.IGNORECASE)
                    if match:
                        date_text = match.group(0)
                        break

        seen_urls.add(full_url)
        items.append(
            MerckIrExtractionItem(
                title=title,
                url=full_url,
                date_text=date_text,
                entry_type=entry_type,
                extraction_method="html_parsing",
            )
        )

        if len(items) >= max_items:
            break

    return items


# ---------------------------------------------------------------------------
# Main preflight
# ---------------------------------------------------------------------------


def run_merck_ir_dedicated_preflight(
    discover_only: bool = False,
) -> MerckIrDedicatedPreflightResult:
    """Run the full merck_ir dedicated preflight."""
    result = MerckIrDedicatedPreflightResult(
        source_id="merck_ir",
        entry_url=MERCK_IR_BASE_URL,
        entry_type="investor_news",
    )

    # Step 1: Fetch the IR page
    status, content_type, html, error_type = fetch_url(MERCK_IR_BASE_URL)
    result.http_status = status
    result.content_type = content_type

    if status != 200 or not html:
        result.risk_flags.append(f"fetch_failed: {error_type}")
        apply_merck_ir_decision(result)
        return result

    # Check for blockers
    login_found, paywall_found, captcha_found = check_blocker_hints(html)
    result.login_required = login_found
    result.paywall_observed = paywall_found
    result.captcha_or_antibot_observed = captcha_found

    if login_found:
        result.risk_flags.append("login_required_hint")
    if paywall_found:
        result.risk_flags.append("paywall_hint")
    if captcha_found:
        result.risk_flags.append("captcha_or_antibot_hint")

    # Step 2: Discover IR entry points
    discover_result = discover_ir_entry_points(MERCK_IR_BASE_URL)
    if isinstance(discover_result, tuple):
        candidates, json_ld_count = discover_result
    else:
        candidates = discover_result
        json_ld_count = 0

    result.candidate_url_count = len(candidates)
    result.json_ld_item_count = json_ld_count
    result.sitemap_investor_url_count = 0  # will update if sitemap found

    # Check for RSS/feed
    feed_candidates = [c for c in candidates if c.entry_type == "rss_atom"]
    result.rss_or_feed_found = len(feed_candidates) > 0

    if discover_only:
        result.notes = "Discovery only mode; content extraction skipped."
        apply_merck_ir_decision(result)
        return result

    # Step 3: Try sitemap discovery
    sitemap_url = "https://www.merck.com/sitemap.xml"
    sm_status, sm_ct, sm_html, sm_err = fetch_url(sitemap_url)
    if sm_status == 200 and sm_html:
        # Count investor-related URLs in sitemap
        investor_urls = re.findall(
            r"<loc>([^<]*(?:investor|news|event|presentation)[^<]*)</loc>",
            sm_html,
            re.IGNORECASE,
        )
        result.sitemap_investor_url_count = len(investor_urls)

    # Step 4: Extract items from discovered entry points
    all_items: list[MerckIrExtractionItem] = []
    rejected_nav = 0

    # First try the well-known IR news page
    news_items = extract_ir_items(MERCK_IR_NEWS_URL, "investor_news", max_items=10)
    all_items.extend(news_items)

    # Try events page
    events_items = extract_ir_items(MERCK_IR_EVENTS_URL, "events_presentations", max_items=10)
    all_items.extend(events_items)

    # Try discovered candidates
    for candidate in candidates:
        if candidate.entry_type in ("rss_atom",):
            continue  # skip feeds for now
        if len(all_items) >= 20:
            break
        if candidate.url in (MERCK_IR_NEWS_URL, MERCK_IR_EVENTS_URL, MERCK_IR_BASE_URL):
            continue
        items = extract_ir_items(candidate.url, candidate.entry_type, max_items=5)
        all_items.extend(items)

    # Filter and count
    seen_urls: set[str] = set()
    valid_items: list[MerckIrExtractionItem] = []
    for item in all_items:
        if is_rejected_navigation_title(item.title):
            rejected_nav += 1
            continue
        if item.url in seen_urls:
            continue
        if len(item.title) < 10:
            continue
        seen_urls.add(item.url)
        valid_items.append(item)

    result.valid_item_count = len(valid_items)
    result.rejected_navigation_count = rejected_nav

    # Count dated items
    dated_items = [item for item in valid_items if item.date_text]
    result.dated_item_count = len(dated_items)

    # Sample items (max 5)
    result.sample_items = valid_items[:MAX_SAMPLE_ITEMS_RECORDED]

    # Apply decision
    apply_merck_ir_decision(result)

    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_markdown_report(
    result: MerckIrDedicatedPreflightResult,
    *,
    base_commit: str = "",
    branch: str = "",
    merge_6f_commit: str = "",
    trial_v2_source_count: int = 9,
) -> str:
    """Generate a markdown report for the merck_ir dedicated preflight."""
    lines: list[str] = []
    lines.append("# OPC Foundation M3C-6F.1 Merck IR Dedicated Extraction Preflight Report")
    lines.append("")
    lines.append(f"- **Generated at:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- **Branch:** {branch}")
    lines.append(f"- **Base commit:** {base_commit}")
    lines.append(f"- **M3C-6F merge commit:** {merge_6f_commit}")
    lines.append(f"- **Trial v2 source count:** {trial_v2_source_count}")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- **Source:** {result.source_id}")
    lines.append(f"- **Entry URL:** {result.entry_url}")
    lines.append(f"- **Entry type:** {result.entry_type}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| field | value |")
    lines.append("|---|---|")
    lines.append(f"| http_status | {result.http_status} |")
    lines.append(f"| content_type | {result.content_type} |")
    lines.append(f"| candidate_url_count | {result.candidate_url_count} |")
    lines.append(f"| valid_item_count | {result.valid_item_count} |")
    lines.append(f"| dated_item_count | {result.dated_item_count} |")
    lines.append(f"| rejected_navigation_count | {result.rejected_navigation_count} |")
    lines.append(f"| rss_or_feed_found | {result.rss_or_feed_found} |")
    lines.append(f"| sitemap_investor_url_count | {result.sitemap_investor_url_count} |")
    lines.append(f"| json_ld_item_count | {result.json_ld_item_count} |")
    lines.append(f"| login_required | {result.login_required} |")
    lines.append(f"| paywall_observed | {result.paywall_observed} |")
    lines.append(f"| captcha_or_antibot_observed | {result.captcha_or_antibot_observed} |")
    lines.append(f"| recommended_execution_mode | {result.recommended_execution_mode} |")
    lines.append(f"| trial_v2_allowlist_allowed_now | {result.trial_v2_allowlist_allowed_now} |")
    lines.append(f"| next_action | {result.next_action} |")
    lines.append(f"| risk_flags | {', '.join(result.risk_flags) if result.risk_flags else 'none'} |")
    lines.append("")

    if result.sample_items:
        lines.append("## Sample Items")
        lines.append("")
        lines.append("| title | url | date_text | entry_type |")
        lines.append("|---|---|---|---|")
        for item in result.sample_items:
            lines.append(f"| {item.title} | {item.url} | {item.date_text or '-'} | {item.entry_type} |")
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

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="M3C-6F.1 Merck IR Dedicated Extraction Preflight"
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Only discover IR entry points, skip content extraction",
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Run full extraction (default behavior)",
    )
    args = parser.parse_args()

    print(f"Running merck_ir dedicated preflight (discover_only={args.discover_only})...")

    result = run_merck_ir_dedicated_preflight(discover_only=args.discover_only)

    # Validate
    errors = validate_merck_ir_preflight_result(result)
    if errors:
        print("VALIDATION ERRORS:")
        for err in errors:
            print(f"  - {err}")
        return 1

    # Get current git info
    import subprocess

    def _git(args: str) -> str:
        try:
            return subprocess.check_output(
                f"git {args}", shell=True, cwd=str(_REPO_ROOT), text=True
            ).strip()
        except Exception:
            return ""

    base_commit = _git("rev-parse --short HEAD")
    branch = _git("branch --show-current")

    # Generate report
    report_md = generate_markdown_report(
        result,
        base_commit=base_commit,
        branch=branch,
        merge_6f_commit="a444afe",
        trial_v2_source_count=9,
    )

    # Write runtime data (gitignored)
    RUNTIME_DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_path = _REPO_ROOT / "docs" / "foundation_m3c_6f1_merck_ir_dedicated_preflight_report.md"
    report_path.write_text(report_md, encoding="utf-8")

    json_dict = make_batch_report_dict(
        result,
        base_commit=base_commit,
        branch=branch,
        merge_6f_commit="a444afe",
        trial_v2_source_count=9,
    )
    json_path = RUNTIME_DATA_DIR / "merck_ir_dedicated_preflight_summary.json"
    json_path.write_text(json.dumps(json_dict, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  -> decision={result.recommended_execution_mode}, http={result.http_status}, "
          f"items={result.valid_item_count}, dated={result.dated_item_count}, "
          f"rejected_nav={result.rejected_navigation_count}")
    print(f"Markdown report written to {report_path}")
    print(f"JSON summary written to {json_path}")
    print("Merck IR dedicated preflight completed successfully.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
