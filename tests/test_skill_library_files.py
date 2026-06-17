"""Test that all skill library files exist and contain required content."""
import json
from pathlib import Path

SKILL_ROOT = Path(".agents/skills/opc-product-validation")
MANIFEST_PATH = SKILL_ROOT / "skill_manifest.yaml"

SKILL_IDS = [
    "theme-validation",
    "concierge-mvp",
    "processize",
    "first-customers",
    "pricing-smoke-test",
    "minimalist-review",
]

REQUIRED_SKILL_SECTIONS = [
    "## When to Use",
    "## When Not to Use",
    "## Output Format",
    "This skill is optional and must be explicitly invoked",
]


def test_manifest_file_exists():
    assert MANIFEST_PATH.exists(), "skill_manifest.yaml not found"


def test_library_readme_exists():
    assert (SKILL_ROOT / "README.md").exists()


def test_all_skill_dirs_exist():
    for skill_id in SKILL_IDS:
        assert (SKILL_ROOT / skill_id).is_dir(), f"{skill_id} directory missing"


def test_all_skill_md_exist():
    for skill_id in SKILL_IDS:
        p = SKILL_ROOT / skill_id / "SKILL.md"
        assert p.exists(), f"{skill_id}/SKILL.md missing"


def test_all_input_schemas_exist():
    for skill_id in SKILL_IDS:
        p = SKILL_ROOT / skill_id / "input_schema.example.json"
        assert p.exists(), f"{skill_id}/input_schema.example.json missing"


def test_all_output_schemas_exist():
    for skill_id in SKILL_IDS:
        p = SKILL_ROOT / skill_id / "output_schema.example.json"
        assert p.exists(), f"{skill_id}/output_schema.example.json missing"


def test_input_schemas_valid_json():
    for skill_id in SKILL_IDS:
        p = SKILL_ROOT / skill_id / "input_schema.example.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "theme_id" in data, f"{skill_id}: input schema missing theme_id"


def test_output_schemas_valid_json():
    for skill_id in SKILL_IDS:
        p = SKILL_ROOT / skill_id / "output_schema.example.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "theme_id" in data, f"{skill_id}: output schema missing theme_id"


def test_skill_md_contains_required_sections():
    for skill_id in SKILL_IDS:
        content = (SKILL_ROOT / skill_id / "SKILL.md").read_text(encoding="utf-8")
        for section in REQUIRED_SKILL_SECTIONS:
            assert section in content, f"{skill_id}/SKILL.md missing: {section!r}"


def test_skill_md_prohibits_auto_pipeline():
    """Every SKILL.md must explicitly prohibit automatic pipeline execution."""
    for skill_id in SKILL_IDS:
        content = (SKILL_ROOT / skill_id / "SKILL.md").read_text(encoding="utf-8")
        assert "Do not run this skill automatically" in content, \
            f"{skill_id}/SKILL.md missing auto-pipeline prohibition"


def test_docs_skills_exist():
    docs_dir = Path("docs/skills")
    assert (docs_dir / "opc_skill_library.md").exists()
    assert (docs_dir / "downstream_usage.md").exists()
    assert (docs_dir / "demand_radar_integration_note.md").exists()