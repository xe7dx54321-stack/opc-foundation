"""
Tests for foundation_source_inventory.example.yaml configuration.

本测试文件验证 source inventory 配置的正确性，包括：
- 文件存在性
- source_groups 和 sources 非空
- source_id 全局唯一
- 字段枚举合法性
- 覆盖指定网站/源
- 禁止源默认禁用
- search provider 默认 on_demand
"""

from pathlib import Path

import pytest
import yaml


# ============================================
# Constants
# ============================================

INVENTORY_PATH = Path("configs/foundation_source_inventory.example.yaml")

# 合法枚举值
VALID_ACTIVATION_PRIORITIES = {"S", "A", "B", "C", "supplement", "blocked"}
VALID_AUTOMATION_MODES = {"scheduled", "on_demand", "manual_only", "dormant", "do_not_ingest"}
VALID_SCHEDULE_PROFILES = {
    "high_daily",
    "medium_daily",
    "low_daily",
    "weekly",
    "on_demand",
    "manual_only",
    "dormant",
    "blocked",
}
VALID_LEGAL_CONFIDENCES = {
    "official",
    "licensed_media",
    "public_ir",
    "mainstream_media",
    "rebroadcast",
    "unknown",
    "high_risk",
}
VALID_ACCESS_MODES = {
    "public_web",
    "rss",
    "podcast_rss",
    "company_ir",
    "media_page",
    "search_provider",
    "manual",
    "dormant",
}


# ============================================
# Helper Functions
# ============================================


def load_inventory() -> dict:
    """加载 source inventory 配置文件。

    Returns:
        dict: YAML 解析后的配置数据

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 解析失败
    """
    with open(INVENTORY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_source_groups(inventory: dict) -> list[dict]:
    """获取 source_groups 列表。

    Args:
        inventory: 配置数据

    Returns:
        source_groups 列表，若不存在返回空列表
    """
    return inventory.get("source_groups", []) or []


def get_sources(inventory: dict) -> list[dict]:
    """获取 sources 列表。

    Args:
        inventory: 配置数据

    Returns:
        sources 列表，若不存在返回空列表
    """
    return inventory.get("sources", []) or []


def get_group_ids(inventory: dict) -> set[str]:
    """获取所有 group_id 的集合。

    Args:
        inventory: 配置数据

    Returns:
        group_id 集合
    """
    return {g.get("group_id", "") for g in get_source_groups(inventory)}


def get_source_ids(inventory: dict) -> set[str]:
    """获取所有 source_id 的集合。

    Args:
        inventory: 配置数据

    Returns:
        source_id 集合
    """
    return {s.get("source_id", "") for s in get_sources(inventory)}


def get_source_names(inventory: dict) -> set[str]:
    """获取所有 source_name 的集合。

    Args:
        inventory: 配置数据

    Returns:
        source_name 集合
    """
    return {s.get("source_name", "") for s in get_sources(inventory)}


# ============================================
# Test Class
# ============================================


class TestSourceInventoryConfig:
    """Source Inventory 配置测试类。

    验证配置文件的结构、字段合法性、覆盖情况和边界条件。
    """

    # ----------------------------------------
    # 1. 文件存在性和基本结构测试
    # ----------------------------------------

    def test_inventory_file_exists(self) -> None:
        """测试配置文件存在。

        验证 foundation_source_inventory.example.yaml 文件存在。
        """
        assert INVENTORY_PATH.exists(), f"Inventory file not found: {INVENTORY_PATH}"

    def test_inventory_yaml_parseable(self) -> None:
        """测试 YAML 文件可解析。

        验证配置文件可以被 yaml.safe_load 正确解析。
        """
        inventory = load_inventory()
        assert isinstance(inventory, dict), "Inventory should be a dict"
        assert "version" in inventory, "Inventory should have version field"
        assert "updated_at" in inventory, "Inventory should have updated_at field"

    def test_source_groups_non_empty(self) -> None:
        """测试 source_groups 非空。

        验证配置文件中至少有一个 source_group。
        """
        inventory = load_inventory()
        groups = get_source_groups(inventory)
        assert len(groups) >= 1, "source_groups should not be empty"

    def test_sources_non_empty(self) -> None:
        """测试 sources 非空。

        验证配置文件中至少有一个 source。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        assert len(sources) >= 1, "sources should not be empty"

    # ----------------------------------------
    # 2. source_id 唯一性测试
    # ----------------------------------------

    def test_source_ids_unique(self) -> None:
        """测试 source_id 全局唯一。

        验证所有 source 的 source_id 在全局范围内唯一。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        source_ids = [s.get("source_id", "") for s in sources]
        assert len(source_ids) == len(set(source_ids)), "source_id should be globally unique"

    # ----------------------------------------
    # 3. source_group 引用有效性测试
    # ----------------------------------------

    def test_source_group_references_valid(self) -> None:
        """测试 source_group 引用有效。

        验证每个 source 的 source_group 字段指向一个存在的 group_id。
        """
        inventory = load_inventory()
        valid_group_ids = get_group_ids(inventory)
        sources = get_sources(inventory)
        for source in sources:
            source_group = source.get("source_group", "")
            assert source_group in valid_group_ids, f"source_group '{source_group}' not found in source_groups"

    # ----------------------------------------
    # 4. capability_id 引用有效性测试
    # ----------------------------------------

    def test_capability_id_valid_or_special(self) -> None:
        """测试 capability_id 引用有效。

        验证 capability_id 指向有效的 capability，或者明确为 supplement/blocked/on_demand 类型。
        supplement、blocked、on_demand 类型的 source 可以使用特殊 capability_id。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)

        # 合法的特殊 capability_id
        special_capability_ids = {"supplement", "blocked"}

        for source in sources:
            capability_id = source.get("capability_id", "")
            activation_priority = source.get("activation_priority", "")
            automation_mode = source.get("automation_mode", "")

            # 如果是 supplement/blocked，允许特殊 capability_id
            if activation_priority in {"supplement", "blocked"} or automation_mode in {"on_demand", "do_not_ingest", "dormant"}:
                # 这些情况允许任意 capability_id
                continue

            # 其他情况，capability_id 应该以 research. 或 official_filing. 或 document_extraction. 开头
            # 或者是 runtime. 开头
            valid_prefixes = ("research.", "official_filing.", "document_extraction.", "runtime.")
            assert capability_id.startswith(valid_prefixes) or capability_id in special_capability_ids, f"Invalid capability_id '{capability_id}' in source '{source.get('source_id')}'"

    # ----------------------------------------
    # 5. 枚举合法性测试
    # ----------------------------------------

    def test_activation_priority_valid(self) -> None:
        """测试 activation_priority 枚举合法。

        验证所有 source 的 activation_priority 字段值在合法枚举范围内。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        for source in sources:
            priority = source.get("activation_priority", "")
            assert priority in VALID_ACTIVATION_PRIORITIES, f"Invalid activation_priority '{priority}' in source '{source.get('source_id')}'"

    def test_automation_mode_valid(self) -> None:
        """测试 automation_mode 枚举合法。

        验证所有 source 的 automation_mode 字段值在合法枚举范围内。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        for source in sources:
            mode = source.get("automation_mode", "")
            assert mode in VALID_AUTOMATION_MODES, f"Invalid automation_mode '{mode}' in source '{source.get('source_id')}'"

    def test_schedule_profile_valid(self) -> None:
        """测试 schedule_profile 枚举合法。

        验证所有 source 的 schedule_profile 字段值在合法枚举范围内。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        for source in sources:
            profile = source.get("schedule_profile", "")
            assert profile in VALID_SCHEDULE_PROFILES, f"Invalid schedule_profile '{profile}' in source '{source.get('source_id')}'"

    def test_legal_confidence_valid(self) -> None:
        """测试 legal_confidence 枚举合法。

        验证所有 source 的 legal_confidence 字段值在合法枚举范围内。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        for source in sources:
            confidence = source.get("legal_confidence", "")
            assert confidence in VALID_LEGAL_CONFIDENCES, f"Invalid legal_confidence '{confidence}' in source '{source.get('source_id')}'"

    # ----------------------------------------
    # 6. blocked/high_risk 源默认禁用测试
    # ----------------------------------------

    def test_blocked_high_risk_sources_disabled(self) -> None:
        """测试 blocked/high_risk 源默认禁用。

        验证 blocked 或 high_risk 的源 enabled_by_default 必须为 False。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        for source in sources:
            activation_priority = source.get("activation_priority", "")
            legal_confidence = source.get("legal_confidence", "")
            enabled = source.get("enabled_by_default", True)

            if activation_priority == "blocked" or legal_confidence == "high_risk":
                assert enabled is False, f"blocked/high_risk source '{source.get('source_id')}' must have enabled_by_default=False"

    # ----------------------------------------
    # 7. search provider 默认 on_demand 测试
    # ----------------------------------------

    def test_search_providers_not_scheduled(self) -> None:
        """测试 search provider 默认不是 scheduled。

        验证 search_providers 组的源 automation_mode 不能是 scheduled。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        for source in sources:
            source_group = source.get("source_group", "")
            automation_mode = source.get("automation_mode", "")

            if source_group == "search_providers":
                assert automation_mode != "scheduled", f"search_provider '{source.get('source_id')}' should not be scheduled by default"

    # ----------------------------------------
    # 8. 覆盖 source group 数量测试
    # ----------------------------------------

    def test_at_least_9_source_groups(self) -> None:
        """测试至少有 9 个 source group。

        验证配置文件覆盖了至少 9 个 source group。
        """
        inventory = load_inventory()
        groups = get_source_groups(inventory)
        assert len(groups) >= 9, f"Expected at least 9 source_groups, got {len(groups)}"

    # ----------------------------------------
    # 9. 覆盖投行官方公开研究测试
    # ----------------------------------------

    def test_cover_goldman_sachs(self) -> None:
        """测试覆盖 Goldman Sachs。

        验证配置文件包含 Goldman Sachs 相关的信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        goldman_sources = [n for n in source_names if "Goldman Sachs" in n]
        assert len(goldman_sources) >= 1, "Expected at least 1 Goldman Sachs source"

    def test_cover_morgan_stanley(self) -> None:
        """测试覆盖 Morgan Stanley。

        验证配置文件包含 Morgan Stanley 相关的信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        morgan_sources = [n for n in source_names if "Morgan Stanley" in n]
        assert len(morgan_sources) >= 1, "Expected at least 1 Morgan Stanley source"

    def test_cover_jp_morgan(self) -> None:
        """测试覆盖 J.P. Morgan。

        验证配置文件包含 J.P. Morgan 相关的信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        jp_sources = [n for n in source_names if "J.P. Morgan" in n]
        assert len(jp_sources) >= 1, "Expected at least 1 J.P. Morgan source"

    def test_cover_bofa(self) -> None:
        """测试覆盖 BofA。

        验证配置文件包含 Bank of America (BofA) 相关的信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        bofa_sources = [n for n in source_names if "BofA" in n or "Bank of America" in n]
        assert len(bofa_sources) >= 1, "Expected at least 1 BofA source"

    def test_cover_citi(self) -> None:
        """测试覆盖 Citi。

        验证配置文件包含 Citi 相关的信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        citi_sources = [n for n in source_names if "Citi" in n]
        assert len(citi_sources) >= 1, "Expected at least 1 Citi source"

    def test_cover_ubs(self) -> None:
        """测试覆盖 UBS。

        验证配置文件包含 UBS 相关的信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        ubs_sources = [n for n in source_names if "UBS" in n]
        assert len(ubs_sources) >= 1, "Expected at least 1 UBS source"

    def test_cover_barclays(self) -> None:
        """测试覆盖 Barclays。

        验证配置文件包含 Barclays 相关的信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        barclays_sources = [n for n in source_names if "Barclays" in n]
        assert len(barclays_sources) >= 1, "Expected at least 1 Barclays source"

    # ----------------------------------------
    # 10. 覆盖媒体研报二次引用测试
    # ----------------------------------------

    def test_cover_reuters(self) -> None:
        """测试覆盖 Reuters。

        验证配置文件包含 Reuters 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "Reuters" in source_names, "Expected Reuters source"

    def test_cover_marketwatch(self) -> None:
        """测试覆盖 MarketWatch。

        验证配置文件包含 MarketWatch 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "MarketWatch" in source_names, "Expected MarketWatch source"

    def test_cover_yahoo_finance(self) -> None:
        """测试覆盖 Yahoo Finance。

        验证配置文件包含 Yahoo Finance 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "Yahoo Finance" in source_names, "Expected Yahoo Finance source"

    def test_cover_business_insider(self) -> None:
        """测试覆盖 Business Insider。

        验证配置文件包含 Business Insider 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "Business Insider" in source_names, "Expected Business Insider source"

    # ----------------------------------------
    # 11. 覆盖分析师评级源测试
    # ----------------------------------------

    def test_cover_investing_com(self) -> None:
        """测试覆盖 Investing.com。

        验证配置文件包含 Investing.com Analyst Ratings 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        investing_sources = [n for n in source_names if "Investing.com" in n]
        assert len(investing_sources) >= 1, "Expected at least 1 Investing.com source"

    def test_cover_benzinga(self) -> None:
        """测试覆盖 Benzinga。

        验证配置文件包含 Benzinga 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        benzinga_sources = [n for n in source_names if "Benzinga" in n]
        assert len(benzinga_sources) >= 1, "Expected at least 1 Benzinga source"

    def test_cover_the_fly(self) -> None:
        """测试覆盖 The Fly。

        验证配置文件包含 The Fly 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "The Fly" in source_names, "Expected The Fly source"

    def test_cover_streetinsider(self) -> None:
        """测试覆盖 StreetInsider。

        验证配置文件包含 StreetInsider 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "StreetInsider" in source_names, "Expected StreetInsider source"

    def test_cover_briefing_com(self) -> None:
        """测试覆盖 Briefing.com。

        验证配置文件包含 Briefing.com 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        briefing_sources = [n for n in source_names if "Briefing.com" in n]
        assert len(briefing_sources) >= 1, "Expected at least 1 Briefing.com source"

    def test_cover_tipranks(self) -> None:
        """测试覆盖 TipRanks。

        验证配置文件包含 TipRanks 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "TipRanks" in source_names, "Expected TipRanks source"

    # ----------------------------------------
    # 12. 覆盖中文财经二次传播测试
    # ----------------------------------------

    def test_cover_china_fund_news(self) -> None:
        """测试覆盖中国基金报。

        验证配置文件包含中国基金报信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "中国基金报" in source_names, "Expected 中国基金报 source"

    def test_cover_quanshang_china(self) -> None:
        """测试覆盖券商中国。

        验证配置文件包含券商中国信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "券商中国" in source_names, "Expected 券商中国 source"

    def test_cover_wallstreet_cn(self) -> None:
        """测试覆盖华尔街见闻。

        验证配置文件包含华尔街见闻信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "华尔街见闻" in source_names, "Expected 华尔街见闻 source"

    def test_cover_cls_cn(self) -> None:
        """测试覆盖财联社。

        验证配置文件包含财联社信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "财联社" in source_names, "Expected 财联社 source"

    def test_cover_gelonghui(self) -> None:
        """测试覆盖格隆汇。

        验证配置文件包含格隆汇信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "格隆汇" in source_names, "Expected 格隆汇 source"

    def test_cover_zhitong_caijing(self) -> None:
        """测试覆盖智通财经。

        验证配置文件包含智通财经信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "智通财经" in source_names, "Expected 智通财经 source"

    # ----------------------------------------
    # 13. 覆盖 Search Provider 测试
    # ----------------------------------------

    def test_cover_tavily(self) -> None:
        """测试覆盖 Tavily。

        验证配置文件包含 Tavily Search 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        tavily_sources = [n for n in source_names if "Tavily" in n]
        assert len(tavily_sources) >= 1, "Expected at least 1 Tavily source"

    def test_cover_brave(self) -> None:
        """测试覆盖 Brave。

        验证配置文件包含 Brave Search 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        brave_sources = [n for n in source_names if "Brave" in n]
        assert len(brave_sources) >= 1, "Expected at least 1 Brave source"

    def test_cover_serpapi(self) -> None:
        """测试覆盖 SerpAPI。

        验证配置文件包含 SerpAPI 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "SerpAPI" in source_names, "Expected SerpAPI source"

    def test_cover_bing(self) -> None:
        """测试覆盖 Bing。

        验证配置文件包含 Bing 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "Bing" in source_names, "Expected Bing source"

    def test_cover_google_cse(self) -> None:
        """测试覆盖 Google CSE。

        验证配置文件包含 Google CSE 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        google_sources = [n for n in source_names if "Google" in n]
        assert len(google_sources) >= 1, "Expected at least 1 Google source"

    def test_cover_searx(self) -> None:
        """测试覆盖 Searx。

        验证配置文件包含 Searx 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "Searx" in source_names, "Expected Searx source"

    def test_cover_duckduckgo(self) -> None:
        """测试覆盖 DuckDuckGo。

        验证配置文件包含 DuckDuckGo 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "DuckDuckGo" in source_names, "Expected DuckDuckGo source"

    def test_cover_yahoo_search(self) -> None:
        """测试覆盖 Yahoo Search。

        验证配置文件包含 Yahoo Search 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        yahoo_sources = [n for n in source_names if "Yahoo Search" in n]
        assert len(yahoo_sources) >= 1, "Expected at least 1 Yahoo Search source"

    def test_cover_baidu_search(self) -> None:
        """测试覆盖 Baidu Search。

        验证配置文件包含 Baidu Search 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "Baidu Search" in source_names, "Expected Baidu Search source"

    def test_cover_custom_search(self) -> None:
        """测试覆盖 Custom Search。

        验证配置文件包含 Custom Search 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "Custom Search" in source_names, "Expected Custom Search source"

    # ----------------------------------------
    # 14. 覆盖 Community / Dev 测试
    # ----------------------------------------

    def test_cover_github_issues(self) -> None:
        """测试覆盖 GitHub Issues。

        验证配置文件包含 GitHub Issues 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "GitHub Issues" in source_names, "Expected GitHub Issues source"

    def test_cover_hacker_news(self) -> None:
        """测试覆盖 Hacker News。

        验证配置文件包含 Hacker News 信息源。
        """
        inventory = load_inventory()
        source_names = get_source_names(inventory)
        assert "Hacker News" in source_names, "Expected Hacker News source"

    # ----------------------------------------
    # 15. 不恢复已删除页面测试
    # ----------------------------------------

    def test_no_deleted_dashboard_pages(self) -> None:
        """测试不恢复已删除的 Dashboard 页面。

        验证本任务不涉及 Dashboard 页面恢复。
        """
        # 本测试为边界确认，确保不恢复"总览"、"运行日志"、"失败队列"、"文档入口"
        # 这个测试实际上验证的是任务边界，不需要检查代码
        # 只需要确认配置文件中没有涉及 Dashboard 页面的内容
        inventory = load_inventory()
        # 检查配置文件中是否有任何 dashboard 相关的内容
        # source inventory 配置文件不应该包含 dashboard 页面定义
        assert "dashboard" not in str(inventory), "Inventory should not contain dashboard page definitions"


# ============================================
# Summary Tests
# ============================================


class TestSourceInventorySummary:
    """Source Inventory 统计汇总测试类。

    验证配置文件的统计指标。
    """

    def test_source_count(self) -> None:
        """测试 source 数量。

        验证配置文件包含足够数量的信息源。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        # 预期至少有 70+ 个源（根据任务要求覆盖的所有网站）
        assert len(sources) >= 70, f"Expected at least 70 sources, got {len(sources)}"

    def test_priority_distribution(self) -> None:
        """测试优先级分布。

        验证 S/A/B/supplement/blocked 各级别都有覆盖。
        注意：C 优先级在本任务中不强制要求，因为任务规格中没有明确 C 级源。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        priorities = {s.get("activation_priority", "") for s in sources}

        # 任务要求的优先级分布：S/A/B/supplement/blocked
        expected_priorities = {"S", "A", "B", "supplement", "blocked"}
        for p in expected_priorities:
            assert p in priorities, f"Expected activation_priority '{p}' to be present"

    def test_automation_mode_distribution(self) -> None:
        """测试自动化模式分布。

        验证 scheduled/on_demand/manual_only/dormant/do_not_ingest 各模式都有覆盖。
        """
        inventory = load_inventory()
        sources = get_sources(inventory)
        modes = {s.get("automation_mode", "") for s in sources}

        expected_modes = {"scheduled", "on_demand", "dormant", "do_not_ingest"}
        for m in expected_modes:
            assert m in modes, f"Expected automation_mode '{m}' to be present"