"""Source yield metrics – generic counters downstream projects can populate."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel
from ..run.time_utils import utcnow_iso


class SourceYieldMetrics(BaseModel):
    source_id: str
    run_id: str | None = None
    pipeline_name: str | None = None

    # Generic counts (Foundation populates these)
    total_fetched: int = 0
    total_after_dedupe: int = 0
    total_extracted: int = 0

    # Downstream backfill (business project populates, Foundation does not interpret)
    downstream_metric_name: str | None = None
    downstream_positive_count: int | None = None
    downstream_reject_count: int | None = None
    downstream_yield_rate: float | None = None

    recorded_at: str = ""
    metadata: dict[str, Any] = {}

    def model_post_init(self, __context: Any) -> None:
        if not self.recorded_at:
            self.recorded_at = utcnow_iso()