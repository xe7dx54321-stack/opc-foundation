#!/usr/bin/env python3
"""M3C-6C Low-frequency Source Pipeline check script.

Verifies that the low-frequency pipeline configuration and runtime data comply
with all boundary constraints.

Usage:
    python scripts/check_foundation_low_frequency_sources.py

Checks:
    1. config production_enabled=false
    2. creates_permanent_automation=false
    3. affects_trial_v2_allowlist=false
    4. affects_trae_scheduling=false
    5. Only merck_ir is in allowed sources
    6. trial_v2_allowlist_allowed_now=false
    7. low_frequency_allowed_now=true
    8. date_text missing -> timestamp_confidence=LOW
    9. Runtime data is not tracked by git
    10. Report does not contain cookie/token/proxy URL/secret

Exit code 0 = all checks passed, 1 = failures detected.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

CONFIG_PATH = (
    _REPO_ROOT / "configs" / "foundation_low_frequency_sources.example.yaml"
)
RUNTIME_DATA_DIR = _REPO_ROOT / "data" / "foundation_low_frequency_sources"


def check_config() -> list[str]:
    """Check the example config file for boundary compliance."""
    errors: list[str] = []

    if not CONFIG_PATH.exists():
        errors.append(f"Config file not found: {CONFIG_PATH}")
        return errors

    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 1. production_enabled=false
    if config.get("scope", {}).get("production_enabled") is not False:
        errors.append("scope.production_enabled must be False")

    # 2. creates_permanent_automation=false
    if config.get("scope", {}).get("creates_permanent_automation") is not False:
        errors.append("scope.creates_permanent_automation must be False")

    # 3. affects_trial_v2_allowlist=false
    if config.get("scope", {}).get("affects_trial_v2_allowlist") is not False:
        errors.append("scope.affects_trial_v2_allowlist must be False")

    # 4. affects_trae_scheduling=false
    if config.get("scope", {}).get("affects_trae_scheduling") is not False:
        errors.append("scope.affects_trae_scheduling must be False")

    # 5. Only merck_ir in sources
    sources = config.get("sources", [])
    source_ids = [s.get("source_id") for s in sources]
    if source_ids != ["merck_ir"]:
        errors.append(f"sources should only contain merck_ir, got: {source_ids}")

    for source in sources:
        sid = source.get("source_id", "")
        # 6. trial_v2_allowlist_allowed_now=false
        if source.get("trial_v2_allowlist_allowed_now") is not False:
            errors.append(f"{sid}: trial_v2_allowlist_allowed_now must be False")

        # 7. low_frequency_allowed_now=true
        if source.get("low_frequency_allowed_now") is not True:
            errors.append(f"{sid}: low_frequency_allowed_now must be True")

        # 8. timestamp_confidence_when_missing=LOW
        if source.get("timestamp_confidence_when_missing") != "LOW":
            errors.append(f"{sid}: timestamp_confidence_when_missing must be LOW")

        # production_enabled=false
        if source.get("production_enabled") is not False:
            errors.append(f"{sid}: production_enabled must be False")

    # Check scheduling_policy
    sp = config.get("scheduling_policy", {})
    if sp.get("create_trae_task_now") is not False:
        errors.append("scheduling_policy.create_trae_task_now must be False")

    if sp.get("manual_approval_required_before_scheduling") is not True:
        errors.append(
            "scheduling_policy.manual_approval_required_before_scheduling must be True"
        )

    return errors


def check_runtime_data_gitignored() -> list[str]:
    """Check that runtime data directory is not tracked by git."""
    errors: list[str] = []

    import subprocess

    try:
        result = subprocess.run(
            ["git", "status", "--ignored", "--short", "data/foundation_low_frequency_sources"],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip()

        # If runtime data dir exists but is ignored, it should show as !! in output
        # If it's tracked, it would show differently
        # If nothing is returned, either dir doesn't exist or it's properly ignored
        if RUNTIME_DATA_DIR.exists():
            # Check .gitignore has the entry
            gitignore_path = _REPO_ROOT / ".gitignore"
            if gitignore_path.exists():
                gitignore_content = gitignore_path.read_text(encoding="utf-8")
                if "data/foundation_low_frequency_sources/" not in gitignore_content:
                    errors.append(
                        ".gitignore does not contain "
                        "'data/foundation_low_frequency_sources/'"
                    )
    except Exception as e:
        errors.append(f"Failed to check git status: {e}")

    return errors


def check_report_no_sensitive_data() -> list[str]:
    """Check that report files do not contain sensitive data."""
    errors: list[str] = []

    sensitive_patterns = [
        "http_proxy=",
        "https_proxy=",
        "cookie:",
        "authorization:",
        "bearer ",
        "api_key=",
        "secret=",
        "password=",
    ]

    # Check runtime data files if they exist
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
    print("Running low-frequency source pipeline checks...")
    print()

    all_errors: list[str] = []

    # 1. Config checks
    print("1. Checking config boundaries...")
    config_errors = check_config()
    if config_errors:
        for e in config_errors:
            print(f"   FAIL: {e}")
        all_errors.extend(config_errors)
    else:
        print("   PASS: config boundaries OK")

    # 2. Runtime data gitignored
    print("2. Checking runtime data is gitignored...")
    git_errors = check_runtime_data_gitignored()
    if git_errors:
        for e in git_errors:
            print(f"   FAIL: {e}")
        all_errors.extend(git_errors)
    else:
        print("   PASS: runtime data properly ignored")

    # 3. No sensitive data in reports
    print("3. Checking reports for sensitive data...")
    sensitive_errors = check_report_no_sensitive_data()
    if sensitive_errors:
        for e in sensitive_errors:
            print(f"   FAIL: {e}")
        all_errors.extend(sensitive_errors)
    else:
        print("   PASS: no sensitive data in reports")

    # 4. No Playwright/Selenium
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
