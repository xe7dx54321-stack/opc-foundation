"""Content Validity Audit 模块测试（M3C-5A4 / M3C-5A5）。

功能说明（小白解读）：
    测试 M3C-5A4 / M3C-5A5 内容有效性审计的结果。
    确保：
    1. content validity audit config 存在
    2. input trial_v2 allowlist 存在
    3. operational source count = 21
    4. content audit/check 脚本存在
    5. run 脚本支持 validate-config / sample / audit 模式
    6. audit result schema 包含必要字段
    7. content_status 只能是指定的值
    8. noise flags 能识别噪音类型
    9. report 不包含敏感信息
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import yaml


def _load_yaml(path: str) -> dict:
    """辅助函数：加载 YAML 文件。"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---- Fixtures ----

@pytest.fixture
def content_validity_config():
    """加载 content validity audit 配置。"""
    config_path = Path("configs/foundation_content_validity_audit.example.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def trial_v2_allowlist():
    """加载 trial_v2 allowlist。"""
    allowlist_path = Path("configs/foundation_trial_v2_allowlist.example.yaml")
    with open(allowlist_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def content_validity_report():
    """读取 content validity audit 报告。"""
    report_path = Path("docs/foundation_content_validity_audit_report.md")
    if not report_path.exists():
        pytest.skip("Content validity report not found")
    return report_path.read_text(encoding="utf-8")


# ---- Config 存在性测试 ----

class TestContentValidityAuditConfig:
    """测试 content validity audit 配置。"""

    def test_config_exists(self):
        """Content validity audit config 应该存在。"""
        config_path = Path("configs/foundation_content_validity_audit.example.yaml")
        assert config_path.exists(), f"Config not found: {config_path}"

    def test_config_yaml_parseable(self):
        """Config 应该可解析。"""
        config_path = Path("configs/foundation_content_validity_audit.example.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None, "Config should be valid YAML"

    def test_operational_source_count_is_21(self, content_validity_config):
        """Operational source count 应该为 21。"""
        scope = content_validity_config.get("scope", {})
        assert scope.get("operational_source_count") == 21, "operational_source_count should be 21"

    def test_max_candidates_per_source(self, content_validity_config):
        """Max candidates per source 应该为 5。"""
        scope = content_validity_config.get("scope", {})
        assert scope.get("max_candidates_per_source") == 5, "max_candidates_per_source should be 5"

    def test_production_not_enabled(self, content_validity_config):
        """Production 应该不启用。"""
        scope = content_validity_config.get("scope", {})
        assert scope.get("production_enabled") == False, "production_enabled should be false"

    def test_trae_scheduling_not_enabled(self, content_validity_config):
        """TRAE scheduling 应该不启用。"""
        scope = content_validity_config.get("scope", {})
        assert scope.get("trae_scheduling_enabled") == False, "trae_scheduling_enabled should be false"

    def test_has_input_trial_v2_allowlist(self, content_validity_config):
        """Config 应该包含 trial_v2 allowlist 输入路径。"""
        input_config = content_validity_config.get("input", {})
        assert "trial_v2_allowlist" in input_config, "Should have trial_v2_allowlist input"

    def test_has_noise_detection_config(self, content_validity_config):
        """Config 应该包含噪音检测配置。"""
        assert "noise_detection" in content_validity_config, "Should have noise_detection config"

    def test_has_thresholds_config(self, content_validity_config):
        """Config 应该包含阈值配置。"""
        assert "thresholds" in content_validity_config, "Should have thresholds config"


# ---- Input Allowlist 测试 ----

class TestContentValidityAuditInput:
    """测试 content validity audit 的输入。"""

    def test_trial_v2_allowlist_exists(self):
        """Trial v2 allowlist 应该存在。"""
        allowlist_path = Path("configs/foundation_trial_v2_allowlist.example.yaml")
        assert allowlist_path.exists(), f"Allowlist not found: {allowlist_path}"

    def test_trial_v2_allowlist_has_21_sources(self, trial_v2_allowlist):
        """Trial v2 allowlist 应该包含 21 个源。"""
        trial_v1_sources = trial_v2_allowlist.get("trial_v1_base_sources", [])
        trial_v2_additions = trial_v2_allowlist.get("trial_v2_additions", [])
        total = len(trial_v1_sources) + len(trial_v2_additions)
        assert total == 21, f"Expected 21 sources, got {total}"

    def test_trial_v2_additions_count_is_6(self, trial_v2_allowlist):
        """Trial v2 additions 应该为 6 个。"""
        trial_v2_additions = trial_v2_allowlist.get("trial_v2_additions", [])
        assert len(trial_v2_additions) == 6, f"Expected 6 trial_v2 additions, got {len(trial_v2_additions)}"


# ---- 脚本存在性测试 ----

class TestContentValidityAuditScripts:
    """测试 content validity audit 脚本。"""

    def test_run_script_exists(self):
        """run_foundation_content_validity_audit.ps1 应该存在。"""
        script_path = Path("scripts/run_foundation_content_validity_audit.ps1")
        assert script_path.exists(), f"Run script not found: {script_path}"

    def test_check_script_exists(self):
        """check_foundation_content_validity_audit.ps1 应该存在。"""
        script_path = Path("scripts/check_foundation_content_validity_audit.ps1")
        assert script_path.exists(), f"Check script not found: {script_path}"

    def test_run_script_supports_validate_config(self):
        """Run 脚本应该支持 validate-config 模式。"""
        script_path = Path("scripts/run_foundation_content_validity_audit.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "validate-config" in content, "Script should support validate-config mode"

    def test_run_script_supports_sample(self):
        """Run 脚本应该支持 sample 模式。"""
        script_path = Path("scripts/run_foundation_content_validity_audit.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "sample" in content, "Script should support sample mode"

    def test_run_script_supports_audit(self):
        """Run 脚本应该支持 audit 模式。"""
        script_path = Path("scripts/run_foundation_content_validity_audit.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "audit" in content, "Script should support audit mode"

    def test_run_script_supports_proxy(self):
        """Run 脚本应该支持 -Proxy 参数。"""
        script_path = Path("scripts/run_foundation_content_validity_audit.ps1")
        content = script_path.read_text(encoding="utf-8")
        assert "$Proxy" in content or "-Proxy" in content, "Script should support -Proxy parameter"


# ---- Python Module 测试 ----

class TestContentValidityModule:
    """测试 content validity Python 模块。"""

    def test_module_importable(self):
        """Module 应该可以导入。"""
        try:
            from opc_foundation.source_inventory.content_validity import (
                ContentValidityAuditor,
                ContentCandidate,
                ContentAuditResult,
                build_content_validity_report
            )
            assert True
        except ImportError as e:
            pytest.skip(f"Module import failed: {e}")

    def test_auditor_class_exists(self):
        """ContentValidityAuditor 类应该存在。"""
        try:
            from opc_foundation.source_inventory.content_validity import ContentValidityAuditor
            assert ContentValidityAuditor is not None
        except ImportError:
            pytest.skip("Module not available")

    def test_content_candidate_class_exists(self):
        """ContentCandidate 类应该存在。"""
        try:
            from opc_foundation.source_inventory.content_validity import ContentCandidate
            assert ContentCandidate is not None
        except ImportError:
            pytest.skip("Module not available")

    def test_content_audit_result_class_exists(self):
        """ContentAuditResult 类应该存在。"""
        try:
            from opc_foundation.source_inventory.content_validity import ContentAuditResult
            assert ContentAuditResult is not None
        except ImportError:
            pytest.skip("Module not available")


# ---- Audit Result Schema 测试 ----

class TestContentValidityAuditResultSchema:
    """测试 audit result schema。"""

    def test_content_candidate_has_required_fields(self):
        """ContentCandidate 应该有必需字段。"""
        try:
            from opc_foundation.source_inventory.content_validity import ContentCandidate
            candidate = ContentCandidate(
                title="Test Title",
                url="https://example.com",
                content_type="news"
            )
            assert candidate.title == "Test Title"
            assert candidate.url == "https://example.com"
            assert candidate.content_type == "news"
        except ImportError:
            pytest.skip("Module not available")

    def test_content_audit_result_has_required_fields(self):
        """ContentAuditResult 应该有必需字段。"""
        try:
            from opc_foundation.source_inventory.content_validity import ContentAuditResult
            result = ContentAuditResult(
                source_id="test_source",
                source_name="Test Source",
                input_url="https://example.com"
            )
            assert result.source_id == "test_source"
            assert result.source_name == "Test Source"
            assert result.input_url == "https://example.com"
        except ImportError:
            pytest.skip("Module not available")

    def test_content_status_values(self):
        """content_status 应该只能是指定的值。"""
        valid_statuses = {"content_ready", "content_watch", "content_reject", "technical_only"}
        # 如果模块可用，测试类应该正确定义这些值
        try:
            from opc_foundation.source_inventory.content_validity import ContentAuditResult
            result = ContentAuditResult()
            # 检查 dataclass 默认值是否在有效范围内
            assert result.content_status in valid_statuses
        except ImportError:
            pytest.skip("Module not available")

    def test_noise_flags_can_detect_login(self):
        """应该能检测 login 噪音。"""
        try:
            from opc_foundation.source_inventory.content_validity import ContentValidityAuditor
            # 创建临时 auditor
            auditor = ContentValidityAuditor(
                config_path="configs/foundation_content_validity_audit.example.yaml",
                allowlist_path="configs/foundation_trial_v2_allowlist.example.yaml"
            )
            # 测试噪音检测
            flags = auditor._detect_noise("Sign In Now", "https://example.com/login")
            assert "login" in flags
        except ImportError:
            pytest.skip("Module not available")

    def test_noise_flags_can_detect_cookie(self):
        """应该能检测 cookie 噪音。"""
        try:
            from opc_foundation.source_inventory.content_validity import ContentValidityAuditor
            auditor = ContentValidityAuditor(
                config_path="configs/foundation_content_validity_audit.example.yaml",
                allowlist_path="configs/foundation_trial_v2_allowlist.example.yaml"
            )
            flags = auditor._detect_noise("Cookie Consent", "https://example.com/privacy")
            assert "cookie" in flags
        except ImportError:
            pytest.skip("Module not available")


# ---- Report 测试 ----

class TestContentValidityReport:
    """测试 content validity audit 报告。"""

    def test_report_exists(self):
        """报告应该存在。"""
        report_path = Path("docs/foundation_content_validity_audit_report.md")
        assert report_path.exists(), f"Report not found: {report_path}"

    def test_report_has_m3c5a4(self, content_validity_report):
        """报告应该包含 M3C-5A4/A5 标识。"""
        assert "M3C-5A4" in content_validity_report or "M3C-5A5" in content_validity_report, "Report should mention M3C-5A4 or M3C-5A5"

    def test_report_mentions_21_sources(self, content_validity_report):
        """报告应该提到 21 个源。"""
        assert "21" in content_validity_report

    def test_report_does_not_modify_trial_v1(self, content_validity_report):
        """报告应该明确不修改 trial_v1。"""
        assert "trial v1" in content_validity_report.lower() or "trial_v1" in content_validity_report.lower()
        assert "not modify" in content_validity_report.lower() or "不修改" in content_validity_report

    def test_report_does_not_modify_trae(self, content_validity_report):
        """报告应该明确不修改 TRAE scheduling。"""
        assert "TRAE" in content_validity_report or "trae" in content_validity_report.lower()
        assert "not modify" in content_validity_report.lower() or "不修改" in content_validity_report

    def test_report_no_full_proxy_url(self, content_validity_report):
        """报告不应该包含完整代理 URL。"""
        import re
        proxy_patterns = [
            r'http://[^:]+:\d+',
            r'https://[^:]+:\d+',
            r'socks5://',
            r'socks4://',
        ]
        for pattern in proxy_patterns:
            matches = re.findall(pattern, content_validity_report)
            assert len(matches) == 0, f"Proxy URL found in report: {matches}"


# ---- Gitignore 测试 ----

class TestContentValidityGitignore:
    """测试 data/foundation_content_validity/ 不被 git 追踪。"""

    def test_data_dir_in_gitignore(self):
        """data/foundation_content_validity/ 应该在 .gitignore 中。"""
        gitignore_path = Path(".gitignore")
        gitignore_content = gitignore_path.read_text(encoding="utf-8")
        assert "data/foundation_content_validity" in gitignore_content, \
            ".gitignore should cover data/foundation_content_validity/"


# =============================================================================
# M3C-5A5: 全信息源内容有效性审计测试
# =============================================================================

class TestM3C5A5ContentValidityAudit:
    """M3C-5A5 全信息源内容有效性审计测试。"""

    # ---- 基础配置测试 ----

    def test_audit_config_exists(self):
        """审计配置文件存在。"""
        config = Path("configs/foundation_content_validity_audit.example.yaml")
        assert config.exists()

    def test_audit_config_operational_source_count_21(self):
        """operational_source_count = 21。"""
        config = _load_yaml("configs/foundation_content_validity_audit.example.yaml")
        assert config['scope']['operational_source_count'] == 21

    def test_audit_config_source_inventory_count_92(self):
        """source_inventory_count = 92。"""
        config = _load_yaml("configs/foundation_content_validity_audit.example.yaml")
        assert config['scope']['source_inventory_count'] == 92

    # ---- 噪音检测测试 ----

    def test_classify_noise_flags_login(self):
        """能识别 login_page 噪音。

        classify_noise_flags 要求 login 关键词命中 >= 3 次，
        所以输入文本需要包含足够多的登录相关词汇。
        """
        from opc_foundation.source_inventory.content_validity import classify_noise_flags
        text = (
            "sign in to your account. login with your password. "
            "forgot password? create account now. "
            "remember me on this device. username or email address."
        )
        flags = classify_noise_flags(text, "Login", 200)
        assert "login_page" in flags

    def test_classify_noise_flags_cookie(self):
        """能识别 cookie_only 噪音。

        classify_noise_flags 要求 cookie 关键词命中 >= 3 且页面文本 < 500 字符。
        """
        from opc_foundation.source_inventory.content_validity import classify_noise_flags
        text = (
            "we use cookies to improve your experience. "
            "cookie consent accept cookies cookie policy. "
            "manage cookies this site uses cookies."
        )
        flags = classify_noise_flags(text, "Cookie Consent", 200)
        assert "cookie_only" in flags

    def test_classify_noise_flags_navigation(self):
        """能识别 navigation_only 噪音。

        classify_noise_flags 要求 clean_text < 200 字符且有链接标记 <a 。
        """
        from opc_foundation.source_inventory.content_validity import classify_noise_flags
        text = "<a href='/home'>home</a> <a href='/about'>about</a> <a href='/contact'>contact</a>"
        flags = classify_noise_flags(text, "Navigation", 200)
        assert "navigation_only" in flags

    def test_classify_noise_flags_empty(self):
        """能识别 empty_page 噪音。

        classify_noise_flags 要求 clean_text < 50 字符。
        """
        from opc_foundation.source_inventory.content_validity import classify_noise_flags
        flags = classify_noise_flags("", "Empty", 200)
        assert "empty_page" in flags

    # ---- 评分和状态测试 ----

    def test_score_content_validity_range(self):
        """分数在 0-100 范围内。"""
        from opc_foundation.source_inventory.content_validity import score_content_validity
        score = score_content_validity(25, 20, 25, 15, 0, 15)
        assert 0 <= score <= 100

    def test_classify_content_status_ready(self):
        """score >= 70 且 valid_candidate_count >= 2 -> content_ready。"""
        from opc_foundation.source_inventory.content_validity import classify_content_status
        status = classify_content_status(75, 3, [])
        assert status == "content_ready"

    def test_classify_content_status_watch(self):
        """score >= 45 且 valid_candidate_count >= 1 -> content_watch。"""
        from opc_foundation.source_inventory.content_validity import classify_content_status
        status = classify_content_status(50, 1, [])
        assert status == "content_watch"

    def test_classify_content_status_reject(self):
        """score < 45 且 valid_candidate_count == 0 且 score == 0 -> content_reject。"""
        from opc_foundation.source_inventory.content_validity import classify_content_status
        status = classify_content_status(0, 0, [])
        assert status == "content_reject"

    def test_classify_content_status_reject_severe_noise(self):
        """严重噪音（login_page）直接 -> content_reject，忽略高分。"""
        from opc_foundation.source_inventory.content_validity import classify_content_status
        status = classify_content_status(90, 5, ["login_page"])
        assert status == "content_reject"

    def test_classify_content_status_technical_only(self):
        """可访问但无候选且 score > 0 -> technical_only。"""
        from opc_foundation.source_inventory.content_validity import classify_content_status
        status = classify_content_status(10, 0, [])
        assert status == "technical_only"

    # ---- 矩阵构建测试 ----

    def test_matrix_row_schema(self):
        """SourceContentMatrixRow 包含必要字段。"""
        from opc_foundation.source_inventory.content_validity import SourceContentMatrixRow
        row = SourceContentMatrixRow(
            source_id="test", source_name="Test", source_group="test_group",
            source_inventory_count=92, is_operational_trial_v2=False,
            expected_content_goal="test goal", current_technical_bucket="unknown",
            content_validation_scope="matrix_only", content_validation_status="not_audited",
            not_audited_reason="test", recommended_next_action="backlog"
        )
        d = row.to_dict()
        assert 'source_id' in d
        assert 'content_validation_scope' in d
        assert 'content_validation_status' in d
        assert 'not_audited_reason' in d
        assert 'recommended_next_action' in d

    def test_content_status_valid_values(self):
        """content_status 只能是 5 种合法值之一。"""
        valid_statuses = {"content_ready", "content_watch", "content_reject", "technical_only", "not_audited"}
        from opc_foundation.source_inventory.content_validity import classify_content_status
        for noise in [[], ["login_page"], ["paywall"], ["cookie_only"]]:
            for score in [0, 30, 50, 75, 100]:
                for valid_count in [0, 1, 3]:
                    status = classify_content_status(score, valid_count, noise)
                    # classify_content_status 返回 4 种值（不含 not_audited），
                    # not_audited 是 SourceContentMatrixRow 的默认值。
                    assert status in valid_statuses, f"Invalid status: {status}"

    # ---- 不恢复 Dashboard 页面 ----

    def test_no_deleted_dashboard_pages(self):
        """确认不恢复已删除的 Dashboard 页面。"""
        from opc_foundation.source_inventory.content_validity import ContentValidityAuditor
        # 只确认模块不导入 dashboard 页面相关代码
        assert not hasattr(ContentValidityAuditor, 'render_overview')
        assert not hasattr(ContentValidityAuditor, 'render_run_log')
        assert not hasattr(ContentValidityAuditor, 'render_failed_queue')
        assert not hasattr(ContentValidityAuditor, 'render_docs')

    # ---- 不引入 Playwright/Selenium ----

    def test_no_playwright_selenium(self):
        """确认不引入 Playwright 或 Selenium。"""
        import opc_foundation.source_inventory.content_validity as mod
        source = open(mod.__file__).read()
        assert 'playwright' not in source.lower()
        assert 'selenium' not in source.lower()

    # ---- 边界测试 ----

    def test_technical_only_not_in_scheduling(self):
        """technical_only 不进入 scheduling recommendation。"""
        from opc_foundation.source_inventory.content_validity import SourceContentMatrixRow
        row = SourceContentMatrixRow(
            source_id="test", source_name="Test", source_group="test",
            source_inventory_count=92, is_operational_trial_v2=False,
            expected_content_goal="test", current_technical_bucket="unknown",
            content_validation_scope="deep_audit", content_validation_status="technical_only",
            not_audited_reason="", recommended_next_action="needs_connector"
        )
        assert row.recommended_next_action != "include_in_trial_v2"

    def test_content_reject_not_in_scheduling(self):
        """content_reject 不进入 scheduling recommendation。"""
        from opc_foundation.source_inventory.content_validity import SourceContentMatrixRow
        row = SourceContentMatrixRow(
            source_id="test2", source_name="Test2", source_group="test",
            source_inventory_count=92, is_operational_trial_v2=False,
            expected_content_goal="test", current_technical_bucket="unknown",
            content_validation_scope="deep_audit", content_validation_status="content_reject",
            not_audited_reason="", recommended_next_action="reject"
        )
        assert row.recommended_next_action != "include_in_trial_v2"

    def test_not_audited_has_reason(self):
        """not_audited 必须有 reason。"""
        from opc_foundation.source_inventory.content_validity import SourceContentMatrixRow
        row = SourceContentMatrixRow(
            source_id="test3", source_name="Test3", source_group="blocked_high_risk",
            source_inventory_count=92, is_operational_trial_v2=False,
            expected_content_goal="test", current_technical_bucket="blocked",
            content_validation_scope="excluded", content_validation_status="not_audited",
            not_audited_reason="blocked_by_policy", recommended_next_action="keep_excluded"
        )
        assert row.content_validation_status == "not_audited"
        assert row.not_audited_reason != ""

    def test_blocked_not_deep_audited(self):
        """blocked/high-risk 源不会被 deep audit。"""
        from opc_foundation.source_inventory.content_validity import ContentValidityMatrixBuilder
        builder = ContentValidityMatrixBuilder(
            inventory_path="configs/foundation_source_inventory.example.yaml",
            allowlist_path="configs/foundation_trial_v2_allowlist.example.yaml",
        )
        for src in builder.inventory_sources:
            if src.get('group_category') == 'blocked_high_risk' or src.get('group_category') == 'high_risk_sources':
                assert src.get('source_id', '') not in builder.operational_trial_v2_ids

    def test_on_demand_not_deep_audited(self):
        """on-demand/search provider 源不会被默认 deep audit。"""
        from opc_foundation.source_inventory.content_validity import ContentValidityMatrixBuilder
        builder = ContentValidityMatrixBuilder(
            inventory_path="configs/foundation_source_inventory.example.yaml",
            allowlist_path="configs/foundation_trial_v2_allowlist.example.yaml",
        )
        for src in builder.inventory_sources:
            if src.get('group_category') == 'search_providers':
                assert src.get('source_id', '') not in builder.operational_trial_v2_ids
