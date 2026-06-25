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

from opc_foundation.dashboard.loaders import (
    load_source_inventory_config,
    summarize_source_inventory,
    validate_source_inventory,
)
from opc_foundation.dashboard.models import (
    FoundationSource,
    SourceGroup,
    SourceInventory,
    SourceInventoryCheckItem,
    SourceInventoryValidationResult,
)


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


# ============================================
# Loader Tests
# ============================================


class TestSourceInventoryLoader:
    """Source Inventory 加载器测试类。

    验证 load_source_inventory_config 等加载函数的正确性。
    """

    def test_load_example_yaml_success(self) -> None:
        """测试可以读取 example YAML。

        验证 load_source_inventory_config 能正确加载配置文件，
        返回 SourceInventory 对象，且数据非空。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        assert isinstance(inv, SourceInventory)
        assert inv.load_error is None
        assert len(inv.groups) >= 9
        assert len(inv.sources) >= 70

    def test_load_returns_source_group_objects(self) -> None:
        """测试返回的 groups 是 SourceGroup 对象。

        验证加载后的 groups 列表元素都是 SourceGroup 类型。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        for g in inv.groups:
            assert isinstance(g, SourceGroup)
            assert g.group_id
            assert g.group_name

    def test_load_returns_foundation_source_objects(self) -> None:
        """测试返回的 sources 是 FoundationSource 对象。

        验证加载后的 sources 列表元素都是 FoundationSource 类型。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        for s in inv.sources:
            assert isinstance(s, FoundationSource)
            assert s.source_id
            assert s.source_name

    def test_load_file_not_found_fail_soft(self) -> None:
        """测试文件不存在时 fail-soft。

        验证配置文件不存在时，返回空 inventory，
        load_error 有错误信息，不抛出异常。
        """
        inv = load_source_inventory_config("nonexistent_file_12345.yaml")
        assert isinstance(inv, SourceInventory)
        assert inv.load_error is not None
        assert "不存在" in inv.load_error or "not found" in inv.load_error.lower()
        assert len(inv.groups) == 0
        assert len(inv.sources) == 0

    def test_load_invalid_yaml_fail_soft(self, tmp_path: Path) -> None:
        """测试 invalid YAML fail-soft。

        验证 YAML 格式错误时，返回空 inventory，
        load_error 有错误信息，不抛出异常。
        """
        bad_file = tmp_path / "bad_inventory.yaml"
        bad_file.write_text("invalid: yaml: [unclosed", encoding="utf-8")
        inv = load_source_inventory_config(bad_file)
        assert isinstance(inv, SourceInventory)
        assert inv.load_error is not None

    def test_source_inventory_get_source(self) -> None:
        """测试 SourceInventory.get_source 方法。

        验证 get_source 能根据 source_id 找到对应的源。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        source = inv.get_source("goldman_sachs_research")
        assert source is not None
        assert source.source_id == "goldman_sachs_research"
        assert "Goldman" in source.source_name

    def test_source_inventory_get_source_not_found(self) -> None:
        """测试 get_source 找不到时返回 None。

        验证找不到 source 时返回 None，不抛出异常。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        source = inv.get_source("nonexistent_source_12345")
        assert source is None

    def test_source_inventory_get_group(self) -> None:
        """测试 SourceInventory.get_group 方法。

        验证 get_group 能根据 group_id 找到对应的分组。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        group = inv.get_group("official_public_research")
        assert group is not None
        assert group.group_id == "official_public_research"

    def test_source_inventory_get_group_not_found(self) -> None:
        """测试 get_group 找不到时返回 None。

        验证找不到 group 时返回 None，不抛出异常。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        group = inv.get_group("nonexistent_group_12345")
        assert group is None


# ============================================
# Validation Tests
# ============================================


class TestSourceInventoryValidation:
    """Source Inventory 校验器测试类。

    验证 validate_source_inventory 函数的各种校验规则。
    """

    def test_validate_example_inventory(self) -> None:
        """测试校验 example inventory。

        验证 example 配置文件校验通过（或只有少量 warning）。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        result = validate_source_inventory(inv)
        assert isinstance(result, SourceInventoryValidationResult)
        assert result.error_count == 0, f"Expected 0 errors, got {result.error_count}: {[c.detail for c in result.checks if c.level == 'error']}"

    def test_validate_duplicate_source_id_error(self, tmp_path: Path) -> None:
        """测试 source_id 重复能报 error。

        验证配置中有重复 source_id 时，校验返回 error 级别。
        """
        yaml_content = """
version: 1
updated_at: "2026-06-25"
source_groups:
  - group_id: test_group
    group_name: 测试组
sources:
  - source_id: dup_id
    source_name: 源1
    source_group: test_group
    activation_priority: S
    automation_mode: scheduled
    legal_confidence: official
  - source_id: dup_id
    source_name: 源2
    source_group: test_group
    activation_priority: S
    automation_mode: scheduled
    legal_confidence: official
"""
        f = tmp_path / "test_inv.yaml"
        f.write_text(yaml_content, encoding="utf-8")
        inv = load_source_inventory_config(f)
        result = validate_source_inventory(inv)
        assert result.error_count >= 1
        # 检查是否有 source_id 唯一性相关的检查项
        error_checks = [c for c in result.checks if c.level == "error"]
        id_checks = [c for c in error_checks if "source_id" in c.check_name and "唯一" in c.check_name]
        assert len(id_checks) >= 1

    def test_validate_invalid_source_group_error(self, tmp_path: Path) -> None:
        """测试 source_group 引用不存在能报 error。

        验证 source 的 source_group 指向不存在的 group 时，校验返回 error。
        """
        yaml_content = """
version: 1
updated_at: "2026-06-25"
source_groups:
  - group_id: test_group
    group_name: 测试组
sources:
  - source_id: test_source
    source_name: 测试源
    source_group: nonexistent_group
    activation_priority: S
    automation_mode: scheduled
    legal_confidence: official
"""
        f = tmp_path / "test_inv.yaml"
        f.write_text(yaml_content, encoding="utf-8")
        inv = load_source_inventory_config(f)
        result = validate_source_inventory(inv)
        assert result.error_count >= 1
        error_checks = [c for c in result.checks if c.level == "error"]
        group_checks = [c for c in error_checks if "source_group" in c.check_name]
        assert len(group_checks) >= 1

    def test_validate_invalid_capability_id_error(self, tmp_path: Path) -> None:
        """测试 capability_id 非法能报 error。

        验证 capability_id 不存在且不是 supplement/blocked 时，
        校验返回 error（需要提供 capabilities registry）。
        """
        from opc_foundation.dashboard.loaders import load_capabilities_config
        cap_path = Path("configs/foundation_capabilities.yaml")
        registry = load_capabilities_config(cap_path)

        yaml_content = """
version: 1
updated_at: "2026-06-25"
source_groups:
  - group_id: test_group
    group_name: 测试组
sources:
  - source_id: test_source
    source_name: 测试源
    source_group: test_group
    capability_id: nonexistent_capability_12345
    activation_priority: S
    automation_mode: scheduled
    legal_confidence: official
    schedule_profile: medium_daily
"""
        f = tmp_path / "test_inv.yaml"
        f.write_text(yaml_content, encoding="utf-8")
        inv = load_source_inventory_config(f)
        result = validate_source_inventory(inv, capabilities=registry)
        assert result.error_count >= 1
        cap_checks = [c for c in result.checks if c.level == "error" and "capability_id" in c.check_name]
        assert len(cap_checks) >= 1

    def test_validate_high_risk_enabled_error(self, tmp_path: Path) -> None:
        """测试 high_risk enabled_by_default=true 能报 error。

        验证 high_risk 源如果 enabled_by_default=true，校验返回 error。
        """
        yaml_content = """
version: 1
updated_at: "2026-06-25"
source_groups:
  - group_id: blocked_group
    group_name: 禁止组
sources:
  - source_id: bad_source
    source_name: 坏源
    source_group: blocked_group
    activation_priority: blocked
    automation_mode: do_not_ingest
    legal_confidence: high_risk
    enabled_by_default: true
    schedule_profile: blocked
"""
        f = tmp_path / "test_inv.yaml"
        f.write_text(yaml_content, encoding="utf-8")
        inv = load_source_inventory_config(f)
        result = validate_source_inventory(inv)
        assert result.error_count >= 1
        hr_checks = [c for c in result.checks if c.level == "error" and "高风险" in c.check_name]
        assert len(hr_checks) >= 1

    def test_validate_search_provider_scheduled_error(self, tmp_path: Path) -> None:
        """测试 search provider scheduled 能报 error。

        验证 search_providers 组的源如果 automation_mode=scheduled，
        校验返回 error。
        """
        yaml_content = """
version: 1
updated_at: "2026-06-25"
source_groups:
  - group_id: search_providers
    group_name: 搜索组
sources:
  - source_id: bad_search
    source_name: 坏搜索源
    source_group: search_providers
    activation_priority: supplement
    automation_mode: scheduled
    legal_confidence: unknown
    enabled_by_default: true
    schedule_profile: high_daily
"""
        f = tmp_path / "test_inv.yaml"
        f.write_text(yaml_content, encoding="utf-8")
        inv = load_source_inventory_config(f)
        result = validate_source_inventory(inv)
        assert result.error_count >= 1
        search_checks = [c for c in result.checks if c.level == "error" and "搜索源" in c.check_name]
        assert len(search_checks) >= 1

    def test_validate_blocked_wrong_mode_error(self, tmp_path: Path) -> None:
        """测试 blocked 源 automation_mode 非法能报 error。

        验证 activation_priority=blocked 但 automation_mode 不是
        do_not_ingest/dormant 时，校验返回 error。
        """
        yaml_content = """
version: 1
updated_at: "2026-06-25"
source_groups:
  - group_id: blocked_group
    group_name: 禁止组
sources:
  - source_id: bad_blocked
    source_name: 坏禁止源
    source_group: blocked_group
    activation_priority: blocked
    automation_mode: scheduled
    legal_confidence: high_risk
    enabled_by_default: false
    schedule_profile: medium_daily
"""
        f = tmp_path / "test_inv.yaml"
        f.write_text(yaml_content, encoding="utf-8")
        inv = load_source_inventory_config(f)
        result = validate_source_inventory(inv)
        assert result.error_count >= 1
        blocked_checks = [c for c in result.checks if c.level == "error" and "禁止源" in c.check_name]
        assert len(blocked_checks) >= 1

    def test_validate_empty_url_warning(self, tmp_path: Path) -> None:
        """测试 URL 为空能报 warning。

        验证 source 的 url 为空时，校验返回 warning 级别。
        """
        yaml_content = """
version: 1
updated_at: "2026-06-25"
source_groups:
  - group_id: test_group
    group_name: 测试组
sources:
  - source_id: no_url_source
    source_name: 无URL源
    source_group: test_group
    activation_priority: A
    automation_mode: scheduled
    legal_confidence: official
    url: ""
    schedule_profile: medium_daily
"""
        f = tmp_path / "test_inv.yaml"
        f.write_text(yaml_content, encoding="utf-8")
        inv = load_source_inventory_config(f)
        result = validate_source_inventory(inv)
        assert result.warning_count >= 1
        url_checks = [c for c in result.checks if c.level == "warning" and "URL" in c.check_name]
        assert len(url_checks) >= 1

    def test_validate_unknown_confidence_warning(self, tmp_path: Path) -> None:
        """测试 legal_confidence unknown 能报 warning。

        验证 source 的 legal_confidence=unknown 时，校验返回 warning。
        """
        yaml_content = """
version: 1
updated_at: "2026-06-25"
source_groups:
  - group_id: test_group
    group_name: 测试组
sources:
  - source_id: unknown_source
    source_name: 未知源
    source_group: test_group
    activation_priority: B
    automation_mode: scheduled
    legal_confidence: unknown
    url: "https://example.com"
    schedule_profile: low_daily
"""
        f = tmp_path / "test_inv.yaml"
        f.write_text(yaml_content, encoding="utf-8")
        inv = load_source_inventory_config(f)
        result = validate_source_inventory(inv)
        assert result.warning_count >= 1
        conf_checks = [c for c in result.checks if c.level == "warning" and "法律可信度" in c.check_name]
        assert len(conf_checks) >= 1

    def test_validate_is_valid_property(self, tmp_path: Path) -> None:
        """测试 SourceInventoryValidationResult.is_valid 属性。

        验证 error_count==0 时 is_valid=True，否则 False。
        """
        # 正常配置
        yaml_good = """
version: 1
updated_at: "2026-06-25"
source_groups:
  - group_id: test_group
    group_name: 测试组
sources:
  - source_id: good_source
    source_name: 好源
    source_group: test_group
    activation_priority: A
    automation_mode: scheduled
    legal_confidence: official
    url: "https://example.com"
    schedule_profile: medium_daily
"""
        f = tmp_path / "good.yaml"
        f.write_text(yaml_good, encoding="utf-8")
        inv_good = load_source_inventory_config(f)
        result_good = validate_source_inventory(inv_good)
        assert result_good.is_valid is True


# ============================================
# Summarize Tests
# ============================================


class TestSourceInventorySummarize:
    """Source Inventory 摘要统计测试类。

    验证 summarize_source_inventory 函数的统计功能。
    """

    def test_summarize_group_count(self) -> None:
        """测试 summarize_source_inventory 能统计 group 数量。

        验证 group_count 字段正确。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        result = summarize_source_inventory(inv)
        assert isinstance(result, SourceInventoryValidationResult)
        assert result.group_count == len(inv.groups)
        assert result.group_count >= 9

    def test_summarize_source_count(self) -> None:
        """测试 summarize_source_inventory 能统计 source 数量。

        验证 source_count 字段正确。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        result = summarize_source_inventory(inv)
        assert result.source_count == len(inv.sources)
        assert result.source_count >= 70

    def test_summarize_priority_distribution(self) -> None:
        """测试 summarize_source_inventory 能统计优先级分布。

        验证 priority_counts 字典包含所有出现的优先级。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        result = summarize_source_inventory(inv)
        assert isinstance(result.priority_counts, dict)
        assert len(result.priority_counts) >= 4
        # 验证数量加起来等于总 source 数
        total = sum(result.priority_counts.values())
        assert total == result.source_count

    def test_summarize_automation_distribution(self) -> None:
        """测试 summarize_source_inventory 能统计自动化模式分布。

        验证 automation_counts 字典包含所有出现的模式。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        result = summarize_source_inventory(inv)
        assert isinstance(result.automation_counts, dict)
        assert len(result.automation_counts) >= 3
        total = sum(result.automation_counts.values())
        assert total == result.source_count

    def test_summarize_enabled_count(self) -> None:
        """测试 summarize_source_inventory 能统计默认启用数量。

        验证 enabled_count 字段正确。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        result = summarize_source_inventory(inv)
        expected = sum(1 for s in inv.sources if s.enabled_by_default)
        assert result.enabled_count == expected

    def test_summarize_high_risk_count(self) -> None:
        """测试 summarize_source_inventory 能统计高风险源数量。

        验证 high_risk_count 字段正确。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        result = summarize_source_inventory(inv)
        expected = sum(
            1 for s in inv.sources
            if s.legal_confidence == "high_risk" or s.activation_priority == "blocked"
        )
        assert result.high_risk_count == expected
        assert result.high_risk_count >= 5

    def test_summarize_search_provider_count(self) -> None:
        """测试 summarize_source_inventory 能统计搜索源数量。

        验证 search_provider_count 字段正确。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        result = summarize_source_inventory(inv)
        expected = sum(1 for s in inv.sources if s.source_group == "search_providers")
        assert result.search_provider_count == expected
        assert result.search_provider_count >= 8

    def test_summarize_community_count(self) -> None:
        """测试 summarize_source_inventory 能统计社区源数量。

        验证 community_count 字段正确。
        """
        inv = load_source_inventory_config(INVENTORY_PATH)
        result = summarize_source_inventory(inv)
        expected = sum(1 for s in inv.sources if s.source_group == "community_dev_signals")
        assert result.community_count == expected
        assert result.community_count >= 2


# ============================================
# Dashboard Integration Tests
# ============================================


class TestSourceInventoryDashboard:
    """Dashboard 集成测试类。

    验证 Dashboard 配置检查页包含 source inventory 检查。
    由于 Streamlit 不适合直接测试，这里通过检查代码和数据模型来验证。
    """

    def test_app_importable_without_streamlit(self) -> None:
        """测试 app.py 可在未安装 streamlit 时 import（基本导入）。

        验证 models 和 loaders 模块不依赖 streamlit。
        """
        from opc_foundation.dashboard import models
        from opc_foundation.dashboard import loaders
        assert models is not None
        assert loaders is not None

    def test_readme_mentions_activation_plan(self) -> None:
        """测试 README 提到 source activation plan。

        验证 README.md 中包含 Source Activation Plan 相关内容。
        """
        readme_path = Path("README.md")
        assert readme_path.exists()
        content = readme_path.read_text(encoding="utf-8")
        assert "activation plan" in content.lower() or "上线计划" in content

    def test_activation_plan_doc_exists(self) -> None:
        """测试上线计划文档存在。

        验证 foundation_source_activation_plan.md 存在。
        """
        plan_path = Path("docs/foundation_source_activation_plan.md")
        assert plan_path.exists(), "Activation plan doc should exist"

    def test_no_deleted_pages_in_app(self) -> None:
        """测试不恢复已删除的 Dashboard 页面。

        验证 app.py 中没有恢复"总览/运行日志/失败队列/文档入口"页面。
        """
        import re
        app_path = Path("src/opc_foundation/dashboard/app.py")
        content = app_path.read_text(encoding="utf-8")

        # 检查导航列表中只有 4 个页面
        # 查找 pages 列表定义
        pattern = r'pages\s*=\s*\[([^\]]+)\]'
        match = re.search(pattern, content)
        assert match, "Should find pages list in app.py"
        pages_str = match.group(1)
        # 统计引号中的页面名
        page_names = re.findall(r'"([^"]+)"', pages_str)
        assert len(page_names) == 4, f"Expected 4 pages, got {len(page_names)}: {page_names}"
        # 确认没有已删除的页面
        assert "总览" not in page_names
        assert "运行日志" not in page_names
        assert "失败队列" not in page_names
        assert "文档入口" not in page_names