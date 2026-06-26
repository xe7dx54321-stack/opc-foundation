"""测试 live smoke runner。

功能说明（小白解读）：
    测试 probe_source、run_live_smoke 等核心函数。
    重点验证：
    - blocked 源不会被访问
    - on_demand 源不会默认跑
    - dormant 源不会默认跑
    - search provider 不会跑搜索
    - RSS 解析器能解析 fixture
    - HTML 解析器能解析 fixture
    - max_candidates_per_source 生效
    - timeout 参数存在
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _make_source(**overrides) -> object:
    """创建一个测试用的 FoundationSource。"""
    from opc_foundation.dashboard.models import FoundationSource

    defaults = {
        "source_id": "test_source",
        "source_name": "Test Source",
        "source_group": "test_group",
        "source_category": "test",
        "access_mode": "public_web",
        "url": "https://example.com",
        "automation_mode": "scheduled",
        "activation_priority": "A",
        "enabled_by_default": True,
    }
    defaults.update(overrides)
    return FoundationSource(**defaults)


class TestBlockedSources:
    """测试 blocked/high_risk 源不会被访问。"""

    def test_blocked_priority_not_visited(self) -> None:
        """测试 activation_priority=blocked 的源不会被访问。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="blocked_test",
            activation_priority="blocked",
            automation_mode="scheduled",
        )
        config = LiveSmokeRunConfig()
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.BLOCKED_BY_POLICY
        assert result.visited is False
        assert result.fetched is False

    def test_do_not_ingest_not_visited(self) -> None:
        """测试 automation_mode=do_not_ingest 的源不会被访问。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="do_not_ingest_test",
            automation_mode="do_not_ingest",
        )
        config = LiveSmokeRunConfig()
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.BLOCKED_BY_POLICY
        assert result.visited is False
        assert result.fetched is False

    def test_blocked_group_not_visited(self) -> None:
        """测试 source_group=blocked_high_risk_sources 的源不会被访问。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="blocked_group_test",
            source_group="blocked_high_risk_sources",
            automation_mode="scheduled",
            activation_priority="A",
        )
        config = LiveSmokeRunConfig()
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.BLOCKED_BY_POLICY
        assert result.visited is False
        assert result.fetched is False


class TestOnDemandSources:
    """测试 on_demand 源不会默认运行。"""

    def test_on_demand_not_run(self) -> None:
        """测试 automation_mode=on_demand 的源不会默认运行。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="on_demand_test",
            automation_mode="on_demand",
            activation_priority="A",
        )
        config = LiveSmokeRunConfig()
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.ON_DEMAND_NOT_RUN
        assert result.visited is False
        assert result.fetched is False

    def test_manual_not_run(self) -> None:
        """测试 automation_mode=manual 的源不会默认运行。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="manual_test",
            automation_mode="manual",
        )
        config = LiveSmokeRunConfig()
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.ON_DEMAND_NOT_RUN
        assert result.visited is False
        assert result.fetched is False

    def test_search_provider_not_run(self) -> None:
        """测试 search_providers 组的源不会默认运行。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="search_provider_test",
            source_group="search_providers",
            access_mode="api",
            automation_mode="scheduled",
            activation_priority="A",
        )
        config = LiveSmokeRunConfig()
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.ON_DEMAND_NOT_RUN
        assert result.visited is False
        assert result.fetched is False


class TestDormantSources:
    """测试 dormant 源不会默认运行。"""

    def test_dormant_not_run(self) -> None:
        """测试 automation_mode=dormant 的源不会默认运行。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="dormant_test",
            automation_mode="dormant",
            activation_priority="C",
        )
        config = LiveSmokeRunConfig()
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.DORMANT_NOT_RUN
        assert result.visited is False
        assert result.fetched is False

    def test_disabled_supplement_not_run(self) -> None:
        """测试 enabled_by_default=False 且 priority=supplement 的源不会运行。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="disabled_supplement_test",
            automation_mode="scheduled",
            activation_priority="supplement",
            enabled_by_default=False,
        )
        config = LiveSmokeRunConfig()
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.DORMANT_NOT_RUN
        assert result.visited is False
        assert result.fetched is False


class TestRssParser:
    """测试 RSS 解析器。"""

    def test_parse_rss_feed(self) -> None:
        """测试能解析 fixture RSS feed。"""
        from opc_foundation.source_inventory.live_smoke import _parse_rss_feed

        fixture_path = REPO_ROOT / "tests" / "fixtures" / "rss_feed.xml"
        if not fixture_path.exists():
            fixture_path = REPO_ROOT / "tests" / "research" / "fixtures" / "sample_feed.xml"

        if fixture_path.exists():
            content = fixture_path.read_text(encoding="utf-8")
            items = _parse_rss_feed(content, max_items=3)
            assert isinstance(items, list)
            assert len(items) >= 1
            assert items[0].title
            assert items[0].url
        else:
            sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Item 1</title>
      <link>https://example.com/1</link>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
      <description>Description 1</description>
    </item>
    <item>
      <title>Item 2</title>
      <link>https://example.com/2</link>
      <description>Description 2</description>
    </item>
  </channel>
</rss>"""
            items = _parse_rss_feed(sample_rss, max_items=3)
            assert len(items) == 2
            assert items[0].title == "Item 1"
            assert items[0].url == "https://example.com/1"

    def test_parse_rss_max_items(self) -> None:
        """测试 max_items 参数生效。"""
        from opc_foundation.source_inventory.live_smoke import _parse_rss_feed

        sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    <item><title>A</title><link>https://a.com</link></item>
    <item><title>B</title><link>https://b.com</link></item>
    <item><title>C</title><link>https://c.com</link></item>
    <item><title>D</title><link>https://d.com</link></item>
    <item><title>E</title><link>https://e.com</link></item>
  </channel>
</rss>"""

        items = _parse_rss_feed(sample_rss, max_items=2)
        assert len(items) == 2

    def test_parse_rss_empty(self) -> None:
        """测试空 feed 返回空列表。"""
        from opc_foundation.source_inventory.live_smoke import _parse_rss_feed

        items = _parse_rss_feed("", max_items=5)
        assert items == []

    def test_parse_rss_malformed(self) -> None:
        """测试坏 XML 返回空列表不报错。"""
        from opc_foundation.source_inventory.live_smoke import _parse_rss_feed

        items = _parse_rss_feed("not valid xml <<<", max_items=5)
        assert items == []


class TestHtmlParser:
    """测试 HTML 解析器。"""

    def test_extract_title(self) -> None:
        """测试从 HTML 提取 title。"""
        from opc_foundation.source_inventory.live_smoke import _html_extract_title

        html = "<html><head><title>Test Page</title></head><body></body></html>"
        title = _html_extract_title(html)
        assert title == "Test Page"

    def test_extract_meta_description(self) -> None:
        """测试从 HTML 提取 meta description。"""
        from opc_foundation.source_inventory.live_smoke import _html_extract_meta_description

        html = '<html><head><meta name="description" content="Test description"></head></html>'
        desc = _html_extract_meta_description(html)
        assert desc == "Test description"

    def test_extract_links(self) -> None:
        """测试从 HTML 提取链接。"""
        from opc_foundation.source_inventory.live_smoke import _html_extract_links

        html = """<html><body>
            <a href="https://example.com/page1">Page 1</a>
            <a href="https://example.com/page2">Page 2</a>
            <a href="#anchor">Skip me</a>
            <a href="javascript:void(0)">Skip me too</a>
        </body></html>"""
        links = _html_extract_links(html, "https://example.com", max_links=10)
        assert len(links) == 2
        assert links[0][0] == "Page 1"
        assert links[0][1] == "https://example.com/page1"

    def test_extract_links_max(self) -> None:
        """测试 max_links 参数生效。"""
        from opc_foundation.source_inventory.live_smoke import _html_extract_links

        html = "".join(
            f'<a href="https://example.com/page{i}">Page {i}</a>' for i in range(10)
        )
        links = _html_extract_links(html, "https://example.com", max_links=3)
        assert len(links) == 3


class TestMaxCandidates:
    """测试 max_candidates_per_source 参数。"""

    def test_max_candidates_per_source_in_config(self) -> None:
        """测试配置里有 max_candidates_per_source 参数。"""
        from opc_foundation.source_inventory.models import LiveSmokeRunConfig

        config = LiveSmokeRunConfig(max_candidates_per_source=3)
        assert config.max_candidates_per_source == 3

    def test_timeout_seconds_in_config(self) -> None:
        """测试配置里有 timeout_seconds 参数。"""
        from opc_foundation.source_inventory.models import LiveSmokeRunConfig

        config = LiveSmokeRunConfig(timeout_seconds=30)
        assert config.timeout_seconds == 30


class TestDryRun:
    """测试 dry-run 模式。"""

    def test_dry_run_does_not_access_network(self) -> None:
        """测试 dry-run 模式下 scheduled 源也不会访问网络。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="dry_run_test",
            access_mode="public_web",
            automation_mode="scheduled",
        )
        config = LiveSmokeRunConfig(dry_run=True)
        result = probe_source(source, config)

        assert result.visited is False
        assert result.fetched is False
        assert "dry-run" in result.notes.lower() or result.status == LiveSmokeStatus.LIVE_OK


class TestApiSource:
    """测试 API 类型的源。"""

    def test_api_source_needs_connector(self) -> None:
        """测试 access_mode=api 的源标记为 needs_connector。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="api_test",
            access_mode="api",
            automation_mode="scheduled",
            activation_priority="A",
        )
        config = LiveSmokeRunConfig()
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.NEEDS_CONNECTOR
        assert result.visited is False


class TestRunLiveSmoke:
    """测试 run_live_smoke 整体流程。"""

    def test_run_live_smoke_dry_run(self) -> None:
        """测试 dry-run 模式下能遍历所有源。"""
        from opc_foundation.dashboard.models import (
            FoundationSource,
            SourceGroup,
            SourceInventory,
        )
        from opc_foundation.source_inventory.live_smoke import run_live_smoke
        from opc_foundation.source_inventory.models import LiveSmokeRunConfig

        groups = [
            SourceGroup(group_id="g1", group_name="Group 1"),
            SourceGroup(group_id="g2", group_name="Group 2"),
        ]
        sources = [
            FoundationSource(
                source_id="s1",
                source_name="Source 1",
                source_group="g1",
                access_mode="public_web",
                url="https://example.com/1",
                automation_mode="scheduled",
                activation_priority="A",
            ),
            FoundationSource(
                source_id="s2",
                source_name="Source 2",
                source_group="g1",
                access_mode="rss",
                url="https://example.com/feed",
                automation_mode="scheduled",
                activation_priority="A",
            ),
            FoundationSource(
                source_id="s3",
                source_name="Blocked Source",
                source_group="g2",
                activation_priority="blocked",
                automation_mode="do_not_ingest",
            ),
        ]
        inventory = SourceInventory(
            version="1.0",
            updated_at="2024-01-01",
            groups=groups,
            sources=sources,
        )

        config = LiveSmokeRunConfig(dry_run=True)
        summary = run_live_smoke(inventory, config)

        assert summary.total_sources == 3
        assert len(summary.groups) == 2
        assert summary.run_started_at
        assert summary.run_finished_at
        assert summary.total_duration_ms >= 0

        blocked_group = next(g for g in summary.groups if g.group_id == "g2")
        assert len(blocked_group.results) == 1
        assert blocked_group.results[0].status.value == "blocked_by_policy"


class TestProxySupport:
    """测试代理支持。"""

    def test_proxy_config_field(self) -> None:
        """测试 LiveSmokeRunConfig 有 proxy_url 和 proxy_mode 字段。"""
        from opc_foundation.source_inventory.models import LiveSmokeRunConfig

        config = LiveSmokeRunConfig(proxy_url="http://127.0.0.1:7890", proxy_mode="cli")
        assert config.proxy_url == "http://127.0.0.1:7890"
        assert config.proxy_mode == "cli"

    def test_run_live_smoke_proxy_enabled_flag(self) -> None:
        """测试 run_live_smoke 把 proxy 信息写入 summary。"""
        from opc_foundation.dashboard.models import (
            FoundationSource,
            SourceGroup,
            SourceInventory,
        )
        from opc_foundation.source_inventory.live_smoke import run_live_smoke
        from opc_foundation.source_inventory.models import LiveSmokeRunConfig

        groups = [SourceGroup(group_id="g1", group_name="Group 1")]
        sources = [
            FoundationSource(
                source_id="s1",
                source_name="Source 1",
                source_group="g1",
                access_mode="public_web",
                url="https://example.com",
                automation_mode="scheduled",
                activation_priority="A",
            ),
        ]
        inventory = SourceInventory(
            version="1.0",
            updated_at="2024-01-01",
            groups=groups,
            sources=sources,
        )

        config = LiveSmokeRunConfig(
            dry_run=True,
            proxy_url="http://127.0.0.1:7890",
            proxy_mode="cli",
        )
        summary = run_live_smoke(inventory, config)

        assert summary.proxy_enabled is True
        assert summary.proxy_mode == "cli"

    def test_run_live_smoke_no_proxy(self) -> None:
        """测试没有代理时 proxy_enabled=false、proxy_mode=none。"""
        from opc_foundation.dashboard.models import (
            FoundationSource,
            SourceGroup,
            SourceInventory,
        )
        from opc_foundation.source_inventory.live_smoke import run_live_smoke
        from opc_foundation.source_inventory.models import LiveSmokeRunConfig

        groups = [SourceGroup(group_id="g1", group_name="Group 1")]
        sources = [
            FoundationSource(
                source_id="s1",
                source_name="Source 1",
                source_group="g1",
                access_mode="public_web",
                url="https://example.com",
                automation_mode="scheduled",
                activation_priority="A",
            ),
        ]
        inventory = SourceInventory(
            version="1.0",
            updated_at="2024-01-01",
            groups=groups,
            sources=sources,
        )

        config = LiveSmokeRunConfig(dry_run=True)
        summary = run_live_smoke(inventory, config)

        assert summary.proxy_enabled is False
        assert summary.proxy_mode == "none"

    def test_blocked_sources_still_not_visited_with_proxy(self) -> None:
        """测试即使开了代理，blocked 源仍然不访问。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="blocked_with_proxy",
            activation_priority="blocked",
            automation_mode="do_not_ingest",
        )
        config = LiveSmokeRunConfig(
            proxy_url="http://127.0.0.1:7890",
            proxy_mode="cli",
        )
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.BLOCKED_BY_POLICY
        assert result.visited is False
        assert result.fetched is False

    def test_on_demand_still_not_run_with_proxy(self) -> None:
        """测试即使开了代理，on_demand/search provider 源仍然不默认运行。"""
        from opc_foundation.source_inventory.live_smoke import probe_source
        from opc_foundation.source_inventory.models import (
            LiveSmokeRunConfig,
            LiveSmokeStatus,
        )

        source = _make_source(
            source_id="search_with_proxy",
            source_group="search_providers",
            access_mode="api",
            automation_mode="on_demand",
            activation_priority="supplement",
            enabled_by_default=False,
        )
        config = LiveSmokeRunConfig(
            proxy_url="http://127.0.0.1:7890",
            proxy_mode="cli",
        )
        result = probe_source(source, config)

        assert result.status == LiveSmokeStatus.ON_DEMAND_NOT_RUN
        assert result.visited is False
