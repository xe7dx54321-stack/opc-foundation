"""Test hardened StructuredRunner."""
import pytest
from unittest.mock import MagicMock
from pydantic import BaseModel
from opc_foundation.llm.structured_runner import (
    StructuredRunner, StructuredRunResult, _extract_json_text
)
from opc_foundation.llm.client_base import LLMResponse, LLMRequest, LLMMessage


class SimpleModel(BaseModel):
    name: str
    value: int


def _mock_client(text: str):
    client = MagicMock()
    client.complete.return_value = LLMResponse(text=text, model="gpt-test")
    return client


def _req():
    return LLMRequest(
        model="gpt-test",
        messages=[LLMMessage(role="user", content="Test")]
    )


def test_parse_plain_json():
    runner = StructuredRunner(_mock_client('{"name": "Alice", "value": 42}'))
    result = runner.run_safe(_req(), SimpleModel)
    assert result.success is True
    assert result.parsed.name == "Alice"
    assert result.parsed.value == 42


def test_parse_fenced_json():
    text = '```json\n{"name": "Bob", "value": 99}\n```'
    runner = StructuredRunner(_mock_client(text))
    result = runner.run_safe(_req(), SimpleModel)
    assert result.success is True
    assert result.parsed.name == "Bob"


def test_extract_json_text_strips_fence():
    text = '```json\n{"key": "val"}\n```'
    extracted = _extract_json_text(text)
    assert extracted.strip() == '{"key": "val"}'


def test_extract_json_text_trims_surrounding():
    text = 'Here is the result:\n{"name": "x", "value": 1}\nDone.'
    extracted = _extract_json_text(text)
    import json
    data = json.loads(extracted)
    assert data["name"] == "x"


def test_validation_failure_returns_structured_error():
    # Missing required field "value"
    runner = StructuredRunner(_mock_client('{"name": "incomplete"}'))
    result = runner.run_safe(_req(), SimpleModel)
    assert result.success is False
    assert len(result.errors) > 0
    assert result.parsed is None


def test_invalid_json_returns_structured_error():
    runner = StructuredRunner(_mock_client("not json at all"))
    result = runner.run_safe(_req(), SimpleModel)
    assert result.success is False
    assert "JSON parse error" in " ".join(result.errors)


def test_llm_call_failure_returns_structured_error():
    client = MagicMock()
    client.complete.side_effect = Exception("network error")
    runner = StructuredRunner(client)
    result = runner.run_safe(_req(), SimpleModel)
    assert result.success is False
    assert "LLM call failed" in " ".join(result.errors)


def test_run_raises_on_failure():
    runner = StructuredRunner(_mock_client("not json"))
    with pytest.raises(ValueError):
        runner.run(_req(), SimpleModel)


def test_run_succeeds_backward_compat():
    runner = StructuredRunner(_mock_client('{"name": "compat", "value": 7}'))
    obj = runner.run(_req(), SimpleModel)
    assert obj.name == "compat"