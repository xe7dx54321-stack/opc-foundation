"""Test versioning."""
import subprocess
import sys


def test_version_importable():
    from opc_foundation import __version__
    assert isinstance(__version__, str)
    assert __version__.startswith("0.")


def test_version_module():
    from opc_foundation.version import __version__
    assert __version__ == "0.1.2"


def test_version_cli():
    result = subprocess.run(
        [sys.executable, "-m", "opc_foundation.cli", "version"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "0.1" in result.stdout