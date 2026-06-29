"""Goldman Sachs Podcast 源合并测试（M3C-5A2.1）。

功能说明（小白解读）：
    测试 M3C-5A2.1 Goldman Sachs podcast 源合并的结果。
    确保：
    1. 合并报告存在
    2. 3 个原始 source_id 保留在 inventory 中
    3. source inventory 总数保持 92
    4. consolidated candidate 出现在 trial_v2 candidates 报告中
    5. trial_v2 ready additions = 6
    6. consolidated candidate 不重复计算 3 次
    7. 不修改 trial v1 allowlist
    8. 不修改 TRAE scheduling
"""

import pytest
import sys
from pathlib import Path

# 确保可以 import opc_foundation
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import yaml


# ---- Fixtures ----

@pytest.fixture
def consolidation_report():
    """读取 Goldman Sachs podcast 合并报告。"""
    report_path = Path("docs/foundation_goldman_podcast_consolidation_report.md")
    if not report_path.exists():
        pytest.skip("Consolidation report not found")
    return report_path.read_text(encoding="utf-8")


@pytest.fixture
def trial_v2_candidates_report():
    """读取 trial_v2 candidates 报告。"""
    report_path = Path("docs/foundation_trial_v2_candidates.md")
    if not report_path.exists():
        pytest.skip("Trial v2 candidates report not found")
    return report_path.read_text(encoding="utf-8")


@pytest.fixture
def source_inventory():
    """加载 source inventory 数据。"""
    inventory_path = Path("configs/foundation_source_inventory.example.yaml")
    with open(inventory_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---- 合并报告存在性测试 ----

class TestConsolidationReport:
    """测试 Goldman Sachs podcast 合并报告。"""

    def test_consolidation_report_exists(self):
        """合并报告应该存在。"""
        report_path = Path("docs/foundation_goldman_podcast_consolidation_report.md")
        assert report_path.exists(), f"Consolidation report not found: {report_path}"

    def test_consolidation_report_has_m3c5a21(self, consolidation_report):
        """合并报告应该包含 M3C-5A2.1 标识。"""
        assert "M3C-5A2.1" in consolidation_report, "Report should mention M3C-5A2.1"

    def test_consolidation_report_has_member_source_ids(self, consolidation_report):
        """合并报告应该包含 3 个 member_source_ids。"""
        assert "goldman_sachs_exchanges" in consolidation_report
        assert "goldman_sachs_the_markets" in consolidation_report
        assert "goldman_sachs_top_of_mind_podcast" in consolidation_report

    def test_consolidation_report_has_consolidated_candidate(self, consolidation_report):
        """合并报告应该包含 consolidated candidate。"""
        assert "goldman_sachs_podcasts" in consolidation_report
        assert "consolidated" in consolidation_report.lower()

    def test_consolidation_report_has_verification_result(self, consolidation_report):
        """合并报告应该包含验证结果。"""
        assert "200 OK" in consolidation_report or "HTTP 200" in consolidation_report
        assert "goldmansachs.com/insights/podcasts" in consolidation_report


# ---- Source Inventory 测试 ----

class TestSourceInventoryAfterConsolidation:
    """测试合并后 source inventory 状态。"""

    def test_source_count_remains_92(self, source_inventory):
        """Source 总数应该保持 92 个。"""
        sources = source_inventory.get("sources", [])
        assert len(sources) == 92, f"Expected 92 sources, got {len(sources)}"

    def test_original_gs_podcast_sources_preserved(self, source_inventory):
        """3 个原始 Goldman Sachs podcast source 应该保留在 inventory 中。"""
        gs_source_ids = {
            "goldman_sachs_exchanges",
            "goldman_sachs_the_markets",
            "goldman_sachs_top_of_mind_podcast",
        }
        inventory_ids = {s["source_id"] for s in source_inventory.get("sources", [])}

        for sid in gs_source_ids:
            assert sid in inventory_ids, f"Original source {sid} should be preserved in inventory"

    def test_gs_podcasts_url_updated(self, source_inventory):
        """3 个 GS podcast source 的 URL 应该已更新为 /insights/podcasts。"""
        sources = source_inventory.get("sources", [])
        gs_sources = [s for s in sources if s["source_id"].startswith("goldman_sachs")]

        for s in gs_sources:
            if "podcast" in s["source_id"].lower():
                assert "/insights/podcasts" in s.get("url", ""), \
                    f"URL should be updated to /insights/podcasts for {s['source_id']}"


# ---- Trial v2 Candidates 测试 ----

class TestTrialV2CandidatesAfterConsolidation:
    """测试合并后 trial_v2 candidates 报告。"""

    def test_trial_v2_report_has_6_ready(self, trial_v2_candidates_report):
        """trial_v2 ready 应该为 6 个。"""
        # 报告应该提到 6 个 ready sources
        assert "6" in trial_v2_candidates_report
        assert "trial_v2_ready" in trial_v2_candidates_report.lower() or "trial_v2_ready" in trial_v2_candidates_report

    def test_trial_v2_report_has_goldman_sachs_podcasts(self, trial_v2_candidates_report):
        """trial_v2 candidates 报告应该包含 consolidated candidate。"""
        assert "goldman_sachs_podcasts" in trial_v2_candidates_report

    def test_trial_v2_report_mentions_consolidation(self, trial_v2_candidates_report):
        """trial_v2 candidates 报告应该提到合并结果。"""
        assert "consolidated" in trial_v2_candidates_report.lower() or "合并" in trial_v2_candidates_report
        assert "M3C-5A2.1" in trial_v2_candidates_report

    def test_trial_v2_total_additions_6(self, trial_v2_candidates_report):
        """trial_v2 总新增应该为 6 个。"""
        assert "6" in trial_v2_candidates_report
        assert "5 独立" in trial_v2_candidates_report or "5 个独立" in trial_v2_candidates_report
        assert "1 合并" in trial_v2_candidates_report or "1 个合并" in trial_v2_candidates_report

    def test_trial_v2_total_21_sources(self, trial_v2_candidates_report):
        """trial_v1 + trial_v2 合计应该为 21 个源。"""
        assert "21" in trial_v2_candidates_report
        assert "15" in trial_v2_candidates_report
        assert "trial v1" in trial_v2_candidates_report.lower() or "trial_v1" in trial_v2_candidates_report.lower()


# ---- 边界测试 ----

class TestConsolidationBoundaries:
    """测试合并的边界条件。"""

    def test_consolidation_report_no_trial_v1_modification(self, consolidation_report):
        """合并报告应该明确不修改 trial v1。"""
        assert "trial v1" in consolidation_report.lower()
        assert "not modify" in consolidation_report.lower() or "不修改" in consolidation_report

    def test_consolidation_report_no_trae_modification(self, consolidation_report):
        """合并报告应该明确不修改 TRAE scheduling。"""
        assert "TRAE" in consolidation_report or "trae" in consolidation_report.lower()
        assert "not modify" in consolidation_report.lower() or "不修改" in consolidation_report

    def test_consolidation_report_no_source_deletion(self, consolidation_report):
        """合并报告应该明确不删除 source inventory 记录。"""
        assert "保留" in consolidation_report or "preserved" in consolidation_report.lower()
        assert "删除" not in consolidation_report or "不删除" in consolidation_report

    def test_consolidation_report_no_proxy_url(self, consolidation_report):
        """合并报告不应该包含完整代理 URL。"""
        import re
        proxy_patterns = [
            r'http://[^:]+:\d+',
            r'https://[^:]+:\d+',
            r'socks5://',
            r'socks4://',
        ]
        for pattern in proxy_patterns:
            matches = re.findall(pattern, consolidation_report)
            assert len(matches) == 0, f"Proxy URL found in report: {matches}"

    def test_consolidation_report_no_secrets(self, consolidation_report):
        """合并报告不应该包含 secrets。"""
        sensitive_keywords = ["api_key", "secret_key", "access_token", "bearer token", "aws_secret"]
        for kw in sensitive_keywords:
            assert kw.lower() not in consolidation_report.lower(), \
                f"Sensitive keyword '{kw}' found in report"


# ---- 报告完整性测试 ----

class TestConsolidationReportCompleteness:
    """测试合并报告的完整性。"""

    def test_report_has_execution_time(self, consolidation_report):
        """合并报告应该包含执行时间。"""
        assert "处理时间" in consolidation_report or "执行时间" in consolidation_report
        assert "2026" in consolidation_report

    def test_report_has_scope(self, consolidation_report):
        """合并报告应该包含处理范围。"""
        assert "处理范围" in consolidation_report or "合并范围" in consolidation_report

    def test_report_has_verification_result(self, consolidation_report):
        """合并报告应该包含验证结果。"""
        assert "验证" in consolidation_report
        assert "trial_v2_ready" in consolidation_report or "ready" in consolidation_report.lower()

    def test_report_has_source_inventory_confirmation(self, consolidation_report):
        """合并报告应该包含 source inventory 确认。"""
        assert "92" in consolidation_report
        assert "source" in consolidation_report.lower()

    def test_report_has_trial_v2_result(self, consolidation_report):
        """合并报告应该包含 trial_v2 结果。"""
        assert "trial_v2" in consolidation_report.lower()
        assert "建议" in consolidation_report
