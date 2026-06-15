"""LLM response cache keyed by provider/model/prompt_version/input/config/scope."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..storage.path_utils import ensure_parent


def _make_cache_key(
    provider: str,
    model: str,
    prompt_version: str,
    input_hash: str,
    config_version: str,
    run_scope: str,
) -> str:
    raw = json.dumps(
        {
            "provider": provider,
            "model": model,
            "prompt_version": prompt_version,
            "input_hash": input_hash,
            "config_version": config_version,
            "run_scope": run_scope,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


class LLMCache:
    """File-based JSON cache for LLM responses.

    Cache key must include provider, model, prompt_version, input_hash,
    config_version, and run_scope to prevent stale-cache cross-contamination.
    """

    def __init__(self, cache_dir: str | Path = ".llm_cache") -> None:
        self._cache_dir = Path(cache_dir)

    def _path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def get(
        self,
        provider: str,
        model: str,
        prompt_version: str,
        input_hash: str,
        config_version: str = "v1",
        run_scope: str = "global",
    ) -> dict[str, Any] | None:
        key = _make_cache_key(provider, model, prompt_version, input_hash, config_version, run_scope)
        p = self._path(key)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return None

    def set(
        self,
        provider: str,
        model: str,
        prompt_version: str,
        input_hash: str,
        value: dict[str, Any],
        config_version: str = "v1",
        run_scope: str = "global",
    ) -> str:
        key = _make_cache_key(provider, model, prompt_version, input_hash, config_version, run_scope)
        p = ensure_parent(self._path(key))
        p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        return key

    def make_input_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def make_key(
        self,
        provider: str,
        model: str,
        prompt_version: str,
        input_hash: str,
        config_version: str = "v1",
        run_scope: str = "global",
    ) -> str:
        return _make_cache_key(provider, model, prompt_version, input_hash, config_version, run_scope)
