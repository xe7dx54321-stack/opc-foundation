"""Test SourceDefinitionV2 and SourceRegistryV2."""
import pytest
from pathlib import Path
from pydantic import ValidationError
from opc_foundation.sources_v2 import SourceDefinitionV2, SourceRegistryV2


def _make_source(**kwargs):
    base = dict(
        source_id="test_src", source_name="Test", source_type="search",
        source_category="search_discovery", fetch_method="search_provider",
        trust_tier="medium",
    )
    base.update(kwargs)
    return SourceDefinitionV2(**base)


def test_valid_source():
    s = _make_source()
    assert s.source_id == "test_src"
    assert s.trust_tier == "medium"
    assert s.enabled is True


def test_invalid_trust_tier():
    with pytest.raises(ValidationError):
        _make_source(trust_tier="excellent")


def test_invalid_signal_fit_range():
    with pytest.raises(ValidationError):
        _make_source(signal_fit={"pain_evidence": 1.5})


def test_valid_signal_fit():
    s = _make_source(signal_fit={"pain_evidence": 0.7, "market_context": 0.4})
    assert s.signal_fit["pain_evidence"] == 0.7


def test_registry_validate_no_errors():
    reg = SourceRegistryV2(
        registry_id="r1", version="0.1",
        sources=[_make_source()]
    )
    errors = reg.validate_registry()
    assert errors == []


def test_registry_validate_duplicate_ids():
    reg = SourceRegistryV2(
        registry_id="r1", version="0.1",
        sources=[_make_source(), _make_source()]
    )
    errors = reg.validate_registry()
    assert any("Duplicate" in e for e in errors)


def test_registry_requires_key_no_env_vars():
    s = _make_source(requires_key=True, required_env_vars=[])
    reg = SourceRegistryV2(registry_id="r1", version="0.1", sources=[s])
    errors = reg.validate_registry()
    assert any("required_env_vars" in e for e in errors)


def test_registry_get_enabled():
    s1 = _make_source(source_id="a", enabled=True)
    s2 = _make_source(source_id="b", enabled=False)
    reg = SourceRegistryV2(registry_id="r1", version="0.1", sources=[s1, s2])
    enabled = reg.get_enabled()
    assert len(enabled) == 1
    assert enabled[0].source_id == "a"


def test_registry_filter_by_type():
    s1 = _make_source(source_id="a", source_type="search")
    s2 = _make_source(source_id="b", source_type="rss")
    reg = SourceRegistryV2(registry_id="r1", version="0.1", sources=[s1, s2])
    assert len(reg.filter_by_type("search")) == 1


def test_load_example_yaml():
    p = Path("examples/source_registry_v2.example.yaml")
    assert p.exists()
    reg = SourceRegistryV2.from_yaml(str(p))
    assert len(reg.sources) > 0
    errors = reg.validate_registry()
    assert errors == []