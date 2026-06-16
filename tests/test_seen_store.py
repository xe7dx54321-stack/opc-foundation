"""Test SeenStore incremental dedupe."""
from opc_foundation.signals.seen_store import SeenStore, SeenSignalRecord
from opc_foundation.signals.raw_signal_schema import RawSignal
from opc_foundation.run.time_utils import utcnow_iso


def _sig(signal_id, url=None, text="some content here", note=None):
    return RawSignal(
        signal_id=signal_id,
        source_id="src",
        source_type="web",
        source_url=url,
        source_note=note or (None if url else "fallback note"),
        raw_text=text,
        fetched_at=utcnow_iso(),
    )


def test_has_seen_returns_false_for_new(tmp_path):
    store = SeenStore(tmp_path / "seen.jsonl")
    sig = _sig("s1", url="https://example.com/a")
    assert store.has_seen(sig) is False


def test_mark_seen_creates_record(tmp_path):
    store = SeenStore(tmp_path / "seen.jsonl")
    sig = _sig("s1", url="https://example.com/a")
    rec = store.mark_seen(sig, run_id="run_001")
    assert rec.source_id == "src"
    assert rec.seen_count == 1
    assert rec.last_run_id == "run_001"


def test_has_seen_after_mark(tmp_path):
    store = SeenStore(tmp_path / "seen.jsonl")
    sig = _sig("s1", url="https://example.com/a")
    store.mark_seen(sig)
    assert store.has_seen(sig) is True


def test_mark_seen_updates_count(tmp_path):
    store = SeenStore(tmp_path / "seen.jsonl")
    sig = _sig("s1", url="https://example.com/a")
    store.mark_seen(sig, run_id="run_001")
    rec = store.mark_seen(sig, run_id="run_002")
    assert rec.seen_count == 2
    assert rec.last_run_id == "run_002"


def test_filter_new_separates_new_and_seen(tmp_path):
    store = SeenStore(tmp_path / "seen.jsonl")
    sig_a = _sig("s1", url="https://example.com/a", text="content a")
    sig_b = _sig("s2", url="https://example.com/b", text="content b")
    sig_c = _sig("s3", url="https://example.com/c", text="content c")

    # Pre-mark sig_a
    store.mark_seen(sig_a)

    new_sigs, already_seen = store.filter_new([sig_a, sig_b, sig_c])
    assert len(new_sigs) == 2
    assert len(already_seen) == 1
    assert already_seen[0].signal_id == "s1"


def test_filter_new_marks_all_seen(tmp_path):
    store = SeenStore(tmp_path / "seen.jsonl")
    sigs = [_sig(f"s{i}", url=f"https://example.com/{i}", text=f"content {i}") for i in range(3)]
    new_sigs, already_seen = store.filter_new(sigs)
    assert len(new_sigs) == 3
    assert len(already_seen) == 0
    # Run again — all should now be seen
    new_sigs2, already_seen2 = store.filter_new(sigs)
    assert len(new_sigs2) == 0
    assert len(already_seen2) == 3


def test_persistence_across_instances(tmp_path):
    path = tmp_path / "seen.jsonl"
    store1 = SeenStore(path)
    sig = _sig("s1", url="https://example.com/persistent")
    store1.mark_seen(sig)

    store2 = SeenStore(path)
    assert store2.has_seen(sig) is True


def test_content_hash_fallback(tmp_path):
    store = SeenStore(tmp_path / "seen.jsonl")
    # No URL — falls back to content hash
    sig1 = _sig("s1", note="manual note", text="unique content body text")
    sig2 = _sig("s2", note="other note", text="unique content body text")
    store.mark_seen(sig1)
    assert store.has_seen(sig2) is True  # same content hash