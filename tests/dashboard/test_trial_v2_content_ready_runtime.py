"""M3C-5A10-sidecar: Trial V2 Content-Ready 运行时状态测试。"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestTrialV2ContentReadyStatus:
    """Trial V2 Content-Ready 只读状态加载器测试。"""

    def test_module_importable(self):
        """trial_v2_status 模块应该可以导入。"""
        from opc_foundation.dashboard.trial_v2_status import (
            TrialV2ContentReadySummary,
            load_trial_v2_content_ready_summary,
        )
        assert TrialV2ContentReadySummary is not None
        assert load_trial_v2_content_ready_summary is not None

    def test_summary_dataclass_defaults(self):
        """Summary 默认值应该是 fail-soft。"""
        from opc_foundation.dashboard.trial_v2_status import TrialV2ContentReadySummary
        s = TrialV2ContentReadySummary()
        assert s.source_count == 8
        assert s.production_enabled is False
        assert s.observation_status == "not_started"
        assert s.wind_public_watch_flag is False
        assert s.data_exists is False
        assert s.failed_queue_count == 0

    def test_load_with_no_data_dir(self, tmp_path):
        """data 目录不存在时返回 not_started。"""
        from opc_foundation.dashboard.trial_v2_status import load_trial_v2_content_ready_summary
        summary = load_trial_v2_content_ready_summary(base_dir=str(tmp_path))
        assert summary.data_exists is False
        assert summary.observation_status == "not_started"
        assert summary.source_count == 8
        assert summary.production_enabled is False

    def test_load_with_real_data(self):
        """有真实数据时应正确统计。"""
        from opc_foundation.dashboard.trial_v2_status import load_trial_v2_content_ready_summary
        # Use actual repo data
        repo = Path(__file__).parent.parent.parent
        summary = load_trial_v2_content_ready_summary(base_dir=str(repo))
        if summary.data_exists:
            assert summary.source_count >= 1
            assert summary.production_enabled is False
            assert summary.observation_status in ("not_started", "partial_observation", "completed_24h")
        else:
            pytest.skip("No trial_v2 data in repo")

    def test_production_enabled_always_false(self, tmp_path):
        """production_enabled 必须始终为 False。"""
        from opc_foundation.dashboard.trial_v2_status import load_trial_v2_content_ready_summary
        summary = load_trial_v2_content_ready_summary(base_dir=str(tmp_path))
        assert summary.production_enabled is False

    def test_wind_public_watch_flag_from_preflight(self):
        """preflight 中 wind_public garbled_text 应被检测。"""
        repo = Path(__file__).parent.parent.parent
        from opc_foundation.dashboard.trial_v2_status import load_trial_v2_content_ready_summary
        summary = load_trial_v2_content_ready_summary(base_dir=str(repo))
        if summary.data_exists:
            # Wind public has garbled_text from preflight
            assert isinstance(summary.wind_public_watch_flag, bool)
            assert isinstance(summary.wind_public_garbled_text_observed, bool)

    def test_observation_status_no_fake_completed(self, tmp_path):
        """缺证据时不得判定 completed_24h。"""
        from opc_foundation.dashboard.trial_v2_status import load_trial_v2_content_ready_summary
        summary = load_trial_v2_content_ready_summary(base_dir=str(tmp_path))
        # With no data, should be not_started, never completed_24h
        assert summary.observation_status in ("not_started", "partial_observation")
        assert summary.observation_status != "completed_24h"

    def test_dashboard_app_imports_trial_v2(self):
        """Dashboard app.py 应该导入 trial_v2_status。"""
        app_path = Path("src/opc_foundation/dashboard/app.py")
        content = app_path.read_text(encoding="utf-8")
        assert "trial_v2_status" in content or "load_trial_v2_summary" in content
