"""Tests for M3C-6E1 Investment On-demand Registry scripts.

Tests cover:
    - Dry-run runner produces route plan
    - Dry-run runner does not perform real fetch
    - Dry-run runner does not call search APIs
    - Dry-run runner produces evidence packet skeletons
    - Evidence packets do not contain forbidden investment fields
    - Check script detects forbidden fields
    - production_enabled=false
    - performs_real_fetch=false
    - affects_trial_v2_allowlist=false
    - affects_trae_scheduling=false
    - No data committed
    - No cookie/token/proxy/secret in output
    - No Playwright/Selenium
    - No Dashboard deleted pages restored
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_SCRIPTS_DIR))


class TestDryRunRunner:
    """Dry-run runner script tests."""

    def test_runner_exists(self):
        runner_path = _SCRIPTS_DIR / "run_investment_on_demand_registry.py"
        assert runner_path.exists()

    def test_check_script_exists(self):
        check_path = _SCRIPTS_DIR / "check_investment_on_demand_registry.py"
        assert check_path.exists()

    def test_runner_no_network_imports(self):
        runner_path = _SCRIPTS_DIR / "run_investment_on_demand_registry.py"
        text = runner_path.read_text(encoding="utf-8")
        forbidden_imports = [
            "import requests",
            "import httpx",
            "import aiohttp",
            "from urllib.request",
            "import tavily",
            "import serpapi",
        ]
        for imp in forbidden_imports:
            assert imp not in text, f"forbidden import in runner: {imp}"

    def test_runner_no_network_calls(self):
        runner_path = _SCRIPTS_DIR / "run_investment_on_demand_registry.py"
        text = runner_path.read_text(encoding="utf-8")
        forbidden_calls = [
            "requests.get",
            "requests.post",
            "httpx.get",
            "httpx.post",
            "urlopen(",
            "tavily.search",
        ]
        for call in forbidden_calls:
            assert call not in text, f"forbidden network call in runner: {call}"

    def test_runner_no_playwright_selenium(self):
        runner_path = _SCRIPTS_DIR / "run_investment_on_demand_registry.py"
        text = runner_path.read_text(encoding="utf-8")
        # Check for actual import statements, not docstring mentions
        assert "import playwright" not in text.lower()
        assert "from playwright" not in text.lower()
        assert "import selenium" not in text.lower()
        assert "from selenium" not in text.lower()

    def test_runner_example_dry_run(self):
        """Run the runner with --example --dry-run and verify output."""
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS_DIR / "run_investment_on_demand_registry.py"),
                "--example",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"runner failed: {result.stderr}"
        assert "route_plan" in result.stdout
        assert "evidence_packet_skeletons" in result.stdout
        assert '"performs_real_fetch": false' in result.stdout
        assert '"production_enabled": false' in result.stdout

    def test_runner_fail_closed_on_run_flag(self):
        """Runner must fail-closed when --run is passed."""
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS_DIR / "run_investment_on_demand_registry.py"),
                "--example",
                "--run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode != 0
        assert "not supported" in result.stderr.lower() or "fail" in result.stderr.lower()

    def test_runner_no_forbidden_fields_in_output(self):
        """Runner output must not contain forbidden investment fields."""
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS_DIR / "run_investment_on_demand_registry.py"),
                "--example",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        forbidden = [
            "rating",
            "target_price",
            "buy_sell_hold",
            "investment_recommendation",
            "position_size",
            "trade_signal",
        ]
        for field in forbidden:
            # The field name should not appear as a key in the JSON output
            assert f'"{field}"' not in result.stdout, f"forbidden field '{field}' in output"

    def test_runner_no_sensitive_data_in_output(self):
        """Runner output must not contain cookie/token/proxy/secret."""
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS_DIR / "run_investment_on_demand_registry.py"),
                "--example",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        sensitive_patterns = [
            "http_proxy=",
            "https_proxy=",
            "cookie:",
            "authorization:",
            "api_key=",
            "secret=",
            "password=",
        ]
        lower_output = result.stdout.lower()
        for pattern in sensitive_patterns:
            assert pattern not in lower_output, f"sensitive pattern '{pattern}' in output"

    def test_runner_query_pack_from_yaml(self):
        """Runner can load a query pack from the example YAML config."""
        config_path = _REPO_ROOT / "configs" / "foundation_investment_on_demand_registry.example.yaml"
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS_DIR / "run_investment_on_demand_registry.py"),
                "--query-pack",
                str(config_path),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"runner failed: {result.stderr}"
        assert "route_plan" in result.stdout

    def test_runner_does_not_modify_trial_v2(self):
        """Runner output must show affects_trial_v2_allowlist=false."""
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS_DIR / "run_investment_on_demand_registry.py"),
                "--example",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert '"affects_trial_v2_allowlist": false' in result.stdout

    def test_runner_does_not_modify_trae_scheduling(self):
        """Runner output must show affects_trae_scheduling=false."""
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS_DIR / "run_investment_on_demand_registry.py"),
                "--example",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert '"affects_trae_scheduling": false' in result.stdout


class TestCheckScript:
    """Check script tests."""

    def test_check_script_passes(self):
        """Check script should pass all checks."""
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS_DIR / "check_investment_on_demand_registry.py"),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"check failed: {result.stderr}\n{result.stdout}"
        assert "ALL CHECKS PASSED" in result.stdout

    def test_check_script_no_playwright_selenium(self):
        check_path = _SCRIPTS_DIR / "check_investment_on_demand_registry.py"
        text = check_path.read_text(encoding="utf-8")
        assert "playwright" not in text.lower()
        assert "selenium" not in text.lower()


class TestNoDataCommitted:
    """Verify no data/ directory is created by the runner."""

    def test_no_data_dir_created(self):
        """The runner should not create any data/ files."""
        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS_DIR / "run_investment_on_demand_registry.py"),
                "--example",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        # Check that no data files were created
        data_dir = _REPO_ROOT / "data" / "investment_on_demand"
        assert not data_dir.exists() or not any(data_dir.iterdir())


class TestNoDashboardRestored:
    """Verify Dashboard deleted pages are not restored."""

    def test_no_dashboard_pages_restored(self):
        """No Dashboard pages (总览/运行日志/失败队列/文档入口) should be created."""
        dashboard_dir = _REPO_ROOT / "dashboard"
        if dashboard_dir.exists():
            for page in ("overview", "run_logs", "failure_queue", "doc_entry"):
                assert not (dashboard_dir / f"{page}.html").exists()
        # Also check no new dashboard files in docs
        docs_dir = _REPO_ROOT / "docs"
        deleted_pages = ["总览", "运行日志", "失败队列", "文档入口"]
        for page in deleted_pages:
            for f in docs_dir.iterdir():
                if f.is_file() and page in f.name:
                    pytest.fail(f"deleted dashboard page '{page}' found in docs: {f.name}")
