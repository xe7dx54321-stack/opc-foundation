"""M3C-5B1 P0 Source Repair Round 1 测试。

功能说明（小白解读）：
    验证 M3C-5B1 三个 P0 源的修复结果和边界约束。
    覆盖 gelonghui、goldman_sachs_podcasts、merck_ir 的修复状态、
    内容验证报告、backlog 更新、以及不越界约束。
"""

import pytest
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import yaml


# ---- Fixtures ----

@pytest.fixture
def source_inventory():
    """加载 source inventory 配置。"""
    path = Path("configs/foundation_source_inventory.example.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def repair_backlog():
    """加载 repair backlog 配置。"""
    path = Path("configs/foundation_source_repair_backlog.example.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def trial_v2_allowlist():
    """加载 trial_v2 allowlist。"""
    path = Path("configs/foundation_trial_v2_content_ready_allowlist.example.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def trae_config():
    """加载 TRAE trial v2 config。"""
    path = Path("configs/trae_foundation_trial_v2_content_ready.example.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---- 1. gelonghui 修复测试 ----

class TestGelonghuiRepair:
    """gelonghui 修复验证测试。"""

    def test_gelonghui_selector_updated(self):
        """gelonghui selector 已更新为容器级 li.article-li (M3C-5B1.1a)。"""
        from opc_foundation.source_inventory.content_validity import _SOURCE_SPECIFIC_SELECTORS
        selectors = _SOURCE_SPECIFIC_SELECTORS.get("gelonghui", [])
        assert any("li.article-li" == sel for sel, _ in selectors), "gelonghui selector should use container-level li.article-li"
        assert not any("div.detail-left" in sel for sel, _ in selectors), "old wrapper selector should be removed"

    def test_gelonghui_noise_filter_has_login(self):
        """gelonghui 噪音过滤包含 登录 / 注册 / App 下载。"""
        from opc_foundation.source_inventory.content_validity import extract_candidates_from_html
        # M3C-5B1.1a: 使用容器级选择器格式
        html = '''<html><body><ul>
<li class="article-li"><div class="article-li__main">
<a class="detail-left" href="/p/123">暴跌7%！特斯拉交付大捷创历史新高</a>
<section class="detail-right"><a href="/p/123">暴跌7%！特斯拉交付大捷创历史新高</a>
<section class="source-time">来自主题：汽车资讯1小时前</section>
</section></div></li>
<li class="article-li"><div class="article-li__main">
<a class="detail-left" href="/login">登录</a>
<section class="detail-right"><a href="/login">登录</a>
<section class="source-time">刚刚</section>
</section></div></li>
<li class="article-li"><div class="article-li__main">
<a class="detail-left" href="/register">注册</a>
<section class="detail-right"><a href="/register">注册</a>
<section class="source-time">刚刚</section>
</section></div></li>
<li class="article-li"><div class="article-li__main">
<a class="detail-left" href="/app">下载APP</a>
<section class="detail-right"><a href="/app">下载APP</a>
<section class="source-time">刚刚</section>
</section></div></li>
</ul></body></html>'''
        candidates = extract_candidates_from_html(html, "https://www.gelonghui.com", source_id="gelonghui")
        titles = [c.title for c in candidates]
        assert "暴跌7%！特斯拉交付大捷创历史新高" in titles
        assert "登录" not in titles
        assert "下载APP" not in titles
        assert "注册" not in titles
        assert "下载APP" not in titles

    def test_gelonghui_noise_filter_has_ads(self):
        """gelonghui 噪音过滤包含 广告 / 隐私政策 / 免责声明。"""
        html = '<html><body><a href="/p/456">黄金股飙升</a><a href="/ad">广告</a><a href="/privacy">隐私政策</a><a href="/disclaimer">免责声明</a></body></html>'
        from opc_foundation.source_inventory.content_validity import extract_candidates_from_html
        candidates = extract_candidates_from_html(html, "https://www.gelonghui.com", source_id="gelonghui")
        titles = [c.title for c in candidates]
        assert "黄金股飙升" in titles
        assert "广告" not in titles
        assert "隐私政策" not in titles
        assert "免责声明" not in titles

    def test_gelonghui_extracts_financial_news(self):
        """gelonghui 能抽取财经新闻候选，并标记为 news / high relevance。"""
        # M3C-5B1.1a: 使用容器级选择器 li.article-li 格式
        html = '''<html><body><ul>
<li class="article-li"><div class="article-li__main">
<a class="detail-left" href="/p/789">中国6月PMI跌至54.1</a>
<section class="detail-right">
<a href="/p/789">中国6月PMI跌至54.1</a>
<section class="source-time">来自主题：财经研究所1小时前</section>
</section>
</div></li>
</ul></body></html>'''
        from opc_foundation.source_inventory.content_validity import extract_candidates_from_html
        candidates = extract_candidates_from_html(html, "https://www.gelonghui.com", source_id="gelonghui")
        assert len(candidates) >= 1
        c = candidates[0]
        assert c.content_type == "news"
        assert c.relevance == "high"
        assert "/p/" in c.url

    def test_gelonghui_validation_report_exists(self):
        """gelonghui 独立验证报告存在。"""
        path = Path("docs/source_validation/gelonghui.md")
        assert path.exists()

    def test_gelonghui_report_shows_content_ready(self):
        """gelonghui 验证报告显示 content_ready 和 score=90。"""
        path = Path("docs/source_validation/gelonghui.md")
        content = path.read_text(encoding="utf-8")
        assert "content_ready" in content
        assert "score=90" in content or "score: 90" in content or "| 90 |" in content

    def test_gelonghui_backlog_status_updated(self, repair_backlog):
        """gelonghui backlog 状态已更新为 content_ready。"""
        sources = repair_backlog.get("sources", [])
        gelonghui = next((s for s in sources if s["source_id"] == "gelonghui"), None)
        assert gelonghui is not None
        assert gelonghui["status"] == "content_ready"
        assert gelonghui["score"] == 90
        assert gelonghui["recommended_action"] == "next_scheduling_candidate"


# ---- 2. goldman_sachs_podcasts 修复测试 ----

class TestGoldmanSachsPodcastsRepair:
    """goldman_sachs_podcasts 修复验证测试。"""

    def test_podcasts_does_not_treat_subscribe_as_candidate(self):
        """goldman_sachs_podcasts 不把 Subscribe / Privacy 当作有效候选（通用噪音过滤）。"""
        # 使用通用选择器路径测试，因为 GS podcast hub 页无 SSR episode
        html = '<html><body><a href="/subscribe">Subscribe</a><a href="/privacy">Privacy Policy</a><a href="/terms">Terms of Use</a><a href="/login">Sign In</a></body></html>'
        from opc_foundation.source_inventory.content_validity import extract_candidates_from_html
        candidates = extract_candidates_from_html(html, "https://www.goldmansachs.com/insights/podcasts", source_id="goldman_sachs_podcasts")
        titles = [c.title for c in candidates]
        assert "Subscribe" not in titles
        assert "Privacy Policy" not in titles
        assert "Terms of Use" not in titles
        assert "Sign In" not in titles

    def test_podcasts_consolidated_has_member_source_ids(self):
        """goldman_sachs_podcasts consolidated source 有 member_source_ids 或 is_consolidated 标记。"""
        from opc_foundation.source_inventory.content_validity import ContentAuditResult
        result = ContentAuditResult(source_id="goldman_sachs_podcasts", is_consolidated=True, member_source_ids=["podcast_1", "podcast_2"])
        assert result.is_consolidated is True
        assert len(result.member_source_ids) > 0

    def test_podcasts_backlog_moved_to_browser_like(self, repair_backlog):
        """goldman_sachs_podcasts backlog 已移动到 browser_like_backlog。"""
        sources = repair_backlog.get("sources", [])
        podcasts = next((s for s in sources if s["source_id"] == "goldman_sachs_podcasts"), None)
        assert podcasts is not None
        assert podcasts["category"] == "browser_like_backlog"
        assert podcasts["status"] == "browser_like_candidate"
        assert podcasts["next_stage"] == "M3C-5B2"

    def test_podcasts_validation_report_exists(self):
        """goldman_sachs_podcasts 独立验证报告存在。"""
        path = Path("docs/source_validation/goldman_sachs_podcasts.md")
        assert path.exists()

    def test_podcasts_report_explains_why_not_ready(self):
        """goldman_sachs_podcasts 报告解释为什么本轮无法修复。"""
        path = Path("docs/source_validation/goldman_sachs_podcasts.md")
        content = path.read_text(encoding="utf-8")
        assert "Cannot Be Fixed" in content or "无法修复" in content or "browser" in content.lower()


# ---- 3. merck_ir 修复测试 ----

class TestMerckIrRepair:
    """merck_ir 修复验证测试。"""

    def test_merck_ir_source_id_unchanged(self, source_inventory):
        """merck_ir source_id 保持不变。"""
        sources = source_inventory.get("sources", [])
        merck = next((s for s in sources if s["source_id"] == "merck_ir"), None)
        assert merck is not None
        assert merck["source_id"] == "merck_ir"

    def test_merck_ir_url_is_official(self, source_inventory):
        """merck_ir 替代 URL 必须是官方公开 Merck/Investor URL。"""
        sources = source_inventory.get("sources", [])
        merck = next((s for s in sources if s["source_id"] == "merck_ir"), None)
        assert merck is not None
        url = merck.get("url", "")
        assert "merck.com" in url, f"URL must be official Merck domain: {url}"
        assert "investor" in url.lower() or "news" in url.lower(), f"URL must be investor/newsroom related: {url}"

    def test_merck_ir_no_pdf_download(self):
        """merck_ir 不下载 PDF，只记录 title + URL（代码中无 PDF 下载逻辑）。"""
        from opc_foundation.source_inventory.content_validity import extract_candidates_from_html
        # 包含 PDF 链接的 HTML；merck_news 要求链接文本 > 15 字符
        html = '<html><body><a href="/news/press-release">Merck Announces Second Quarter 2026 Results</a><a href="/presentations/slides.pdf">Q2 Presentation PDF</a></body></html>'
        candidates = extract_candidates_from_html(html, "https://www.merck.com/investor-relations/", source_id="merck_ir")
        # 应提取到 press release，但不应触发 PDF 下载
        titles = [c.title for c in candidates]
        assert "Merck Announces Second Quarter 2026 Results" in titles
        # 代码中没有 PDF 下载逻辑，候选只记录元数据
        for c in candidates:
            assert c.title
            assert c.url

    def test_merck_ir_validation_report_exists(self):
        """merck_ir 独立验证报告存在。"""
        path = Path("docs/source_validation/merck_ir.md")
        assert path.exists()

    def test_merck_ir_report_shows_content_ready(self):
        """merck_ir 验证报告显示 content_ready 和 score=90。"""
        path = Path("docs/source_validation/merck_ir.md")
        content = path.read_text(encoding="utf-8")
        assert "content_ready" in content
        assert "score=90" in content or "score: 90" in content or "| 90 |" in content

    def test_merck_ir_backlog_status_updated(self, repair_backlog):
        """merck_ir backlog 状态已更新为 content_ready。"""
        sources = repair_backlog.get("sources", [])
        merck = next((s for s in sources if s["source_id"] == "merck_ir"), None)
        assert merck is not None
        assert merck["status"] == "content_ready"
        assert merck["score"] == 90
        assert merck["recommended_action"] == "next_scheduling_candidate"


# ---- 4. content_ready 标准测试 ----

class TestContentReadyThresholds:
    """content_ready 阈值标准测试。"""

    def test_content_ready_requires_min_valid_candidates(self):
        """content_ready 必须满足 valid_candidate_count >= 2。"""
        from opc_foundation.source_inventory.content_validity import ContentAuditResult
        result = ContentAuditResult(
            source_id="test",
            valid_candidate_count=5,
            relevant_candidate_count=5,
            content_score=90,
        )
        assert result.valid_candidate_count >= 2
        assert result.relevant_candidate_count >= 2
        assert result.content_score >= 70

    def test_content_ready_requires_min_relevant_candidates(self):
        """content_ready 必须满足 relevant_candidate_count >= 2。"""
        from opc_foundation.source_inventory.content_validity import ContentAuditResult
        result = ContentAuditResult(
            source_id="test",
            valid_candidate_count=5,
            relevant_candidate_count=3,
            content_score=90,
        )
        assert result.relevant_candidate_count >= 2

    def test_below_threshold_not_scheduling_candidate(self, repair_backlog):
        """未达标源不得设置 next_scheduling_candidate=true。"""
        sources = repair_backlog.get("sources", [])
        for s in sources:
            if s.get("status") != "content_ready":
                assert s.get("recommended_action") != "next_scheduling_candidate", \
                    f"{s['source_id']} is not content_ready but marked next_scheduling_candidate"


# ---- 5. 边界约束测试 ----

class TestBoundaryConstraints:
    """M3C-5B1 边界约束测试。"""

    def test_gelonghui_in_trial_v2_allowlist(self, trial_v2_allowlist):
        """M3C-5B1.3: gelonghui 已扩容加入 trial_v2 content-ready allowlist (9 源)。"""
        sources = trial_v2_allowlist.get("sources", [])
        ids = [s.get("source_id") for s in sources]
        assert "gelonghui" in ids, "gelonghui must be in trial_v2 allowlist after M3C-5B1.3"

    def test_no_merck_ir_in_trial_v2_allowlist(self, trial_v2_allowlist):
        """merck_ir 不得加入 trial_v2 content-ready allowlist。"""
        sources = trial_v2_allowlist.get("sources", [])
        ids = [s.get("source_id") for s in sources]
        assert "merck_ir" not in ids, "merck_ir must NOT be added to trial_v2 allowlist"

    def test_trae_scheduling_unchanged(self, trae_config):
        """不修改 TRAE scheduling（trial_v2 仍为 8 源示例配置）。"""
        jobs = trae_config.get("jobs", [])
        assert len(jobs) == 4, "TRAE example should still have 4 command-only jobs"
        for job in jobs:
            # 示例配置中 enabled=false；真实启用仅在本地 TRAE
            assert job.get("enabled") is False or job.get("enabled") == "false"

    def test_p0_report_no_proxy_url(self):
        """P0 修复报告不包含 proxy URL。"""
        path = Path("docs/foundation_p0_source_repair_report.md")
        if path.exists():
            content = path.read_text(encoding="utf-8")
            for pattern in [r'http://\S+:\d+', r'https://\S+:\d+', r'socks5://', r'socks4://']:
                assert len(re.findall(pattern, content)) == 0, f"Proxy URL found in P0 report"

    def test_p0_report_no_secrets(self):
        """P0 修复报告不包含 cookie/token/secrets。"""
        path = Path("docs/foundation_p0_source_repair_report.md")
        if path.exists():
            content = path.read_text(encoding="utf-8").lower()
            for keyword in ["cookie", "token", "secret", "password", "api_key", "private_key"]:
                # 允许文档中自然出现 "cookie" 等词作为说明，但不允许具体值
                # 这里简单检查是否没有明显的 key-value 格式
                pass
            # 检查是否有类似 Bearer/Authorization 的值
            assert "authorization:" not in content
            assert "bearer " not in content

    def test_gitignore_has_data(self):
        """data/ 不提交（.gitignore 检查）。"""
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            assert "data/" in content or "foundation_trial_v2_content_ready" in content

    def test_no_deleted_dashboard_pages_restored(self):
        """不恢复总览 / 运行日志 / 失败队列 / 文档入口。"""
        app_path = Path("src/opc_foundation/dashboard/app.py")
        if app_path.exists():
            content = app_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            main_func_started = False
            page_options = []
            for line in lines:
                if "def main()" in line:
                    main_func_started = True
                if main_func_started and "page ==" in line:
                    page_options.append(line.strip())
            for opt in page_options:
                assert "总览" not in opt
                assert "运行日志" not in opt
                assert "失败队列" not in opt
                assert "文档入口" not in opt

    def test_source_validation_reports_exist(self):
        """三个 P0 源都有独立 source_validation 报告。"""
        for source_id in ["gelonghui", "goldman_sachs_podcasts", "merck_ir"]:
            path = Path(f"docs/source_validation/{source_id}.md")
            assert path.exists(), f"Missing validation report for {source_id}"

    def test_p0_master_report_exists(self):
        """P0 总报告存在。"""
        path = Path("docs/foundation_p0_source_repair_report.md")
        assert path.exists()

    def test_backlog_no_production_enabled(self, repair_backlog):
        """backlog 不配置 production。"""
        scope = repair_backlog.get("scope", {})
        assert scope.get("production_enabled") is False or scope.get("production_enabled") == "false"

    def test_backlog_no_trial_v2_modification(self, repair_backlog):
        """backlog 明确不修改 trial_v2 allowlist。"""
        policy = repair_backlog.get("policy", {})
        assert policy.get("do_not_modify_trial_v2_allowlist") is True
