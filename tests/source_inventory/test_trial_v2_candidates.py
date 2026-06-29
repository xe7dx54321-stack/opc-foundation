"""Trial v2 Candidates 模块测试（M3C-5A2）。

功能说明（小白解读）：
    测试 M3C-5A2 trial_v2 candidates 验证的结果。
    确保：
    1. trial_v2 candidate allowlist 文件存在
    2. candidate_count = 8
    3. candidate source_id 全部存在于 source inventory
    4. allowlist 不包含 trial v1 源
    5. allowlist 不包含 blocked/search/dormant/TLS/微信源
    6. run/check 脚本存在且支持 validate/dry-run/run 模式
    7. report 不包含完整 proxy URL
    8. report 明确不修改 TRAE scheduling
    9. data/foundation_trial_v2/ 不提交
"""

import pytest
import sys
from pathlib import Path

# 确保可以 import opc_foundation
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import yaml


# ---- Fixtures ----

@pytest.fixture
def trial_v2_allowlist():
    """加载 trial_v2 candidate allowlist 数据。"""
    allowlist_path = Path("configs/foundation_trial_v2_candidate_allowlist.example.yaml")
    with open(allowlist_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def source_inventory():
    """加载 source inventory 数据。"""
    inventory_path = Path("configs/foundation_source_inventory.example.yaml")
    with open(inventory_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def trial_v2_validation_report():
    """读取 trial_v2 validation 报告内容。"""
    report_path = Path("docs/foundation_trial_v2_validation_report.md")
    if not report_path.exists():
        pytest.skip("Trial v2 validation report not found")
    return report_path.read_text(encoding="utf-8")


# ---- Allowlist 存在性测试 ----

class TestTrialV2Allowlist:
    """测试 trial_v2 candidate allowlist 文件。"""

    def test_allowlist_exists(self):
        """Trial v2 candidate allowlist 应该存在。"""
        allowlist_path = Path("configs/foundation_trial_v2_candidate_allowlist.example.yaml")
        assert allowlist_path.exists(), f"Allowlist not found: {allowlist_path}"

    def test_allowlist_yaml_parseable(self):
        """Trial v2 candidate allowlist 应该可解析。"""
        allowlist_path = Path("configs/foundation_trial_v2_candidate_allowlist.example.yaml")
        with open(allowlist_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None, "Allowlist should be valid YAML"

    def test_candidate_count_is_8(self, trial_v2_allowlist):
        """Candidate 数应该为 8。"""
        expected = trial_v2_allowlist.get("scope", {}).get("candidate_count")
        candidates = trial_v2_allowlist.get("trial_v2_candidates", [])
        assert len(candidates) == 8, f"Expected 8 candidates, got {len(candidates)}"
        assert expected == 8, f"scope.candidate_count should be 8, got {expected}"

    def test_candidate_ids_unique(self, trial_v2_allowlist):
        """Candidate source_id 不应该有重复。"""
        candidates = trial_v2_allowlist.get("trial_v2_candidates", [])
        ids = [c["source_id"] for c in candidates]
        dupes = [sid for sid in ids if ids.count(sid) > 1]
        assert len(dupes) == 0, f"Duplicate candidate source_ids: {set(dupes)}"

    def test_all_candidates_in_source_inventory(self, trial_v2_allowlist, source_inventory):
        """所有 candidate source_id 应该存在于 source inventory。"""
        candidates = trial_v2_allowlist.get("trial_v2_candidates", [])
        inventory_ids = {s["source_id"] for s in source_inventory.get("sources", [])}
        for c in candidates:
            assert c["source_id"] in inventory_ids, f"Candidate {c['source_id']} not in inventory"

    def test_no_trial_v1_sources_in_candidates(self, trial_v2_allowlist):
        """Candidate 不应该包含 trial v1 源。"""
        trial_v1_ids = {
            "goldman_sachs_research",
            "goldman_sachs_reports",
            "goldman_sachs_top_of_mind",
            "goldman_sachs_insights",
            "barclays_our_insights",
            "microsoft_ir",
            "yahoo_finance",
            "business_insider",
            "markets_insider",
            "the_fly",
            "briefing_com_upgrades",
            "wallstreet_cn",
            "cls_cn",
            "wind_public",
            "gelonghui",
            "zhitong_caijing",
        }
        candidates = trial_v2_allowlist.get("trial_v2_candidates", [])
        candidate_ids = {c["source_id"] for c in candidates}
        conflict = trial_v1_ids & candidate_ids
        assert len(conflict) == 0, f"Trial v1 sources in candidates: {conflict}"

    def test_no_blocked_sources_in_candidates(self, trial_v2_allowlist):
        """Candidate 不应该包含 blocked 源。"""
        blocked_ids = {"telegram_groups", "cloud_drive_share", "pdf_download_sites",
                      "unknown_wechat_pdf", "report_download_proxy"}
        candidates = trial_v2_allowlist.get("trial_v2_candidates", [])
        candidate_ids = {c["source_id"] for c in candidates}
        conflict = blocked_ids & candidate_ids
        assert len(conflict) == 0, f"Blocked sources in candidates: {conflict}"

    def test_no_search_providers_in_candidates(self, trial_v2_allowlist):
        """Candidate 不应该包含 search provider。"""
        search_ids = {"tavily_search", "brave_search", "serpapi", "bing_search",
                     "google_cse", "searx", "duckduckgo", "yahoo_search",
                     "baidu_search", "custom_search"}
        candidates = trial_v2_allowlist.get("trial_v2_candidates", [])
        candidate_ids = {c["source_id"] for c in candidates}
        conflict = search_ids & candidate_ids
        assert len(conflict) == 0, f"Search providers in candidates: {conflict}"

    def test_no_dormant_sources_in_candidates(self, trial_v2_allowlist):
        """Candidate 不应该包含 dormant 源。"""
        dormant_ids = {"github_issues", "hacker_news"}
        candidates = trial_v2_allowlist.get("trial_v2_candidates", [])
        candidate_ids = {c["source_id"] for c in candidates}
        conflict = dormant_ids & candidate_ids
        assert len(conflict) == 0, f"Dormant sources in candidates: {conflict}"

    def test_no_tls_sources_in_candidates(self, trial_v2_allowlist):
        """Candidate 不应该包含 TLS 失败源。"""
        tls_ids = {"morgan_stanley_insights", "jp_morgan_research", "ubs_global_research",
                  "bofa_global_research_insights", "citi_research", "deutsche_bank_tech_conference"}
        candidates = trial_v2_allowlist.get("trial_v2_candidates", [])
        candidate_ids = {c["source_id"] for c in candidates}
        conflict = tls_ids & candidate_ids
        assert len(conflict) == 0, f"TLS sources in candidates: {conflict}"

    def test_no_wechat_sources_in_candidates(self, trial_v2_allowlist):
        """Candidate 不应该包含微信源。"""
        wechat_ids = {"goldman_sachs_china_wechat", "morgan_stanley_china_wechat",
                     "morgan_stanley_fund_wechat", "yanbaoshe_wechat",
                     "touyan_circle_wechat", "wechat_secondary_broadcast"}
        candidates = trial_v2_allowlist.get("trial_v2_candidates", [])
        candidate_ids = {c["source_id"] for c in candidates}
        conflict = wechat_ids & candidate_ids
        assert len(conflict) == 0, f"WeChat sources in candidates: {conflict}"


# ---- 脚本存在性测试 ----

class TestTrialV2Scripts:
    """测试 trial_v2 验证脚本。"""

    def test_run_script_exists(self):
        """run_foundation_trial_v2_candidates.ps1 应该存在。"""
        script_path = Path("scripts/run_foundation_trial_v2_candidates.ps1")
        assert script_path.exists(), f"Run script not found: {script_path}"

    def test_check_script_exists(self):
        """check_foundation_trial_v2_candidates.ps1 应该存在。"""
        script_path = Path("scripts/check_foundation_trial_v2_candidates.ps1")
        assert script_path.exists(), f"Check script not found: {script_path}"

    def test_run_script_supports_validate_config(self):
        """run 脚本应该支持 validate-config 模式。"""
        script_path = Path("scripts/run_foundation_trial_v2_candidates.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "validate-config" in content, "Script should support validate-config mode"

    def test_run_script_supports_dry_run(self):
        """run 脚本应该支持 dry-run 模式。"""
        script_path = Path("scripts/run_foundation_trial_v2_candidates.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "dry-run" in content, "Script should support dry-run mode"

    def test_run_script_supports_run_mode(self):
        """run 脚本应该支持 run 模式。"""
        script_path = Path("scripts/run_foundation_trial_v2_candidates.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert '"run"' in content or "'run'" in content, "Script should support run mode"

    def test_run_script_supports_proxy_param(self):
        """run 脚本应该支持 -Proxy 参数。"""
        script_path = Path("scripts/run_foundation_trial_v2_candidates.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "$Proxy" in content or "-Proxy" in content, "Script should support -Proxy parameter"

    def test_run_script_has_repo_root_logic(self):
        """run 脚本应该自动定位 RepoRoot。"""
        script_path = Path("scripts/run_foundation_trial_v2_candidates.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "Get-RepoRoot" in content or ".git" in content, "Script should auto-locate RepoRoot"

    def test_run_script_sets_pythonpath(self):
        """run 脚本应该设置 PYTHONPATH。"""
        script_path = Path("scripts/run_foundation_trial_v2_candidates.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "PYTHONPATH" in content, "Script should set PYTHONPATH"


# ---- 验证报告测试 ----

class TestTrialV2ValidationReport:
    """测试 trial_v2 验证报告。"""

    def test_validation_report_exists(self):
        """验证报告应该存在。"""
        report_path = Path("docs/foundation_trial_v2_validation_report.md")
        assert report_path.exists(), f"Validation report not found: {report_path}"

    def test_validation_report_has_m3c5a2(self, trial_v2_validation_report):
        """验证报告应该包含 M3C-5A2 标识。"""
        assert "M3C-5A2" in trial_v2_validation_report, "Report should mention M3C-5A2"

    def test_validation_report_has_check_results(self, trial_v2_validation_report):
        """验证报告应该包含 check 结果。"""
        assert "check" in trial_v2_validation_report.lower() or "检查" in trial_v2_validation_report

    def test_report_does_not_modify_trae(self, trial_v2_validation_report):
        """验证报告应该明确不修改 TRAE scheduling。"""
        # 检查报告中是否说明不修改 TRAE
        assert "TRAE" in trial_v2_validation_report or "trae" in trial_v2_validation_report.lower()
        # 应该提到"未修改"或"不修改"或"not modify"
        has_not_modify = ("未修改" in trial_v2_validation_report or 
                          "不修改" in trial_v2_validation_report or
                          "not modify" in trial_v2_validation_report.lower() or
                          "未变动" in trial_v2_validation_report)
        assert has_not_modify, "Report should mention not modifying TRAE"

    def test_report_does_not_affect_trial_v1(self, trial_v2_validation_report):
        """验证报告应该明确不影响 trial v1。"""
        # 报告中有"当前 trial v1"和"未受影响"
        assert "trial v1" in trial_v2_validation_report.lower() or "trial_v1" in trial_v2_validation_report.lower()
        has_not_affect = ("未受影响" in trial_v2_validation_report or 
                          "不受影响" in trial_v2_validation_report or
                          "不影响" in trial_v2_validation_report or
                          "not affect" in trial_v2_validation_report.lower() or
                          "不变" in trial_v2_validation_report)
        assert has_not_affect, "Report should mention not affecting trial v1"


# ---- 安全测试 ----

class TestTrialV2Security:
    """测试 trial_v2 相关文件不包含敏感信息。"""

    def test_report_no_full_proxy_url(self, trial_v2_validation_report):
        """验证报告不应该包含完整代理 URL。"""
        import re
        proxy_patterns = [
            r'http://[^:]+:\d+',
            r'https://[^:]+:\d+',
            r'socks5://',
            r'socks4://',
        ]
        for pattern in proxy_patterns:
            matches = re.findall(pattern, trial_v2_validation_report)
            assert len(matches) == 0, f"Proxy URL found in report: {matches}"

    def test_allowlist_no_secrets(self, trial_v2_allowlist):
        """Allowlist 不应该包含 secrets。"""
        import json
        allowlist_str = json.dumps(trial_v2_allowlist)
        sensitive_keywords = ["api_key", "secret", "token", "cookie", "password"]
        for kw in sensitive_keywords:
            assert kw.lower() not in allowlist_str.lower(), f"Sensitive keyword '{kw}' found in allowlist"


# ---- Gitignore 测试 ----

class TestTrialV2Gitignore:
    """测试 data/foundation_trial_v2/ 不被 git 追踪。"""

    def test_data_dir_in_gitignore(self):
        """data/foundation_trial/ 应该在 .gitignore 中（覆盖 foundation_trial_v2/）。"""
        gitignore_path = Path(".gitignore")
        gitignore_content = gitignore_path.read_text(encoding="utf-8")
        # 应该包含 data/foundation_trial/ 通配符
        assert "data/foundation_trial" in gitignore_content, ".gitignore should cover data/foundation_trial/"
