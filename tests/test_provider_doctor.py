"""Test ProviderDoctor."""
import os
import pytest
from unittest.mock import patch
from opc_foundation.providers import ProviderDoctor, ProviderSecretStatus
from opc_foundation.providers.env_loader import mask_key


def _clean_env():
    keys = ["TAVILY_API_KEY","BRAVE_SEARCH_API_KEY","SERPAPI_API_KEY",
            "BING_SEARCH_API_KEY","GOOGLE_CSE_API_KEY","GOOGLE_CSE_ID","GITHUB_TOKEN"]
    return {k: os.environ.pop(k, None) for k in keys}


def _restore_env(saved):
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v


def test_all_missing():
    saved = _clean_env()
    try:
        doctor = ProviderDoctor()
        report = doctor.check_all()
        tavily = next(s for s in report.statuses if s.provider_name == "tavily")
        assert not tavily.available
        assert "TAVILY_API_KEY" in tavily.missing_env_vars
    finally:
        _restore_env(saved)


def test_tavily_available_with_env():
    saved = _clean_env()
    os.environ["TAVILY_API_KEY"] = "fake-key-abc"
    try:
        doctor = ProviderDoctor()
        report = doctor.check_all(run_test_query=False)
        tavily = next(s for s in report.statuses if s.provider_name == "tavily")
        assert tavily.available
        assert "TAVILY_API_KEY" in tavily.found_env_vars
    finally:
        _restore_env(saved)
        os.environ.pop("TAVILY_API_KEY", None)


def test_preferred_provider_priority():
    saved = _clean_env()
    os.environ["BRAVE_SEARCH_API_KEY"] = "brave-fake"
    os.environ["TAVILY_API_KEY"] = "tavily-fake"
    try:
        doctor = ProviderDoctor()
        preferred = doctor.detect_preferred_search()
        assert preferred == "tavily"   # tavily wins
    finally:
        _restore_env(saved)
        os.environ.pop("BRAVE_SEARCH_API_KEY", None)
        os.environ.pop("TAVILY_API_KEY", None)


def test_no_provider_preferred_is_none():
    saved = _clean_env()
    try:
        doctor = ProviderDoctor()
        preferred = doctor.detect_preferred_search()
        assert preferred is None
    finally:
        _restore_env(saved)


def test_secret_not_in_report():
    saved = _clean_env()
    os.environ["TAVILY_API_KEY"] = "super-secret-key-xyz"
    try:
        doctor = ProviderDoctor()
        report = doctor.check_all()
        report_json = report.model_dump_json()
        assert "super-secret-key-xyz" not in report_json
    finally:
        _restore_env(saved)
        os.environ.pop("TAVILY_API_KEY", None)


def test_mask_key():
    assert "super" not in mask_key("super-secret-key-xyz")
    assert len(mask_key("short")) == 5
    assert mask_key("") == ""


def test_doctor_report_schema():
    doctor = ProviderDoctor()
    report = doctor.check_all()
    assert report.generated_at
    assert isinstance(report.statuses, list)
    assert isinstance(report.summary, dict)