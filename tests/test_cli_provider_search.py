"""Test CLI commands: version, provider doctor, search (via subprocess)."""
import subprocess
import sys
import os
from pathlib import Path

# 确保 subprocess 从 src 目录导入（优先于系统 site-packages 中的旧版本）
_SRC_PATH = str(Path(__file__).parent.parent / "src")


def _run(args, extra_env=None):
    """通过 subprocess 运行 CLI 命令，确保 PYTHONPATH 指向 src 目录。

    参数：
        args: CLI 命令参数列表
        extra_env: 额外的环境变量

    返回：
        CompletedProcess 对象
    """
    env = {**os.environ}
    env["PYTHONPATH"] = _SRC_PATH + os.pathsep + env.get("PYTHONPATH", "")
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
    r = _run(["provider", "doctor"], extra_env=env)
    assert r.returncode == 0
    assert "Provider Doctor" in r.stdout
    # Must not contain any fake or real key values
    assert "TAVILY_API_KEY" not in r.stdout or "missing" in r.stdout.lower() or "required" in r.stdout.lower()


def test_provider_detect_search_no_keys():
    env = {k: v for k, v in os.environ.items()
           if k not in {"TAVILY_API_KEY","BRAVE_SEARCH_API_KEY"}}
    r = _run(["provider", "detect-search"], extra_env=env)
    assert r.returncode != 0 or "No search provider" in r.stdout


def test_search_no_provider_returns_error():
    env = {k: v for k, v in os.environ.items()
           if k not in {"TAVILY_API_KEY","BRAVE_SEARCH_API_KEY"}}
    r = _run(["search", "AI tools"], extra_env=env)
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
