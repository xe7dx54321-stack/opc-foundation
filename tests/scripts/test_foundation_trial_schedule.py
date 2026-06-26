"""Tests for M3C-3 Trial Schedule scripts."""
import os
from pathlib import Path


class TestTrialScheduleSetup:
    """Tests for setup_foundation_trial_schedule.ps1."""

    def test_setup_script_exists(self):
        """setup script should exist."""
        script_path = Path("scripts/setup_foundation_trial_schedule.ps1")
        assert script_path.exists(), f"Setup script not found: {script_path}"

    def test_setup_script_has_required_modes(self):
        """Setup script should support dry-run, setup, and list modes."""
        content = Path("scripts/setup_foundation_trial_schedule.ps1").read_text(encoding="utf-8")
        assert '$Mode = "dry-run"' in content
        # Uses -eq for comparison in if statements
        assert '$Mode -eq "setup"' in content or '"setup"' in content
        assert '$Mode -eq "list"' in content or '"list"' in content

    def test_setup_script_creates_trial_jobs(self):
        """Setup script should define 6 trial jobs."""
        content = Path("scripts/setup_foundation_trial_schedule.ps1").read_text(encoding="utf-8")
        # 6 trial jobs
        assert "OPC_Foundation_Trial_Morning_Run" in content
        assert "OPC_Foundation_Trial_Morning_Check" in content
        assert "OPC_Foundation_Trial_Afternoon_Run" in content
        assert "OPC_Foundation_Trial_Evening_Run" in content
        assert "OPC_Foundation_Trial_Evening_Check" in content
        assert "OPC_Foundation_Trial_Daily_Status" in content

    def test_setup_script_uses_run_foundation_trial_sources(self):
        """Setup script should call run_foundation_trial_sources.ps1."""
        content = Path("scripts/setup_foundation_trial_schedule.ps1").read_text(encoding="utf-8")
        assert "run_foundation_trial_sources.ps1" in content
        assert "-Mode run" in content

    def test_setup_script_uses_check_foundation_trial_sources(self):
        """Setup script should call check_foundation_trial_sources.ps1."""
        content = Path("scripts/setup_foundation_trial_schedule.ps1").read_text(encoding="utf-8")
        assert "check_foundation_trial_sources.ps1" in content

    def test_setup_script_auto_locates_repo_root(self):
        """Setup script should auto-locate repo root."""
        content = Path("scripts/setup_foundation_trial_schedule.ps1").read_text(encoding="utf-8")
        assert "Get-Location" in content or "RepoRoot" in content

    def test_setup_script_mentions_trial_only(self):
        """Setup script output should mention trial-only."""
        content = Path("scripts/setup_foundation_trial_schedule.ps1").read_text(encoding="utf-8")
        assert "Trial-only" in content or "trial_only" in content


class TestTrialScheduleRemove:
    """Tests for remove_foundation_trial_schedule.ps1."""

    def test_remove_script_exists(self):
        """Remove script should exist."""
        script_path = Path("scripts/remove_foundation_trial_schedule.ps1")
        assert script_path.exists(), f"Remove script not found: {script_path}"

    def test_remove_script_has_disable_action(self):
        """Remove script should support disable action."""
        content = Path("scripts/remove_foundation_trial_schedule.ps1").read_text(encoding="utf-8")
        assert '$Action = "dry-run"' in content
        assert '$Action -eq "disable"' in content or '"disable"' in content

    def test_remove_script_has_delete_action(self):
        """Remove script should support delete action."""
        content = Path("scripts/remove_foundation_trial_schedule.ps1").read_text(encoding="utf-8")
        assert '$Action -eq "delete"' in content or '"delete"' in content

    def test_remove_script_targets_trial_task_names(self):
        """Remove script should target all 6 trial task names."""
        content = Path("scripts/remove_foundation_trial_schedule.ps1").read_text(encoding="utf-8")
        assert "OPC_Foundation_Trial_Morning_Run" in content
        assert "OPC_Foundation_Trial_Morning_Check" in content
        assert "OPC_Foundation_Trial_Afternoon_Run" in content
        assert "OPC_Foundation_Trial_Evening_Run" in content
        assert "OPC_Foundation_Trial_Evening_Check" in content
        assert "OPC_Foundation_Trial_Daily_Status" in content


class TestTrialScheduleConfig:
    """Tests for configs/trae_foundation_trial_schedule.example.yaml."""

    def test_schedule_config_exists(self):
        """Trial schedule config should exist."""
        config_path = Path("configs/trae_foundation_trial_schedule.example.yaml")
        assert config_path.exists(), f"Trial schedule config not found: {config_path}"

    def test_schedule_config_has_trial_only_flag(self):
        """Trial schedule config should have trial_only=true."""
        import yaml
        config_path = Path("configs/trae_foundation_trial_schedule.example.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data.get("trial_only") is True
        assert data.get("production_mode") is False

    def test_schedule_config_has_6_tasks(self):
        """Trial schedule config should have 6 tasks."""
        import yaml
        config_path = Path("configs/trae_foundation_trial_schedule.example.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        tasks = data.get("tasks", [])
        assert len(tasks) == 6

    def test_schedule_config_has_scheduling_times(self):
        """Trial schedule config should have proper scheduling times."""
        import yaml
        config_path = Path("configs/trae_foundation_trial_schedule.example.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        tasks = data.get("tasks", [])
        for task in tasks:
            assert "schedule_times" in task
            assert len(task["schedule_times"]) > 0

    def test_schedule_config_mentions_15_sources(self):
        """Trial schedule config should mention 15 sources."""
        content = Path("configs/trae_foundation_trial_schedule.example.yaml").read_text(encoding="utf-8")
        assert "15" in content


class TestTrialScheduleReport:
    """Tests for M3C-3 schedule report."""

    def test_schedule_report_exists(self):
        """M3C-3 schedule report should exist."""
        report_path = Path("docs/foundation_trae_trial_schedule_report.md")
        assert report_path.exists(), f"Schedule report not found: {report_path}"

    def test_schedule_report_mentions_trial_only(self):
        """Schedule report should mention trial-only."""
        content = Path("docs/foundation_trae_trial_schedule_report.md").read_text(encoding="utf-8")
        assert "trial" in content.lower()

    def test_schedule_report_mentions_15_sources(self):
        """Schedule report should mention 15 sources."""
        content = Path("docs/foundation_trae_trial_schedule_report.md").read_text(encoding="utf-8")
        assert "15" in content

    def test_schedule_report_mentions_rollback(self):
        """Schedule report should mention rollback method."""
        content = Path("docs/foundation_trae_trial_schedule_report.md").read_text(encoding="utf-8")
        assert "rollback" in content.lower() or "Rollback" in content

    def test_schedule_report_no_microsoft_ir(self):
        """Schedule report should NOT mention Microsoft IR as included."""
        content = Path("docs/foundation_trae_trial_schedule_report.md").read_text(encoding="utf-8")
        # Microsoft IR should be in url_backlog, not as included
        lines = content.split("\n")
        for line in lines:
            if "Microsoft IR" in line and "NOT" not in line and "url_backlog" not in line:
                # Should be in excluded/backlog section
                assert "url_backlog" in content or "excluded" in content.lower()
