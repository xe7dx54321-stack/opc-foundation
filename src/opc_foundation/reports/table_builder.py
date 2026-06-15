"""Table builder helper."""
from __future__ import annotations


def build_table(headers: list[str], rows: list[list[str]]) -> str:
    """Return a GitHub-flavored Markdown table string."""
    header_row = "| " + " | ".join(str(h) for h in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body_rows = ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join([header_row, separator] + body_rows) + "\n"
