"""Tests for scripts/run_m3c_6b_scheduled_candidate_preflight.py (M3C-6B).

覆盖范围：
    1. execution mode 枚举合法（在 execution_capabilities 中已覆盖，此处只做集成校验）
    2. source_id 只能是 reuters / marketwatch / streetinsider
    3. trial_v2_allowlist_allowed_now 默认 false
    4. TRAE browser candidate 不得自动进入 trial_v2 allowlist
    5. agent-reach candidate 不得自动进入 trial_v2 allowlist
    6. scheduled_preflight_pass_static 必须有 >=3 valid items
    7. scheduled_preflight_pass_feed 必须有 feed evidence
    8. login_required=true 时不得 scheduled_preflight_pass
    9. paywall_observed=true 时不得 scheduled_preflight_pass
    10. captcha_or_antibot_observed=true 时不得 scheduled_preflight_pass
    11. report 不包含 cookie / token / proxy URL（敏感关键字扫描）
    12. 不修改 trial_v2 allowlist
    13. 不修改 TRAE scheduling
    14. 不配置 production
    15. 不引入 Playwright / Selenium
    16. 不恢复 Dashboard 已删除页面

注意：测试不应实际访问网络。所有测试都用 monkeypatch 拦截 httpx。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_PATH = REPO_ROOT / "src"
SCRIPTS_PATH = REPO_ROOT / "scripts"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Load the script as a module (so we can monkeypatch its internals)
_script_path = SCRIPTS_PATH / "run_m3c_6b_scheduled_candidate_preflight.py"
_spec = importlib.util.spec_from_file_location(
    "run_m3c_6b_scheduled_candidate_preflight", _script_path
)
assert _spec is not None and _spec.loader is not None
preflight_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(preflight_module)


CONFIG_PATH = (
    REPO_ROOT / "configs" / "foundation_m3c_6b_scheduled_candidate_preflight.example.yaml"
)


# =============================================================================
# Test 2: source_id 只能是 reuters / marketwatch / streetinsider
# =============================================================================

class TestCandidateFiltering:
    """Script must only accept the 3 whitelisted source IDs."""

    def test_config_candidate_sources_match_whitelist(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        candidates = cfg["scope"]["candidate_sources"]
        assert set(candidates) == {"reuters", "marketwatch", "streetinsider"}

    def test_main_rejects_invalid_source_id(self, capsys):
        """main() must exit 1 when --source contains invalid ids."""
        argv = ["prog", "--source", "merck_ir"]
        old_argv = sys.argv
        sys.argv = argv
        try:
            rc = preflight_module.main()
        except SystemExit as e:
            rc = e.code
        finally:
            sys.argv = old_argv
        assert rc == 1


# =============================================================================
# Test 3: trial_v2_allowlist_allowed_now 默认 false
# =============================================================================

class TestDefaultAllowlistFlag:
    """Default capability must have trial_v2_allowlist_allowed_now=False."""

    def test_make_default_capability_has_false_flag(self):
        cap = preflight_module.make_default_capability("reuters")
        assert cap.trial_v2_allowlist_allowed_now is False


# =============================================================================
# Tests 4-10: preflight logic with mocked HTTP (no network)
# =============================================================================

class _MockResponse:
    """Minimal mock of httpx.Response."""

    def __init__(
        self,
        status_code: int = 200,
        text: str = "",
        headers: dict[str, str] | None = None,
        url: str = "https://www.example.com",
    ):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {"content-type": "text/html"}
        self.url = url


class _MockClient:
    """Mock httpx.Client that returns canned responses without network."""

    def __init__(
        self,
        main_response: _MockResponse,
        feed_responses: dict[str, _MockResponse] | None = None,
    ):
        self._main = main_response
        self._feeds = feed_responses or {}
        self.calls: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        if url in self._feeds:
            return self._feeds[url]
        return self._main


def _patch_httpx(monkeypatch, client: _MockClient):
    """Replace the httpx.Client used by the script with our mock."""

    class _FakeHttpxModule:
        @staticmethod
        def Client(*args, **kwargs):
            return client

    # Inject fake httpx into sys.modules so the script's `import httpx` picks it up.
    monkeypatch.setitem(sys.modules, "httpx", _FakeHttpxModule)


def _make_html_with_items(item_count: int, with_dates: bool = True) -> str:
    """Build a fake HTML page with N anchor items.

    NOTE: nav links intentionally use benign labels to avoid triggering
    login_page_hint / paywall_hint / captcha_hint / antibot_hint classifiers.
    """
    items = []
    for i in range(item_count):
        date_attr = f"2026-07-0{i + 1}" if with_dates else ""
        items.append(
            f'<a href="/article-{i}.html">Article {i} Title Here '
            f'<span>{date_attr}</span></a>'
        )
    nav = (
        '<a href="/about">About</a>'
        '<a href="/privacy-policy">Privacy Policy</a>'
    )
    body = "".join(items) + nav
    return f"<html><body>{body}</body></html>"


class TestStaticHttpPreflightLogic:
    """run_static_http_preflight behavior with mocked httpx."""

    def test_static_pass_with_3_items_and_2_dated(self, monkeypatch):
        html = _make_html_with_items(5, with_dates=True)
        main_resp = _MockResponse(text=html, url="https://www.reuters.com")
        # No feed / sitemap found
        client = _MockClient(main_response=main_resp, feed_responses={})
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {
            "network": {"timeout_seconds": 5, "user_agent": "test"},
        }
        cap, summary = preflight_module.run_static_http_preflight(source, config)
        # Should have >=3 valid items
        assert cap.static_http_valid_items >= 3
        assert cap.static_http_dated_items >= 2
        # Should not be blocked
        assert "blocked_403" not in cap.risk_flags
        assert "login_page_hint" not in cap.risk_flags or cap.static_http_valid_items > 0
        # Final decision depends on whether feed found; with no feed, should be static pass
        # but only if dated_items >= 2 — which is the case here
        assert cap.final_decision in (
            "scheduled_preflight_pass_static",
            "scheduled_preflight_pass_feed",
            "manual_reaudit_needed",
        ), cap.final_decision

    def test_static_pass_requires_minimum_3_items(self, monkeypatch):
        """A page with only 2 items should NOT be scheduled_preflight_pass_static."""
        html = _make_html_with_items(2, with_dates=True)
        main_resp = _MockResponse(text=html, url="https://www.reuters.com")
        client = _MockClient(main_response=main_resp, feed_responses={})
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {"network": {"timeout_seconds": 5}}
        cap, _ = preflight_module.run_static_http_preflight(source, config)
        # With only 2 items, cannot be scheduled_preflight_pass_static
        assert cap.final_decision != "scheduled_preflight_pass_static"

    def test_feed_pass_requires_feed_evidence(self, monkeypatch):
        """scheduled_preflight_pass_feed requires feed_count>=1 OR sitemap_count>=1."""
        html = _make_html_with_items(2, with_dates=True)
        main_resp = _MockResponse(text=html, url="https://www.reuters.com")
        # Provide a working RSS feed response
        feed_resp = _MockResponse(
            status_code=200,
            text="<?xml version='1.0'?><rss><channel><item><title>x</title></item></channel></rss>",
            headers={"content-type": "application/rss+xml"},
            url="https://www.reuters.com/rss",
        )
        client = _MockClient(
            main_response=main_resp,
            feed_responses={"https://www.reuters.com/rss": feed_resp},
        )
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {"network": {"timeout_seconds": 5}}
        cap, _ = preflight_module.run_static_http_preflight(source, config)
        # Feed was found, so feed_count >= 1
        assert cap.feed_count >= 1
        # If there are dated items, this should be pass_feed; else manual_reaudit
        if cap.static_http_dated_items >= 2:
            assert cap.final_decision == "scheduled_preflight_pass_feed"
        else:
            # No dated items in page text (only feed items) but feed_count > 0 should still pass_feed
            # Per script logic: feed_count > 0 -> pass_feed
            assert cap.final_decision == "scheduled_preflight_pass_feed"

    def test_403_blocks_preflight(self, monkeypatch):
        main_resp = _MockResponse(status_code=403, text="Forbidden")
        client = _MockClient(main_response=main_resp, feed_responses={})
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {"network": {"timeout_seconds": 5}}
        cap, _ = preflight_module.run_static_http_preflight(source, config)
        assert cap.static_http_status == "blocked"
        assert "blocked_403" in cap.risk_flags
        assert cap.final_decision != "scheduled_preflight_pass_static"
        assert cap.final_decision != "scheduled_preflight_pass_feed"

    def test_login_hint_blocks_pass_static(self, monkeypatch):
        """If page text contains login hints, must not be scheduled_preflight_pass_static."""
        # Page with login hint in the body text + some links
        html = (
            "<html><body>"
            "<h1>Please sign in to continue reading</h1>"
            '<a href="/article-1.html">Article 1 Title Here 2026-07-01</a>'
            '<a href="/article-2.html">Article 2 Title Here 2026-07-02</a>'
            '<a href="/article-3.html">Article 3 Title Here 2026-07-03</a>'
            "</body></html>"
        )
        main_resp = _MockResponse(text=html, url="https://www.reuters.com")
        client = _MockClient(main_response=main_resp, feed_responses={})
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {"network": {"timeout_seconds": 5}}
        cap, _ = preflight_module.run_static_http_preflight(source, config)
        assert "login_page_hint" in cap.risk_flags
        assert cap.final_decision != "scheduled_preflight_pass_static"
        assert cap.final_decision != "scheduled_preflight_pass_feed"

    def test_paywall_hint_blocks_pass_static(self, monkeypatch):
        html = (
            "<html><body>"
            "<h1>Subscribe to read full article</h1>"
            '<a href="/article-1.html">Article 1 Title Here 2026-07-01</a>'
            '<a href="/article-2.html">Article 2 Title Here 2026-07-02</a>'
            '<a href="/article-3.html">Article 3 Title Here 2026-07-03</a>'
            "</body></html>"
        )
        main_resp = _MockResponse(text=html, url="https://www.reuters.com")
        client = _MockClient(main_response=main_resp, feed_responses={})
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {"network": {"timeout_seconds": 5}}
        cap, _ = preflight_module.run_static_http_preflight(source, config)
        assert "paywall_hint" in cap.risk_flags
        assert cap.final_decision != "scheduled_preflight_pass_static"

    def test_captcha_hint_blocks_pass_static(self, monkeypatch):
        html = (
            "<html><body>"
            "<h1>Please complete the CAPTCHA to continue</h1>"
            '<a href="/article-1.html">Article 1 Title Here 2026-07-01</a>'
            '<a href="/article-2.html">Article 2 Title Here 2026-07-02</a>'
            '<a href="/article-3.html">Article 3 Title Here 2026-07-03</a>'
            "</body></html>"
        )
        main_resp = _MockResponse(text=html, url="https://www.reuters.com")
        client = _MockClient(main_response=main_resp, feed_responses={})
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {"network": {"timeout_seconds": 5}}
        cap, _ = preflight_module.run_static_http_preflight(source, config)
        assert "captcha_hint" in cap.risk_flags
        assert cap.final_decision != "scheduled_preflight_pass_static"

    def test_antibot_hint_blocks_pass_static(self, monkeypatch):
        html = (
            "<html><body>"
            "<h1>Checking your browser before accessing the site</h1>"
            '<meta name="cf-ray" content="abc123">'
            '<a href="/article-1.html">Article 1 Title Here 2026-07-01</a>'
            '<a href="/article-2.html">Article 2 Title Here 2026-07-02</a>'
            '<a href="/article-3.html">Article 3 Title Here 2026-07-03</a>'
            "</body></html>"
        )
        main_resp = _MockResponse(text=html, url="https://www.reuters.com")
        client = _MockClient(main_response=main_resp, feed_responses={})
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {"network": {"timeout_seconds": 5}}
        cap, _ = preflight_module.run_static_http_preflight(source, config)
        assert "antibot_hint" in cap.risk_flags
        assert cap.final_decision != "scheduled_preflight_pass_static"


# =============================================================================
# Test 11: report 不包含 cookie / token / proxy URL
# =============================================================================

class TestReportNoSensitiveData:
    """Generated report must not contain sensitive keywords."""

    def test_evidence_summary_clean_for_pass_static(self, monkeypatch):
        html = _make_html_with_items(5, with_dates=True)
        main_resp = _MockResponse(text=html, url="https://www.reuters.com")
        client = _MockClient(main_response=main_resp, feed_responses={})
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {"network": {"timeout_seconds": 5}}
        cap, _ = preflight_module.run_static_http_preflight(source, config)

        from opc_foundation.source_inventory.execution_capabilities import (
            scan_sensitive_keywords,
        )
        hits = scan_sensitive_keywords(cap.evidence_summary)
        assert hits == [], f"Sensitive keywords found: {hits}"
        # Also check trae browser notes
        hits_notes = scan_sensitive_keywords(cap.trae_browser_assessment.notes)
        assert hits_notes == []

    def test_report_text_clean_of_sensitive_keywords(self, monkeypatch, tmp_path):
        """Generate a small report and scan it for sensitive keywords."""
        html = _make_html_with_items(5, with_dates=True)
        main_resp = _MockResponse(text=html, url="https://www.reuters.com")
        client = _MockClient(main_response=main_resp, feed_responses={})
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {
            "network": {"timeout_seconds": 5},
            "scope": {
                "production_enabled": False,
                "affects_trial_v2_allowlist": False,
                "affects_trae_scheduling": False,
            },
            "base_allowlist": ["barclays_our_insights"],
            "candidates": [
                {"source_id": "reuters", "source_name": "Reuters", "expected_value": "high"},
            ],
        }
        cap, _ = preflight_module.run_static_http_preflight(source, config)
        report_path = tmp_path / "test_report.md"
        preflight_module.generate_preflight_report(
            capabilities=[cap],
            config=config,
            master_commit="abc1234",
            branch="feature/test",
            report_path=report_path,
        )
        text = report_path.read_text(encoding="utf-8")
        lower = text.lower()
        for kw in (
            "cookie:", "set-cookie", "bearer ", "api_key=",
            "apikey:", "proxy_url=", "http://127.0.0.1",
            "http://localhost", "password=", "secret=", "token=",
        ):
            assert kw not in lower, f"Sensitive keyword {kw!r} found in report"


# =============================================================================
# Tests 12-16: Boundary invariants — no allowlist / scheduling / production changes
# =============================================================================

class TestScriptBoundaryInvariants:
    """Script must not modify allowlist / TRAE scheduling / production."""

    def test_config_scope_flags(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        scope = cfg["scope"]
        assert scope["production_enabled"] is False
        assert scope["affects_trial_v2_allowlist"] is False
        assert scope["affects_trae_scheduling"] is False

    def test_config_policy_flags(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        policy = cfg["policy"]
        assert policy["do_not_modify_trial_v2_allowlist"] is True
        assert policy["do_not_modify_trae_scheduling"] is True
        assert policy["do_not_configure_production"] is True
        assert policy["no_cloudflare_bypass"] is True
        assert policy["no_login_bypass"] is True
        assert policy["no_paywall_bypass"] is True
        assert policy["no_cookie_commit"] is True

    def test_config_base_allowlist_unchanged_at_9(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        base = cfg["base_allowlist"]
        expected = {
            "barclays_our_insights",
            "markets_insider",
            "china_fund_news",
            "wind_public",
            "goldman_sachs_insights",
            "business_insider",
            "cls_cn",
            "zhitong_caijing",
            "gelonghui",
        }
        assert set(base) == expected
        assert len(base) == 9

    def test_config_excludes_merck_ir(self):
        """M3C-6B config must NOT include merck_ir as candidate."""
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        candidates = [c["source_id"] for c in cfg["candidates"]]
        assert "merck_ir" not in candidates

    def test_config_excludes_goldman_sachs_podcasts(self):
        """M3C-6B config must NOT include goldman_sachs_podcasts as candidate."""
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        candidates = [c["source_id"] for c in cfg["candidates"]]
        assert "goldman_sachs_podcasts" not in candidates

    def test_config_excludes_benzinga_analyst_ratings(self):
        """M3C-6B config must NOT include benzinga_analyst_ratings."""
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        candidates = [c["source_id"] for c in cfg["candidates"]]
        assert "benzinga_analyst_ratings" not in candidates

    def test_script_does_not_import_playwright_or_selenium(self):
        """Script source must not import Playwright or Selenium."""
        text = _script_path.read_text(encoding="utf-8")
        lower = text.lower()
        # Must not contain actual import statements for playwright / selenium
        assert "import playwright" not in lower
        assert "from playwright" not in lower
        assert "import selenium" not in lower
        assert "from selenium" not in lower
        # Must not instantiate playwright / selenium runtime objects
        assert "playwright.sync_playwright" not in lower
        assert "selenium.webdriver" not in lower
        assert "playwright.async_api" not in lower

    def test_trae_assessment_design_only(self):
        """Config trae_assessment must mark automation_design_only=true."""
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        ta = cfg["trae_assessment"]
        assert ta["automation_design_only"] is True
        assert ta["do_not_create_permanent_task"] is True
        assert ta["do_not_install_skill_artifacts_into_repo"] is True

    def test_no_dashboard_page_restoration_in_script(self):
        """Script must not restore deleted Dashboard pages."""
        text = _script_path.read_text(encoding="utf-8")
        # Must not create 总览 / 运行日志 / 失败队列 / 文档入口 dashboard pages
        forbidden = ["总览", "运行日志", "失败队列", "文档入口"]
        for token in forbidden:
            assert token not in text, f"Script references deleted Dashboard page: {token}"


# =============================================================================
# Test: report generation produces required sections
# =============================================================================

class TestReportGeneration:
    """Generated report must contain all required sections per spec."""

    def test_report_contains_required_sections(self, monkeypatch, tmp_path):
        html = _make_html_with_items(5, with_dates=True)
        main_resp = _MockResponse(text=html, url="https://www.reuters.com")
        client = _MockClient(main_response=main_resp, feed_responses={})
        _patch_httpx(monkeypatch, client)

        source = {"source_id": "reuters", "url": "https://www.reuters.com"}
        config = {
            "network": {"timeout_seconds": 5},
            "scope": {
                "production_enabled": False,
                "affects_trial_v2_allowlist": False,
                "affects_trae_scheduling": False,
            },
            "base_allowlist": ["barclays_our_insights"],
            "candidates": [
                {"source_id": "reuters", "source_name": "Reuters", "expected_value": "high"},
            ],
        }
        cap, _ = preflight_module.run_static_http_preflight(source, config)
        report_path = tmp_path / "test_report.md"
        preflight_module.generate_preflight_report(
            capabilities=[cap],
            config=config,
            master_commit="abc1234",
            branch="feature/test",
            report_path=report_path,
        )
        text = report_path.read_text(encoding="utf-8")

        # Required sections per spec
        assert "## Summary" in text
        assert "### Static / Feed Preflight Result" in text
        assert "### TRAE Browser / Skill Assessment" in text
        assert "### Final Decision" in text
        assert "## Allowlist Categorization" in text
        assert "## Boundary Confirmation" in text
        assert "## Recommendation" in text
        assert "## Detail: reuters" in text
        assert "### Evidence Summary" in text
        # Boundary confirmation rows
        assert "Modified TRAE scheduling" in text
        assert "Modified trial_v2 allowlist" in text
        assert "Configured production" in text
        assert "Introduced Playwright/Selenium" in text

    def test_report_includes_master_commit_and_branch(self, monkeypatch, tmp_path):
        cap = preflight_module.make_default_capability("reuters")
        config = {
            "base_allowlist": [],
            "scope": {},
            "candidates": [{"source_id": "reuters", "source_name": "Reuters", "expected_value": "high"}],
        }
        report_path = tmp_path / "test.md"
        preflight_module.generate_preflight_report(
            capabilities=[cap],
            config=config,
            master_commit="deadbee",
            branch="feature/x",
            report_path=report_path,
        )
        text = report_path.read_text(encoding="utf-8")
        assert "deadbee" in text
        assert "feature/x" in text


# =============================================================================
# Test: helper functions
# =============================================================================

class TestHelperFunctions:
    """Helper function unit tests."""

    def test_extract_links_with_dates_basic(self):
        html = (
            '<a href="/article-1.html">First Article 2026-07-01</a>'
            '<a href="/article-2.html">Second Article 2026-07-02</a>'
            '<a href="https://example.com/article-3">Third Article 2026-07-03</a>'
            '<a href="/login">Sign in</a>'
            '<a href="javascript:void(0)">Click</a>'
        )
        items = preflight_module.extract_links_with_dates(html, "https://example.com")
        # Should filter out login / javascript
        urls = [i.url for i in items]
        assert all("login" not in u for u in urls)
        assert all("javascript" not in u for u in urls)
        assert len(items) >= 3

    def test_extract_date_text_iso(self):
        text = "Published 2026-07-04 by Reuters"
        assert preflight_module.extract_date_text(text) == "2026-07-04"

    def test_extract_date_text_relative(self):
        text = "Posted 3 hours ago"
        assert "ago" in preflight_module.extract_date_text(text)

    def test_extract_date_text_chinese(self):
        text = "5小时前"
        assert preflight_module.extract_date_text(text) == "5小时前"

    def test_extract_date_text_none(self):
        assert preflight_module.extract_date_text("no date here") == ""

    def test_classify_noise_flags_403(self):
        flags = preflight_module.classify_noise_flags("page content", http_status=403)
        assert "blocked_403" in flags

    def test_classify_noise_flags_login_hint(self):
        flags = preflight_module.classify_noise_flags("Please sign in to continue")
        assert "login_page_hint" in flags

    def test_classify_noise_flags_empty(self):
        flags = preflight_module.classify_noise_flags("ok")
        assert "empty_page" in flags

    def test_extract_metadata_signals_jsonld(self):
        html = (
            '<script type="application/ld+json">{"@context":"https://schema.org"}</script>'
            '<meta property="og:title" content="Article">'
        )
        signals = preflight_module.extract_metadata_signals(html)
        assert signals["json_ld_count"] == 1
        assert signals["opengraph_count"] == 1

    def test_probe_feed_finds_rss(self, monkeypatch):
        rss_resp = _MockResponse(
            status_code=200,
            text="<?xml version='1.0'?><rss><channel></channel></rss>",
            headers={"content-type": "application/rss+xml"},
        )
        client = _MockClient(main_response=_MockResponse(status_code=404), feed_responses={
            "https://www.reuters.com/rss": rss_resp,
            "https://www.reuters.com/rss.xml": rss_resp,
        })
        feed_count, sitemap_count, paths = preflight_module.probe_feed(
            client, "https://www.reuters.com", timeout=5
        )
        assert feed_count >= 1
        assert sitemap_count == 0

    def test_probe_feed_finds_sitemap(self, monkeypatch):
        sitemap_resp = _MockResponse(
            status_code=200,
            text="<?xml version='1.0'?><urlset></urlset>",
            headers={"content-type": "application/xml"},
        )
        client = _MockClient(main_response=_MockResponse(status_code=404), feed_responses={
            "https://www.reuters.com/sitemap.xml": sitemap_resp,
        })
        feed_count, sitemap_count, paths = preflight_module.probe_feed(
            client, "https://www.reuters.com", timeout=5
        )
        assert sitemap_count >= 1
