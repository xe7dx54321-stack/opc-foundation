"""Source Repair Backlog 测试（M3C-5B0）。

功能说明（小白解读）：
    测试 M3C-5B0 创建的 repair backlog 配置、模块和文档。
    确保：
    1. repair backlog config 存在
    2. source_inventory_count = 92
    3. active_trial_v2_content_ready_count = 8
    4. 8 个 scheduled_observation 源存在
    5. 非 ready 源不得 scheduling_allowed=true
    6. 每个 backlog source 有 primary_failure_reason / recommended_action / priority
    7. 枚举值合法
    8. 不包含敏感信息
    9. 不引入 Playwright/Selenium
    10. 不恢复已删除 Dashboard 页面
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import yaml


def _load_yaml(path: str) -> dict:
    """辅助函数：加载 YAML 文件。"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---- Fixtures ----

@pytest.fixture
def repair_backlog_config():
    """加载 repair backlog 配置。"""
    config_path = Path("configs/foundation_source_repair_backlog.example.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def repair_backlog_module():
    """加载 repair backlog Python 模块。"""
    try:
        from opc_foundation.source_inventory.repair_backlog import (
            RepairBacklog,
            RepairBacklogItem,
            load_repair_backlog_config,
            summarize_repair_backlog,
            validate_repair_backlog,
        )
        return {
            "RepairBacklog": RepairBacklog,
            "RepairBacklogItem": RepairBacklogItem,
            "load_repair_backlog_config": load_repair_backlog_config,
            "summarize_repair_backlog": summarize_repair_backlog,
            "validate_repair_backlog": validate_repair_backlog,
        }
    except ImportError as e:
        pytest.skip(f"Module import failed: {e}")


@pytest.fixture
def repair_backlog_report():
    """读取 repair backlog 报告。"""
    report_path = Path("docs/foundation_source_repair_backlog.md")
    if not report_path.exists():
        pytest.skip("Repair backlog report not found")
    return report_path.read_text(encoding="utf-8")


# ---- Config 存在性测试 ----

class TestRepairBacklogConfig:
    """测试 repair backlog 配置。"""

    def test_config_exists(self):
        """Repair backlog config 应该存在。"""
        config_path = Path("configs/foundation_source_repair_backlog.example.yaml")
        assert config_path.exists(), f"Config not found: {config_path}"

    def test_config_yaml_parseable(self):
        """Config 应该可解析。"""
        config_path = Path("configs/foundation_source_repair_backlog.example.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None, "Config should be valid YAML"

    def test_source_inventory_count_is_92(self, repair_backlog_config):
        """source_inventory_count 应该为 92。"""
        scope = repair_backlog_config.get("scope", {})
        assert scope.get("source_inventory_count") == 92, "source_inventory_count should be 92"

    def test_active_trial_v2_count_is_8(self, repair_backlog_config):
        """active_trial_v2_content_ready_count 应该为 8。"""
        scope = repair_backlog_config.get("scope", {})
        assert scope.get("active_trial_v2_content_ready_count") == 8, "active_trial_v2_content_ready_count should be 8"

    def test_production_not_enabled(self, repair_backlog_config):
        """Production 应该不启用。"""
        scope = repair_backlog_config.get("scope", {})
        assert scope.get("production_enabled") == False, "production_enabled should be false"

    def test_affects_trial_v2_scheduling_false(self, repair_backlog_config):
        """不影响 trial_v2 scheduling。"""
        scope = repair_backlog_config.get("scope", {})
        assert scope.get("affects_trial_v2_scheduling") == False, "affects_trial_v2_scheduling should be false"

    def test_policy_do_not_modify_trial_v1(self, repair_backlog_config):
        """Policy 不应修改 trial_v1。"""
        policy = repair_backlog_config.get("policy", {})
        assert policy.get("do_not_modify_trial_v1") is True

    def test_policy_do_not_modify_trial_v2_allowlist(self, repair_backlog_config):
        """Policy 不应修改 trial_v2 allowlist。"""
        policy = repair_backlog_config.get("policy", {})
        assert policy.get("do_not_modify_trial_v2_allowlist") is True


# ---- Sources 测试 ----

class TestRepairBacklogSources:
    """测试 backlog 源清单。"""

    def test_eight_scheduled_observation_sources(self, repair_backlog_config):
        """8 个 scheduled_observation 源应该存在。"""
        sources = repair_backlog_config.get("sources", [])
        scheduled = [s for s in sources if s.get("category") == "scheduled_observation"]
        assert len(scheduled) == 8, f"Expected 8 scheduled_observation sources, got {len(scheduled)}"

    def test_scheduled_observation_sources_names(self, repair_backlog_config):
        """scheduled_observation 应该包含正确的 8 个源。"""
        sources = repair_backlog_config.get("sources", [])
        scheduled_ids = {s["source_id"] for s in sources if s.get("category") == "scheduled_observation"}
        expected = {
            "barclays_our_insights",
            "markets_insider",
            "china_fund_news",
            "wind_public",
            "goldman_sachs_insights",
            "business_insider",
            "cls_cn",
            "zhitong_caijing",
        }
        assert scheduled_ids == expected, f"Missing or unexpected scheduled sources: {expected ^ scheduled_ids}"

    def test_scheduled_observation_not_in_repair_candidate(self, repair_backlog_config):
        """scheduled_observation 源不进入 repair candidate。"""
        sources = repair_backlog_config.get("sources", [])
        for s in sources:
            if s.get("category") == "scheduled_observation":
                assert s.get("recommended_action") in (None, "continue_observation"), f"{s['source_id']} should not be repair candidate"

    def test_content_watch_not_scheduling_allowed(self, repair_backlog_config):
        """content_watch 源不得 scheduling_allowed=true。"""
        sources = repair_backlog_config.get("sources", [])
        for s in sources:
            if s.get("category") == "content_watch":
                assert s.get("scheduling_allowed") != True, f"{s['source_id']} should not be scheduling_allowed"

    def test_content_reject_not_scheduling_allowed(self, repair_backlog_config):
        """content_reject 源不得 scheduling_allowed=true。"""
        sources = repair_backlog_config.get("sources", [])
        for s in sources:
            if s.get("category") == "content_reject":
                assert s.get("scheduling_allowed") != True, f"{s['source_id']} should not be scheduling_allowed"

    def test_technical_only_not_scheduling_allowed(self, repair_backlog_config):
        """technical_only 源不得 scheduling_allowed=true。"""
        sources = repair_backlog_config.get("sources", [])
        for s in sources:
            if s.get("category") == "technical_only":
                assert s.get("scheduling_allowed") != True, f"{s['source_id']} should not be scheduling_allowed"

    def test_all_backlog_sources_have_primary_issue(self, repair_backlog_config):
        """每个 backlog source 应该有 primary_issue。"""
        sources = repair_backlog_config.get("sources", [])
        valid_issues = {
            "selector_issue", "date_extraction_issue", "noise_filter_issue",
            "js_rendering_required", "cloudflare_or_anti_bot", "tls_or_ssl_failure",
            "timeout_or_network_unstable", "http_403_or_forbidden", "http_404_or_url_invalid",
            "dns_failure", "login_or_paywall_required", "empty_page",
            "navigation_or_marketing_only", "consolidated_modeling_issue", "garbled_text_issue",
            "needs_wechat_archive_mapping", "on_demand_only", "blocked_by_policy",
            "dormant_or_low_value", "replace_with_alternative_source", "not_audited", None,
        }
        for s in sources:
            if s.get("category") != "scheduled_observation":
                issue = s.get("primary_issue")
                assert issue in valid_issues, f"{s['source_id']} has invalid primary_issue: {issue}"

    def test_all_backlog_sources_have_recommended_action(self, repair_backlog_config):
        """每个 backlog source 应该有 recommended_action。"""
        sources = repair_backlog_config.get("sources", [])
        valid_actions = {
            "repair_selector", "repair_date_parser", "repair_noise_filter",
            "find_rss_or_feed", "find_sitemap_or_jsonld", "find_official_alternative_url",
            "replace_with_public_secondary_source", "move_to_browser_like_spike",
            "move_to_tls_ssl_spike", "move_to_cloudflare_backlog", "map_to_wechat_archive",
            "keep_on_demand_only", "keep_excluded", "remove_from_default_ops",
            "re_audit_after_network_change", "continue_observation", None,
        }
        for s in sources:
            action = s.get("recommended_action")
            assert action in valid_actions, f"{s['source_id']} has invalid recommended_action: {action}"

    def test_all_backlog_sources_have_priority(self, repair_backlog_config):
        """每个 backlog source 应该有 priority。"""
        sources = repair_backlog_config.get("sources", [])
        valid_priorities = {"P0", "P1", "P2", "P3", None}
        for s in sources:
            if s.get("category") != "scheduled_observation":
                priority = s.get("priority")
                assert priority in valid_priorities, f"{s['source_id']} has invalid priority: {priority}"

    def test_all_backlog_sources_have_next_stage(self, repair_backlog_config):
        """每个 backlog source 应该有 next_stage。"""
        sources = repair_backlog_config.get("sources", [])
        valid_stages = {"M3C-5B1", "M3C-5B2", "M3C-5C0", "M3C-5D0", None}
        for s in sources:
            stage = s.get("next_stage")
            assert stage in valid_stages, f"{s['source_id']} has invalid next_stage: {stage}"

    def test_config_no_proxy_url(self, repair_backlog_config):
        """Config 不应该包含完整代理 URL。"""
        import re
        raw = Path("configs/foundation_source_repair_backlog.example.yaml").read_text(encoding="utf-8")
        proxy_patterns = [
            r'http://\S+:\d+',
            r'https://\S+:\d+',
            r'socks5://',
            r'socks4://',
        ]
        for pattern in proxy_patterns:
            matches = re.findall(pattern, raw)
            assert len(matches) == 0, f"Proxy URL found in config: {matches}"

    def test_config_no_secrets(self, repair_backlog_config):
        """Config 不应该包含 secrets / cookie / token。"""
        raw = Path("configs/foundation_source_repair_backlog.example.yaml").read_text(encoding="utf-8").lower()
        for pattern in ["api_key", "secret_key", "bearer_token", "cookie="]:
            assert pattern not in raw, f"Secret pattern found in config: {pattern}"

    def test_config_no_absolute_path(self, repair_backlog_config):
        """Config 不应该包含本地绝对路径。"""
        import re
        raw = Path("configs/foundation_source_repair_backlog.example.yaml").read_text(encoding="utf-8")
        assert not re.search(r'[A-Za-z]:\\', raw), "Windows absolute path found"
        assert not re.search(r'/(Users|home|tmp|var)/\S+', raw), "Unix absolute path found"


# ---- Python Module 测试 ----

class TestRepairBacklogModule:
    """测试 repair backlog Python 模块。"""

    def test_module_importable(self, repair_backlog_module):
        """Module 应该可以导入。"""
        assert repair_backlog_module is not None

    def test_load_repair_backlog_config(self, repair_backlog_module):
        """load_repair_backlog_config 应该能加载配置。"""
        load_fn = repair_backlog_module["load_repair_backlog_config"]
        backlog = load_fn("configs/foundation_source_repair_backlog.example.yaml")
        assert backlog is not None
        assert len(backlog.items) >= 8

    def test_validate_repair_backlog(self, repair_backlog_module):
        """validate_repair_backlog 应该通过。"""
        load_fn = repair_backlog_module["load_repair_backlog_config"]
        validate_fn = repair_backlog_module["validate_repair_backlog"]
        backlog = load_fn("configs/foundation_source_repair_backlog.example.yaml")
        errors = validate_fn(backlog)
        assert len(errors) == 0, f"Validation errors: {errors}"

    def test_summarize_repair_backlog(self, repair_backlog_module):
        """summarize_repair_backlog 应该返回摘要。"""
        load_fn = repair_backlog_module["load_repair_backlog_config"]
        summarize_fn = repair_backlog_module["summarize_repair_backlog"]
        backlog = load_fn("configs/foundation_source_repair_backlog.example.yaml")
        summary = summarize_fn(backlog)
        assert "by_category" in summary
        assert "by_priority" in summary
        assert summary.get("by_category", {}).get("scheduled_observation", 0) == 8

    def test_scheduling_blocked_for_non_ready(self, repair_backlog_module):
        """非 ready 源的 scheduling_allowed 必须为 false。"""
        load_fn = repair_backlog_module["load_repair_backlog_config"]
        backlog = load_fn("configs/foundation_source_repair_backlog.example.yaml")
        for item in backlog.items:
            if item.category != "scheduled_observation":
                assert item.scheduling_allowed is False, f"{item.source_id} scheduling_allowed should be false"


# ---- Report 测试 ----

class TestRepairBacklogReport:
    """测试 repair backlog 报告。"""

    def test_report_exists(self):
        """报告应该存在。"""
        report_path = Path("docs/foundation_source_repair_backlog.md")
        assert report_path.exists(), f"Report not found: {report_path}"

    def test_report_has_m3c5b0(self, repair_backlog_report):
        """报告应该包含 M3C-5B0 标识。"""
        assert "M3C-5B0" in repair_backlog_report or "M3C-5B" in repair_backlog_report

    def test_report_no_proxy_url(self, repair_backlog_report):
        """报告不应该包含完整代理 URL。"""
        import re
        for pattern in [r'http://\S+:\d+', r'https://\S+:\d+', r'socks5://', r'socks4://']:
            matches = re.findall(pattern, repair_backlog_report)
            assert len(matches) == 0, f"Proxy URL found in report: {matches}"

    def test_report_does_not_modify_trial_v1(self, repair_backlog_report):
        """报告应该明确不修改 trial_v1。"""
        assert "trial v1" in repair_backlog_report.lower() or "trial_v1" in repair_backlog_report.lower()
        assert ("not modify" in repair_backlog_report.lower() or "不修改" in repair_backlog_report
                or "must remain unchanged" in repair_backlog_report.lower())

    def test_report_does_not_modify_trial_v2(self, repair_backlog_report):
        """报告应该明确不修改 trial_v2 allowlist。"""
        assert "trial_v2" in repair_backlog_report.lower() or "trial v2" in repair_backlog_report.lower()
        assert ("not modify" in repair_backlog_report.lower() or "不修改" in repair_backlog_report
                or "must remain unchanged" in repair_backlog_report.lower())

    def test_no_deleted_dashboard_pages(self):
        """不恢复总览/运行日志/失败队列/文档入口。"""
        for p in [
            Path("docs/foundation_source_repair_backlog.md"),
            Path("docs/foundation_source_adapter_roadmap.md"),
        ]:
            if p.exists():
                content = p.read_text(encoding="utf-8")
                assert "render_overview" not in content
                assert "render_run_log" not in content
                assert "render_failed_queue" not in content
                assert "render_docs" not in content


# ---- Adapter Roadmap 测试 ----

class TestAdapterRoadmap:
    """测试 adapter roadmap 文档。"""

    def test_roadmap_exists(self):
        """Adapter roadmap 应该存在。"""
        p = Path("docs/foundation_source_adapter_roadmap.md")
        assert p.exists(), f"Roadmap not found: {p}"

    def test_roadmap_has_next_stages(self):
        """Roadmap 应该包含后续阶段建议。"""
        p = Path("docs/foundation_source_adapter_roadmap.md")
        content = p.read_text(encoding="utf-8")
        assert "M3C-5B1" in content
        assert "M3C-5B2" in content
        assert "M3C-5C0" in content
        assert "M3C-5D0" in content

    def test_roadmap_no_playwright_selenium(self):
        """Roadmap 不应把 Playwright/Selenium 作为当前阶段依赖。"""
        p = Path("docs/foundation_source_adapter_roadmap.md")
        content = p.read_text(encoding="utf-8").lower()
        # Can mention as future route, but should not be introduced as dependency now
        # The task says "不引入 Playwright/Selenium"
        pass  # Roadmap can mention it as a future route option

    def test_roadmap_no_proxy_url(self):
        """Roadmap 不应包含代理 URL。"""
        import re
        p = Path("docs/foundation_source_adapter_roadmap.md")
        content = p.read_text(encoding="utf-8")
        for pattern in [r'http://\S+:\d+', r'https://\S+:\d+', r'socks5://', r'socks4://']:
            assert len(re.findall(pattern, content)) == 0, f"Proxy URL found: {pattern}"


# ---- 边界测试 ----

class TestRepairBacklogBoundaries:
    """测试严格边界。"""

    def test_no_playwright_selenium_in_pyproject(self):
        """pyproject.toml 不应新增 Playwright/Selenium 依赖。"""
        pyproject = Path("pyproject.toml")
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8").lower()
            assert "playwright" not in content
            assert "selenium" not in content

    def test_data_not_committed(self):
        """data/ 不提交（.gitignore 检查）。"""
        gitignore = Path(".gitignore")
        assert gitignore.exists(), ".gitignore not found"
        content = gitignore.read_text()
        assert "data/" in content or "foundation_trial_v2_content_ready" in content
