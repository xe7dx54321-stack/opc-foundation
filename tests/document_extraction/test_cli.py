"""CLI 测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.document_extraction.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestValidateConfig:
    """测试 validate-config 命令。"""

    def test_validate_nonexistent_config(self, tmp_path: Path):
        """不存在的配置文件应该报错。"""
        result = runner.invoke(app, ["--config", str(tmp_path / "nonexistent.yaml")])
        assert result.exit_code != 0
