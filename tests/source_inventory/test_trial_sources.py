"""Trial Source 模块测试。

功能说明（小白解读）：
    测试 trial 配置验证逻辑。
    确保 16 个 trial source 是对的，不会误包含 blocked/search/dormant 等问题源。
"""

import pytest
import sys
from pathlib import Path

# 确保可以 import opc_foundation
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import yaml


# ---- Fixtures ----

@pytest.fixture
def allowlist_path(tmp_path) -> Path:
    """创建一个合法的 trial allowlist fixture。"""
    config = {
        "version": 1,
        "updated_at": "2026-06-26",
        "trial_scope": {
            "name": "foundation_m3c_2d_trial",
            "source_count": 16,
        },
        "trial_source_ids": [
            {"source_id": "goldman_sachs_research", "trial_enabled": True},
            {"source_id": "goldman_sachs_reports", "trial_enabled": True},
            {"source_id": "goldman_sachs_top_of_mind", "trial_enabled": True},
            {"source_id": "goldman_sachs_insights", "trial_enabled": True},
            {"source_id": "barclays_our_insights", "trial_enabled": True},
            {"source_id": "microsoft_ir", "trial_enabled": True},
            {"source_id": "yahoo_finance", "trial_enabled": True},
            {"source_id": "business_insider", "trial_enabled": True},
            {"source_id": "markets_insider", "trial_enabled": True},
            {"source_id": "the_fly", "trial_enabled": True},
            {"source_id": "briefing_com_upgrades", "trial_enabled": True},
            {"source_id": "wallstreet_cn", "trial_enabled": True},
            {"source_id": "cls_cn", "trial_enabled": True},
            {"source_id": "wind_public", "trial_enabled": True},
            {"source_id": "gelonghui", "trial_enabled": True},
            {"source_id": "zhitong_caijing", "trial_enabled": True},
        ],
        "excluded_source_ids": [
            "telegram_groups", "cloud_drive_share", "pdf_download_sites",
            "morgan_stanley_insights", "tavily_search", "github_issues",
        ],
    }
    path = tmp_path / "allowlist.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f)
    return path


# ---- 测试 allowlist 基础 ----

class TestTrialAllowlist:
    """测试 trial allowlist 基础属性。"""

    def test_allowlist_file_exists(self):
        """Trial allowlist 文件应该存在。"""
        from pathlib import Path

        allowlist_path = Path("configs/foundation_trial_source_allowlist.example.yaml")
        assert allowlist_path.exists(), f"Allowlist not found: {allowlist_path}"

    def test_allowlist_source_count(self):
        """Trial allowlist 应该包含 16 个 source。"""
        from pathlib import Path

        allowlist_path = Path("configs/foundation_trial_source_allowlist.example.yaml")
        with open(allowlist_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        trial_ids = [x["source_id"] for x in data["trial_source_ids"]]
        assert len(trial_ids) == 16, f"Expected 16 trial sources, got {len(trial_ids)}"

    def test_allowlist_no_duplicates(self):
        """Trial allowlist 不应该有重复的 source_id。"""
        from pathlib import Path

        allowlist_path = Path("configs/foundation_trial_source_allowlist.example.yaml")
        with open(allowlist_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        trial_ids = [x["source_id"] for x in data["trial_source_ids"]]
        dupes = [x for x in trial_ids if trial_ids.count(x) > 1]
        assert len(dupes) == 0, f"Duplicate source_ids: {set(dupes)}"

    def test_no_blocked_sources(self):
        """Trial allowlist 不应该包含 blocked 源。"""
        from pathlib import Path

        allowlist_path = Path("configs/foundation_trial_source_allowlist.example.yaml")
        with open(allowlist_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        trial_ids = [x["source_id"] for x in data["trial_source_ids"]]
        blocked = {"telegram_groups", "cloud_drive_share", "pdf_download_sites",
                   "unknown_wechat_pdf", "report_download_proxy"}
        bad = [x for x in trial_ids if x in blocked]
        assert len(bad) == 0, f"Trial contains blocked sources: {bad}"

    def test_no_search_provider(self):
        """Trial allowlist 不应该包含 search provider。"""
        from pathlib import Path

        allowlist_path = Path("configs/foundation_trial_source_allowlist.example.yaml")
        with open(allowlist_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        trial_ids = [x["source_id"] for x in data["trial_source_ids"]]
        search_providers = {"tavily_search", "brave_search", "serpapi", "bing_search",
                            "google_cse", "searx", "duckduckgo", "yahoo_search",
                            "baidu_search", "custom_search"}
        bad = [x for x in trial_ids if x in search_providers]
        assert len(bad) == 0, f"Trial contains search providers: {bad}"

    def test_no_dormant_sources(self):
        """Trial allowlist 不应该包含 dormant 源。"""
        from pathlib import Path

        allowlist_path = Path("configs/foundation_trial_source_allowlist.example.yaml")
        with open(allowlist_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        trial_ids = [x["source_id"] for x in data["trial_source_ids"]]
        dormant = {"github_issues", "hacker_news"}
        bad = [x for x in trial_ids if x in dormant]
        assert len(bad) == 0, f"Trial contains dormant sources: {bad}"

    def test_no_tls_failed_sources(self):
        """Trial allowlist 不应该包含 TLS handshake failed 源。"""
        from pathlib import Path

        allowlist_path = Path("configs/foundation_trial_source_allowlist.example.yaml")
        with open(allowlist_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        trial_ids = [x["source_id"] for x in data["trial_source_ids"]]
        tls_failed = {"morgan_stanley_insights", "jp_morgan_research", "ubs_global_research",
                       "bofa_global_research_insights", "citi_research", "deutsche_bank_tech_conference"}
        bad = [x for x in trial_ids if x in tls_failed]
        assert len(bad) == 0, f"Trial contains TLS-failed sources: {bad}"

    def test_no_wechat_sources(self):
        """Trial allowlist 不应该包含微信待映射源。"""
        from pathlib import Path

        allowlist_path = Path("configs/foundation_trial_source_allowlist.example.yaml")
        with open(allowlist_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        trial_ids = [x["source_id"] for x in data["trial_source_ids"]]
        wechat_sources = {"goldman_sachs_china_wechat", "morgan_stanley_china_wechat",
                          "morgan_stanley_fund_wechat", "yanbaoshe_wechat",
                          "touyan_circle_wechat", "wechat_secondary_broadcast"}
        bad = [x for x in trial_ids if x in wechat_sources]
        assert len(bad) == 0, f"Trial contains WeChat sources: {bad}"

    def test_trial_source_ids_match_inventory(self):
        """Trial source_id 必须存在于 source inventory。"""
        from pathlib import Path

        allowlist_path = Path("configs/foundation_trial_source_allowlist.example.yaml")
        inventory_path = Path("configs/foundation_source_inventory.example.yaml")

        with open(allowlist_path, "r", encoding="utf-8") as f:
            allowlist = yaml.safe_load(f)
        with open(inventory_path, "r", encoding="utf-8") as f:
            inventory = yaml.safe_load(f)

        trial_ids = [x["source_id"] for x in allowlist["trial_source_ids"]]
        inventory_ids = {s["source_id"] for s in inventory["sources"]}

        for sid in trial_ids:
            assert sid in inventory_ids, f"Trial source_id not in inventory: {sid}"


class TestTrialConfig:
    """测试 trial config 文件。"""

    def test_trial_config_exists(self):
        """Trial config 文件应该存在。"""
        from pathlib import Path

        config_path = Path("configs/trae_foundation_trial_sources.example.yaml")
        assert config_path.exists(), f"Config not found: {config_path}"

    def test_trial_config_source_count(self):
        """Trial config 应该包含 16 个 sources。"""
        from pathlib import Path

        config_path = Path("configs/trae_foundation_trial_sources.example.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        sources = data.get("sources", [])
        assert len(sources) == 16, f"Expected 16 sources in trial config, got {len(sources)}"

    def test_trial_config_trial_metadata(self):
        """Trial config 应该有正确的 trial metadata。"""
        from pathlib import Path

        config_path = Path("configs/trae_foundation_trial_sources.example.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data.get("trial_mode") is True, "trial_mode should be True"
        assert data.get("production_mode") is False, "production_mode should be False"
        assert data.get("trial", {}).get("source_count") == 16, "trial source_count should be 16"

    def test_trial_config_all_enabled(self):
        """Trial config 中所有 source.enabled 应该是 True。"""
        from pathlib import Path

        config_path = Path("configs/trae_foundation_trial_sources.example.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        sources = data.get("sources", [])
        for s in sources:
            assert s.get("enabled") is True, f"Source {s['source_id']} should be enabled"

    def test_trial_config_has_feed_urls(self):
        """Trial config 中每个 source 应该有 feed_url。"""
        from pathlib import Path

        config_path = Path("configs/trae_foundation_trial_sources.example.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        sources = data.get("sources", [])
        for s in sources:
            assert s.get("feed_url"), f"Source {s['source_id']} missing feed_url"


class TestTrialCLI:
    """测试 trial CLI 命令。"""

    def test_trial_validate_command(self):
        """trial-validate 命令应该能正常执行。"""
        import subprocess

        result = subprocess.run(
            [
                sys.executable, "-m", "opc_foundation.source_inventory.cli",
                "trial-validate",
            ],
            capture_output=True,
            text=True,
            cwd="src/..",
        )
        assert result.returncode == 0, f"trial-validate failed: {result.stderr}"
        assert "Trial Configuration Validation: PASSED" in result.stdout
        assert "Trial source count: 16" in result.stdout

    def test_trial_run_dry_run_command(self):
        """trial-run --dry-run 命令应该能正常执行。"""
        import subprocess
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    sys.executable, "-m", "opc_foundation.source_inventory.cli",
                    "trial-run",
                    "--output-dir", tmp_dir,
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                cwd="src/..",
                timeout=60,
            )
            assert result.returncode == 0, f"trial-run --dry-run failed: {result.stderr}"
            assert "Trial run:" in result.stdout

            # 检查输出文件是否生成
            health = os.path.join(tmp_dir, "index", "source_health.jsonl")
            summary = os.path.join(tmp_dir, "index", "run_summary.json")
            assert os.path.exists(health), "source_health.jsonl should be generated"
            assert os.path.exists(summary), "run_summary.json should be generated"


class TestTrialScripts:
    """测试 PowerShell 脚本。"""

    def test_run_script_exists(self):
        """run_foundation_trial_sources.ps1 应该存在。"""
        from pathlib import Path

        script_path = Path("scripts/run_foundation_trial_sources.ps1")
        assert script_path.exists(), f"Run script not found: {script_path}"

    def test_check_script_exists(self):
        """check_foundation_trial_sources.ps1 应该存在。"""
        from pathlib import Path

        script_path = Path("scripts/check_foundation_trial_sources.ps1")
        assert script_path.exists(), f"Check script not found: {script_path}"

    def test_run_script_has_mode_params(self):
        """run 脚本应该支持 validate-config/dry-run/run 模式。"""
        from pathlib import Path

        script_path = Path("scripts/run_foundation_trial_sources.ps1")
        content = script_path.read_text(encoding="utf-8")

        assert 'Mode = "run"' in content or "-Mode " in content
        assert "validate-config" in content
        assert "dry-run" in content

    def test_run_script_has_proxy_param(self):
        """run 脚本应该支持 -Proxy 参数。"""
        from pathlib import Path

        script_path = Path("scripts/run_foundation_trial_sources.ps1")
        content = script_path.read_text(encoding="utf-8")

        assert "$Proxy" in content or "-Proxy" in content

    def test_run_script_sets_pythonpath(self):
        """run 脚本应该设置 PYTHONPATH。"""
        from pathlib import Path

        script_path = Path("scripts/run_foundation_trial_sources.ps1")
        content = script_path.read_text(encoding="utf-8")

        assert "PYTHONPATH" in content

    def test_run_script_auto_locates_repo_root(self):
        """run 脚本应该自动定位 RepoRoot。"""
        from pathlib import Path

        script_path = Path("scripts/run_foundation_trial_sources.ps1")
        content = script_path.read_text(encoding="utf-8")

        assert "Get-RepoRoot" in content
        assert ".git" in content
