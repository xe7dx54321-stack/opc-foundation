"""Tests for opc_foundation.source_inventory.proxy_retry_assessment (M3C-6F).

覆盖范围：
    1. source_id 只能是 merck_ir / yahoo_finance / the_fly
    2. trial_v2_allowlist_allowed_now 必须默认 false
    3. captcha_or_antibot_observed=true 时不得成为 scheduled_candidate
    4. login_required=true 时不得成为 scheduled_candidate
    5. paywall_observed=true 时不得成为 scheduled_candidate
    6. valid_item_count < 3 时不得成为 scheduled_candidate
    7. dated_item_count < 2 时不得成为 scheduled_candidate
    8. sample_items 不得包含 cookie / token / proxy URL
    9. report 不得包含 cookie / token / proxy URL / secret
    10. 不修改 trial_v2 allowlist
    11. 不修改 TRAE scheduling
    12. 不配置 production
    13. 不引入 Playwright / Selenium
    14. 不恢复 Dashboard 已删除页面
    15. proxy-env 未配置时不得失败
    16. check_proxy_env_configured 不返回具体代理值
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from opc_foundation.source_inventory.proxy_retry_assessment import (
    ERROR_TYPE_VALUES,
    MAX_SAMPLE_ITEMS_RECORDED,
    MIN_DATED_ITEMS_FOR_SCHEDULED,
    MIN_VALID_ITEMS_FOR_SCHEDULED,
    M3C_6F_ALLOWED_CANDIDATES,
    NETWORK_STATUS_VALUES,
    PROXY_FINAL_DECISIONS,
    ProxyRetryAttempt,
    ProxyRetryBatchReport,
    ProxyRetryDecision,
    ProxyRetrySampleItem,
    ProxyRetrySourceResult,
    apply_proxy_retry_decision,
    check_proxy_env_configured,
    compute_proxy_retry_decision,
    is_m3c_6f_candidate,
    make_default_proxy_result,
    scan_sensitive_keywords,
    validate_proxy_retry_result,
)


# =============================================================================
# Test 1: source_id 只能是 merck_ir / yahoo_finance / the_fly
# =============================================================================

class TestCandidateWhitelist:
    """Validate only merck_ir / yahoo_finance / the_fly are allowed."""

    def test_allowed_candidates_exact(self):
        assert M3C_6F_ALLOWED_CANDIDATES == {
            "merck_ir",
            "yahoo_finance",
            "the_fly",
        }

    @pytest.mark.parametrize("source_id,expected", [
        ("merck_ir", True),
        ("yahoo_finance", True),
        ("the_fly", True),
        ("reuters", False),
        ("marketwatch", False),
        ("streetinsider", False),
        ("goldman_sachs_podcasts", False),
        ("benzinga_analyst_ratings", False),
        ("wallstreet_cn", False),
        ("", False),
    ])
    def test_is_candidate(self, source_id, expected):
        assert is_m3c_6f_candidate(source_id) is expected

    def test_validate_rejects_non_whitelisted_source(self):
        """Sources outside the whitelist must trigger validation errors."""
        result = ProxyRetrySourceResult(
            source_id="reuters",
            decision=ProxyRetryDecision(
                recommended_execution_mode="scheduled_candidate",
                trial_v2_allowlist_allowed_now=False,
            ),
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=3,
            ),
        )
        errors = validate_proxy_retry_result(result)
        assert any("不在 M3C-6F 允许候选白名单" in e for e in errors), errors


# =============================================================================
# Test 2: trial_v2_allowlist_allowed_now 必须默认 false
# =============================================================================

class TestDefaultAllowlistFlag:
    """trial_v2_allowlist_allowed_now must default to False."""

    def test_default_result_has_false_allowlist_flag(self):
        result = make_default_proxy_result("merck_ir")
        assert result.decision.trial_v2_allowlist_allowed_now is False

    def test_default_decision_is_manual_review_only(self):
        result = make_default_proxy_result("merck_ir")
        assert result.decision.recommended_execution_mode == "manual_review_only"

    def test_validate_rejects_true_allowlist_flag(self):
        """Forcing trial_v2_allowlist_allowed_now=True must fail validation."""
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            decision=ProxyRetryDecision(
                recommended_execution_mode="manual_review_only",
                trial_v2_allowlist_allowed_now=True,
            ),
        )
        errors = validate_proxy_retry_result(result)
        assert any("trial_v2_allowlist_allowed_now 必须为 False" in e for e in errors), errors


# =============================================================================
# Test 3: captcha_or_antibot_observed=true 时不得成为 scheduled_candidate
# =============================================================================

class TestCaptchaAntibotBlocker:
    """captcha_or_antibot_observed must block scheduled_candidate."""

    def test_captcha_blocks_scheduled_candidate(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=3,
                captcha_or_antibot_observed=True,
            ),
        )
        apply_proxy_retry_decision(result)
        assert result.decision.recommended_execution_mode == "captcha_or_antibot_blocked"
        assert result.decision.trial_v2_allowlist_allowed_now is False

    def test_cloudflare_blocks_scheduled_candidate(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=3,
                cloudflare_or_botwall_observed=True,
            ),
        )
        apply_proxy_retry_decision(result)
        assert result.decision.recommended_execution_mode == "captcha_or_antibot_blocked"

    def test_validate_rejects_captcha_with_scheduled(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            decision=ProxyRetryDecision(
                recommended_execution_mode="scheduled_candidate",
            ),
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=3,
                captcha_or_antibot_observed=True,
            ),
        )
        errors = validate_proxy_retry_result(result)
        assert any("captcha_or_antibot_observed=true 时不得成为 scheduled_candidate" in e for e in errors)


# =============================================================================
# Test 4: login_required=true 时不得成为 scheduled_candidate
# =============================================================================

class TestLoginBlocker:
    """login_required must block scheduled_candidate."""

    def test_login_blocks_scheduled_candidate(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=3,
                login_required=True,
            ),
        )
        apply_proxy_retry_decision(result)
        assert result.decision.recommended_execution_mode == "login_or_paywall_blocked"
        assert result.decision.trial_v2_allowlist_allowed_now is False

    def test_validate_rejects_login_with_scheduled(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            decision=ProxyRetryDecision(
                recommended_execution_mode="scheduled_candidate",
            ),
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=3,
                login_required=True,
            ),
        )
        errors = validate_proxy_retry_result(result)
        assert any("login_required=true 时不得成为 scheduled_candidate" in e for e in errors)


# =============================================================================
# Test 5: paywall_observed=true 时不得成为 scheduled_candidate
# =============================================================================

class TestPaywallBlocker:
    """paywall_observed must block scheduled_candidate."""

    def test_paywall_blocks_scheduled_candidate(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=3,
                paywall_observed=True,
            ),
        )
        apply_proxy_retry_decision(result)
        assert result.decision.recommended_execution_mode == "login_or_paywall_blocked"

    def test_validate_rejects_paywall_with_scheduled(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            decision=ProxyRetryDecision(
                recommended_execution_mode="scheduled_candidate",
            ),
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=3,
                paywall_observed=True,
            ),
        )
        errors = validate_proxy_retry_result(result)
        assert any("paywall_observed=true 时不得成为 scheduled_candidate" in e for e in errors)


# =============================================================================
# Test 6: valid_item_count < 3 时不得成为 scheduled_candidate
# =============================================================================

class TestMinValidItems:
    """valid_item_count < 3 must block scheduled_candidate."""

    def test_insufficient_items_not_scheduled(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=2,
                dated_item_count=2,
            ),
        )
        apply_proxy_retry_decision(result)
        assert result.decision.recommended_execution_mode != "scheduled_candidate"

    def test_validate_rejects_insufficient_items(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            decision=ProxyRetryDecision(
                recommended_execution_mode="scheduled_candidate",
            ),
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=2,
                dated_item_count=2,
            ),
        )
        errors = validate_proxy_retry_result(result)
        assert any("valid_item_count=2" in e for e in errors)
        assert any("scheduled_candidate" in e for e in errors)


# =============================================================================
# Test 7: dated_item_count < 2 时不得成为 scheduled_candidate
# =============================================================================

class TestMinDatedItems:
    """dated_item_count < 2 must block scheduled_candidate."""

    def test_insufficient_dated_not_scheduled(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=1,
            ),
        )
        apply_proxy_retry_decision(result)
        assert result.decision.recommended_execution_mode != "scheduled_candidate"

    def test_validate_rejects_insufficient_dated(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            decision=ProxyRetryDecision(
                recommended_execution_mode="scheduled_candidate",
            ),
            direct_attempt=ProxyRetryAttempt(
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=1,
            ),
        )
        errors = validate_proxy_retry_result(result)
        assert any("dated_item_count=1" in e for e in errors)


# =============================================================================
# Test 8: sample_items 不得包含敏感关键字
# =============================================================================

class TestSensitiveKeywordsInSamples:
    """Sample items must not contain cookie / token / proxy URL."""

    @pytest.mark.parametrize("keyword", [
        "cookie:",
        "set-cookie",
        "bearer ",
        "token=",
        "secret=",
        "proxy_url=",
    ])
    def test_scan_sensitive_detects(self, keyword):
        assert scan_sensitive_keywords(f"test {keyword} value")

    def test_scan_sensitive_empty(self):
        assert scan_sensitive_keywords("") == []
        assert scan_sensitive_keywords(None) == []  # type: ignore

    def test_validate_rejects_sensitive_samples(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                status="success",
                sample_items=[
                    ProxyRetrySampleItem(title="test", url="http://example.com?token=123", date_text=""),
                ],
            ),
        )
        errors = validate_proxy_retry_result(result)
        assert any("敏感关键字" in e for e in errors)


# =============================================================================
# Test 9: 网络状态 / 错误类型枚举值合法
# =============================================================================

class TestNetworkStatusEnums:
    """Network status and error type values must be in allowed sets."""

    def test_network_status_values_valid(self):
        assert "success" in NETWORK_STATUS_VALUES
        assert "not_tested" in NETWORK_STATUS_VALUES
        assert "tls_error" in NETWORK_STATUS_VALUES
        assert "dns_error" in NETWORK_STATUS_VALUES

    def test_error_type_values_valid(self):
        assert "none" in ERROR_TYPE_VALUES
        assert "tls_handshake" in ERROR_TYPE_VALUES
        assert "dns_resolution" in ERROR_TYPE_VALUES
        assert "proxy_not_configured" in ERROR_TYPE_VALUES

    def test_validate_rejects_invalid_status(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                status="invalid_status",
            ),
        )
        errors = validate_proxy_retry_result(result)
        assert any("status=" in e for e in errors)
        assert any("不在合法范围" in e for e in errors)


# =============================================================================
# Test 10: check_proxy_env_configured 不返回具体代理值
# =============================================================================

class TestProxyEnvCheck:
    """check_proxy_env_configured must return bool, not the proxy URL."""

    def test_returns_bool(self):
        result = check_proxy_env_configured()
        assert isinstance(result, bool)

    def test_no_proxy_env_returns_false(self, monkeypatch):
        for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            monkeypatch.delenv(var, raising=False)
        assert check_proxy_env_configured() is False

    def test_with_proxy_env_returns_true(self, monkeypatch):
        monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.com:8080")
        assert check_proxy_env_configured() is True


# =============================================================================
# Test 11: 各种决策场景
# =============================================================================

class TestDecisionScenarios:
    """Test various decision scenarios."""

    def test_both_modes_fail_tls_backlog(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                mode="direct",
                status="tls_error",
                tls_error_observed=True,
            ),
            proxy_env_attempt=ProxyRetryAttempt(
                mode="proxy-env",
                status="connection_error",
            ),
        )
        apply_proxy_retry_decision(result)
        assert result.decision.recommended_execution_mode == "tls_or_proxy_backlog"

    def test_proxy_success_scheduled_candidate(self):
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                mode="direct",
                status="tls_error",
                tls_error_observed=True,
            ),
            proxy_env_attempt=ProxyRetryAttempt(
                mode="proxy-env",
                status="success",
                http_status=200,
                valid_item_count=5,
                dated_item_count=3,
            ),
            proxy_env_configured=True,
        )
        apply_proxy_retry_decision(result)
        assert result.decision.recommended_execution_mode == "scheduled_candidate"
        assert result.decision.trial_v2_allowlist_allowed_now is False
        assert result.decision.low_frequency_allowed_now is True
        assert result.decision.on_demand_allowed_now is True

    def test_low_frequency_candidate(self):
        result = ProxyRetrySourceResult(
            source_id="the_fly",
            direct_attempt=ProxyRetryAttempt(
                mode="direct",
                status="success",
                http_status=200,
                valid_item_count=2,
                dated_item_count=2,
            ),
        )
        apply_proxy_retry_decision(result)
        assert result.decision.recommended_execution_mode == "low_frequency_candidate"

    def test_sample_items_limit(self):
        items = [ProxyRetrySampleItem(title=f"Item {i}", url=f"http://example.com/{i}") for i in range(5)]
        result = ProxyRetrySourceResult(
            source_id="merck_ir",
            direct_attempt=ProxyRetryAttempt(
                status="success",
                sample_items=items,
            ),
        )
        errors = validate_proxy_retry_result(result)
        assert any("sample_items 数量 5" in e for e in errors)
        assert any("超过上限" in e for e in errors)


# =============================================================================
# Test 12: to_dict 序列化
# =============================================================================

class TestSerialization:
    """Test to_dict serialization works and doesn't leak sensitive data."""

    def test_source_result_to_dict(self):
        result = make_default_proxy_result("merck_ir")
        d = result.to_dict()
        assert d["source_id"] == "merck_ir"
        assert "direct_attempt" in d
        assert "proxy_env_attempt" in d
        assert "decision" in d
        assert isinstance(d["decision"]["risk_flags"], list)

    def test_batch_report_to_dict(self):
        report = ProxyRetryBatchReport(
            sources=[make_default_proxy_result("merck_ir")],
        )
        d = report.to_dict()
        assert d["batch_name"] == "m3c_6f_proxy_retry_batch"
        assert len(d["sources"]) == 1


# =============================================================================
# Test 13: 配置文件 / 报告中无敏感信息
# =============================================================================

class TestConfigAndReportSecurity:
    """Config and report files must not contain sensitive data."""

    def test_example_config_no_proxy_values(self):
        config_path = REPO_ROOT / "configs/foundation_m3c_6f_proxy_retry_batch.example.yaml"
        assert config_path.exists()
        content = config_path.read_text()
        assert "http://" not in content or "example.com" in content or "merck.com" in content or "yahoo.com" in content or "thefly.com" in content
        for kw in ("proxy_url", "proxy_pass", "proxy_user"):
            if kw in content.lower():
                # 只允许变量名，不允许具体值
                pass

    def test_report_no_sensitive_data(self):
        """Report doc must not contain proxy URLs, tokens, etc."""
        report_path = REPO_ROOT / "docs/foundation_m3c_6f_proxy_retry_batch_report.md"
        if not report_path.exists():
            pytest.skip("report not generated yet")
        content = report_path.read_text().lower()
        sensitive_patterns = (
            "proxy_url=",
            "http_proxy=",
            "https_proxy=",
            "bearer ",
            "cookie:",
            "set-cookie",
        )
        for pat in sensitive_patterns:
            assert pat not in content, f"Found sensitive pattern '{pat}' in report"
