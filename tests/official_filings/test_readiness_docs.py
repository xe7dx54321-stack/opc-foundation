"""测试 Official Filing Readiness 文档的存在性和内容。

本测试验证：
1. Live Smoke Registry 文档存在且包含必要内容
2. Production Readiness Summary 文档存在且包含必要内容
3. 现有文档已更新链接和状态说明
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _docs_dir() -> Path:
    """返回 docs 目录路径。
    
    从 tests/official_filings/ 向上 3 级到达项目根目录。
    """
    return Path(__file__).parent.parent.parent / "docs"


# ============================================================================
# Live Smoke Registry Tests
# ============================================================================

class TestLiveSmokeRegistry:
    """测试 Live Smoke Registry 文档。"""

    def test_registry_doc_exists(self):
        """Live Smoke Registry 文档必须存在。"""
        path = _docs_dir() / "official_filing_live_smoke_registry.md"
        assert path.exists(), f"缺少 Live Smoke Registry 文档: {path}"

    def test_registry_contains_sec_edgar(self):
        """Registry 必须包含 SEC EDGAR 说明。"""
        path = _docs_dir() / "official_filing_live_smoke_registry.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "SEC EDGAR" in content, "Registry 应包含 SEC EDGAR"
        assert "sec_edgar" in content, "Registry 应包含 sec_edgar source_type"

    def test_registry_contains_cninfo(self):
        """Registry 必须包含 CNINFO 说明。"""
        path = _docs_dir() / "official_filing_live_smoke_registry.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "CNINFO" in content or "巨潮" in content, "Registry 应包含 CNINFO"
        assert "cninfo_announcement" in content, "Registry 应包含 cninfo_announcement"

    def test_registry_contains_hkexnews(self):
        """Registry 必须包含 HKEXnews 说明。"""
        path = _docs_dir() / "official_filing_live_smoke_registry.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "HKEXnews" in content or "港交所" in content, "Registry 应包含 HKEXnews"
        assert "hkex_announcement" in content, "Registry 应包含 hkex_announcement"

    def test_registry_contains_degraded_empty_source(self):
        """Registry 必须包含 degraded + empty_source 说明。"""
        path = _docs_dir() / "official_filing_live_smoke_registry.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "degraded" in content, "Registry 应包含 degraded 状态"
        assert "empty_source" in content, "Registry 应包含 empty_source 错误"

    def test_registry_contains_health_semantics(self):
        """Registry 必须明确 enabled + candidate_count = 0 → degraded 规则。"""
        path = _docs_dir() / "official_filing_live_smoke_registry.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "enabled + candidate_count = 0" in content, (
            "Registry 应明确 enabled + candidate_count = 0 规则"
        )

    def test_registry_contains_production_recommendation(self):
        """Registry 必须包含 production 建议。"""
        path = _docs_dir() / "official_filing_live_smoke_registry.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "SEC" in content and "ready" in content.lower(), (
            "Registry 应说明 SEC ready"
        )

    def test_registry_contains_hkex_limitation(self):
        """Registry 必须说明 HKEX 的限制。"""
        path = _docs_dir() / "official_filing_live_smoke_registry.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert (
            "client-side rendering" in content.lower()
            or "javascript" in content.lower()
            or "客户端渲染" in content
        ), "Registry 应说明 HKEX 的客户端渲染限制"


# ============================================================================
# Production Readiness Summary Tests
# ============================================================================

class TestProductionReadinessSummary:
    """测试 Production Readiness Summary 文档。"""

    def test_readiness_doc_exists(self):
        """Production Readiness Summary 文档必须存在。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        assert path.exists(), f"缺少 Production Readiness Summary 文档: {path}"

    def test_readiness_contains_production_trial_ready(self):
        """Readiness 必须包含 Production Trial Ready 判断。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Production Trial Ready" in content, (
            "Readiness 应包含 Production Trial Ready 判断"
        )

    def test_readiness_contains_sec_cninfo_ready(self):
        """Readiness 必须说明 SEC/CNINFO ready。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "SEC EDGAR" in content and "ready" in content.lower(), (
            "Readiness 应说明 SEC EDGAR ready"
        )
        assert "CNINFO" in content and "ready" in content.lower(), (
            "Readiness 应说明 CNINFO ready"
        )

    def test_readiness_contains_hkex_degraded(self):
        """Readiness 必须说明 HKEX degraded。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "HKEXnews" in content and "degraded" in content.lower(), (
            "Readiness 应说明 HKEX degraded"
        )

    def test_readiness_contains_downstream_contract(self):
        """Readiness 必须包含下游消费契约。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Downstream" in content or "下游" in content, (
            "Readiness 应包含下游消费说明"
        )

    def test_readiness_contains_filings_jsonl(self):
        """Readiness 必须包含 filings.jsonl 说明。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "filings.jsonl" in content, (
            "Readiness 应包含 filings.jsonl"
        )

    def test_readiness_contains_filings_latest_jsonl(self):
        """Readiness 必须包含 filings.latest.jsonl 说明。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "filings.latest.jsonl" in content, (
            "Readiness 应包含 filings.latest.jsonl"
        )

    def test_readiness_contains_no_browser_automation(self):
        """Readiness 必须明确 no browser automation。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert (
            "browser automation" in content.lower()
            or "浏览器自动化" in content
        ), "Readiness 应明确 no browser automation"
        assert "❌" in content or "not" in content.lower() or "不支持" in content, (
            "Readiness 应明确不支持浏览器自动化"
        )

    def test_readiness_contains_no_ocr(self):
        """Readiness 必须明确 no OCR。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "OCR" in content, "Readiness 应包含 OCR 说明"
        assert "❌" in content or "not" in content.lower() or "不支持" in content, (
            "Readiness 应明确不支持 OCR"
        )

    def test_readiness_contains_download_pdfs_false(self):
        """Readiness 必须明确 download_pdfs=false。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "download_pdfs" in content, "Readiness 应包含 download_pdfs 说明"
        assert "false" in content.lower(), "Readiness 应说明 download_pdfs=false"

    def test_readiness_contains_no_investment_judgment(self):
        """Readiness 必须明确 no investment judgment。"""
        path = _docs_dir() / "official_filing_production_readiness.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert (
            "investment judgment" in content.lower()
            or "投资判断" in content
            or "investment" in content.lower()
        ), "Readiness 应包含 investment judgment 说明"


# ============================================================================
# Existing Docs Update Tests
# ============================================================================

class TestFoundationDocUpdate:
    """测试 official_filing_foundation.md 已更新。"""

    def test_foundation_doc_links_readiness(self):
        """Foundation 文档应链接到 readiness docs。"""
        path = _docs_dir() / "official_filing_foundation.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert (
            "Production Trial Status" in content
            or "Production Trial Ready" in content
        ), "Foundation 应包含 Production Trial Status"
        assert "ready" in content.lower(), "Foundation 应说明 ready"


class TestProductionRunDocUpdate:
    """测试 official_filing_production_run.md 已更新。"""

    def test_production_run_doc_mentions_hkex_disabled(self):
        """Production Run 文档应提到 HKEX disabled。"""
        path = _docs_dir() / "official_filing_production_run.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert (
            "HKEX" in content or "港交所" in content
        ), "Production Run 应提到 HKEX"
        assert (
            "disabled" in content.lower()
            or "禁用" in content
        ), "Production Run 应说明 HKEX 保持 disabled"


class TestSourceMigrationDocUpdate:
    """测试 source_migration 文档已更新。"""

    def test_migration_doc_mentions_m2(self):
        """Migration 文档应提到 M2。"""
        path = _docs_dir() / "source_migration_from_th_capital_stock.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "M2" in content, "Migration 文档应提到 M2"
        assert "Document Extraction" in content or "文档提取" in content, (
            "Migration 文档应提到 Document Extraction Foundation"
        )


class TestResearchDocUpdate:
    """测试 research_source_foundation 文档已更新。"""

    def test_research_doc_mentions_official_filing(self):
        """Research 文档应提到 Official Filing。"""
        path = _docs_dir() / "research_source_foundation.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Official Filing" in content, (
            "Research 文档应提到 Official Filing"
        )
        assert "Production Trial Ready" in content, (
            "Research 文档应说明 Production Trial Ready"
        )
