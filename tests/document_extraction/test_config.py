"""Document Extraction 配置测试。"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from opc_foundation.document_extraction.config import (
    load_config,
    validate_config,
)


class TestLoadConfig:
    """测试配置加载。"""

    def test_load_example_config(self, tmp_path: Path):
        """测试加载示例配置。"""
        config_data = {
            "archive_root": "./data/document_extraction",
            "defaults": {
                "max_documents": 20,
                "save_raw": True,
                "save_markdown": True,
                "save_metadata": True,
                "extract_text": True,
                "extract_tables": False,
                "ocr_enabled": False,
            },
            "sources": [
                {
                    "source_id": "test_local",
                    "source_name": "Test Local Documents",
                    "source_type": "local_document",
                    "input_path": str(tmp_path / "docs"),
                    "input_glob": "*.txt",
                    "enabled": False,  # 全部 disabled
                    "legal_profile": "user_provided",
                }
            ],
        }

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert config.archive_root == "./data/document_extraction"
        assert len(config.sources) == 1
        assert config.sources[0].source_id == "test_local"
        assert config.sources[0].enabled is False


class TestValidateConfig:
    """测试配置验证。"""
    pass  # MVP 版本暂时跳过复杂验证测试
