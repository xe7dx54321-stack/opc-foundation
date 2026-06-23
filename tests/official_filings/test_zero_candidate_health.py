"""测试 enabled source + 0 candidates = degraded 的 health 逻辑。

核心测试场景：
    当 enabled source 没有发现任何候选时，health 状态应为 degraded，
    last_error 应为 "empty_source"。

这是统一的行为规则，适用于所有 enabled source。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from opc_foundation.official_filings.config import load_filing_config
from opc_foundation.official_filings.archiver import FilingArchiver
from opc_foundation.official_filings.health import load_source_health


# ---------------------------------------------------------------------------
# Mock Connectors
# ---------------------------------------------------------------------------

class MockConnectorZeroCandidates:
    """模拟 connector，返回 0 个 candidates。"""
    connector_id = "mock_announcement"

    def discover(self, source, config):
        return []  # 返回空列表


class MockConnectorNonZeroCandidates:
    """模拟 connector，返回 3 个 candidates。"""
    connector_id = "mock_announcement"

    def discover(self, source, config):
        from opc_foundation.official_filings.models import FilingCandidate
        return [
            FilingCandidate(
                source_id=source.source_id,
                source_type="mock_announcement",
                market="TEST",
                jurisdiction="TEST",
                issuer_name="Test Corp",
                issuer_code="TEST001",
                filing_type="10-K",
                filing_title="Annual Report",
                filing_date="2024-01-01",
                announcement_id="123",
                source_url="http://test.com/1",
                document_url="http://test.com/doc/1",
                discovered_at="2024-01-01T00:00:00Z",
            )
        ] * 3


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_zero_candidate_enabled_source_health_degraded():
    """测试：enabled=True + 0 candidates → degraded + empty_source。
    
    核心断言：
        - health.status == "degraded"
        - health.last_error == "empty_source"
        - health.candidate_count_last_run == 0
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        archive_root = Path(tmpdir) / "data"
        
        config_data = {
            "archive_root": str(archive_root),
            "defaults": {
                "max_items_per_source": 5,
                "save_raw": True,
                "save_html": True,
                "save_pdf_metadata": True,
                "download_pdfs": False,
                "fetch_timeout_seconds": 30,
            },
            "sources": [
                {
                    "source_id": "mock_zero_candidate",
                    "source_name": "Mock Zero Candidate Source",
                    "source_type": "mock_announcement",
                    "market": "TEST",
                    "jurisdiction": "TEST",
                    "enabled": True,  # 启用
                    "legal_profile": "official_public",
                    "max_items": 5,
                }
            ]
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True)
        
        config = load_filing_config(str(config_path))
        
        archiver = FilingArchiver(
            config,
            connector_overrides={"mock_announcement": MockConnectorZeroCandidates()}
        )
        
        result = archiver.run(mode="run")
        
        # 验证基本结果
        assert result.candidate_count == 0, "候选数应为 0"
        assert result.saved_count == 0, "保存数应为 0"
        
        # 检查 source health
        health = load_source_health(archive_root)
        assert "mock_zero_candidate" in health, "mock_zero_candidate 应该有 health 记录"
        
        mock_health = health["mock_zero_candidate"]
        
        # 核心断言：enabled=True + 0 candidates = degraded
        assert mock_health.status == "degraded", (
            f"enabled=True + 0 candidates 应为 degraded，实际为 {mock_health.status}"
        )
        
        # 核心断言：last_error = "empty_source"
        assert mock_health.last_error == "empty_source", (
            f"last_error 应为 empty_source，实际为 {mock_health.last_error}"
        )
        
        # 验证统计字段
        assert mock_health.candidate_count_last_run == 0, (
            "candidate_count_last_run 应为 0"
        )


def test_nonzero_candidate_enabled_source_health_healthy():
    """测试：enabled=True + >0 candidates + no errors → healthy。
    
    验证正常情况下有候选时，health 状态应为 healthy。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        archive_root = Path(tmpdir) / "data"
        
        config_data = {
            "archive_root": str(archive_root),
            "defaults": {
                "max_items_per_source": 5,
                "save_raw": True,
                "save_html": True,
                "save_pdf_metadata": True,
                "download_pdfs": False,
                "fetch_timeout_seconds": 30,
            },
            "sources": [
                {
                    "source_id": "mock_nonzero",
                    "source_name": "Mock NonZero Source",
                    "source_type": "mock_announcement",
                    "market": "TEST",
                    "jurisdiction": "TEST",
                    "enabled": True,
                    "legal_profile": "official_public",
                    "max_items": 5,
                }
            ]
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True)
        
        config = load_filing_config(str(config_path))
        archiver = FilingArchiver(
            config,
            connector_overrides={"mock_announcement": MockConnectorNonZeroCandidates()}
        )
        
        result = archiver.run(mode="run")
        
        # 验证
        assert result.candidate_count == 3, "候选数应为 3"
        
        health = load_source_health(archive_root)
        mock_health = health["mock_nonzero"]
        
        # 有候选且无错误，应为 healthy
        assert mock_health.status == "healthy", (
            f"enabled=True + 3 candidates 应为 healthy，实际为 {mock_health.status}"
        )
        assert mock_health.last_error is None, (
            f"healthy 状态的 last_error 应为 None，实际为 {mock_health.last_error}"
        )
        assert mock_health.candidate_count_last_run == 3, (
            "candidate_count_last_run 应为 3"
        )
