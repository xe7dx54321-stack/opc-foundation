"""Trial v2 Full Validation 模块测试（M3C-5A3）。

功能说明（小白解读）：
    测试 M3C-5A3 21 源 trial_v2 完整验证的结果。
    确保：
    1. trial_v2 allowlist 文件存在
    2. trial_v1 base count = 15
    3. trial_v2 additions count = 6
    4. operational source count = 21
    5. source inventory 总数保持 92
    6. consolidated candidate 只计为 1 个
    7. 不包含 blocked/search/dormant/TLS/微信源
    8. run/check 脚本存在且支持 validate/dry-run/run 模式
    9. report 不包含完整 proxy URL
    10. report 明确不修改 TRAE scheduling 和 trial_v1
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import yaml


# ---- Fixtures ----

@pytest.fixture
def trial_v2_allowlist():
    """加载 trial_v2 allowlist 数据。"""
    allowlist_path = Path("configs/foundation_trial_v2_allowlist.example.yaml")
    with open(allowlist_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def trial_v2_full_validation_report():
    """读取 trial_v2 full validation 报告。"""
    report_path = Path("docs/foundation_trial_v2_full_validation_report.md")
    if not report_path.exists():
        pytest.skip("Trial v2 full validation report not found")
    return report_path.read_text(encoding="utf-8")


@pytest.fixture
def source_inventory():
    """加载 source inventory 数据。"""
    inventory_path = Path("configs/foundation_source_inventory.example.yaml")
    with open(inventory_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---- Allowlist 存在性测试 ----

class TestTrialV2Allowlist:
    """测试 trial_v2 allowlist 文件。"""

    def test_trial_v2_allowlist_exists(self):
        """Trial v2 allowlist 应该存在。"""
        allowlist_path = Path("configs/foundation_trial_v2_allowlist.example.yaml")
        assert allowlist_path.exists(), f"Allowlist not found: {allowlist_path}"

    def test_trial_v2_allowlist_yaml_parseable(self):
        """Trial v2 allowlist 应该可解析。"""
        allowlist_path = Path("configs/foundation_trial_v2_allowlist.example.yaml")
        with open(allowlist_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None, "Allowlist should be valid YAML"

    def test_trial_v1_base_count_is_15(self, trial_v2_allowlist):
        """Trial v1 base count 应该为 15。"""
        scope = trial_v2_allowlist.get("scope", {})
        assert scope.get("base_trial_v1_count") == 15, "base_trial_v1_count should be 15"

    def test_trial_v2_additions_count_is_6(self, trial_v2_allowlist):
        """Trial v2 additions count 应该为 6。"""
        scope = trial_v2_allowlist.get("scope", {})
        assert scope.get("trial_v2_ready_additions_count") == 6, "trial_v2_ready_additions_count should be 6"

    def test_operational_source_count_is_21(self, trial_v2_allowlist):
        """Operational source count 应该为 21。"""
        scope = trial_v2_allowlist.get("scope", {})
        assert scope.get("operational_source_count") == 21, "operational_source_count should be 21"

    def test_source_inventory_count_should_remain_92(self, trial_v2_allowlist):
        """Source inventory count should remain 92。"""
        scope = trial_v2_allowlist.get("scope", {})
        assert scope.get("source_inventory_count_should_remain") == 92, "source_inventory_count_should_remain should be 92"

    def test_production_not_enabled(self, trial_v2_allowlist):
        """Production should not be enabled。"""
        scope = trial_v2_allowlist.get("scope", {})
        assert scope.get("production_enabled") == False, "production_enabled should be false"

    def test_trae_scheduling_not_enabled(self, trial_v2_allowlist):
        """TRAE scheduling should not be enabled。"""
        scope = trial_v2_allowlist.get("scope", {})
        assert scope.get("trae_scheduling_enabled") == False, "trae_scheduling_enabled should be false"


# ---- Trial v2 Additions 测试 ----

class TestTrialV2Additions:
    """测试 trial_v2 additions。"""

    def test_additions_count_is_6(self, trial_v2_allowlist):
        """Trial v2 additions 应该为 6 个。"""
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        assert len(additions) == 6, f"Expected 6 additions, got {len(additions)}"

    def test_all_additions_are_trial_v2_ready(self, trial_v2_allowlist):
        """所有 additions 的 trial_v2_status 应该为 trial_v2_ready。"""
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        for a in additions:
            assert a.get("trial_v2_status") == "trial_v2_ready", f"{a['source_id']} should be trial_v2_ready"

    def test_five_independent_additions_are_inventory_backed(self, trial_v2_allowlist):
        """5 个独立 additions 应该是 inventory_backed。"""
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        independent = [a for a in additions if a.get("candidate_type") == "inventory_backed"]
        assert len(independent) == 5, f"Expected 5 inventory_backed additions, got {len(independent)}"

    def test_one_consolidated_addition(self, trial_v2_allowlist):
        """应该有 1 个 consolidated addition。"""
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        consolidated = [a for a in additions if a.get("candidate_type") == "consolidated"]
        assert len(consolidated) == 1, f"Expected 1 consolidated addition, got {len(consolidated)}"

    def test_goldman_sachs_podcasts_is_consolidated(self, trial_v2_allowlist):
        """goldman_sachs_podcasts 应该是 consolidated。"""
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        gs_podcasts = [a for a in additions if a.get("source_id") == "goldman_sachs_podcasts"]
        assert len(gs_podcasts) == 1, "goldman_sachs_podcasts should be in additions"
        assert gs_podcasts[0].get("candidate_type") == "consolidated"

    def test_goldman_sachs_podcasts_has_3_member_sources(self, trial_v2_allowlist):
        """goldman_sachs_podcasts 应该包含 3 个 member_source_ids。"""
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        gs_podcasts = [a for a in additions if a.get("source_id") == "goldman_sachs_podcasts"][0]
        member_ids = gs_podcasts.get("member_source_ids", [])
        assert len(member_ids) == 3, f"Expected 3 member sources, got {len(member_ids)}"

    def test_all_independent_additions_in_source_inventory(self, trial_v2_allowlist, source_inventory):
        """所有独立 additions 的 source_id 应该存在于 source inventory。"""
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        independent = [a for a in additions if a.get("candidate_type") == "inventory_backed"]
        inventory_ids = {s["source_id"] for s in source_inventory.get("sources", [])}

        for a in independent:
            assert a["source_id"] in inventory_ids, f"{a['source_id']} not in inventory"


# ---- Consolidated Sources 测试 ----

class TestConsolidatedSources:
    """测试 consolidated sources。"""

    def test_consolidated_sources_has_goldman_podcasts(self, trial_v2_allowlist):
        """consolidated_sources 应该包含 goldman_sachs_podcasts。"""
        consolidated = trial_v2_allowlist.get("consolidated_sources", [])
        gs_entries = [c for c in consolidated if c.get("consolidated_source_id") == "goldman_sachs_podcasts"]
        assert len(gs_entries) == 1, "goldman_sachs_podcasts should be in consolidated_sources"

    def test_consolidated_sources_counts_as_1(self, trial_v2_allowlist):
        """consolidated sources 应该只计为 1 个 operational count。"""
        consolidated = trial_v2_allowlist.get("consolidated_sources", [])
        gs_entry = [c for c in consolidated if c.get("consolidated_source_id") == "goldman_sachs_podcasts"][0]
        assert gs_entry.get("operational_count") == 1, "operational_count should be 1"

    def test_consolidated_sources_has_3_members(self, trial_v2_allowlist):
        """consolidated sources 应该有 3 个 member sources。"""
        consolidated = trial_v2_allowlist.get("consolidated_sources", [])
        gs_entry = [c for c in consolidated if c.get("consolidated_source_id") == "goldman_sachs_podcasts"][0]
        assert gs_entry.get("member_count") == 3, "member_count should be 3"


# ---- 边界测试 ----

class TestTrialV2Boundaries:
    """测试 trial_v2 allowlist 的边界条件。"""

    def test_no_blocked_sources_in_additions(self, trial_v2_allowlist):
        """additions 不应该包含 blocked 源。"""
        blocked_ids = {"telegram_groups", "cloud_drive_share", "pdf_download_sites"}
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        addition_ids = {a["source_id"] for a in additions}
        conflict = blocked_ids & addition_ids
        assert len(conflict) == 0, f"Blocked sources in additions: {conflict}"

    def test_no_search_providers_in_additions(self, trial_v2_allowlist):
        """additions 不应该包含 search provider。"""
        search_ids = {"tavily_search", "brave_search", "serpapi"}
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        addition_ids = {a["source_id"] for a in additions}
        conflict = search_ids & addition_ids
        assert len(conflict) == 0, f"Search providers in additions: {conflict}"

    def test_no_dormant_sources_in_additions(self, trial_v2_allowlist):
        """additions 不应该包含 dormant 源。"""
        dormant_ids = {"github_issues", "hacker_news"}
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        addition_ids = {a["source_id"] for a in additions}
        conflict = dormant_ids & addition_ids
        assert len(conflict) == 0, f"Dormant sources in additions: {conflict}"

    def test_no_tls_sources_in_additions(self, trial_v2_allowlist):
        """additions 不应该包含 TLS 失败源。"""
        tls_ids = {"morgan_stanley_insights", "jp_morgan_research"}
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        addition_ids = {a["source_id"] for a in additions}
        conflict = tls_ids & addition_ids
        assert len(conflict) == 0, f"TLS sources in additions: {conflict}"

    def test_no_wechat_sources_in_additions(self, trial_v2_allowlist):
        """additions 不应该包含微信源。"""
        wechat_ids = {"goldman_sachs_china_wechat", "morgan_stanley_china_wechat"}
        additions = trial_v2_allowlist.get("trial_v2_additions", [])
        addition_ids = {a["source_id"] for a in additions}
        conflict = wechat_ids & addition_ids
        assert len(conflict) == 0, f"WeChat sources in additions: {conflict}"


# ---- 脚本存在性测试 ----

class TestTrialV2Scripts:
    """测试 trial_v2 验证脚本。"""

    def test_run_script_exists(self):
        """run_foundation_trial_v2.ps1 应该存在。"""
        script_path = Path("scripts/run_foundation_trial_v2.ps1")
        assert script_path.exists(), f"Run script not found: {script_path}"

    def test_check_script_exists(self):
        """check_foundation_trial_v2.ps1 应该存在。"""
        script_path = Path("scripts/check_foundation_trial_v2.ps1")
        assert script_path.exists(), f"Check script not found: {script_path}"

    def test_run_script_supports_validate_config(self):
        """run 脚本应该支持 validate-config 模式。"""
        script_path = Path("scripts/run_foundation_trial_v2.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "validate-config" in content, "Script should support validate-config mode"

    def test_run_script_supports_dry_run(self):
        """run 脚本应该支持 dry-run 模式。"""
        script_path = Path("scripts/run_foundation_trial_v2.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "dry-run" in content, "Script should support dry-run mode"

    def test_run_script_supports_run_mode(self):
        """run 脚本应该支持 run 模式。"""
        script_path = Path("scripts/run_foundation_trial_v2.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert '"run"' in content or "'run'" in content, "Script should support run mode"

    def test_run_script_supports_proxy_param(self):
        """run 脚本应该支持 -Proxy 参数。"""
        script_path = Path("scripts/run_foundation_trial_v2.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "$Proxy" in content or "-Proxy" in content, "Script should support -Proxy parameter"


# ---- 验证报告测试 ----

class TestTrialV2ValidationReport:
    """测试 trial_v2 验证报告。"""

    def test_validation_report_exists(self):
        """验证报告应该存在。"""
        report_path = Path("docs/foundation_trial_v2_full_validation_report.md")
        assert report_path.exists(), f"Validation report not found: {report_path}"

    def test_validation_report_has_m3c5a3(self, trial_v2_full_validation_report):
        """验证报告应该包含 M3C-5A3 标识。"""
        assert "M3C-5A3" in trial_v2_full_validation_report, "Report should mention M3C-5A3"

    def test_validation_report_has_21_sources(self, trial_v2_full_validation_report):
        """验证报告应该包含 21 个源。"""
        assert "21" in trial_v2_full_validation_report
        assert "Operational Total" in trial_v2_full_validation_report

    def test_report_does_not_modify_trae(self, trial_v2_full_validation_report):
        """验证报告应该明确不修改 TRAE scheduling。"""
        has_trae = "TRAE" in trial_v2_full_validation_report or "trae" in trial_v2_full_validation_report.lower()
        has_not_modify = ("未修改" in trial_v2_full_validation_report or 
                          "不修改" in trial_v2_full_validation_report or
                          "not modify" in trial_v2_full_validation_report.lower() or
                          "未变动" in trial_v2_full_validation_report)
        assert has_trae, "Report should mention TRAE"
        assert has_not_modify, "Report should mention not modifying TRAE"

    def test_report_does_not_modify_trial_v1(self, trial_v2_full_validation_report):
        """验证报告应该明确不修改 trial_v1。"""
        has_trial_v1 = "trial v1" in trial_v2_full_validation_report.lower() or "trial_v1" in trial_v2_full_validation_report.lower()
        has_not_affect = ("未受影响" in trial_v2_full_validation_report or 
                          "不受影响" in trial_v2_full_validation_report or
                          "不影响" in trial_v2_full_validation_report or
                          "not affect" in trial_v2_full_validation_report.lower() or
                          "不变" in trial_v2_full_validation_report)
        assert has_trial_v1, "Report should mention trial v1"
        assert has_not_affect, "Report should mention not affecting trial v1"

    def test_report_no_full_proxy_url(self, trial_v2_full_validation_report):
        """验证报告不应该包含完整代理 URL。"""
        import re
        proxy_patterns = [
            r'http://[^:]+:\d+',
            r'https://[^:]+:\d+',
            r'socks5://',
            r'socks4://',
        ]
        for pattern in proxy_patterns:
            matches = re.findall(pattern, trial_v2_full_validation_report)
            assert len(matches) == 0, f"Proxy URL found in report: {matches}"


# ---- Gitignore 测试 ----

class TestTrialV2Gitignore:
    """测试 data/foundation_trial_v2_full/ 不被 git 追踪。"""

    def test_data_dir_in_gitignore(self):
        """data/foundation_trial/ 应该在 .gitignore 中（覆盖 foundation_trial_v2_full/）。"""
        gitignore_path = Path(".gitignore")
        gitignore_content = gitignore_path.read_text(encoding="utf-8")
        assert "data/foundation_trial" in gitignore_content, ".gitignore should cover data/foundation_trial/"
