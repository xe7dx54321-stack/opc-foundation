"""Test SkillDefinition and SkillLibraryManifest schemas."""
import pytest
from pydantic import ValidationError
from opc_foundation.skills.skill_manifest_schema import SkillDefinition, SkillLibraryManifest


def _make_skill(**kwargs):
    base = dict(
        skill_id="theme-validation",
        name="Theme Validation",
        path="theme-validation/SKILL.md",
        stage="post_theme_grouping",
        default_enabled=False,
        requires_user_trigger=True,
        input_types=["demand_theme"],
        output_types=["validation_verdict"],
    )
    base.update(kwargs)
    return SkillDefinition(**base)


def _make_manifest(skills=None):
    return SkillLibraryManifest(
        library_id="opc-product-validation",
        library_name="OPC Product Validation Skills",
        version="0.1.0",
        default_enabled=False,
        requires_explicit_invocation=True,
        skills=skills or [_make_skill()],
    )


def test_skill_definition_valid():
    s = _make_skill()
    assert s.skill_id == "theme-validation"
    assert s.default_enabled is False
    assert s.requires_user_trigger is True


def test_manifest_valid():
    m = _make_manifest()
    assert m.library_id == "opc-product-validation"
    assert len(m.skills) == 1


def test_get_skill_by_id():
    m = _make_manifest()
    skill = m.get_skill("theme-validation")
    assert skill is not None
    assert skill.name == "Theme Validation"


def test_get_skill_not_found():
    m = _make_manifest()
    assert m.get_skill("nonexistent") is None


def test_validate_manifest_no_errors():
    m = _make_manifest()
    errors = m.validate_manifest()
    assert errors == []


def test_validate_manifest_default_enabled_error():
    bad_skill = _make_skill(default_enabled=True)
    m = _make_manifest(skills=[bad_skill])
    errors = m.validate_manifest()
    assert any("default_enabled" in e for e in errors)


def test_validate_manifest_user_trigger_error():
    bad_skill = _make_skill(requires_user_trigger=False)
    m = _make_manifest(skills=[bad_skill])
    errors = m.validate_manifest()
    assert any("requires_user_trigger" in e for e in errors)


def test_validate_manifest_duplicate_ids():
    s1 = _make_skill(skill_id="s1")
    s2 = _make_skill(skill_id="s1")
    m = _make_manifest(skills=[s1, s2])
    errors = m.validate_manifest()
    assert any("Duplicate" in e for e in errors)


def test_manifest_principles_stored():
    m = SkillLibraryManifest(
        library_id="test", library_name="Test", version="0.1",
        principles=["Evidence first", "Manual before software"],
        skills=[]
    )
    assert len(m.principles) == 2