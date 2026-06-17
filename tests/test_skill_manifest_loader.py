"""Test skill manifest loader functions."""
import pytest
from pathlib import Path
from opc_foundation.skills import (
    load_skill_manifest, validate_skill_manifest,
    list_skills, get_skill_by_id, skill_files_exist
)

_MANIFEST_PATH = ".agents/skills/opc-product-validation/skill_manifest.yaml"


def test_load_manifest():
    manifest = load_skill_manifest(_MANIFEST_PATH)
    assert manifest.library_id == "opc-product-validation"
    assert manifest.version == "0.1.0"


def test_manifest_default_enabled_false():
    manifest = load_skill_manifest(_MANIFEST_PATH)
    assert manifest.default_enabled is False


def test_manifest_requires_explicit_invocation():
    manifest = load_skill_manifest(_MANIFEST_PATH)
    assert manifest.requires_explicit_invocation is True


def test_list_skills_returns_6():
    skills = list_skills(_MANIFEST_PATH)
    assert len(skills) == 6


def test_all_skills_default_enabled_false():
    skills = list_skills(_MANIFEST_PATH)
    for s in skills:
        assert s.default_enabled is False, f"{s.skill_id} has default_enabled=True"


def test_all_skills_require_user_trigger():
    skills = list_skills(_MANIFEST_PATH)
    for s in skills:
        assert s.requires_user_trigger is True, f"{s.skill_id} has requires_user_trigger=False"


def test_get_skill_by_id_found():
    skill = get_skill_by_id(_MANIFEST_PATH, "theme-validation")
    assert skill is not None
    assert skill.name == "Theme Validation"
    assert skill.stage == "post_theme_grouping"


def test_get_skill_by_id_not_found():
    skill = get_skill_by_id(_MANIFEST_PATH, "nonexistent-skill")
    assert skill is None


def test_validate_manifest_no_errors():
    errors = validate_skill_manifest(_MANIFEST_PATH)
    assert errors == [], f"Unexpected errors: {errors}"


def test_load_missing_manifest():
    with pytest.raises(FileNotFoundError):
        load_skill_manifest("/nonexistent/path/manifest.yaml")


def test_skill_files_exist():
    status = skill_files_exist(_MANIFEST_PATH)
    assert len(status) == 6
    for skill_id, files in status.items():
        assert files["skill_md"] is True, f"{skill_id}: SKILL.md missing"
        assert files["input_schema"] is True, f"{skill_id}: input_schema.example.json missing"
        assert files["output_schema"] is True, f"{skill_id}: output_schema.example.json missing"