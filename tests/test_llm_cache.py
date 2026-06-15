"""Test LLM cache key composition."""
from opc_foundation.llm.llm_cache import LLMCache, _make_cache_key


def test_cache_key_includes_all_dimensions():
    key = _make_cache_key(
        provider="openai",
        model="gpt-4o",
        prompt_version="v2",
        input_hash="abc123",
        config_version="cfg_v1",
        run_scope="run_001",
    )
    assert isinstance(key, str)
    assert len(key) == 64  # sha256 hex


def test_different_prompt_version_gives_different_key():
    k1 = _make_cache_key("openai", "gpt-4o", "v1", "abc", "cfg", "scope")
    k2 = _make_cache_key("openai", "gpt-4o", "v2", "abc", "cfg", "scope")
    assert k1 != k2


def test_different_run_scope_gives_different_key():
    k1 = _make_cache_key("openai", "gpt-4o", "v1", "abc", "cfg", "run_001")
    k2 = _make_cache_key("openai", "gpt-4o", "v1", "abc", "cfg", "run_002")
    assert k1 != k2


def test_different_input_hash_gives_different_key():
    k1 = _make_cache_key("openai", "gpt-4o", "v1", "abc", "cfg", "scope")
    k2 = _make_cache_key("openai", "gpt-4o", "v1", "xyz", "cfg", "scope")
    assert k1 != k2


def test_cache_set_and_get(tmp_path):
    cache = LLMCache(cache_dir=tmp_path)
    cache.set("openai", "gpt-4o", "v1", "hash001", {"text": "result"}, run_scope="run_x")
    result = cache.get("openai", "gpt-4o", "v1", "hash001", run_scope="run_x")
    assert result is not None
    assert result["text"] == "result"


def test_cache_miss_returns_none(tmp_path):
    cache = LLMCache(cache_dir=tmp_path)
    result = cache.get("openai", "gpt-4o", "v1", "missing_hash", run_scope="run_y")
    assert result is None


def test_cache_scope_isolation(tmp_path):
    cache = LLMCache(cache_dir=tmp_path)
    cache.set("openai", "gpt-4o", "v1", "h1", {"text": "old"}, run_scope="run_001")
    result = cache.get("openai", "gpt-4o", "v1", "h1", run_scope="run_002")
    assert result is None  # Different run scope = cache miss
