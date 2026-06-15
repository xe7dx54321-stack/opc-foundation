"""Test CsvStore."""
from opc_foundation.storage.csv_store import CsvStore


def test_write_and_load(tmp_path):
    p = tmp_path / "data.csv"
    rows = [{"url": "http://a.com", "title": "A"}, {"url": "http://b.com", "title": "B"}]
    CsvStore.write_csv_dicts(p, rows)
    loaded = CsvStore.load_csv_dicts(p)
    assert len(loaded) == 2
    assert loaded[0]["url"] == "http://a.com"


def test_empty_file(tmp_path):
    p = tmp_path / "empty.csv"
    CsvStore.write_csv_dicts(p, [])
    loaded = CsvStore.load_csv_dicts(p)
    assert loaded == []


def test_missing_file(tmp_path):
    p = tmp_path / "missing.csv"
    loaded = CsvStore.load_csv_dicts(p)
    assert loaded == []
