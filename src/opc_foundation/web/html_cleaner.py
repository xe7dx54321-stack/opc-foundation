"""Basic HTML cleaning utility."""
from __future__ import annotations

import re


def clean_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
