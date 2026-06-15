"""Lightweight Markdown report builder."""
from __future__ import annotations

from pathlib import Path

from ..storage.path_utils import ensure_parent


class MarkdownBuilder:
    """Build a Markdown document section by section."""

    def __init__(self) -> None:
        self._parts: list[str] = []

    def heading(self, level: int, text: str) -> "MarkdownBuilder":
        prefix = "#" * max(1, min(level, 6))
        self._parts.append(f"{prefix} {text}\n")
        return self

    def paragraph(self, text: str) -> "MarkdownBuilder":
        self._parts.append(f"{text}\n")
        return self

    def bullet_list(self, items: list[str]) -> "MarkdownBuilder":
        for item in items:
            self._parts.append(f"- {item}\n")
        self._parts.append("")
        return self

    def table(self, headers: list[str], rows: list[list[str]]) -> "MarkdownBuilder":
        from .table_builder import build_table
        self._parts.append(build_table(headers, rows))
        return self

    def code_block(self, text: str, language: str = "") -> "MarkdownBuilder":
        self._parts.append(f"```{language}\n{text}\n```\n")
        return self

    def horizontal_rule(self) -> "MarkdownBuilder":
        self._parts.append("---\n")
        return self

    def build(self) -> str:
        return "\n".join(self._parts)

    def write_report(self, path: str | Path) -> None:
        p = ensure_parent(path)
        p.write_text(self.build(), encoding="utf-8")
