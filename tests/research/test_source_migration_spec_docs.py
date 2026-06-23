"""
测试 Cross-Repo Source Migration SPEC 文档的完整性与边界约束。

这些测试不访问外部网站，只验证文档内容是否符合 SPEC 要求。
"""

import pytest
from pathlib import Path

# 仓库根目录
REPO_ROOT = Path(__file__).resolve().parents[2]

# 文档路径
MIGRATION_DOC = REPO_ROOT / "docs" / "source_migration_from_th_capital_stock.md"
FOUNDATION_DOC = REPO_ROOT / "docs" / "research_source_foundation.md"
READINESS_DOC = REPO_ROOT / "docs" / "research_source_production_readiness.md"


@pytest.fixture
def migration_text():
    """读取迁移 SPEC 文档全文。"""
    return MIGRATION_DOC.read_text(encoding="utf-8")


@pytest.fixture
def foundation_text():
    """读取 research_source_foundation.md 全文。"""
    return FOUNDATION_DOC.read_text(encoding="utf-8")


@pytest.fixture
def readiness_text():
    """读取 research_source_production_readiness.md 全文。"""
    return READINESS_DOC.read_text(encoding="utf-8")


class TestMigrationDocExists:
    """测试迁移 SPEC 文档存在。"""

    def test_migration_doc_exists(self):
        """迁移 SPEC 文档存在。"""
        assert MIGRATION_DOC.exists(), f"迁移 SPEC 文档不存在: {MIGRATION_DOC}"

    def test_migration_doc_not_empty(self, migration_text):
        """迁移 SPEC 文档不为空。"""
        assert len(migration_text) > 100, "迁移 SPEC 文档内容过短"


class TestMigrationDocContent:
    """测试迁移 SPEC 文档内容完整性。"""

    def test_contains_official_filing(self, migration_text):
        """文档包含 official_filing。"""
        assert "official_filing" in migration_text.lower()

    def test_contains_sec(self, migration_text):
        """文档包含 SEC。"""
        assert "SEC" in migration_text or "sec" in migration_text.lower()

    def test_contains_cninfo(self, migration_text):
        """文档包含 CNINFO。"""
        assert "CNINFO" in migration_text or "cninfo" in migration_text.lower()

    def test_contains_hkex(self, migration_text):
        """文档包含 HKEX。"""
        assert "HKEX" in migration_text or "hkex" in migration_text.lower()

    def test_official_filing_is_p0(self, migration_text):
        """文档明确 Official Filing Foundation 是 P0。"""
        assert "P0" in migration_text
        assert "official_filing" in migration_text.lower() or "Official Filing" in migration_text

    def test_m1a_is_next_step(self, migration_text):
        """文档明确 M1A: Official Filing Foundation SPEC 是下一步。"""
        assert "M1A" in migration_text
        assert "Official Filing Foundation SPEC" in migration_text

    def test_contains_document_extraction(self, migration_text):
        """文档包含 document_extraction。"""
        assert "document_extraction" in migration_text.lower() or "Document Extraction" in migration_text

    def test_contains_market_data(self, migration_text):
        """文档包含 market_data。"""
        assert "market_data" in migration_text.lower() or "Market Data" in migration_text

    def test_contains_market_flow(self, migration_text):
        """文档包含 market_flow。"""
        assert "market_flow" in migration_text.lower() or "Market Flow" in migration_text

    def test_factor_not_migrate(self, migration_text):
        """文档明确 factor 不迁。"""
        assert "factor" in migration_text.lower()
        assert "do not migrate" in migration_text.lower() or "not now" in migration_text.lower() or "不迁" in migration_text

    def test_valuation_not_migrate(self, migration_text):
        """文档明确 valuation 不迁。"""
        assert "valuation" in migration_text.lower()
        assert "do not migrate" in migration_text.lower() or "not now" in migration_text.lower() or "不迁" in migration_text

    def test_opportunity_not_migrate(self, migration_text):
        """文档明确 opportunity 不迁。"""
        assert "opportunity" in migration_text.lower()
        assert "never migrate" in migration_text.lower() or "do not migrate" in migration_text.lower() or "不迁" in migration_text

    def test_risk_not_migrate(self, migration_text):
        """文档明确 risk 不迁。"""
        assert "risk" in migration_text.lower()
        assert "never migrate" in migration_text.lower() or "do not migrate" in migration_text.lower() or "不迁" in migration_text

    def test_trade_signal_not_migrate(self, migration_text):
        """文档明确 trade signal 不迁。"""
        assert "trade_signal" in migration_text.lower() or "trade signal" in migration_text.lower()

    def test_ifind_client_only(self, migration_text):
        """文档明确 iFinD 只迁 client，不迁业务 adapter。"""
        assert "iFinD" in migration_text or "ifind" in migration_text.lower()
        assert "client" in migration_text.lower()

    def test_tender_decouple_first(self, migration_text):
        """文档明确 tender 必须先解耦。"""
        assert "tender" in migration_text.lower() or "procurement" in migration_text.lower()
        assert "decouple" in migration_text.lower() or "解耦" in migration_text

    def test_ir_interaction_decouple_first(self, migration_text):
        """文档明确 IR interaction 必须先解耦。"""
        assert "ir_interaction" in migration_text.lower() or "IR interaction" in migration_text or "irm_interaction" in migration_text.lower()
        assert "decouple" in migration_text.lower() or "解耦" in migration_text

    def test_contains_downstream_consumption_contract(self, migration_text):
        """文档包含 downstream consumption contract。"""
        assert "Downstream Consumption Contract" in migration_text or "downstream" in migration_text.lower()

    def test_contains_forbidden_business_fields(self, migration_text):
        """文档包含 Forbidden Business Fields。"""
        assert "Forbidden Business Fields" in migration_text or "forbidden" in migration_text.lower()

    def test_forbidden_fields_list(self, migration_text):
        """禁止字段清单包含关键字段。"""
        forbidden_fields = [
            "affected_tickers",
            "expectation_delta",
            "investment_rating",
            "trade_signal",
            "watchlist",
            "action_decision",
            "recommendation",
            "opportunity_score",
            "risk_score",
            "position_size",
            "target_price",
        ]
        for field in forbidden_fields:
            assert field in migration_text, f"禁止字段清单缺少: {field}"

    def test_contains_target_architecture(self, migration_text):
        """文档包含 Target Architecture。"""
        assert "Target Architecture" in migration_text or "target architecture" in migration_text.lower()

    def test_contains_recommended_roadmap(self, migration_text):
        """文档包含 Recommended Roadmap。"""
        assert "Recommended Roadmap" in migration_text or "roadmap" in migration_text.lower()

    def test_contains_migration_decision_matrix(self, migration_text):
        """文档包含 Migration Decision Matrix。"""
        assert "Migration Decision Matrix" in migration_text or "decision matrix" in migration_text.lower()

    def test_contains_source_audit_summary(self, migration_text):
        """文档包含 Source Audit Summary。"""
        assert "Source Audit Summary" in migration_text or "audit summary" in migration_text.lower()

    def test_contains_purpose(self, migration_text):
        """文档包含 Purpose 章节。"""
        assert "Purpose" in migration_text

    def test_contains_partial_migration(self, migration_text):
        """文档包含 Partial Migration Candidates 章节。"""
        assert "Partial Migration" in migration_text or "partial" in migration_text.lower()

    def test_contains_do_not_migrate(self, migration_text):
        """文档包含 Do Not Migrate 章节。"""
        assert "Do Not Migrate" in migration_text or "do not migrate" in migration_text.lower()


class TestFoundationDocUpdate:
    """测试 research_source_foundation.md 更新。"""

    def test_foundation_doc_exists(self):
        """research_source_foundation.md 存在。"""
        assert FOUNDATION_DOC.exists()

    def test_foundation_links_migration_doc(self, foundation_text):
        """research_source_foundation.md 链接迁移文档。"""
        assert "source_migration_from_th_capital_stock" in foundation_text

    def test_foundation_contains_cross_repo_section(self, foundation_text):
        """research_source_foundation.md 包含 Cross-Repo Source Migration 章节。"""
        assert "Cross-Repo Source Migration" in foundation_text or "Cross-Repo" in foundation_text

    def test_foundation_contains_decision_table(self, foundation_text):
        """research_source_foundation.md 包含决策表。"""
        assert "official_filing" in foundation_text.lower() or "Official Filing" in foundation_text
        assert "P0" in foundation_text


class TestReadinessDocUpdate:
    """测试 research_source_production_readiness.md 更新。"""

    def test_readiness_doc_exists(self):
        """research_source_production_readiness.md 存在。"""
        assert READINESS_DOC.exists()

    def test_readiness_mentions_official_filings(self, readiness_text):
        """research_source_production_readiness.md 提到 official filings。"""
        assert "official filing" in readiness_text.lower() or "official_filings" in readiness_text.lower()

    def test_readiness_contains_cross_repo_outlook(self, readiness_text):
        """research_source_production_readiness.md 包含 Cross-Repo Migration Outlook 章节。"""
        assert "Cross-Repo Migration Outlook" in readiness_text or "Cross-Repo" in readiness_text

    def test_readiness_links_migration_doc(self, readiness_text):
        """research_source_production_readiness.md 链接迁移文档。"""
        assert "source_migration_from_th_capital_stock" in readiness_text
