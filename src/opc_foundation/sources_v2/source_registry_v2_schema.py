"""Source Registry v2 – richer source metadata including provider, trust, signal_fit."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, model_validator
from ..run.time_utils import utcnow_iso

SOURCE_TYPES = {
    "rss", "api", "search", "webpage", "manual_url",
    "community", "review_site", "app_store", "repo_issue",
}
SOURCE_CATEGORIES = {
    "user_discussion", "product_review", "workaround_discussion",
    "community_question", "generic_news", "technical_issue",
    "search_discovery", "practitioner_blog",
    "job_description", "manual_seed", "unknown",
}
FETCH_METHODS = {
    "rss", "api", "search_provider", "url_extraction", "manual", "custom_connector",
}
TRUST_TIERS = {"high", "medium", "low", "unknown"}


class SourceDefinitionV2(BaseModel):
    source_id: str
    source_name: str

    source_type: str
    source_category: str
    fetch_method: str

    provider: str | None = None
    connector: str | None = None

    trust_tier: str = "unknown"

    signal_fit: dict[str, float] = {}
    expected_signal_types: list[str] = []

    requires_key: bool = False
    required_env_vars: list[str] = []

    compliance_note: str | None = None
    enabled: bool = True

    metadata: dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_fields(self) -> "SourceDefinitionV2":
        if self.trust_tier not in TRUST_TIERS:
            raise ValueError(f"trust_tier must be one of {TRUST_TIERS}")
        for k, v in self.signal_fit.items():
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"signal_fit[{k!r}] must be 0.0-1.0, got {v}")
        return self


class SourceRegistryV2(BaseModel):
    registry_id: str
    version: str = "0.1"
    sources: list[SourceDefinitionV2] = []
    created_at: str = ""
    metadata: dict[str, Any] = {}

    def model_post_init(self, __context: Any) -> None:
        if not self.created_at:
            self.created_at = utcnow_iso()

    @classmethod
    def from_yaml(cls, path: str) -> "SourceRegistryV2":
        from ..config.loader import load_yaml_config
        data = load_yaml_config(path)
        return cls.model_validate(data)

    def get_enabled(self) -> list[SourceDefinitionV2]:
        return [s for s in self.sources if s.enabled]

    def get_by_id(self, source_id: str) -> SourceDefinitionV2 | None:
        return next((s for s in self.sources if s.source_id == source_id), None)

    def filter_by_type(self, source_type: str) -> list[SourceDefinitionV2]:
        return [s for s in self.sources if s.source_type == source_type]

    def filter_by_category(self, category: str) -> list[SourceDefinitionV2]:
        return [s for s in self.sources if s.source_category == category]

    def validate_registry(self) -> list[str]:
        errors: list[str] = []
        ids: set[str] = set()
        for s in self.sources:
            if s.source_id in ids:
                errors.append(f"Duplicate source_id: {s.source_id}")
            ids.add(s.source_id)
            if s.requires_key and not s.required_env_vars:
                errors.append(f"[{s.source_id}] requires_key=True but no required_env_vars")
        return errors