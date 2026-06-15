"""Test RawSignal schema validation."""
import pytest
from pydantic import ValidationError
from opc_foundation.signals.raw_signal_schema import RawSignal


def _make(**kwargs):
    base = dict(
        signal_id="sig_001",
        source_id="hn",
        source_type="community_discussion",
        source_url="https://example.com",
        raw_text="Some text content here.",
        fetched_at="2026-06-01T00:00:00+00:00",
    )
    base.update(kwargs)
    return RawSignal(**base)


def test_valid_signal():
    sig = _make()
    assert sig.signal_id == "sig_001"
    assert sig.source_url == "https://example.com"


def test_missing_source_url_and_note():
    with pytest.raises(ValidationError):
        _make(source_url=None, source_note=None)


def test_source_note_alone_is_ok():
    sig = _make(source_url=None, source_note="manual batch item")
    assert sig.source_note == "manual batch item"


def test_empty_raw_text():
    with pytest.raises(ValidationError):
        _make(raw_text="")


def test_metadata_extension():
    sig = _make(metadata={"custom_key": "value"})
    assert sig.metadata["custom_key"] == "value"
