"""Test config loader."""
import tempfile
import json
from pathlib import Path
import pytest
from opc_foundation.config.loader import load_yaml_config, load_json_config
from opc_foundation.config.schema import FoundationConfig


def test_load_yaml(tmp_path):
    f = tmp_path / "cfg.yaml"
    f.write_text("project_id: test\npipeline_name: p1\n", encoding="utf-8")
    data = load_yaml_config(f)
    assert data["project_id"] == "test"
    assert data["pipeline_name"] == "p1"


def test_load_json(tmp_path):
    f = tmp_path / "cfg.json"
    f.write_text(json.dumps({"project_id": "json_test"}), encoding="utf-8")
    data = load_json_config(f)
    assert data["project_id"] == "json_test"


def test_foundation_config_defaults():
    cfg = FoundationConfig()
    assert cfg.pipeline_name == "default"
    assert cfg.output_dir == "outputs"


def test_foundation_config_custom():
    cfg = FoundationConfig(project_id="opc", pipeline_name="acq", output_dir="out")
    assert cfg.project_id == "opc"
    assert cfg.pipeline_name == "acq"
