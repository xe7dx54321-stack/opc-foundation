"""Test SourceSchema models."""
from opc_foundation.sources.source_schema import SourceQuery, SourceDefinition, FetchResult
from opc_foundation.signals.raw_signal_schema import RawSignal
from opc_foundation.run.time_utils import utcnow_iso


def test_source_query_defaults():
    q = SourceQuery(query_id="q1", source_id="hn")
    assert q.max_items == 50
    assert q.tags == []


def test_source_definition():
    sd = SourceDefinition(
        source_id="hn",
        source_name="Hacker News",
        source_type="community_discussion",
        connector="hacker_news",
    )
    assert sd.enabled is True
    assert sd.trust_weight == 0.5


def test_fetch_result():
    sig = RawSignal(
        signal_id="s1", source_id="hn", source_type="community_discussion",
        source_url="https://hn.com/1", raw_text="text", fetched_at=utcnow_iso()
    )
    fr = FetchResult(source_id="hn", connector="hacker_news", raw_signals=[sig], fetched_at=utcnow_iso())
    assert len(fr.raw_signals) == 1
