"""Source registry – load and query source definitions from YAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config.loader import load_yaml_config
from .source_schema import SourceDefinition


class SourceRegistry:
    """Load and query a collection of SourceDefinition objects."""

    def __init__(self, sources: list[SourceDefinition]) -> None:
        self._sources: dict[str, SourceDefinition] = {s.source_id: s for s in sources}

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SourceRegistry":
        """Load registry from a YAML file with a 'sources' key."""
        data: dict[str, Any] = load_yaml_config(path)
        raw_sources = data.get("sources", [])
        sources = [SourceDefinition.model_validate(s) for s in raw_sources]
        return cls(sources)

    def get_enabled_sources(self) -> list[SourceDefinition]:
        return [s for s in self._sources.values() if s.enabled]

    def get_source(self, source_id: str) -> SourceDefinition | None:
        return self._sources.get(source_id)

    def filter_by_tags(self, tags: list[str]) -> list[SourceDefinition]:
        tag_set = set(tags)
        return [s for s in self._sources.values() if tag_set.intersection(s.tags)]

    def validate_registry(self) -> list[str]:
        """Return a list of validation error messages (empty = OK)."""
        errors: list[str] = []
        for s in self._sources.values():
            if not s.source_id:
                errors.append("source_id is required")
            if not s.connector:
                errors.append(f"[{s.source_id}] connector is required")
            if s.trust_weight < 0 or s.trust_weight > 1:
                errors.append(f"[{s.source_id}] trust_weight must be 0-1")
        return errors

    def all_sources(self) -> list[SourceDefinition]:
        return list(self._sources.values())
