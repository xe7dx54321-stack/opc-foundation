"""测试 live smoke 模型。

功能说明（小白解读）：
    测试 source_inventory.models 里的所有 dataclass 和枚举。
    确保模型能正常创建、序列化、反序列化。
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class TestLiveSmokeModels:
    """测试 LiveSmokeStatus 枚举和相关模型。"""

    def test_live_smoke_status_enum_exists(self) -> None:
        """测试 LiveSmokeStatus 枚举存在且包含核心状态。"""
        from opc_foundation.source_inventory.models import LiveSmokeStatus

        assert hasattr(LiveSmokeStatus, "LIVE_OK")
        assert hasattr(LiveSmokeStatus, "BLOCKED_BY_POLICY")
        assert hasattr(LiveSmokeStatus, "ON_DEMAND_NOT_RUN")
        assert hasattr(LiveSmokeStatus, "DORMANT_NOT_RUN")
        assert hasattr(LiveSmokeStatus, "NEEDS_CONNECTOR")
        assert hasattr(LiveSmokeStatus, "PARSER_MISMATCH")
        assert hasattr(LiveSmokeStatus, "MISSING_CONFIG")
        assert hasattr(LiveSmokeStatus, "MISSING_API_KEY")
        assert hasattr(LiveSmokeStatus, "HTTP_ERROR")
        assert hasattr(LiveSmokeStatus, "TIMEOUT")
        assert hasattr(LiveSmokeStatus, "FAILED")

    def test_live_smoke_status_labels_exist(self) -> None:
        """测试中文标签字典存在。"""
        from opc_foundation.source_inventory.models import (
            LIVE_SMOKE_STATUS_LABELS,
            LiveSmokeStatus,
        )

        for status in LiveSmokeStatus:
            assert status in LIVE_SMOKE_STATUS_LABELS, f"Missing label for {status}"
            assert LIVE_SMOKE_STATUS_LABELS[status]

    def test_candidate_item_model(self) -> None:
        """测试 CandidateItem 模型。"""
        from opc_foundation.source_inventory.models import CandidateItem

        item = CandidateItem(
            title="Test Article",
            url="https://example.com/article",
            published="2024-01-01",
            summary="Test summary",
            source="test_source",
        )
        assert item.title == "Test Article"
        assert item.url == "https://example.com/article"

    def test_source_live_result_model(self) -> None:
        """测试 SourceLiveResult 模型。"""
        from opc_foundation.source_inventory.models import (
            CandidateItem,
            LiveSmokeStatus,
            SourceLiveResult,
        )

        result = SourceLiveResult(
            source_id="test_source",
            source_name="Test Source",
            source_group="test_group",
            access_mode="public_web",
            status=LiveSmokeStatus.LIVE_OK,
            visited=True,
            fetched=True,
            candidates_found=3,
            candidates_saved=2,
            candidates=[CandidateItem(title="A", url="https://a.com")],
            response_time_ms=150,
            http_status=200,
            checked_at="2024-01-01T00:00:00Z",
        )
        assert result.source_id == "test_source"
        assert result.status == LiveSmokeStatus.LIVE_OK
        assert result.candidates_found == 3

    def test_source_live_result_to_dict_and_back(self) -> None:
        """测试 SourceLiveResult 的 to_dict 和 from_dict 能正确往返。"""
        from opc_foundation.source_inventory.models import (
            CandidateItem,
            LiveSmokeStatus,
            SourceLiveResult,
        )

        original = SourceLiveResult(
            source_id="test_source",
            source_name="Test Source",
            source_group="test_group",
            access_mode="rss",
            status=LiveSmokeStatus.LIVE_OK_CANDIDATES_FOUND,
            visited=True,
            fetched=True,
            candidates_found=5,
            candidates_saved=5,
            candidates=[
                CandidateItem(title="A", url="https://a.com", published="2024-01-01"),
                CandidateItem(title="B", url="https://b.com"),
            ],
            response_time_ms=200,
            http_status=200,
            error_message="",
            notes="test note",
            checked_at="2024-01-01T00:00:00Z",
        )

        data = original.to_dict()
        assert data["source_id"] == "test_source"
        assert data["status"] == "live_ok_candidates_found"
        assert len(data["candidates"]) == 2

        restored = SourceLiveResult.from_dict(data)
        assert restored.source_id == original.source_id
        assert restored.status == original.status
        assert len(restored.candidates) == len(original.candidates)
        assert restored.candidates[0].title == "A"

    def test_source_group_live_result(self) -> None:
        """测试 SourceGroupLiveResult 模型的统计属性。"""
        from opc_foundation.source_inventory.models import (
            LiveSmokeStatus,
            SourceGroupLiveResult,
            SourceLiveResult,
        )

        group = SourceGroupLiveResult(
            group_id="test_group",
            group_name="Test Group",
            total_sources=3,
            results=[
                SourceLiveResult(source_id="a", status=LiveSmokeStatus.LIVE_OK),
                SourceLiveResult(source_id="b", status=LiveSmokeStatus.LIVE_OK_CANDIDATES_FOUND),
                SourceLiveResult(source_id="c", status=LiveSmokeStatus.HTTP_ERROR),
            ],
        )
        assert group.success_count == 2
        assert group.failure_count == 1
        assert group.status_counts.get("live_ok") == 1
        assert group.status_counts.get("http_error") == 1

    def test_live_smoke_summary(self) -> None:
        """测试 LiveSmokeSummary 模型的全局统计。"""
        from opc_foundation.source_inventory.models import (
            LiveSmokeStatus,
            LiveSmokeSummary,
            SourceGroupLiveResult,
            SourceLiveResult,
        )

        summary = LiveSmokeSummary(
            total_sources=5,
            groups=[
                SourceGroupLiveResult(
                    group_id="g1",
                    group_name="G1",
                    total_sources=3,
                    results=[
                        SourceLiveResult(source_id="a", status=LiveSmokeStatus.LIVE_OK),
                        SourceLiveResult(source_id="b", status=LiveSmokeStatus.BLOCKED_BY_POLICY),
                        SourceLiveResult(source_id="c", status=LiveSmokeStatus.NEEDS_CONNECTOR),
                    ],
                ),
                SourceGroupLiveResult(
                    group_id="g2",
                    group_name="G2",
                    total_sources=2,
                    results=[
                        SourceLiveResult(source_id="d", status=LiveSmokeStatus.ON_DEMAND_NOT_RUN),
                        SourceLiveResult(source_id="e", status=LiveSmokeStatus.TIMEOUT),
                    ],
                ),
            ],
        )

        assert summary.total_sources == 5
        assert summary.success_count == 1
        assert summary.blocked_count == 1
        assert summary.needs_connector_count == 1
        assert summary.failure_count == 1

    def test_live_smoke_run_config_defaults(self) -> None:
        """测试 LiveSmokeRunConfig 的默认值。"""
        from opc_foundation.source_inventory.models import LiveSmokeRunConfig

        config = LiveSmokeRunConfig()
        assert config.max_candidates_per_source == 5
        assert config.timeout_seconds == 20
        assert config.max_retries == 1
        assert config.dry_run is False
        assert config.user_agent
        assert config.proxy_url == ""
        assert config.proxy_mode == "none"

    def test_live_smoke_summary_proxy_fields(self) -> None:
        """测试 LiveSmokeSummary 有 proxy_enabled 和 proxy_mode 字段。"""
        from opc_foundation.source_inventory.models import LiveSmokeSummary

        summary = LiveSmokeSummary()
        assert summary.proxy_enabled is False
        assert summary.proxy_mode == "none"

        summary2 = LiveSmokeSummary(proxy_enabled=True, proxy_mode="cli")
        assert summary2.proxy_enabled is True
        assert summary2.proxy_mode == "cli"
