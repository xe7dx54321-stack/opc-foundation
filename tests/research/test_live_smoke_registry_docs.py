"""Phase 2H 测试：Live Smoke Registry 文档与生产准备就绪说明。

覆盖：
    1. live smoke registry 文档存在
    2. production readiness 文档存在
    3. live smoke registry 包含 6 个已验证 source_type
    4. production readiness 包含 Production Trial Ready
    5. 文档明确 manual_url optional / skipped
    6. 文档明确 wechat_archive pending / separate track
    7. 文档明确不做 JS rendering / browser automation
    8. 文档明确不绕过 paywall
    9. 文档明确不下载 PDF / OCR
    10. 文档明确不下载音频 / 转写音频
    11. 文档明确不做 investment judgment / trade signal
    12. 文档明确 downstream consumes documents.jsonl
    13. production example config 全部 enabled=false
    14. 文档中不得包含真实 local config 路径内容或 secrets
    15. research_source_foundation.md 包含 Phase 2H
"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.config.loader import load_yaml_config
from opc_foundation.research.config import load_research_config, validate_research_config


# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DOC = PROJECT_ROOT / "docs" / "research_source_live_smoke_registry.md"
READINESS_DOC = PROJECT_ROOT / "docs" / "research_source_production_readiness.md"
FOUNDATION_DOC = PROJECT_ROOT / "docs" / "research_source_foundation.md"
PRODUCTION_RUN_DOC = PROJECT_ROOT / "docs" / "research_source_production_run.md"
PRODUCTION_EXAMPLE = PROJECT_ROOT / "configs" / "research_sources.production.example.yaml"


# ---------------------------------------------------------------------------
# 1. 文档存在性
# ---------------------------------------------------------------------------


def test_live_smoke_registry_doc_exists() -> None:
    """live smoke registry 文档必须存在。"""
    assert REGISTRY_DOC.exists(), f"文档不存在: {REGISTRY_DOC}"


def test_production_readiness_doc_exists() -> None:
    """production readiness 文档必须存在。"""
    assert READINESS_DOC.exists(), f"文档不存在: {READINESS_DOC}"


def test_foundation_doc_exists() -> None:
    """research_source_foundation.md 文档必须存在。"""
    assert FOUNDATION_DOC.exists(), f"文档不存在: {FOUNDATION_DOC}"


def test_production_run_doc_exists() -> None:
    """research_source_production_run.md 文档必须存在。"""
    assert PRODUCTION_RUN_DOC.exists(), f"文档不存在: {PRODUCTION_RUN_DOC}"


# ---------------------------------------------------------------------------
# 2. live smoke registry 包含 6 个已验证 source_type
# ---------------------------------------------------------------------------


def test_registry_contains_six_verified_source_types() -> None:
    """live smoke registry 必须包含 6 个已验证 source_type。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    verified_types = [
        "official_public_research",
        "podcast_transcript",
        "conference_transcript",
        "analyst_action",
        "media_mention",
        "rss_feed",
    ]
    for st in verified_types:
        assert st in content, f"registry 文档缺少 source_type: {st}"


# ---------------------------------------------------------------------------
# 3. production readiness 包含 Production Trial Ready
# ---------------------------------------------------------------------------


def test_readiness_contains_production_trial_ready() -> None:
    """production readiness 文档必须包含 Production Trial Ready。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert "Production Trial Ready" in content, "readiness 文档缺少 Production Trial Ready"


# ---------------------------------------------------------------------------
# 4. 文档明确 manual_url optional / skipped
# ---------------------------------------------------------------------------


def test_registry_mentions_manual_url_optional() -> None:
    """registry 文档必须明确 manual_url 可跳过。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "manual_url" in content, "registry 文档缺少 manual_url"
    assert "skipped" in content.lower() or "optional" in content.lower(), (
        "registry 文档未明确 manual_url 可跳过"
    )


def test_readiness_mentions_manual_url_optional() -> None:
    """readiness 文档必须明确 manual_url 可跳过。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert "manual_url" in content, "readiness 文档缺少 manual_url"


# ---------------------------------------------------------------------------
# 5. 文档明确 wechat_archive pending / separate track
# ---------------------------------------------------------------------------


def test_registry_mentions_wechat_archive_pending() -> None:
    """registry 文档必须明确 wechat_archive 待处理。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "wechat_archive" in content, "registry 文档缺少 wechat_archive"
    assert "pending" in content.lower() or "separate" in content.lower(), (
        "registry 文档未明确 wechat_archive 待处理"
    )


def test_readiness_mentions_wechat_archive_separate() -> None:
    """readiness 文档必须明确 wechat_archive 单独处理。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert "wechat_archive" in content, "readiness 文档缺少 wechat_archive"
    assert "separate" in content.lower(), "readiness 文档未明确 wechat_archive 单独处理"


# ---------------------------------------------------------------------------
# 6. 文档明确不做 JS rendering / browser automation
# ---------------------------------------------------------------------------


def test_docs_explicit_no_js_rendering() -> None:
    """文档必须明确不做 JS 渲染。"""
    registry = REGISTRY_DOC.read_text(encoding="utf-8")
    readiness = READINESS_DOC.read_text(encoding="utf-8")
    combined = registry + readiness
    assert "JS" in combined or "JavaScript" in combined, "文档未明确提及 JS 渲染边界"
    assert "browser automation" in combined.lower() or "浏览器自动化" in combined, (
        "文档未明确提及浏览器自动化边界"
    )


# ---------------------------------------------------------------------------
# 7. 文档明确不绕过 paywall
# ---------------------------------------------------------------------------


def test_docs_explicit_no_paywall_bypass() -> None:
    """文档必须明确不绕过 paywall。"""
    registry = REGISTRY_DOC.read_text(encoding="utf-8")
    readiness = READINESS_DOC.read_text(encoding="utf-8")
    combined = registry + readiness
    assert "paywall" in combined.lower(), "文档未明确提及 paywall 边界"


# ---------------------------------------------------------------------------
# 8. 文档明确不下载 PDF / OCR
# ---------------------------------------------------------------------------


def test_docs_explicit_no_pdf_download() -> None:
    """文档必须明确不下载 PDF。"""
    registry = REGISTRY_DOC.read_text(encoding="utf-8")
    readiness = READINESS_DOC.read_text(encoding="utf-8")
    combined = registry + readiness
    assert "PDF" in combined, "文档未明确提及 PDF 边界"


def test_docs_explicit_no_ocr() -> None:
    """文档必须明确不做 OCR。"""
    registry = REGISTRY_DOC.read_text(encoding="utf-8")
    readiness = READINESS_DOC.read_text(encoding="utf-8")
    combined = registry + readiness
    assert "OCR" in combined, "文档未明确提及 OCR 边界"


# ---------------------------------------------------------------------------
# 9. 文档明确不下载音频 / 转写音频
# ---------------------------------------------------------------------------


def test_docs_explicit_no_audio_transcription() -> None:
    """文档必须明确不下载音频、不转写音频。"""
    registry = REGISTRY_DOC.read_text(encoding="utf-8")
    readiness = READINESS_DOC.read_text(encoding="utf-8")
    combined = registry + readiness
    assert "audio" in combined.lower() or "音频" in combined, "文档未明确提及音频边界"


# ---------------------------------------------------------------------------
# 10. 文档明确不做 investment judgment / trade signal
# ---------------------------------------------------------------------------


def test_docs_explicit_no_investment_judgment() -> None:
    """文档必须明确不做投研判断。"""
    registry = REGISTRY_DOC.read_text(encoding="utf-8")
    readiness = READINESS_DOC.read_text(encoding="utf-8")
    combined = registry + readiness
    assert "investment judgment" in combined.lower() or "投研判断" in combined, (
        "文档未明确提及投研判断边界"
    )


# ---------------------------------------------------------------------------
# 11. 文档明确 downstream consumes documents.jsonl
# ---------------------------------------------------------------------------


def test_readiness_mentions_downstream_contract() -> None:
    """readiness 文档必须明确下游消费 documents.jsonl。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert "documents.jsonl" in content, "readiness 文档未提及 documents.jsonl 下游契约"
    assert "downstream" in content.lower() or "下游" in content, (
        "readiness 文档未明确下游消费契约"
    )


# ---------------------------------------------------------------------------
# 12. production example config 全部 enabled=false
# ---------------------------------------------------------------------------


def test_production_example_config_all_disabled() -> None:
    """production example config 中所有 source 必须 enabled=false。"""
    config_dict = load_yaml_config(str(PRODUCTION_EXAMPLE))
    sources = config_dict.get("sources", [])
    assert len(sources) > 0, "production example config 应该至少有一个 source"
    for src in sources:
        assert src.get("enabled") is False, (
            f"source [{src.get('source_id')}] 必须 enabled=false，"
            f"实际为 {src.get('enabled')}"
        )


def test_production_example_config_can_validate() -> None:
    """production example config 必须能通过 validate_research_config。"""
    config = load_research_config(str(PRODUCTION_EXAMPLE))
    errors = validate_research_config(config)
    assert errors == [], f"production example config 校验失败: {errors}"


def test_production_example_config_contains_all_source_types() -> None:
    """production example config 应该覆盖所有 8 个 source_type 的示例。"""
    config_dict = load_yaml_config(str(PRODUCTION_EXAMPLE))
    sources = config_dict.get("sources", [])
    source_types = {src.get("source_type") for src in sources}
    expected_types = {
        "official_public_research",
        "podcast_transcript",
        "conference_transcript",
        "analyst_action",
        "media_mention",
        "rss_feed",
        "manual_url",
        "wechat_archive",
    }
    missing = expected_types - source_types
    assert not missing, f"production example config 缺少 source_type: {missing}"


# ---------------------------------------------------------------------------
# 13. 文档中不得包含真实 local config 路径内容或 secrets
# ---------------------------------------------------------------------------


def test_docs_no_secrets() -> None:
    """文档中不得包含 cookie/token/API key 等 secrets。"""
    docs = [
        REGISTRY_DOC,
        READINESS_DOC,
        FOUNDATION_DOC,
        PRODUCTION_RUN_DOC,
    ]
    forbidden_patterns = [
        "api_key=",
        "API_KEY=",
        "password=",
        "PASSWORD=",
        "secret=",
        "SECRET=",
        "token=",
        "TOKEN=",
    ]
    for doc in docs:
        content = doc.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"文档 {doc.name} 包含疑似 secret: {pattern}"
            )


def test_docs_no_real_local_config_content() -> None:
    """文档中不得包含真实 local config 路径内容。"""
    docs = [REGISTRY_DOC, READINESS_DOC]
    for doc in docs:
        content = doc.read_text(encoding="utf-8")
        # 不应包含真实 URL（example.com 除外）
        # 这里只做基本检查，确保没有明显的真实 URL 硬编码
        assert "configs/research_sources.production.local.yaml" not in content or \
               "local config" in content.lower() or "不提交" in content, (
            f"文档 {doc.name} 可能包含真实 local config 引用"
        )


# ---------------------------------------------------------------------------
# 14. research_source_foundation.md 包含 Phase 2H
# ---------------------------------------------------------------------------


def test_foundation_doc_contains_phase_2h() -> None:
    """research_source_foundation.md 必须包含 Phase 2H。"""
    content = FOUNDATION_DOC.read_text(encoding="utf-8")
    assert "Phase 2H" in content, "foundation 文档缺少 Phase 2H"


def test_foundation_doc_contains_source_type_status_table() -> None:
    """foundation 文档必须包含 source_type 状态表。"""
    content = FOUNDATION_DOC.read_text(encoding="utf-8")
    assert "manual_url" in content, "foundation 文档缺少 manual_url 状态"
    assert "wechat_archive" in content, "foundation 文档缺少 wechat_archive 状态"
    assert "skipped by decision" in content, "foundation 文档缺少 skipped by decision"
    assert "separate track" in content, "foundation 文档缺少 separate track"


# ---------------------------------------------------------------------------
# 15. production_run.md 包含生产选源建议
# ---------------------------------------------------------------------------


def test_production_run_doc_contains_source_selection() -> None:
    """production_run.md 必须包含生产选源建议。"""
    content = PRODUCTION_RUN_DOC.read_text(encoding="utf-8")
    assert "Production Source Selection" in content or "生产选源" in content, (
        "production_run 文档缺少生产选源建议章节"
    )
    assert "rss_feed" in content, "production_run 文档缺少 rss_feed 选源建议"
    assert "manual_url" in content, "production_run 文档缺少 manual_url 说明"
    assert "wechat_archive" in content, "production_run 文档缺少 wechat_archive 说明"
