"""M3B-3b 健康状态校准测试。

功能说明（小白解读）：
    验证 M3B-3b 引入的运行模式校准（utility / known_limited / manual_only / data_source）
    以及 document_extraction 按文件类型精准归因。

    这些测试覆盖以下场景：
    1. 工具能力（runtime.*）显示为 "utility"，不计入任何异常
    2. 已知限制能力（HKEX）的 degraded 不触发 needs_attention
    3. 人工触发能力（manual_url）无记录不视为故障
    4. document_extraction 按文件扩展名精准归因
    5. 状态解释文案正确生成
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opc_foundation.dashboard.health import (
    _extract_file_extension_from_record,
    _match_records_by_file_extension,
    build_runtime_evidence,
    build_runtime_summary_from_evidence,
    suggest_action,
)
from opc_foundation.dashboard.loaders import load_runtime_bindings_config
from opc_foundation.dashboard.models import (
    Capability,
    CapabilityRegistry,
    CapabilityRuntimeBinding,
    CapabilityRuntimeEvidence,
    RuntimeMode,
)


def _make_cap(
    cap_id: str = "test.cap",
    runtime_mode: str = "data_source",
) -> Capability:
    """构造一个测试能力对象。"""
    # 用 cap_id 前缀推断 archive_root（如 document_extraction.pdf -> document_extraction）
    parts = cap_id.split(".")
    if len(parts) >= 2:
        archive = parts[0]
    else:
        archive = "test"
    return Capability(
        capability_id=cap_id,
        name="Test Cap",
        track="test",
        category="测试",
        maturity_status="production_trial_ready",
        description="测试能力",
        input_type="test",
        primary_output=f"data/{archive}/index/documents.latest.jsonl",
        health_file=f"data/{archive}/index/source_health.jsonl",
        run_log_file=f"data/{archive}/index/run_log.jsonl",
        failed_queue_file=f"data/{archive}/index/failed_queue.jsonl",
        docs=[],
        runtime_mode=runtime_mode,
    )


def _make_binding(cap_id: str = "test.cap", exts: list[str] | None = None) -> CapabilityRuntimeBinding:
    """构造一个测试 binding（路径与 _make_cap 保持一致）。"""
    parts = cap_id.split(".")
    if len(parts) >= 2:
        archive = parts[0]
    else:
        archive = "test"
    return CapabilityRuntimeBinding(
        capability_id=cap_id,
        archive_root=f"data/{archive}",
        source_types=[f"{archive}_type"],
        source_ids=[],
        file_extensions=exts or [],
        health_file=f"data/{archive}/index/source_health.jsonl",
        run_log_file=f"data/{archive}/index/run_log.jsonl",
        failed_queue_file=f"data/{archive}/index/failed_queue.jsonl",
        report_dir=f"data/{archive}/reports",
    )


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """把 records 写成 jsonl 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


# ===========================================================================
# RuntimeMode 枚举测试
# ===========================================================================


def test_runtime_mode_enum_values() -> None:
    """RuntimeMode 枚举包含 4 个校准值。"""
    assert RuntimeMode.DATA_SOURCE.value == "data_source"
    assert RuntimeMode.UTILITY.value == "utility"
    assert RuntimeMode.KNOWN_LIMITED.value == "known_limited"
    assert RuntimeMode.MANUAL_ONLY.value == "manual_only"


def test_capability_runtime_mode_enum_property() -> None:
    """Capability 的 runtime_mode_enum 属性正确解析。"""
    cap = _make_cap(runtime_mode="utility")
    assert cap.runtime_mode_enum == RuntimeMode.UTILITY

    cap2 = _make_cap(runtime_mode="known_limited")
    assert cap2.runtime_mode_enum == RuntimeMode.KNOWN_LIMITED

    # 未知值兜底为 data_source
    cap3 = _make_cap(runtime_mode="unknown_value")
    assert cap3.runtime_mode_enum == RuntimeMode.DATA_SOURCE


# ===========================================================================
# 工具能力测试
# ===========================================================================


def test_utility_capability_returns_utility_status(tmp_path: Path) -> None:
    """工具能力（runtime.*）显示为 utility，不计入任何异常。"""
    cap = _make_cap(cap_id="runtime.test_utility", runtime_mode="utility")
    binding = _make_binding(cap_id="runtime.test_utility")

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)

    assert summary.runtime_health == "utility"
    assert summary.needs_attention is False
    assert summary.failed_queue_count == 0
    assert summary.consecutive_failures == 0
    assert "工具能力" in summary.status_explanation


def test_utility_capability_not_counted_in_failures() -> None:
    """suggest_action: utility 返回工具能力文案。"""
    assert suggest_action("utility", False, False) == "工具能力，无需处理"


def test_utility_capability_ignores_records(tmp_path: Path) -> None:
    """工具能力即使有运行记录也保持 utility 状态。"""
    cap = _make_cap(cap_id="runtime.test_util", runtime_mode="utility")
    binding = _make_binding(cap_id="runtime.test_util")

    # 写一些记录
    health_path = tmp_path / "data" / "test" / "index" / "source_health.jsonl"
    _write_jsonl(health_path, [
        {"source_type": "test", "status": "failed", "checked_at": "2026-06-25T00:00:00"},
    ])

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)

    # 工具能力不受影响
    assert summary.runtime_health == "utility"
    assert summary.needs_attention is False


# ===========================================================================
# 已知限制能力测试
# ===========================================================================


def test_known_limited_degraded_does_not_trigger_attention(tmp_path: Path) -> None:
    """HKEX 等已知限制的 degraded 不触发 needs_attention。"""
    cap = _make_cap(cap_id="official_filing.hkex_announcement", runtime_mode="known_limited")
    binding = _make_binding(cap_id="official_filing.hkex_announcement")

    # 写一条 degraded 的 health 记录
    health_path = tmp_path / "data" / "official_filing" / "index" / "source_health.jsonl"
    _write_jsonl(health_path, [
        {
            "source_type": "official_filing_type",
            "status": "degraded",
            "checked_at": "2026-06-25T00:00:00",
            "last_error": "客户端渲染问题，empty_source",
        },
    ])

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)

    assert summary.runtime_health == "degraded"
    # 关键：known_limited 的 degraded 不触发 needs_attention
    assert summary.needs_attention is False
    assert "已知限制" in summary.status_explanation


def test_known_limited_failed_queue_does_not_trigger_attention(tmp_path: Path) -> None:
    """HKEX 的 failed_queue 积压也不触发 needs_attention。"""
    cap = _make_cap(cap_id="official_filing.hkex_announcement", runtime_mode="known_limited")
    binding = _make_binding(cap_id="official_filing.hkex_announcement")

    # 写一条 failed_queue 记录（没 health 记录，会进入 unknown_never_run 分支）
    failed_path = tmp_path / "data" / "official_filing" / "index" / "failed_queue.jsonl"
    _write_jsonl(failed_path, [
        {"source_type": "official_filing_type", "failed_at": "2026-06-25T00:00:00", "error": "client_side_render"},
    ])

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)

    assert summary.runtime_health == "unknown_never_run"
    # 关键：known_limited 的 failed_queue 也不触发 needs_attention
    assert summary.needs_attention is False


def test_known_limited_suggest_action() -> None:
    """suggest_action: known_limited 返回正确中文。"""
    assert suggest_action("known_limited", False, False) == "已知限制，不需作为每日修复项"


# ===========================================================================
# 人工触发能力测试
# ===========================================================================


def test_manual_only_no_records_is_not_error(tmp_path: Path) -> None:
    """manual_only 能力无记录不视为故障。"""
    cap = _make_cap(cap_id="research.manual_url", runtime_mode="manual_only")
    binding = _make_binding(cap_id="research.manual_url")

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)

    assert summary.runtime_health == "unknown_never_run"
    assert "人工触发" in summary.status_explanation


# ===========================================================================
# 未知 / 尚未运行测试
# ===========================================================================


def test_unknown_never_run_with_binding_but_no_records(tmp_path: Path) -> None:
    """有 binding 但无记录时显示 'unknown_never_run'。"""
    cap = _make_cap(cap_id="research.rss_feed", runtime_mode="data_source")
    binding = _make_binding(cap_id="research.rss_feed")

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)

    assert summary.runtime_health == "unknown_never_run"
    assert summary.failed_queue_count == 0
    assert summary.needs_attention is False
    assert "尚未发现运行记录" in summary.status_explanation or "尚未运行" in summary.status_explanation


def test_unknown_never_run_does_not_count_as_failed() -> None:
    """unknown_never_run 不计入 failed。"""
    # suggest_action 已经覆盖了这个
    assert suggest_action("unknown_never_run", False, False) == "尚未发现运行记录，运行能力后会更新"


# ===========================================================================
# document_extraction 文件类型归因测试
# ===========================================================================


def test_extract_file_extension_from_file_extension_field() -> None:
    """从 file_extension 字段提取扩展名。"""
    assert _extract_file_extension_from_record({"file_extension": "pdf"}) == ".pdf"
    assert _extract_file_extension_from_record({"file_extension": ".PDF"}) == ".pdf"
    assert _extract_file_extension_from_record({"file_extension": "html"}) == ".html"


def test_extract_file_extension_from_path_field() -> None:
    """从 path 字段提取扩展名。"""
    assert _extract_file_extension_from_record({"original_path": "/tmp/foo.pdf"}) == ".pdf"
    assert _extract_file_extension_from_record({"document_path": "/tmp/bar.html"}) == ".html"
    assert _extract_file_extension_from_record({"file_path": "/tmp/baz.txt"}) == ".txt"
    assert _extract_file_extension_from_record({"path": "/tmp/qux.md"}) == ".md"


def test_extract_file_extension_from_raw_entry() -> None:
    """从 raw_entry 嵌套字段提取扩展名。"""
    assert _extract_file_extension_from_record({
        "raw_entry": {"path": "/tmp/file.pdf"}
    }) == ".pdf"
    assert _extract_file_extension_from_record({
        "raw_entry": {"file_path": "/tmp/file.html"}
    }) == ".html"


def test_extract_file_extension_from_metadata() -> None:
    """从 metadata.file_extension 提取。"""
    assert _extract_file_extension_from_record({
        "metadata": {"file_extension": "pdf"}
    }) == ".pdf"


def test_extract_file_extension_from_mime_type() -> None:
    """从 mime_type 推断扩展名。"""
    assert _extract_file_extension_from_record({"mime_type": "application/pdf"}) == ".pdf"
    assert _extract_file_extension_from_record({"mime_type": "text/html"}) == ".html"
    assert _extract_file_extension_from_record({"mime_type": "text/plain"}) == ".txt"
    assert _extract_file_extension_from_record({"mime_type": "text/markdown"}) == ".md"


def test_extract_file_extension_returns_empty_when_no_match() -> None:
    """找不到扩展名时返回空字符串。"""
    assert _extract_file_extension_from_record({}) == ""
    assert _extract_file_extension_from_record({"source_type": "pdf"}) == ""


def test_match_records_by_file_extension_filters_correctly() -> None:
    """按文件扩展名过滤记录。"""
    records = [
        {"file_extension": "pdf", "error": "malformed"},
        {"file_extension": "html", "error": "ok"},
        {"file_extension": "txt", "error": "ok"},
        {"file_extension": "md", "error": "ok"},
    ]
    matched = _match_records_by_file_extension(records, [".pdf"])
    assert len(matched) == 1
    assert matched[0]["file_extension"] == "pdf"


def test_pdf_only_matches_pdf_failures() -> None:
    """document_extraction.pdf 只匹配 .pdf 失败，不影响其他类型。"""
    records = [
        {"file_extension": "pdf", "status": "failed", "error": "malformed"},
        {"file_extension": "html", "status": "failed", "error": "ok"},
        {"file_extension": "txt", "status": "failed", "error": "ok"},
        {"file_extension": "md", "status": "failed", "error": "ok"},
    ]
    matched = _match_records_by_file_extension(records, [".pdf"])
    assert len(matched) == 1
    assert matched[0]["file_extension"] == "pdf"


def test_html_matches_html_and_htm() -> None:
    """document_extraction.html 应该同时匹配 .html 和 .htm。"""
    records = [
        {"file_extension": "html"},
        {"file_extension": "htm"},
        {"file_extension": "pdf"},
    ]
    matched = _match_records_by_file_extension(records, [".html", ".htm"])
    assert len(matched) == 2


def test_markdown_matches_md_and_markdown() -> None:
    """document_extraction.markdown 应该同时匹配 .md 和 .markdown。"""
    records = [
        {"file_extension": "md"},
        {"file_extension": "markdown"},
        {"file_extension": "html"},
    ]
    matched = _match_records_by_file_extension(records, [".md", ".markdown"])
    assert len(matched) == 2


def test_pdf_failure_does_not_affect_html(tmp_path: Path) -> None:
    """一个 PDF 失败不会扩散到 document_extraction.html。"""
    cap_pdf = _make_cap(cap_id="document_extraction.pdf", runtime_mode="data_source")
    cap_html = _make_cap(cap_id="document_extraction.html", runtime_mode="data_source")
    binding_pdf = _make_binding(cap_id="document_extraction.pdf", exts=[".pdf"])
    binding_html = _make_binding(cap_id="document_extraction.html", exts=[".html", ".htm"])

    # 写一个 PDF 失败记录
    failed_path = tmp_path / "data" / "document_extraction" / "index" / "failed_queue.jsonl"
    _write_jsonl(failed_path, [
        {"file_extension": "pdf", "error": "malformed", "failed_at": "2026-06-25T00:00:00"},
    ])

    # PDF 能力应该看到这个失败
    evidence_pdf = build_runtime_evidence(cap_pdf, binding_pdf, tmp_path)
    assert len(evidence_pdf.matched_failed_records) == 1

    # HTML 能力不应该看到这个失败
    evidence_html = build_runtime_evidence(cap_html, binding_html, tmp_path)
    assert len(evidence_html.matched_failed_records) == 0


def test_malformed_pdf_only_affects_pdf_capability(tmp_path: Path) -> None:
    """malformed.pdf 失败只影响 document_extraction.pdf，不影响 html/txt/markdown。"""
    binding_pdf = _make_binding(cap_id="document_extraction.pdf", exts=[".pdf"])
    binding_html = _make_binding(cap_id="document_extraction.html", exts=[".html", ".htm"])
    binding_txt = _make_binding(cap_id="document_extraction.txt", exts=[".txt"])
    binding_md = _make_binding(cap_id="document_extraction.markdown", exts=[".md", ".markdown"])

    # 写一个 malformed.pdf 失败
    failed_path = tmp_path / "data" / "document_extraction" / "index" / "failed_queue.jsonl"
    _write_jsonl(failed_path, [
        {"file_extension": "pdf", "error": "malformed", "source_type": "local_document", "failed_at": "2026-06-25T00:00:00"},
    ])

    cap_pdf = _make_cap(cap_id="document_extraction.pdf")
    cap_html = _make_cap(cap_id="document_extraction.html")
    cap_txt = _make_cap(cap_id="document_extraction.txt")
    cap_md = _make_cap(cap_id="document_extraction.markdown")

    ev_pdf = build_runtime_evidence(cap_pdf, binding_pdf, tmp_path)
    ev_html = build_runtime_evidence(cap_html, binding_html, tmp_path)
    ev_txt = build_runtime_evidence(cap_txt, binding_txt, tmp_path)
    ev_md = build_runtime_evidence(cap_md, binding_md, tmp_path)

    # 只有 PDF 看到失败
    assert len(ev_pdf.matched_failed_records) == 1
    assert len(ev_html.matched_failed_records) == 0
    assert len(ev_txt.matched_failed_records) == 0
    assert len(ev_md.matched_failed_records) == 0

    # 只有 PDF 触发 needs_attention
    sum_pdf = build_runtime_summary_from_evidence(cap_pdf, binding_pdf, ev_pdf)
    sum_html = build_runtime_summary_from_evidence(cap_html, binding_html, ev_html)
    sum_txt = build_runtime_summary_from_evidence(cap_txt, binding_txt, ev_txt)
    sum_md = build_runtime_summary_from_evidence(cap_md, binding_md, ev_md)

    assert sum_pdf.needs_attention is True
    assert sum_html.needs_attention is False
    assert sum_txt.needs_attention is False
    assert sum_md.needs_attention is False


# ===========================================================================
# 状态解释测试
# ===========================================================================


def test_status_explanation_for_utility() -> None:
    """工具能力有专门的状态解释。"""
    cap = _make_cap(cap_id="runtime.test", runtime_mode="utility")
    binding = _make_binding(cap_id="runtime.test")
    evidence = build_runtime_evidence(cap, binding, Path("/tmp"))
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)
    assert "工具能力" in summary.status_explanation


def test_status_explanation_for_known_limited() -> None:
    """已知限制有专门的状态解释。"""
    cap = _make_cap(cap_id="official_filing.hkex_announcement", runtime_mode="known_limited")
    binding = _make_binding(cap_id="official_filing.hkex_announcement")
    evidence = build_runtime_evidence(cap, binding, Path("/tmp"))
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)
    assert "已知限制" in summary.status_explanation


def test_status_explanation_for_unknown_never_run() -> None:
    """unknown_never_run 有专门的状态解释。"""
    cap = _make_cap(cap_id="research.rss_feed", runtime_mode="data_source")
    binding = _make_binding(cap_id="research.rss_feed")
    evidence = build_runtime_evidence(cap, binding, Path("/tmp"))
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)
    assert "尚未发现运行记录" in summary.status_explanation


# ===========================================================================
# suggest_action 校准测试
# ===========================================================================


def test_suggest_action_utility() -> None:
    """工具能力的中文建议。"""
    assert suggest_action("utility", False, False) == "工具能力，无需处理"


def test_suggest_action_known_limited() -> None:
    """已知限制的中文建议。"""
    assert suggest_action("known_limited", False, False) == "已知限制，不需作为每日修复项"


def test_suggest_action_healthy_no_action() -> None:
    """运行正常的中文建议。"""
    assert suggest_action("healthy", False, False) == "无需处理"


def test_suggest_action_failed_priority_check() -> None:
    """失败的中文建议优先级最高。"""
    assert suggest_action("failed", False, False) == "优先查看失败队列和最近报告"


# ===========================================================================
# Runtime Binding 加载和运行时模式一致性
# ===========================================================================


def test_utility_capability_does_not_need_binding() -> None:
    """工具能力通常不需要 binding（按设计）。"""
    # 加载主配置
    binding_registry = load_runtime_bindings_config(
        "configs/capability_runtime_bindings.yaml"
    )
    # 工具类能力（runtime.*）不应有 binding
    utility_caps = ["runtime.archive_paths", "runtime.jsonl", "runtime.failed_queue", "runtime.run_log", "runtime.health_status"]
    for cap_id in utility_caps:
        assert binding_registry.get_binding(cap_id) is None, (
            f"{cap_id} 是工具能力，不应该有 binding"
        )
