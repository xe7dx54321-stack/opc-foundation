"""Source-level diagnostics (generic, no business judgment)."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel
from ..run.time_utils import utcnow_iso
from ..run.id_generator import new_id


class SourceDiagnosticsReport(BaseModel):
    report_id: str
    source_id: str
    source_category: str | None = None
    run_id: str | None = None

    total_items: int = 0
    unique_urls: int = 0
    blocked: int = 0
    failed: int = 0
    text_extracted: int = 0
    avg_text_chars: float = 0.0
    provider_errors: list[str] = []

    run_status: str = "unknown"  # success | partial | blocked | failed | unknown

    # Downstream projects may backfill these
    downstream_positive_count: int | None = None
    downstream_reject_count: int | None = None
    downstream_yield_rate: float | None = None
    downstream_metric_name: str | None = None

    generated_at: str = ""
    metadata: dict[str, Any] = {}

    def model_post_init(self, __context: Any) -> None:
        if not self.generated_at:
            self.generated_at = utcnow_iso()
        if not self.report_id:
            self.report_id = new_id("diag_")


def build_diagnostics_report(
    source_id: str,
    source_category: str | None = None,
    run_id: str | None = None,
    total_items: int = 0,
    unique_urls: int = 0,
    blocked: int = 0,
    failed: int = 0,
    text_extracted: int = 0,
    text_lengths: list[int] | None = None,
    provider_errors: list[str] | None = None,
    run_status: str = "unknown",
    metadata: dict[str, Any] | None = None,
) -> SourceDiagnosticsReport:
    avg_chars = (
        sum(text_lengths) / len(text_lengths) if text_lengths else 0.0
    )
    return SourceDiagnosticsReport(
        report_id=new_id("diag_"),
        source_id=source_id,
        source_category=source_category,
        run_id=run_id,
        total_items=total_items,
        unique_urls=unique_urls,
        blocked=blocked,
        failed=failed,
        text_extracted=text_extracted,
        avg_text_chars=avg_chars,
        provider_errors=provider_errors or [],
        run_status=run_status,
        metadata=metadata or {},
    )