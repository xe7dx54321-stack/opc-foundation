"""Skill manifest loader – reads and validates skill library manifests."""
from __future__ import annotations
from pathlib import Path
from typing import Any

import yaml

from .skill_manifest_schema import SkillDefinition, SkillLibraryManifest


def load_skill_manifest(path: str | Path) -> SkillLibraryManifest:
    """Load a skill_manifest.yaml and return a SkillLibraryManifest."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Skill manifest not found: {p}")
    with open(p, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return SkillLibraryManifest.model_validate(data)


def validate_skill_manifest(path: str | Path) -> list[str]:
    """Load and validate a skill manifest. Returns list of error strings."""
    manifest = load_skill_manifest(path)
    return manifest.validate_manifest()


def list_skills(path: str | Path) -> list[SkillDefinition]:
    """Return all skill definitions from a manifest."""
    return load_skill_manifest(path).skills


def get_skill_by_id(path: str | Path, skill_id: str) -> SkillDefinition | None:
    """Return a specific skill by ID, or None if not found."""
    return load_skill_manifest(path).get_skill(skill_id)


def skill_files_exist(manifest_path: str | Path) -> dict[str, dict[str, bool]]:
    """Check that each skill's SKILL.md and schema examples exist.

    Returns: {skill_id: {"skill_md": bool, "input_schema": bool, "output_schema": bool}}
    """
    manifest_dir = Path(manifest_path).parent
    manifest = load_skill_manifest(manifest_path)
    results: dict[str, dict[str, bool]] = {}

    for skill in manifest.skills:
        skill_dir = manifest_dir / Path(skill.path).parent
        results[skill.skill_id] = {
            "skill_md": (manifest_dir / skill.path).exists(),
            "input_schema": (skill_dir / "input_schema.example.json").exists(),
            "output_schema": (skill_dir / "output_schema.example.json").exists(),
        }
    return results