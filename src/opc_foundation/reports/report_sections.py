"""ReportSection data model."""
from __future__ import annotations

from pydantic import BaseModel


class ReportSection(BaseModel):
    title: str
    body: str
    level: int = 2
