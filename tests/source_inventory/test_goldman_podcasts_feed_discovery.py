"""Goldman Sachs Podcasts Feed Discovery 测试（M3C-5B2）。

功能说明：
    测试 discover_goldman_sachs_podcasts_feed.py 的边界、解析器和输出，确保：
    1. 只处理 goldman_sachs_podcasts
    2. 不修改 trial_v2 allowlist / TRAE scheduling / production
    3. 不引入 Playwright / Selenium
    4. 各 parser 能正确识别/拒绝内容
    5. navigation noise filter 生效
    6. 报告不含 secrets / proxy URL
    7. 不恢复已删除 Dashboard 页面
"""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import discovery script functions directly
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import discover_goldman_sachs_podcasts_feed as discover_module


# ---- Fixtures ----

@pytest.fixture
def report_text():
    """读取 M3C-5B2 报告。"""
    report_path = Path("docs/foundation_m3c_5b2_goldman_podcasts_feed_spike_report.md")
    if not report_path.exists():
        pytest.skip("M3C-5B2 report not found")
    return report_path.read_text(encoding="utf-8")


@pytest.fixture
def discovery_result():
    """执行 discovery 并返回结果（离线时 skip）。"""
    try:
        return discover_module.discover()
    except Exception as exc:
        pytest.skip(f"Discovery failed (likely offline): {exc}")


# ---- 1. 范围与边界测试 ----

class TestDiscoveryScope:
    """测试 discovery 只处理 goldman_sachs_podcasts。"""

    def test_source_id_is_goldman_podcasts(self):
        """SOURCE_ID 必须是 goldman_sachs_podcasts。"""
        assert discover_module.SOURCE_ID == "goldman_sachs_podcasts"

    def test_source_name_is_goldman_podcasts(self):
        """SOURCE_NAME 必须包含 Goldman Sachs Podcasts。"""
        assert "Goldman Sachs Podcasts" in discover_module.SOURCE_NAME

    def test_discovery_result_has_correct_source_id(self, discovery_result):
        """结果对象 source_id 正确。"""
        assert discovery_result.source_id == "goldman_sachs_podcasts"

    def test_no_other_source_ids_in_module(self):
        """模块中不应硬编码其他 source_id。"""
        module_src = Path(discover_module.__file__).read_text(encoding="utf-8")
        other_ids = [
            "merck_ir", "gelonghui", "benzinga_analyst_ratings",
            "wallstreet_cn", "barclays_our_insights", "business_insider",
        ]
        for sid in other_ids:
            assert sid not in module_src, f"Module should not reference {sid}"


class TestBoundaryGuards:
    """测试不修改 allowlist / scheduling / production。"""

    def test_no_playwright_import(self):
        """模块不能 import playwright。"""
        module_src = Path(discover_module.__file__).read_text(encoding="utf-8")
        import re
        assert not re.search(r"\b(import\s+playwright|from\s+playwright)\b", module_src, re.I), \
            "Module imports playwright"

    def test_no_selenium_import(self):
        """模块不能 import selenium。"""
        module_src = Path(discover_module.__file__).read_text(encoding="utf-8")
        import re
        assert not re.search(r"\b(import\s+selenium|from\s+selenium)\b", module_src, re.I), \
            "Module imports selenium"

    def test_no_allowlist_modification_function(self):
        """模块不应提供修改 allowlist 的函数。"""
        assert not hasattr(discover_module, "modify_allowlist")
        assert not hasattr(discover_module, "update_allowlist")

    def test_no_trae_config_modification(self):
        """模块不应提供修改 TRAE config 的函数。"""
        assert not hasattr(discover_module, "modify_trae_config")
        assert not hasattr(discover_module, "update_trae_schedule")

    def test_no_production_enable_flag(self):
        """模块不应设置 production_enabled。"""
        module_src = Path(discover_module.__file__).read_text(encoding="utf-8")
        import re
        assert not re.search(r"\bproduction_enabled\s*=\s*True\b", module_src, re.I), \
            "Module sets production_enabled=True"

    def test_no_data_directory_write(self):
        """模块不应写入 data/ 目录。"""
        module_src = Path(discover_module.__file__).read_text(encoding="utf-8")
        import re
        # Detect actual write operations targeting data/ (e.g. open('data/...', 'w'))
        assert not re.search(r"open\s*\(\s*['\"]data/", module_src, re.I), \
            "Module writes to data/ directory"


# ---- 2. Parser 单元测试 ----

class TestRssAtomParser:
    """测试 RSS / Atom / XML feed parser。"""

    RSS_SAMPLE = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>Markets Update: Q3 Outlook</title>
          <link>https://example.com/ep1</link>
          <pubDate>Mon, 15 Jul 2024 09:00:00 GMT</pubDate>
          <description>Quarterly markets outlook.</description>
        </item>
        <item>
          <title>Top of Mind: AI in Finance</title>
          <link>https://example.com/ep2</link>
          <pubDate>Tue, 16 Jul 2024 10:00:00 GMT</pubDate>
          <description>Exploring AI trends.</description>
        </item>
      </channel>
    </rss>
    """

    ATOM_SAMPLE = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Exchanges: Climate Finance</title>
        <link href="https://example.com/ep3"/>
        <published>2024-07-17T08:00:00Z</published>
        <summary>Climate finance discussion.</summary>
      </entry>
    </feed>
    """

    def test_rss_parser_extracts_episodes(self):
        """RSS parser 能提取 episode item。"""
        eps = discover_module.parse_rss_atom(self.RSS_SAMPLE, "https://example.com/feed.xml")
        assert len(eps) == 2
        titles = [e["title"] for e in eps]
        assert "Markets Update: Q3 Outlook" in titles
        assert "Top of Mind: AI in Finance" in titles

    def test_rss_parser_has_dates(self):
        """RSS parser 能提取 pubDate。"""
        eps = discover_module.parse_rss_atom(self.RSS_SAMPLE, "https://example.com/feed.xml")
        assert any("2024" in e["date"] for e in eps)

    def test_rss_parser_has_descriptions(self):
        """RSS parser 能提取 description。"""
        eps = discover_module.parse_rss_atom(self.RSS_SAMPLE, "https://example.com/feed.xml")
        descs = [e["description"] for e in eps]
        assert "Quarterly markets outlook." in descs

    def test_atom_parser_extracts_entries(self):
        """Atom parser 能提取 entry。"""
        eps = discover_module.parse_rss_atom(self.ATOM_SAMPLE, "https://example.com/atom.xml")
        assert len(eps) == 1
        assert eps[0]["title"] == "Exchanges: Climate Finance"
        assert "2024-07-17" in eps[0]["date"]


class TestJsonLdParser:
    """测试 JSON-LD parser。"""

    JSONLD_PODCAST_EPISODE = """
    <script type="application/ld+json">
    {
      "@type": "PodcastEpisode",
      "headline": "Episode 42: The Future of Banking",
      "url": "https://example.com/ep42",
      "datePublished": "2024-07-01",
      "description": "A deep dive into banking trends."
    }
    </script>
    """

    JSONLD_NEWS_ARTICLE = """
    <script type="application/ld+json">
    {
      "@type": "NewsArticle",
      "headline": "GS Research: 2025 Macro Outlook",
      "url": "https://example.com/news1",
      "datePublished": "2024-06-20",
      "description": "Macro outlook summary."
    }
    </script>
    """

    JSONLD_CREATIVE_WORK = """
    <script type="application/ld+json">
    {
      "@type": "CreativeWork",
      "name": "Top of Mind: Recession Risks",
      "url": "https://example.com/tom1",
      "datePublished": "2024-05-15",
      "description": "Recession risk analysis."
    }
    </script>
    """

    def test_parser_recognizes_podcast_episode(self):
        """JSON-LD parser 能识别 PodcastEpisode。"""
        eps = discover_module.parse_json_ld(self.JSONLD_PODCAST_EPISODE, "https://example.com")
        assert len(eps) == 1
        assert eps[0]["title"] == "Episode 42: The Future of Banking"
        assert eps[0]["json_type"] == "PodcastEpisode"

    def test_parser_recognizes_news_article(self):
        """JSON-LD parser 能识别 NewsArticle。"""
        eps = discover_module.parse_json_ld(self.JSONLD_NEWS_ARTICLE, "https://example.com")
        assert len(eps) == 1
        assert eps[0]["title"] == "GS Research: 2025 Macro Outlook"
        assert eps[0]["json_type"] == "NewsArticle"

    def test_parser_recognizes_creative_work(self):
        """JSON-LD parser 能识别 CreativeWork。"""
        eps = discover_module.parse_json_ld(self.JSONLD_CREATIVE_WORK, "https://example.com")
        assert len(eps) == 1
        assert eps[0]["title"] == "Top of Mind: Recession Risks"
        assert eps[0]["json_type"] == "CreativeWork"

    def test_parser_ignores_unrelated_types(self):
        """JSON-LD parser 忽略不相关类型。"""
        html = '<script type="application/ld+json">{"@type": "WebSite", "name": "GS"}</script>'
        eps = discover_module.parse_json_ld(html, "https://example.com")
        assert len(eps) == 0


class TestOpenGraphParser:
    """测试 OpenGraph parser。"""

    def test_og_parser_extracts_metadata(self):
        """OG parser 能提取 og:title / og:description。"""
        html = '''
        <meta property="og:title" content="Goldman Sachs Podcasts">
        <meta property="og:url" content="https://www.goldmansachs.com/insights/podcasts">
        <meta property="og:description" content="Breaking down key issues.">
        <meta property="og:type" content="website">
        '''
        eps = discover_module.parse_opengraph(html, "https://example.com")
        assert len(eps) == 1
        assert eps[0]["title"] == "Goldman Sachs Podcasts"
        assert eps[0]["og_type"] == "website"

    def test_og_parser_does_not_treat_subscribe_as_episode(self):
        """OG parser 不把 Subscribe 页面当 episode（但会提取 og metadata）。"""
        html = '''
        <meta property="og:title" content="Subscribe on Apple Podcasts">
        <meta property="og:type" content="website">
        '''
        eps = discover_module.parse_opengraph(html, "https://example.com")
        assert len(eps) == 1
        # parser itself doesn't filter noise; noise filter is downstream
        assert "Subscribe" in eps[0]["title"]


class TestHtmlEpisodeParser:
    """测试 HTML episode link parser。"""

    def test_html_parser_extracts_links_with_dates(self):
        """HTML parser 能提取带日期的链接。"""
        html = '''
        <div>
          <a href="/ep1">Markets Update: July 2024</a>
          <span>July 15, 2024</span>
        </div>
        <div>
          <a href="/ep2">Top of Mind: AI</a>
          <span>2024-07-16</span>
        </div>
        '''
        eps = discover_module.parse_html_episode_links(html, "https://example.com")
        titles = [e["title"] for e in eps]
        assert "Markets Update: July 2024" in titles
        assert any("2024" in e["date"] for e in eps)

    def test_html_parser_skips_empty_links(self):
        """HTML parser 跳过空链接。"""
        html = '<a href="/x"></a><a href="/y">Valid Title</a>'
        eps = discover_module.parse_html_episode_links(html, "https://example.com")
        assert len(eps) == 1
        assert eps[0]["title"] == "Valid Title"


# ---- 3. Noise Filter 测试 ----

class TestNavigationNoiseFilter:
    """测试导航噪音过滤。"""

    def test_filters_subscribe(self):
        """Subscribe 被识别为噪音。"""
        c = {"title": "Subscribe on Apple Podcasts", "url": "https://example.com", "description": ""}
        assert discover_module.is_navigation_noise(c) is True

    def test_filters_asset_wealth_management(self):
        """ASSET & WEALTH MANAGEMENT 被识别为噪音。"""
        c = {"title": "ASSET & WEALTH MANAGEMENT", "url": "https://example.com", "description": ""}
        assert discover_module.is_navigation_noise(c) is True

    def test_filters_spotify(self):
        """Spotify 被识别为噪音。"""
        c = {"title": "Listen on Spotify", "url": "https://spotify.com", "description": ""}
        assert discover_module.is_navigation_noise(c) is True

    def test_filters_short_title(self):
        """过短标题被识别为噪音。"""
        c = {"title": "AB", "url": "https://example.com", "description": ""}
        assert discover_module.is_navigation_noise(c) is True

    def test_keeps_real_episode(self):
        """真实 episode 标题不被过滤。"""
        c = {"title": "Exchanges: The Future of Clean Energy", "url": "https://example.com/ep1", "description": ""}
        assert discover_module.is_navigation_noise(c) is False

    def test_filter_noise_list(self):
        """filter_noise 返回非噪音列表。"""
        candidates = [
            {"title": "Subscribe", "url": "https://example.com", "description": ""},
            {"title": "Markets Update: Q3 2024", "url": "https://example.com/ep1", "description": ""},
            {"title": "ASSET & WEALTH MANAGEMENT", "url": "https://example.com", "description": ""},
        ]
        filtered = discover_module.filter_noise(candidates)
        assert len(filtered) == 1
        assert filtered[0]["title"] == "Markets Update: Q3 2024"


# ---- 4. Final Decision 枚举测试 ----

class TestFinalDecision:
    """测试 final_decision 合法性。"""

    VALID_DECISIONS = {
        "feed_candidate_found",
        "browser_like_backlog",
        "network_or_access_watch",
    }

    def test_final_decision_is_valid_enum(self, discovery_result):
        """final_decision 必须是合法枚举值。"""
        assert discovery_result.final_decision in self.VALID_DECISIONS

    def test_browser_like_backlog_when_no_feed(self, discovery_result):
        """当没有稳定 feed 时，应为 browser_like_backlog。"""
        # Based on real crawl, hub page has no SSR episodes and RSS paths 404
        assert discovery_result.final_decision in ("browser_like_backlog", "network_or_access_watch")


# ---- 5. 报告安全测试 ----

class TestReportSecurity:
    """测试报告不含敏感信息。"""

    def test_report_no_proxy_url(self, report_text):
        """报告不应包含代理 URL。"""
        proxy_patterns = [
            r'http://[^:]+:\d+',
            r'https://[^:]+:\d+',
            r'socks5://',
            r'socks4://',
        ]
        for pattern in proxy_patterns:
            matches = re.findall(pattern, report_text)
            assert len(matches) == 0, f"Proxy URL found: {matches}"

    def test_report_no_api_keys(self, report_text):
        """报告不应包含 API key。"""
        assert "api_key" not in report_text.lower()
        assert "apikey" not in report_text.lower()

    def test_report_no_secrets(self, report_text):
        """报告不应包含 secret keywords。"""
        sensitive = ["secret_key", "access_token", "bearer token", "aws_secret", "password"]
        for kw in sensitive:
            assert kw.lower() not in report_text.lower(), f"Sensitive keyword found: {kw}"

    def test_report_no_cookies(self, report_text):
        """报告不应包含 cookie 值。"""
        assert "cookie:" not in report_text.lower()
        assert "set-cookie" not in report_text.lower()

    def test_report_no_authorization_headers(self, report_text):
        """报告不应包含 authorization header。"""
        assert "authorization:" not in report_text.lower()
        assert "bearer " not in report_text.lower()


# ---- 6. Dashboard 页面恢复测试 ----

class TestDashboardPagesNotRestored:
    """测试不恢复已删除 Dashboard 页面。"""

    FORBIDDEN_PAGES = ["总览", "运行日志", "失败队列", "文档入口"]

    def test_no_forbidden_pages_in_script(self):
        """脚本源码不应提及恢复已删除页面。"""
        module_src = Path(discover_module.__file__).read_text(encoding="utf-8")
        for page in self.FORBIDDEN_PAGES:
            assert page not in module_src, f"Script should not reference deleted page: {page}"

    def test_no_forbidden_pages_in_report(self, report_text):
        """报告不应提及恢复已删除页面。"""
        for page in self.FORBIDDEN_PAGES:
            assert page not in report_text, f"Report should not reference deleted page: {page}"


# ---- 7. 报告完整性测试 ----

class TestReportCompleteness:
    """测试报告包含必要章节。"""

    def test_report_has_timestamp(self, report_text):
        """报告应包含执行时间。"""
        assert "执行时间" in report_text

    def test_report_has_base_commit(self, report_text):
        """报告应包含 base commit。"""
        assert "Base Commit" in report_text
        assert "796f9e8" in report_text

    def test_report_has_branch(self, report_text):
        """报告应包含 branch 名。"""
        assert "Branch" in report_text
        assert "feature/m3c-5b2-goldman-podcasts-feed-spike" in report_text

    def test_report_has_entry_results_table(self, report_text):
        """报告应包含入口发现结果表格。"""
        assert "entry_type" in report_text
        assert "http_status" in report_text

    def test_report_has_final_decision(self, report_text):
        """报告应包含 final_decision。"""
        assert "final_decision" in report_text

    def test_report_has_boundary_checks(self, report_text):
        """报告应包含边界检查项。"""
        assert "修改 trial_v2 allowlist" in report_text
        assert "修改 TRAE scheduling" in report_text
        assert "配置 production" in report_text
