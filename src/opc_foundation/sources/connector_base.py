"""SourceConnector protocol / abstract base."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .source_schema import FetchResult, SourceDefinition, SourceQuery
from ..run.run_context import RunContext


@runtime_checkable
class SourceConnector(Protocol):
    """Minimal interface every connector must satisfy."""

    connector_id: str

    def fetch(
        self,
        query: SourceQuery,
        source: SourceDefinition,
        context: RunContext,
    ) -> FetchResult:
        ...
