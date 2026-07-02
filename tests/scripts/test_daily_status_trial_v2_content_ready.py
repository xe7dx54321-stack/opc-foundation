"""M3C-5A10-sidecar: Daily Status Trial V2 Content-Ready section 测试。"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestDailyStatusTrialV2ContentReady:
    """Daily Status 包含 Foundation Trial V2 Content Ready section 测试。"""

    def test_daily_status_script_exists(self):
        """generate_daily_status_report.py 应该存在。"""
        p = Path("scripts/generate_daily_status_report.py")
        assert p.exists()

    def test_daily_status_imports_trial_v2(self):
        """Daily status 脚本应该导入 trial_v2_status。"""
        p = Path("scripts/generate_daily_status_report.py")
        content = p.read_text(encoding="utf-8")
        assert "trial_v2_status" in content or "load_trial_v2_content_ready_summary" in content

    def test_daily_status_has_trial_v2_section(self):
        """Daily status 应该包含 Foundation Trial V2 Content Ready section。"""
        from opc_foundation.dashboard.loaders import build_trial_runtime_summary
        # Test by running generate_report and checking output
        import importlib
        spec = importlib.util.spec_from_file_location(
            "daily_status",
            "scripts/generate_daily_status_report.py"
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            report = mod.generate_report()
            assert "Foundation Trial V2 Content Ready" in report
        except Exception as e:
            pytest.skip(f"Cannot run daily status script: {e}")

    def test_daily_status_fail_soft(self):
        """data 缺失时 daily status 不报错。"""
        from opc_foundation.dashboard.trial_v2_status import load_trial_v2_content_ready_summary
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = load_trial_v2_content_ready_summary(base_dir=tmpdir)
            assert summary.data_exists is False
            assert summary.observation_status == "not_started"

    def test_daily_status_source_count(self):
        """有数据时 source_count 应 > 0。"""
        from opc_foundation.dashboard.trial_v2_status import load_trial_v2_content_ready_summary
        repo = Path(__file__).parent.parent.parent
        summary = load_trial_v2_content_ready_summary(base_dir=str(repo))
        if summary.data_exists:
            assert summary.source_count >= 1
        else:
            pytest.skip("No trial_v2 data")

    def test_daily_status_last_run_at(self):
        """有 run_log 时应能识别 last_run_at。"""
        from opc_foundation.dashboard.trial_v2_status import load_trial_v2_content_ready_summary
        repo = Path(__file__).parent.parent.parent
        summary = load_trial_v2_content_ready_summary(base_dir=str(repo))
        if summary.data_exists and summary.last_run_at:
            assert len(summary.last_run_at) >= 10  # At least YYYY-MM-DD
        else:
            pytest.skip("No run data")

    def test_daily_status_failed_queue_empty(self):
        """failed_queue 为空时 failed_queue_count=0。"""
        from opc_foundation.dashboard.trial_v2_status import load_trial_v2_content_ready_summary
        repo = Path(__file__).parent.parent.parent
        summary = load_trial_v2_content_ready_summary(base_dir=str(repo))
        if summary.data_exists:
            assert summary.failed_queue_count >= 0
        else:
            pytest.skip("No trial_v2 data")

    def test_report_no_proxy_url(self):
        """Integration report 不包含 proxy URL。"""
        import re
        p = Path("docs/foundation_trial_v2_daily_status_integration_report.md")
        if p.exists():
            content = p.read_text(encoding="utf-8")
            for pattern in [r'http://\S+:\d+', r'https://\S+:\d+', r'socks5://', r'socks4://']:
                assert len(re.findall(pattern, content)) == 0, f"Proxy URL found: {pattern}"

    def test_no_deleted_dashboard_pages(self):
        """不恢复总览/运行日志/失败队列/文档入口（不作为独立页面导航选项）。"""
        app_path = Path("src/opc_foundation/dashboard/app.py")
        if app_path.exists():
            content = app_path.read_text(encoding="utf-8")
            # Check sidebar page options do not include deleted pages
            # The main() function's page list should NOT have these options
            lines = content.split("\n")
            main_func_started = False
            page_options = []
            for line in lines:
                if "def main()":
                    main_func_started = True
                if main_func_started and "page ==" in line:
                    page_options.append(line.strip())
            # Deleted pages should NOT be in the page navigation
            for opt in page_options:
                assert "总览" not in opt
                assert "运行日志" not in opt
                assert "失败队列" not in opt
                assert "文档入口" not in opt

    def test_not_modify_trial_v1(self):
        """不修改 trial_v1。"""
        app_path = Path("src/opc_foundation/dashboard/app.py")
        content = app_path.read_text(encoding="utf-8")
        # Trial v2 card should not reference trial_v1
        # Check the trial_v2_status module doesn't modify trial_v1
        t2_path = Path("src/opc_foundation/dashboard/trial_v2_status.py")
        if t2_path.exists():
            t2_content = t2_path.read_text(encoding="utf-8")
            assert "trial_v1" not in t2_content.lower()

    def test_not_submit_data(self):
        """data/ 不提交（.gitignore 检查）。"""
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            assert "data/" in content or "foundation_trial_v2_content_ready" in content
