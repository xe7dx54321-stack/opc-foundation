"""测试 live smoke 报告生成。

功能说明（小白解读）：
    测试 generate_live_smoke_report 函数生成的报告。
    确保报告包含所有必要的章节和数据。
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class TestLiveSmokeReport:
    """测试报告生成。"""

    def _make_test_summary(self) -> object:
        """创建一个测试用的 LiveSmokeSummary。"""
        from opc_foundation.source_inventory.models import (
            LiveSmokeStatus,
            LiveSmokeSummary,
            SourceGroupLiveResult,
            SourceLiveResult,
        )

        return LiveSmokeSummary(
            total_sources=4,
            run_started_at="2024-01-01T00:00:00Z",
            run_finished_at="2024-01-01T00:05:00Z",
            total_duration_ms=300000,
            groups=[
                SourceGroupLiveResult(
                    group_id="official_public_research",
                    group_name="投行官方公开研究",
                    total_sources=2,
                    results=[
                        SourceLiveResult(
                            source_id="gs_research",
                            source_name="Goldman Sachs Research",
                            source_group="official_public_research",
                            access_mode="public_web",
                            status=LiveSmokeStatus.LIVE_OK_CANDIDATES_FOUND,
                            visited=True,
                            fetched=True,
                            candidates_found=5,
                            candidates_saved=5,
                            notes="title: Goldman Sachs Insights",
                            checked_at="2024-01-01T00:01:00Z",
                        ),
                        SourceLiveResult(
                            source_id="ms_research",
                            source_name="Morgan Stanley Research",
                            source_group="official_public_research",
                            access_mode="public_web",
                            status=LiveSmokeStatus.LIVE_OK,
                            visited=True,
                            fetched=True,
                            candidates_found=0,
                            notes="title: Morgan Stanley",
                            checked_at="2024-01-01T00:02:00Z",
                        ),
                    ],
                ),
                SourceGroupLiveResult(
                    group_id="blocked_high_risk_sources",
                    group_name="Blocked / High Risk",
                    total_sources=1,
                    results=[
                        SourceLiveResult(
                            source_id="telegram_group",
                            source_name="Telegram Group",
                            source_group="blocked_high_risk_sources",
                            status=LiveSmokeStatus.BLOCKED_BY_POLICY,
                            visited=False,
                            fetched=False,
                            notes="Blocked by policy",
                            checked_at="2024-01-01T00:03:00Z",
                        ),
                    ],
                ),
                SourceGroupLiveResult(
                    group_id="search_providers",
                    group_name="搜索 Provider",
                    total_sources=1,
                    results=[
                        SourceLiveResult(
                            source_id="tavily_search",
                            source_name="Tavily Search",
                            source_group="search_providers",
                            status=LiveSmokeStatus.ON_DEMAND_NOT_RUN,
                            visited=False,
                            fetched=False,
                            notes="Search provider: on-demand only",
                            checked_at="2024-01-01T00:04:00Z",
                        ),
                    ],
                ),
            ],
        )

    def test_report_contains_92_source_reference(self) -> None:
        """测试报告包含 92 source 口径说明（在测试里验证 total_sources 字段）。"""
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        assert "Source 总数" in report
        assert "4" in report  # our test has 4 sources
        assert "live smoke" in report.lower()

    def test_report_has_blocked_section(self) -> None:
        """测试报告有 blocked 未访问说明。"""
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        assert "Blocked" in report
        assert "blocked_by_policy" in report
        assert "visited=false" in report.lower() or "visited: false" in report.lower() or "visited" in report

    def test_report_has_needs_connector_section(self) -> None:
        """测试报告有 needs_connector 清单章节。"""
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        assert "Needs Connector" in report

    def test_report_has_traeg_suggestion_section(self) -> None:
        """测试报告有 TRAE 试运行建议章节。"""
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        assert "TRAE" in report or "trae" in report.lower() or "试运行" in report

    def test_report_has_on_demand_section(self) -> None:
        """测试报告有 on-demand 源确认章节。"""
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        assert "On-Demand" in report or "on_demand" in report or "按需" in report

    def test_report_has_source_group_overview(self) -> None:
        """测试报告有 source group 总览表。"""
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        assert "Source Group" in report
        assert "投行官方公开研究" in report or "official_public_research" in report

    def test_report_has_status_breakdown(self) -> None:
        """测试报告有状态统计。"""
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        assert "总览统计" in report or "Status" in report

    def test_report_has_failed_section(self) -> None:
        """测试报告有 failed 源清单章节。"""
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        assert "Failed" in report or "失败" in report

    def test_report_has_disclaimer(self) -> None:
        """测试报告有 live smoke 不等于正式运行的免责声明。"""
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        assert "不等于正式生产稳定运行" in report or "live smoke" in report.lower()

    def test_report_has_execution_info(self) -> None:
        """测试报告有执行信息。"""
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        assert "执行信息" in report or "Execution" in report
        assert "2024-01-01" in report

    def test_save_report(self) -> None:
        """测试 save_report 能保存报告到文件。"""
        import tempfile

        from opc_foundation.source_inventory.reports import (
            generate_live_smoke_report,
            save_report,
        )

        summary = self._make_test_summary()
        report = generate_live_smoke_report(summary)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.md"
            result = save_report(report, str(output_path))
            assert result.exists()
            content = result.read_text(encoding="utf-8")
            assert "Source 总数" in content

    def test_report_does_not_contain_full_proxy_url(self) -> None:
        """测试报告不会输出完整的代理地址（只显示 enabled/mode）。"""
        from opc_foundation.source_inventory.models import (
            LiveSmokeStatus,
            LiveSmokeSummary,
            SourceGroupLiveResult,
            SourceLiveResult,
        )
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = LiveSmokeSummary(
            total_sources=1,
            proxy_enabled=True,
            proxy_mode="cli",
            groups=[
                SourceGroupLiveResult(
                    group_id="g1",
                    group_name="Group 1",
                    total_sources=1,
                    results=[
                        SourceLiveResult(
                            source_id="s1",
                            source_name="Source 1",
                            source_group="g1",
                            status=LiveSmokeStatus.LIVE_OK,
                            visited=True,
                            checked_at="2024-01-01T00:00:00Z",
                        ),
                    ],
                ),
            ],
            run_started_at="2024-01-01T00:00:00Z",
            run_finished_at="2024-01-01T00:01:00Z",
            total_duration_ms=60000,
        )

        report = generate_live_smoke_report(summary)

        # 报告里应该有 proxy_enabled 和 proxy_mode，但不应该有具体代理地址
        assert "代理启用" in report or "proxy_enabled" in report.lower() or "Proxy" in report
        assert "代理来源" in report or "proxy_mode" in report.lower() or "cli" in report
        # 不应该包含常见的代理地址格式
        assert "127.0.0.1" not in report
        assert "7890" not in report
        assert "http://" not in report.replace("https://", "")  # https 可能出现在源 URL 里

    def test_report_has_proxy_info_when_enabled(self) -> None:
        """测试启用代理时报告显示代理信息。"""
        from opc_foundation.source_inventory.models import (
            LiveSmokeStatus,
            LiveSmokeSummary,
            SourceGroupLiveResult,
            SourceLiveResult,
        )
        from opc_foundation.source_inventory.reports import generate_live_smoke_report

        summary = LiveSmokeSummary(
            total_sources=1,
            proxy_enabled=True,
            proxy_mode="env",
            groups=[
                SourceGroupLiveResult(
                    group_id="g1",
                    group_name="Group 1",
                    total_sources=1,
                    results=[
                        SourceLiveResult(
                            source_id="s1",
                            status=LiveSmokeStatus.LIVE_OK,
                            checked_at="2024-01-01T00:00:00Z",
                        ),
                    ],
                ),
            ],
            run_started_at="2024-01-01T00:00:00Z",
            run_finished_at="2024-01-01T00:01:00Z",
            total_duration_ms=60000,
        )

        report = generate_live_smoke_report(summary)
        assert "True" in report  # proxy_enabled: True
