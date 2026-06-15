"""RunContext – lightweight execution context passed through a pipeline."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .id_generator import new_run_id
from .time_utils import utcnow_iso


class RunContext(BaseModel):
    run_id: str = Field(default_factory=new_run_id)
    project_id: str | None = None
    pipeline_name: str = "default"
    started_at: str = Field(default_factory=utcnow_iso)
    config_paths: list[str] = []
    metadata: dict[str, Any] = {}
