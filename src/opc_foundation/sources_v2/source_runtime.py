"""Source Runtime – dispatch fetch to appropriate provider/connector."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel
from ..run.id_generator import new_id
from ..run.time_utils import utcnow_iso


class SourceRunResult(BaseModel):
    run_id: str
    source_id: str
    source_type: str
    source_category: str

    status: str  # success | partial | blocked | failed

    items_count: int = 0
    errors: list[str] = []
    warnings: list[str] = []

    started_at: str
    finished_at: str | None = None

    artifacts: dict[str, str] = {}
    metrics: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class SourceRuntime:
    """Dispatch source fetching based on SourceDefinitionV2.fetch_method."""

    def __init__(
        self,
        search_registry=None,
        web_extractor=None,
    ) -> None:
        self._search_registry = search_registry
        self._web_extractor = web_extractor

    def run_source(self, source_def) -> SourceRunResult:
        """Route fetch to correct subsystem based on fetch_method."""
        from .source_registry_v2_schema import SourceDefinitionV2
        started = utcnow_iso()
        run_id = new_id("run_")
        errors: list[str] = []
        warnings: list[str] = []
        items_count = 0

        method = source_def.fetch_method

        if method == "search_provider":
            items_count, errors, warnings = self._run_search(source_def)
        elif method in ("url_extraction", "manual"):
            items_count, errors, warnings = self._run_web_extraction(source_def)
        elif method == "rss":
            warnings.append(f"RSS fetch_method: use legacy SourceRegistry + RssConnector.")
            items_count = 0
        else:
            errors.append(f"Unknown fetch_method: {method!r}")

        status = "failed" if errors and not items_count else (
            "partial" if errors else "success"
        )

        return SourceRunResult(
            run_id=run_id,
            source_id=source_def.source_id,
            source_type=source_def.source_type,
            source_category=source_def.source_category,
            status=status,
            items_count=items_count,
            errors=errors,
            warnings=warnings,
            started_at=started,
            finished_at=utcnow_iso(),
        )

    def _run_search(self, source_def) -> tuple[int, list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []

        if self._search_registry is None:
            errors.append("SourceRuntime: no search_registry provided")
            return 0, errors, warnings

        from ..search.search_schema import SearchQuery
        queries = source_def.metadata.get("queries") or source_def.metadata.get("default_queries") or []
        if not queries:
            warnings.append(f"[{source_def.source_id}] no queries in metadata")
            return 0, errors, warnings

        total = 0
        for q in queries:
            sq = SearchQuery(query=q, provider=source_def.provider, max_results=10)
            result = self._search_registry.search(sq, provider_name=source_def.provider)
            total += len(result.results)
            errors.extend(result.errors)
            warnings.extend(result.warnings)

        return total, errors, warnings

    def _run_web_extraction(self, source_def) -> tuple[int, list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []

        urls = source_def.metadata.get("urls") or []
        if not urls:
            warnings.append(f"[{source_def.source_id}] no urls in metadata")
            return 0, errors, warnings

        if self._web_extractor is None:
            errors.append("SourceRuntime: no web_extractor provided")
            return 0, errors, warnings

        total = 0
        for url in urls:
            try:
                result = self._web_extractor.extract(url)
                if result.text:
                    total += 1
                else:
                    warnings.append(f"Empty extraction for {url}")
            except Exception as exc:
                errors.append(f"Extraction error for {url}: {exc}")

        return total, errors, warnings