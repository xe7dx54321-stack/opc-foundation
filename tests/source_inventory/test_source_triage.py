"""Source Triage 模块测试。

功能说明（小白解读）：
    测试 triage 分桶逻辑是否正确。
    不同状态的 source 应该分到不同的桶里，
    不能搞错，比如 blocked 源绝对不能进 TRAE 试运行。
"""

import pytest

from opc_foundation.source_inventory.triage import (
    _detect_error_type,
    triage_source,
    triage_all_sources,
)
from opc_foundation.source_inventory.models import TriageBucket


class TestDetectErrorType:
    """测试错误类型检测函数。"""

    def test_dns_failure_getaddrinfo(self):
        """getaddrinfo 错误应该识别为 DNS 解析失败。"""
        result = _detect_error_type("[Errno 11001] getaddrinfo failed")
        assert result == "dns_resolution_failed"

    def test_tls_handshake_unexpected_eof(self):
        """SSL UNEXPECTED_EOF 应该识别为 TLS 握手失败。"""
        result = _detect_error_type("[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol")
        assert result == "tls_handshake_failed"

    def test_connection_reset_windows(self):
        """Windows 连接重置错误。"""
        result = _detect_error_type("[WinError 10054] 远程主机强迫关闭了一个现有的连接。")
        assert result == "connection_reset"

    def test_ssl_certificate_error(self):
        """SSL 证书错误。"""
        result = _detect_error_type("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch")
        assert result == "ssl_certificate_error"

    def test_http_404_from_message(self):
        """从错误信息里识别 404。"""
        result = _detect_error_type("HTTP Error: 404")
        assert result == "http_404"

    def test_http_403_from_status(self):
        """从 http_status 识别 403。"""
        result = _detect_error_type("", http_status=403)
        assert result == "http_403"

    def test_http_401_from_status(self):
        """从 http_status 识别 401。"""
        result = _detect_error_type("", http_status=401)
        assert result == "http_401"

    def test_timeout(self):
        """超时错误。"""
        result = _detect_error_type("timed out")
        assert result == "timeout"

    def test_unknown_error(self):
        """未知错误。"""
        result = _detect_error_type("some random error")
        assert result == "unknown"


class TestTriageSource:
    """测试单个 source 的分桶逻辑。"""

    def test_blocked_source(self):
        """blocked 源应该分到 blocked_by_policy 桶。"""
        source = {
            "source_id": "test_blocked",
            "source_name": "Test Blocked",
            "source_group": "blocked_high_risk_sources",
            "activation_priority": "blocked",
            "access_mode": "dormant",
            "url": "blocked:test",
        }
        result = triage_source(source)
        assert result.triage_bucket == TriageBucket.BLOCKED_BY_POLICY
        assert result.trae_trial_eligible is False

    def test_search_provider(self):
        """搜索 provider 应该分到 on_demand_only 桶。"""
        source = {
            "source_id": "test_search",
            "source_name": "Test Search",
            "source_group": "search_providers",
            "activation_priority": "supplement",
            "access_mode": "search_provider",
            "url": "https://example.com",
        }
        result = triage_source(source)
        assert result.triage_bucket == TriageBucket.ON_DEMAND_ONLY
        assert result.trae_trial_eligible is False

    def test_dormant_source(self):
        """休眠源应该分到 dormant 桶。"""
        source = {
            "source_id": "test_dormant",
            "source_name": "Test Dormant",
            "source_group": "community_dev_signals",
            "activation_priority": "supplement",
            "access_mode": "public_web",
            "url": "https://example.com",
        }
        result = triage_source(source)
        assert result.triage_bucket == TriageBucket.DORMANT
        assert result.trae_trial_eligible is False

    def test_live_ok_source(self):
        """live_ok 源应该分到 trae_trial_ready 桶。"""
        source = {
            "source_id": "test_ok",
            "source_name": "Test OK",
            "source_group": "official_public_research",
            "activation_priority": "S",
            "access_mode": "public_web",
            "url": "https://example.com",
        }
        live_result = {"source_id": "test_ok", "status": "live_ok"}
        result = triage_source(source, live_result)
        assert result.triage_bucket == TriageBucket.TRAE_TRIAL_READY
        assert result.trae_trial_eligible is True

    def test_live_ok_candidates_source(self):
        """live_ok_candidates_found 源也应该分到 trae_trial_ready 桶。"""
        source = {
            "source_id": "test_candidates",
            "source_name": "Test Candidates",
            "source_group": "official_public_research",
            "activation_priority": "S",
            "access_mode": "public_web",
            "url": "https://example.com",
        }
        live_result = {"source_id": "test_candidates", "status": "live_ok_candidates_found"}
        result = triage_source(source, live_result)
        assert result.triage_bucket == TriageBucket.TRAE_TRIAL_READY
        assert result.trae_trial_eligible is True

    def test_wechat_manual_source(self):
        """微信公众号 manual 源应该分到 wechat_archive_mapping_needed 桶。"""
        source = {
            "source_id": "test_wechat",
            "source_name": "测试公众号",
            "source_group": "chinese_rebroadcast",
            "activation_priority": "B",
            "access_mode": "manual",
            "url": "wechat:test_account",
        }
        live_result = {"source_id": "test_wechat", "status": "needs_connector"}
        result = triage_source(source, live_result)
        assert result.triage_bucket == TriageBucket.WECHAT_ARCHIVE_MAPPING_NEEDED
        assert result.trae_trial_eligible is False

    def test_dns_failed_source(self):
        """DNS 失败源应该分到 dns_resolution_failed 桶。"""
        source = {
            "source_id": "test_dns",
            "source_name": "Test DNS",
            "source_group": "official_public_research",
            "activation_priority": "S",
            "access_mode": "public_web",
            "url": "https://example.com",
        }
        live_result = {
            "source_id": "test_dns",
            "status": "failed",
            "error_message": "[Errno 11001] getaddrinfo failed",
        }
        result = triage_source(source, live_result)
        assert result.triage_bucket == TriageBucket.DNS_RESOLUTION_FAILED
        assert result.trae_trial_eligible is False

    def test_http_404_source(self):
        """404 源应该分到 http_4xx_or_404 桶。"""
        source = {
            "source_id": "test_404",
            "source_name": "Test 404",
            "source_group": "official_public_research",
            "activation_priority": "S",
            "access_mode": "public_web",
            "url": "https://example.com",
        }
        live_result = {
            "source_id": "test_404",
            "status": "http_error",
            "http_status": 404,
            "error_message": "HTTP Error: 404",
        }
        result = triage_source(source, live_result)
        assert result.triage_bucket == TriageBucket.HTTP_4XX_OR_404
        assert result.trae_trial_eligible is False

    def test_tls_handshake_failed_source(self):
        """TLS 握手失败源应该分到 tls_handshake_failed 桶。"""
        source = {
            "source_id": "test_tls",
            "source_name": "Test TLS",
            "source_group": "official_public_research",
            "activation_priority": "S",
            "access_mode": "public_web",
            "url": "https://example.com",
        }
        live_result = {
            "source_id": "test_tls",
            "status": "failed",
            "error_message": "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol",
        }
        result = triage_source(source, live_result)
        assert result.triage_bucket == TriageBucket.TLS_HANDSHAKE_FAILED
        assert result.trae_trial_eligible is False

    def test_blocked_never_trial_eligible(self):
        """blocked 源永远不能进入 TRAE 试运行。"""
        source = {
            "source_id": "bad_source",
            "source_name": "Bad Source",
            "source_group": "blocked_high_risk_sources",
            "activation_priority": "blocked",
            "access_mode": "dormant",
            "url": "blocked:bad",
        }
        # 即使 live smoke 显示 ok（不可能，但防御性测试）
        live_result = {"source_id": "bad_source", "status": "live_ok"}
        result = triage_source(source, live_result)
        assert result.trae_trial_eligible is False
        assert result.triage_bucket == TriageBucket.BLOCKED_BY_POLICY


class TestTriageAllSources:
    """测试批量分桶。"""

    def test_total_count(self):
        """总数应该等于输入数。"""
        sources = [
            {"source_id": f"src_{i}", "source_group": "official_public_research",
             "activation_priority": "S", "access_mode": "public_web", "url": "https://example.com"}
            for i in range(10)
        ]
        summary = triage_all_sources(sources)
        assert summary.total_sources == 10

    def test_mixed_sources(self):
        """混合类型的源应该分到不同的桶。"""
        sources = [
            {
                "source_id": "ok_1",
                "source_name": "OK 1",
                "source_group": "official_public_research",
                "activation_priority": "S",
                "access_mode": "public_web",
                "url": "https://example.com",
            },
            {
                "source_id": "blocked_1",
                "source_name": "Blocked 1",
                "source_group": "blocked_high_risk_sources",
                "activation_priority": "blocked",
                "access_mode": "dormant",
                "url": "blocked:test",
            },
            {
                "source_id": "search_1",
                "source_name": "Search 1",
                "source_group": "search_providers",
                "activation_priority": "supplement",
                "access_mode": "search_provider",
                "url": "https://example.com",
            },
        ]
        live_results = [
            {"source_id": "ok_1", "status": "live_ok"},
        ]
        summary = triage_all_sources(sources, live_results)
        
        assert summary.trae_trial_ready_count == 1
        assert summary.bucket_counts.get("blocked_by_policy", 0) == 1
        assert summary.bucket_counts.get("on_demand_only", 0) == 1
        
        # blocked 源不在 trial ready 列表里
        trial_ids = [r.source_id for r in summary.trae_trial_ready_sources]
        assert "blocked_1" not in trial_ids
        assert "search_1" not in trial_ids
        assert "ok_1" in trial_ids
