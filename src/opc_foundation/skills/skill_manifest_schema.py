"""Skill manifest schema – defines the structure of a skill library manifest."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class SkillDefinition(BaseModel):
    skill_id: str
    name: str
    name_zh: str | None = None
    path: str                        # relative to manifest directory
    stage: str
    default_enabled: bool = False
    requires_user_trigger: bool = True
    input_types: list[str] = []
    output_types: list[str] = []
    recommended_for: list[str] = []
    description: str | None = None


class SkillLibraryManifest(BaseModel):
    library_id: str
    library_name: str
    version: str
    description: str | None = None
    default_enabled: bool = False
    requires_explicit_invocation: bool = True
    principles: list[str] = []
    skills: list[SkillDefinition] = []

    def get_skill(self, skill_id: str) -> SkillDefinition | None:
        return next((s for s in self.skills if s.skill_id == skill_id), None)

    def validate_manifest(self) -> list[str]:
        errors: list[str] = []
        if not self.library_id:
            errors.append("library_id is required")
        ids: set[str] = set()
        for s in self.skills:
            if s.skill_id in ids:
                errors.append(f"Duplicate skill_id: {s.skill_id}")
            ids.add(s.skill_id)
            if s.default_enabled:
                errors.append(f"[{s.skill_id}] default_enabled must be false")
            if not s.requires_user_trigger:
                errors.append(f"[{s.skill_id}] requires_user_trigger must be true")
        return errors