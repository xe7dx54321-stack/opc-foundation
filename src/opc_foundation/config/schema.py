"""Optional typed wrapper for a foundation config block."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FoundationConfig(BaseModel):
    project_id: str | None = None
    pipeline_name: str = "default"
    output_dir: str = "outputs"
    log_dir: str = "logs"
    llm_cache_dir: str = ".llm_cache"
    metadata: dict[str, Any] = {}
