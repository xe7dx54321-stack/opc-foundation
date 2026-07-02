"""Test skills CLI commands."""
import subprocess
import sys
import os
from pathlib import Path


def _run(args):
    _SRC_PATH = str(Path(__file__).parent.parent / "src")
    _CWD = str(Path(__file__).parent.parent)
    run_env = {**os.environ,
           "PYTHONPATH": _SRC_PATH + os.pathsep + os.environ.get("PYTHONPATH", "")}
    return subprocess.run(
        [sys.executable, "-m", "opc_foundation.cli"] + args,
        capture_output=True, text=True, env=run_env,
        cwd=_CWD
    )


def test_version_is_0_1_3():
    r = _run(["version"])
    assert r.returncode == 0
    assert "0.1.3" in r.stdout


def test_skills_list():
    r = _run(["skills", "list"])
    assert r.returncode == 0
    assert "theme-validation" in r.stdout
    assert "concierge-mvp" in r.stdout
    assert "minimalist-review" in r.stdout
    # All should show as OFF (default_enabled=false)
    assert "[OFF]" in r.stdout
    assert "[ON]" not in r.stdout


def test_skills_validate():
    r = _run(["skills", "validate"])
    assert r.returncode == 0
    assert "OK" in r.stdout


def test_skills_show_theme_validation():
    r = _run(["skills", "show", "theme-validation"])
    assert r.returncode == 0
    assert "theme-validation" in r.stdout
    assert "default_enabled" in r.stdout
    assert "requires_user_trigger" in r.stdout


def test_skills_show_not_found():
    r = _run(["skills", "show", "nonexistent-skill"])
    assert r.returncode != 0


def test_skills_list_shows_6_skills():
    r = _run(["skills", "list"])
    assert r.returncode == 0
    # Count skill entries by "[OFF]" markers
    off_count = r.stdout.count("[OFF]")
    assert off_count == 6