"""Test SourceRegistry."""
import pytest
from pathlib import Path
from opc_foundation.sources.source_registry import SourceRegistry


SAMPLE_YAML = """
sources:
  - source_id: hn
    source_name: Hacker News
    source_type: community_discussion
    connector: hacker_news
    enabled: true
    trust_weight: 0.85
    tags:
      - tech
  - source_id: disabled_src
    source_name: Disabled
    source_type: rss
    connector: rss
    enabled: false
    trust_weight: 0.5
"""


def test_load_from_yaml(tmp_path):
    f = tmp_path / "reg.yaml"
    f.write_text(SAMPLE_YAML, encoding="utf-8")
    reg = SourceRegistry.from_yaml(f)
    assert len(reg.all_sources()) == 2


def test_get_enabled_sources(tmp_path):
    f = tmp_path / "reg.yaml"
    f.write_text(SAMPLE_YAML, encoding="utf-8")
    reg = SourceRegistry.from_yaml(f)
    enabled = reg.get_enabled_sources()
    assert len(enabled) == 1
    assert enabled[0].source_id == "hn"


def test_get_source(tmp_path):
    f = tmp_path / "reg.yaml"
    f.write_text(SAMPLE_YAML, encoding="utf-8")
    reg = SourceRegistry.from_yaml(f)
    src = reg.get_source("hn")
    assert src is not None
    assert src.source_name == "Hacker News"


def test_filter_by_tags(tmp_path):
    f = tmp_path / "reg.yaml"
    f.write_text(SAMPLE_YAML, encoding="utf-8")
    reg = SourceRegistry.from_yaml(f)
    result = reg.filter_by_tags(["tech"])
    assert len(result) == 1


def test_validate_registry(tmp_path):
    f = tmp_path / "reg.yaml"
    f.write_text(SAMPLE_YAML, encoding="utf-8")
    reg = SourceRegistry.from_yaml(f)
    errors = reg.validate_registry()
    assert errors == []


def test_example_yaml():
    """The bundled example YAML must load cleanly."""
    p = Path("examples/source_registry.example.yaml")
    assert p.exists(), "example YAML missing"
    reg = SourceRegistry.from_yaml(p)
    assert len(reg.get_enabled_sources()) >= 1
