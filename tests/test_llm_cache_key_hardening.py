"""LLMCache key isolation tests – prompt_version / run_scope / config_version."""
from opc_foundation.llm.llm_cache import LLMCache, _make_cache_key


def test_different_prompt_version_no_cache_hit(tmp_path):
    cache = LLMCache(tmp_path)
    cache.set("openai", "gpt-4o", "v1", "h1", {"result": "old"}, run_scope="run_x")
    assert cache.get("openai", "gpt-4o", "v2", "h1", run_scope="run_x") is None


def test_different_run_scope_no_cache_hit(tmp_path):
    cache = LLMCache(tmp_path)
    cache.set("openai", "gpt-4o", "v1", "h1", {"result": "old"}, run_scope="run_001")
    assert cache.get("openai", "gpt-4o", "v1", "h1", run_scope="run_002") is None


def test_different_config_version_no_cache_hit(tmp_path):
    cache = LLMCache(tmp_path)
    cache.set("openai", "gpt-4o", "v1", "h1", {"r": "x"}, config_version="cfg_v1")
    assert cache.get("openai", "gpt-4o", "v1", "h1", config_version="cfg_v2") is None


def test_different_model_no_cache_hit(tmp_path):
    cache = LLMCache(tmp_path)
    cache.set("openai", "gpt-4o", "v1", "h1", {"r": "x"})
    assert cache.get("openai", "gpt-4o-mini", "v1", "h1") is None


def test_same_key_hits(tmp_path):
    cache = LLMCache(tmp_path)
    cache.set("openai", "gpt-4o", "v1", "h1", {"r": "hit"},
               config_version="cfg_v1", run_scope="run_A")
    result = cache.get("openai", "gpt-4o", "v1", "h1",
                       config_version="cfg_v1", run_scope="run_A")
    assert result is not None
    assert result["r"] == "hit"


def test_make_input_hash_deterministic(tmp_path):
    cache = LLMCache(tmp_path)
    h1 = cache.make_input_hash("same text")
    h2 = cache.make_input_hash("same text")
    h3 = cache.make_input_hash("different text")
    assert h1 == h2
    assert h1 != h3


def test_key_contains_all_dimensions():
    k = _make_cache_key("anthropic", "claude-3", "v2", "abc123", "cfg_v2", "scope_X")
    assert isinstance(k, str) and len(k) == 64
    # Different on every dimension
    assert k != _make_cache_key("openai",    "claude-3", "v2", "abc123", "cfg_v2", "scope_X")
    assert k != _make_cache_key("anthropic", "gpt-4o",   "v2", "abc123", "cfg_v2", "scope_X")
    assert k != _make_cache_key("anthropic", "claude-3", "v1", "abc123", "cfg_v2", "scope_X")
    assert k != _make_cache_key("anthropic", "claude-3", "v2", "xyz999", "cfg_v2", "scope_X")
    assert k != _make_cache_key("anthropic", "claude-3", "v2", "abc123", "cfg_v1", "scope_X")
    assert k != _make_cache_key("anthropic", "claude-3", "v2", "abc123", "cfg_v2", "scope_Y")