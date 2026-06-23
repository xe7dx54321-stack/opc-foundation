"""Document Extraction Production Readiness 文档测试。

覆盖：
1. live smoke registry 文档存在
2. production readiness 文档存在
3. readiness doc 包含 Production Trial Ready
4. readiness doc 包含 OCR disabled
5. readiness doc 包含 no browser automation
6. readiness doc 包含 no remote PDF download
7. readiness doc 包含 downstream contract
8. registry doc 包含 PDF/HTML/TXT/MD 结果
9. registry doc 包含 malformed PDF fail-soft
10. registry doc 包含 source_health 状态
11. registry doc 包含 empty_source = degraded
"""
from __future__ import annotations

from pathlib import Path


# 路径常量
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DOC = PROJECT_ROOT / "docs" / "document_extraction_live_smoke_registry.md"
READINESS_DOC = PROJECT_ROOT / "docs" / "document_extraction_production_readiness.md"
FOUNDATION_DOC = PROJECT_ROOT / "docs" / "document_extraction_foundation.md"
PRODUCTION_RUN_DOC = PROJECT_ROOT / "docs" / "document_extraction_production_run.md"


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
    """foundation 文档必须存在。"""
    assert FOUNDATION_DOC.exists(), f"文档不存在: {FOUNDATION_DOC}"


def test_production_run_doc_exists() -> None:
    """production run 文档必须存在。"""
    assert PRODUCTION_RUN_DOC.exists(), f"文档不存在: {PRODUCTION_RUN_DOC}"


# ---------------------------------------------------------------------------
# 2. Production Readiness 文档内容
# ---------------------------------------------------------------------------


def test_readiness_contains_production_trial_ready() -> None:
    """readiness 文档必须包含 Production Trial Ready。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert "Production Trial Ready" in content, (
        "readiness 文档缺少 Production Trial Ready"
    )


def test_readiness_contains_ocr_disabled() -> None:
    """readiness 文档必须明确 OCR disabled。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert "OCR" in content, "readiness 文档缺少 OCR 说明"
    assert "disabled" in content.lower() or "关闭" in content or "❌" in content, (
        "readiness 文档应明确 OCR disabled"
    )


def test_readiness_contains_no_browser_automation() -> None:
    """readiness 文档必须明确 no browser automation。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert (
        "browser automation" in content.lower() or "浏览器自动化" in content
    ), "readiness 文档缺少 browser automation 说明"


def test_readiness_contains_no_remote_pdf_download() -> None:
    """readiness 文档必须明确 no remote PDF download。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert "PDF" in content, "readiness 文档缺少 PDF 说明"
    assert (
        "remote" in content.lower()
        or "远程" in content
        or "下载" in content
        or "download" in content.lower()
    ), "readiness 文档应明确 remote PDF 边界"


def test_readiness_contains_downstream_contract() -> None:
    """readiness 文档必须包含 downstream contract。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert "documents.jsonl" in content, "readiness 文档缺少 documents.jsonl"
    assert "downstream" in content.lower() or "下游" in content, (
        "readiness 文档缺少 downstream contract 说明"
    )


def test_readiness_contains_no_investment_judgment() -> None:
    """readiness 文档必须明确 no investment judgment。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert (
        "investment judgment" in content.lower()
        or "投资判断" in content
        or "investment" in content.lower()
    ), "readiness 文档缺少 investment judgment 边界说明"


# ---------------------------------------------------------------------------
# 3. Live Smoke Registry 文档内容
# ---------------------------------------------------------------------------


def test_registry_contains_pdf_html_txt_md() -> None:
    """registry 文档必须包含 PDF / HTML / TXT / MD 结果。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "PDF" in content, "registry 缺少 PDF 结果"
    assert "HTML" in content, "registry 缺少 HTML 结果"
    assert "TXT" in content, "registry 缺少 TXT 结果"
    assert "Markdown" in content or "MD" in content, "registry 缺少 Markdown 结果"


def test_registry_contains_malformed_pdf_fail_soft() -> None:
    """registry 文档必须包含 malformed PDF fail-soft。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "malformed" in content.lower(), "registry 缺少 malformed PDF 说明"
    assert "fail-soft" in content.lower() or "失败队列" in content or "failed_queue" in content, (
        "registry 缺少 malformed PDF fail-soft 说明"
    )


def test_registry_contains_source_health_status() -> None:
    """registry 文档必须包含 source_health 状态。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "source" in content.lower() and "health" in content.lower(), (
        "registry 缺少 source_health 状态"
    )
    assert "healthy" in content.lower(), "registry 缺少 healthy 状态"
    assert "degraded" in content.lower(), "registry 缺少 degraded 状态"


def test_registry_contains_empty_source_degraded() -> None:
    """registry 文档必须明确 empty_source = degraded。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "empty_source" in content, "registry 缺少 empty_source 说明"
    assert "degraded" in content, "registry 缺少 degraded 状态"
    assert (
        "candidate_count = 0" in content
        or "candidates = 0" in content
        or "candidates > 0" in content
        or "enabled + candidates" in content
    ), "registry 应明确 empty source 的 health 语义"


def test_registry_contains_ocr_default_off() -> None:
    """registry 文档必须明确 OCR 默认关闭。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "OCR" in content, "registry 缺少 OCR 说明"
    assert "默认关闭" in content or "default" in content.lower() or "false" in content.lower(), (
        "registry 应明确 OCR 默认关闭"
    )


def test_registry_contains_duplicate_info() -> None:
    """registry 文档必须包含 duplicate run 信息。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "duplicate" in content.lower(), "registry 缺少 duplicate 信息"
