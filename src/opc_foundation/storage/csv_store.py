"""CSV read/write helpers."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .path_utils import ensure_parent


class CsvStore:
    """Simple CSV file adapter."""

    @staticmethod
    def load_csv_dicts(path: str | Path) -> list[dict[str, Any]]:
        """Load a CSV file and return a list of dicts."""
        p = Path(path)
        if not p.exists():
            return []
        with open(p, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            return [dict(row) for row in reader]

    @staticmethod
    def write_csv_dicts(
        path: str | Path,
        rows: list[dict[str, Any]],
        fieldnames: list[str] | None = None,
    ) -> None:
        """Write a list of dicts to a CSV file."""
        p = ensure_parent(path)
        if not rows:
            p.write_text("", encoding="utf-8")
            return
        fields = fieldnames or list(rows[0].keys())
        with open(p, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
