"""JSONL (newline-delimited JSON) read/write helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, Type, TypeVar

from pydantic import BaseModel

from .path_utils import ensure_parent

T = TypeVar("T", bound=BaseModel)


class JsonlStore:
    """Simple JSONL file adapter."""

    @staticmethod
    def write_records(
        path: str | Path,
        records: list[BaseModel | dict],
        overwrite: bool = True,
    ) -> None:
        """Write a list of records to a JSONL file."""
        p = ensure_parent(path)
        mode = "w" if overwrite else "a"
        with open(p, mode, encoding="utf-8") as fh:
            for rec in records:
                if isinstance(rec, BaseModel):
                    fh.write(rec.model_dump_json() + "\n")
                else:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    @staticmethod
    def append_record(path: str | Path, record: BaseModel | dict) -> None:
        """Append a single record to a JSONL file."""
        p = ensure_parent(path)
        with open(p, "a", encoding="utf-8") as fh:
            if isinstance(record, BaseModel):
                fh.write(record.model_dump_json() + "\n")
            else:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def load_records(
        path: str | Path, model: Type[T] | None = None
    ) -> list[T | dict[str, Any]]:
        """Load all records from a JSONL file."""
        return list(JsonlStore.iter_records(path, model=model))

    @staticmethod
    def iter_records(
        path: str | Path, model: Type[T] | None = None
    ) -> Iterator[T | dict[str, Any]]:
        """Iterate over records in a JSONL file."""
        p = Path(path)
        if not p.exists():
            return
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if model is not None:
                    yield model.model_validate(data)
                else:
                    yield data
