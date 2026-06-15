"""YAML / JSON configuration loaders."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict."""
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_json_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON file and return its contents as a dict."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
