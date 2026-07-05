#!/usr/bin/env python3
"""M3C-6C.1 Low-frequency Observation check script.

Verifies that the observation harness configuration and runtime data comply
with all boundary constraints.

Usage:
    python scripts/check_foundation_low_frequency_observation.py

Exit code 0 = all checks passed, 1 = failures detected.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

CONFIG_PATH = (
    _REPO_ROOT / "configs" / "foundation_m3c_6c1_low_frequency_observation.example.yaml"
)
RUNTIME_DATA_DIR = _REPO_ROOT / "data" / "foundation_low_frequency_observation"


def check_config() -> list[str]:
    """Check the observation config file."""
    errors: list[str] = []

    if not CONFIG_PATH.exists():
        errors.append(f"Config file not found: {CONFIG_PATH}")
        return errors

    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config.get("scope", {}).get("production_enabled") is not False:
        errors.append("scope.production_enabled must be False")

    if config.get("scope", {}).get("creates_permanent_automation") is not False:
        errors.append("scope.creates_permanent_automation must be False")

    if config.get("scope", {}).get("affects_trial_v2_allowlist") is not False:
        errors.append("scope.affects_trial_v2_allowlist must be False")

    if config.get("scope", {}).get("affects_trae_scheduling") is not False:
        errors.append("scope.affects_trae_scheduling must be False")

    sources = config.get("sources", [])
    source_ids = [s.get("source_id") for s in sources]
    if source_ids != ["merck_ir"]:
        errors.append(f"sources should only contain merck_ir, got: {source_ids}")

    for source in sources:
        sid = source.get("source_id", "")
        if source.get("trial_v2_allowlist_allowed_now") is not False:
            errors.append(f"{sid}: trial_v2_allowlist_allowed_now must be False")
        if source.get("low_frequency_allowed_now") is not True:
            errors.append(f"{sid}: low_frequency_allowed_now must be True")
        if source.get("production_enabled") is not False:
            errors.append(f"{sid}: production_enabled must be False")
        if source.get("timestamp_confidence_when_missing") != "LOW":
            errors.append(f"{sid}: timestamp_confidence_when_missing must be LOW")

    obs = config.get("observation", {})
    if obs.get("target_days") != 7:
        errors.append("observation.target_days must be 7")
    if obs.get("create_trae_task_now") is not False:
        errors.append("observation.create_trae_task_now must be False")
    if obs.get("manual_approval_required_before_scheduling") is not True:
        errors.append("observation.manual_approval_required_before_scheduling must be True")

    return errors


def check_runtime_data_gitignored() -> list[str]:
    """Check that runtime data is gitignored."""
    errors: list[str] = []

    gitignore_path = _REPO_ROOT / ".gitignore"
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text(encoding="utf-8")
        if "data/foundation_low_frequency_observation/" not in gitignore_content:
            errors.append(
                ".gitignore does not contain 'data/foundation_low_frequency_observation/'"
            )

    return errors


def check_no_sensitive_data() -> list[str]:
    """Check that runtime data files don't contain sensitive data."""
    errors: list[str] = []

    sensitive_patterns = [
        "http_proxy=", "https_proxy=", "cookie:", "authorization:",
        "bearer ", "api_key=", "secret=", "password=",
    ]

    if RUNTIME_DATA_DIR.exists():
        for file_path in RUNTIME_DATA_DIR.rglob("*"):
            if file_path.is_file():
                content = file_path.read_text(encoding="utf-8", errors="replace")
                lower = content.lower()
                for pattern in sensitive_patterns:
                    if pattern in lower:
                        errors.append(
                            f"Sensitive keyword '{pattern}' found in {file_path.name}"
                        )

    return errors


def check_no_playwright_selenium() -> list[str]:
    """Check that no Playwright/Selenium is imported in scripts."""
    errors: list[str] = []

    scripts_dir = _REPO_ROOT / "scripts"
    for script in scripts_dir.glob("*.py"):
        content = script.read_text(encoding="utf-8")
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                lower = stripped.lower()
                if "playwright" in lower:
                    errors.append(f"{script.name}: Playwright import found")
                if "selenium" in lower:
                    errors.append(f"{script.name}: Selenium import found")

    return errors


def main() -> int:
    print("Running low-frequency observation checks...")
    print()

    all_errors: list[str] = []

    print("1. Checking observation config boundaries...")
    config_errors = check_config()
    if config_errors:
        for e in config_errors:
            print(f"   FAIL: {e}")
        all_errors.extend(config_errors)
    else:
        print("   PASS: config boundaries OK")

    print("2. Checking runtime data is gitignored...")
    git_errors = check_runtime_data_gitignored()
    if git_errors:
        for e in git_errors:
            print(f"   FAIL: {e}")
        all_errors.extend(git_errors)
    else:
        print("   PASS: runtime data properly ignored")

    print("3. Checking reports for sensitive data...")
    sensitive_errors = check_no_sensitive_data()
    if sensitive_errors:
        for e in sensitive_errors:
            print(f"   FAIL: {e}")
        all_errors.extend(sensitive_errors)
    else:
        print("   PASS: no sensitive data in reports")

    print("4. Checking for Playwright/Selenium imports...")
    ps_errors = check_no_playwright_selenium()
    if ps_errors:
        for e in ps_errors:
            print(f"   FAIL: {e}")
        all_errors.extend(ps_errors)
    else:
        print("   PASS: no Playwright/Selenium imports")

    print()
    if all_errors:
        print(f"FAILED: {len(all_errors)} check(s) failed")
        return 1
    else:
        print("ALL CHECKS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
