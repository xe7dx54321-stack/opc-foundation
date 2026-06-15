"""Test deduplication."""
from opc_foundation.signals.raw_signal_schema import RawSignal
from opc_foundation.signals.dedupe import (
    dedupe_raw_signals, dedupe_by_url_hash, dedupe_by_content_hash,
    hash_url, hash_text
)
from opc_foundation.run.time_utils import utcnow_iso


def _sig(signal_id, url=None, text="some content", note=None):
    return RawSignal(
        signal_id=signal_id,
        source_id="src",
        source_type="web",
        source_url=url,
        source_note=note or (None if url else "fallback note"),
        raw_text=text,
        fetched_at=utcnow_iso(),
    )


def test_dedupe_by_url_identifies_duplicates():
    url = "https://example.com/article"
    sigs = [_sig("s1", url=url), _sig("s2", url=url), _sig("s3", url="https://other.com")]
    result = dedupe_by_url_hash(sigs)
    assert len(result.unique_signals) == 2
    assert result.duplicate_count == 1


def test_dedupe_by_content_identifies_duplicates():
    sigs = [
        _sig("s1", url="https://a.com", text="identical text body"),
        _sig("s2", url="https://b.com", text="identical text body"),
        _sig("s3", url="https://c.com", text="different text"),
    ]
    result = dedupe_by_content_hash(sigs)
    assert len(result.unique_signals) == 2
    assert result.duplicate_count == 1


def test_dedupe_combined():
    sigs = [
        _sig("s1", url="https://a.com", text="text A"),
        _sig("s2", url="https://a.com", text="text A"),   # dup url
        _sig("s3", url="https://b.com", text="text A"),   # dup content
        _sig("s4", url="https://c.com", text="text C"),
    ]
    result = dedupe_raw_signals(sigs, by="both")
    assert len(result.unique_signals) == 2
    assert result.duplicate_count == 2


def test_no_duplicates():
    sigs = [_sig("s1", url="https://a.com", text="aaa"), _sig("s2", url="https://b.com", text="bbb")]
    result = dedupe_raw_signals(sigs)
    assert len(result.unique_signals) == 2
    assert result.duplicate_count == 0


def test_url_normalization():
    url1 = "https://Example.COM/page/"
    url2 = "https://example.com/page"
    assert hash_url(url1) == hash_url(url2)
