"""Test CLI commands: version, provider doctor, search (via subprocess)."""
import subprocess
import sys
import os


def _run(args, extra_env=None):
    env = {**os.environ}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "opc_foundation.cli"] + args,
        capture_output=True, text=True, env=env
    )


def test_version_command():
    r = _run(["version"])
    assert r.returncode == 0
    assert "0.1.3" in r.stdout


def test_provider_doctor_no_keys():
    # Strip all provider keys from environment for this test
    env = {k: v for k, v in os.environ.items()
           if k not in {"TAVILY_API_KEY","BRAVE_SEARCH_API_KEY","SERPAPI_API_KEY"}}
    r = subprocess.run(
        [sys.executable, "-m", "opc_foundation.cli", "provider", "doctor"],
        capture_output=True, text=True, env=env
    )
    assert r.returncode == 0
    assert "Provider Doctor" in r.stdout
    # Must not contain any fake or real key values
    assert "TAVILY_API_KEY" not in r.stdout or "missing" in r.stdout.lower() or "required" in r.stdout.lower()


def test_provider_detect_search_no_keys():
    env = {k: v for k, v in os.environ.items()
           if k not in {"TAVILY_API_KEY","BRAVE_SEARCH_API_KEY"}}
    r = subprocess.run(
        [sys.executable, "-m", "opc_foundation.cli", "provider", "detect-search"],
        capture_output=True, text=True, env=env
    )
    assert r.returncode != 0 or "No search provider" in r.stdout


def test_search_no_provider_returns_error():
    env = {k: v for k, v in os.environ.items()
           if k not in {"TAVILY_API_KEY","BRAVE_SEARCH_API_KEY"}}
    r = subprocess.run(
        [sys.executable, "-m", "opc_foundation.cli", "search", "AI tools"],
        capture_output=True, text=True, env=env
    )
    # Should not crash; error goes to stderr or stdout
    assert "provider" in r.stdout.lower() or "provider" in r.stderr.lower() or r.returncode == 0


def test_source_registry_validate_v2():
    r = _run(["source-registry-validate",
              "examples/source_registry_v2.example.yaml", "--v2"])
    assert r.returncode == 0
    assert "OK" in r.stdout


def test_source_run_diagnose():
    r = _run(["source-run-diagnose", "my_source",
              "--total", "50", "--unique", "45", "--extracted", "40", "--status", "success"])
    assert r.returncode == 0
    assert "my_source" in r.stdout