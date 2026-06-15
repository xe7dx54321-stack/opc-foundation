"""Test JsonlStore."""
import pytest
from pydantic import BaseModel
from opc_foundation.storage.jsonl_store import JsonlStore


class SampleModel(BaseModel):
    name: str
    value: int


def test_write_and_load(tmp_path):
    p = tmp_path / "test.jsonl"
    records = [SampleModel(name="a", value=1), SampleModel(name="b", value=2)]
    JsonlStore.write_records(p, records)
    loaded = JsonlStore.load_records(p, model=SampleModel)
    assert len(loaded) == 2
    assert loaded[0].name == "a"
    assert loaded[1].value == 2


def test_append(tmp_path):
    p = tmp_path / "append.jsonl"
    JsonlStore.write_records(p, [SampleModel(name="x", value=10)])
    JsonlStore.append_record(p, SampleModel(name="y", value=20))
    loaded = JsonlStore.load_records(p, model=SampleModel)
    assert len(loaded) == 2
    assert loaded[1].name == "y"


def test_empty_file(tmp_path):
    p = tmp_path / "empty.jsonl"
    loaded = JsonlStore.load_records(p)
    assert loaded == []


def test_iter_records(tmp_path):
    p = tmp_path / "iter.jsonl"
    JsonlStore.write_records(p, [SampleModel(name="z", value=99)])
    items = list(JsonlStore.iter_records(p, model=SampleModel))
    assert items[0].name == "z"


def test_auto_create_parent(tmp_path):
    p = tmp_path / "nested" / "dir" / "file.jsonl"
    JsonlStore.write_records(p, [SampleModel(name="n", value=0)])
    assert p.exists()
