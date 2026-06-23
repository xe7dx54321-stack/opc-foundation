"""Short unique ID helpers."""
from __future__ import annotations

import uuid


def new_id(prefix: str = "") -> str:
    """Generate a random UUID4-based ID, optionally prefixed."""
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}{uid}" if prefix else uid


def new_run_id() -> str:
    """Generate a run-scoped ID."""
    return new_id("run_")


def generate_document_id() -> str:
    """Generate a document-scoped ID for Document Extraction."""
    return new_id("doc_")
