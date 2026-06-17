"""Provider Doctor – checks env vars and provider availability."""
from __future__ import annotations
from typing import Any
import httpx
from ..run.time_utils import utcnow_iso
from .provider_schema import ProviderSecretStatus, ProviderDoctorReport
from .env_loader import get_env, has_env

# ── Registry of known providers ───────────────────────────────────────────────
_PROVIDER_ENVS: dict[str, list[str]] = {
    "tavily":           ["TAVILY_API_KEY"],
    "brave":            ["BRAVE_SEARCH_API_KEY"],
    "serpapi":          ["SERPAPI_API_KEY"],
    "bing":             ["BING_SEARCH_API_KEY"],
    "google_cse":       ["GOOGLE_CSE_API_KEY", "GOOGLE_CSE_ID"],
    "github":           ["GITHUB_TOKEN"],
    "reddit":           ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"],
}

# Priority order for preferred provider selection
SEARCH_PROVIDER_PRIORITY = ["tavily", "brave", "serpapi", "bing", "google_cse"]


def _check_provider(
    provider_name: str,
    required_env_vars: list[str],
    run_test_query: bool = False,
) -> ProviderSecretStatus:
    found   = [v for v in required_env_vars if has_env(v)]
    missing = [v for v in required_env_vars if not has_env(v)]
    available = len(missing) == 0

    status = ProviderSecretStatus(
        provider_name=provider_name,
        required_env_vars=required_env_vars,
        found_env_vars=found,
        missing_env_vars=missing,
        available=available,
        checked_at=utcnow_iso(),
    )

    if available and run_test_query:
        status.test_query_supported = True
        try:
            _run_test_query(provider_name, status)
        except Exception as exc:
            status.test_query_success = False
            status.test_error_type = "unknown"
            status.test_error_message = str(exc)

    return status


def _run_test_query(provider_name: str, status: ProviderSecretStatus) -> None:
    """Lightweight test query against the provider. Never logs keys."""
    if provider_name == "tavily":
        _test_tavily(status)
    elif provider_name == "brave":
        _test_brave(status)
    else:
        status.test_query_supported = False


def _test_tavily(status: ProviderSecretStatus) -> None:
    key = get_env("TAVILY_API_KEY") or ""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                "https://api.tavily.com/search",
                json={"api_key": key, "query": "test", "max_results": 1},
            )
        if resp.status_code == 200:
            status.test_query_success = True
            status.usable = True
        else:
            status.test_query_success = False
            status.usable = False
            status.test_error_type = f"http_{resp.status_code}"
            status.test_error_message = f"HTTP {resp.status_code}"
    except httpx.TimeoutException:
        status.test_query_success = False
        status.test_error_type = "timeout"
        status.test_error_message = "Request timed out"
    except Exception as exc:
        status.test_query_success = False
        status.test_error_type = "network"
        status.test_error_message = str(exc)


def _test_brave(status: ProviderSecretStatus) -> None:
    key = get_env("BRAVE_SEARCH_API_KEY") or ""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": "test", "count": 1},
                headers={"Accept": "application/json",
                         "Accept-Encoding": "gzip",
                         "X-Subscription-Token": key},
            )
        if resp.status_code == 200:
            status.test_query_success = True
            status.usable = True
        else:
            status.test_query_success = False
            status.usable = False
            status.test_error_type = f"http_{resp.status_code}"
            status.test_error_message = f"HTTP {resp.status_code}"
    except Exception as exc:
        status.test_query_success = False
        status.test_error_type = "network"
        status.test_error_message = str(exc)


class ProviderDoctor:
    """Check availability of configured search / API providers."""

    def __init__(self, provider_envs: dict[str, list[str]] | None = None) -> None:
        self._envs = provider_envs or _PROVIDER_ENVS

    def check_all(self, run_test_query: bool = False) -> ProviderDoctorReport:
        statuses = [
            _check_provider(name, envs, run_test_query)
            for name, envs in self._envs.items()
        ]
        preferred = None
        for name in SEARCH_PROVIDER_PRIORITY:
            s = next((x for x in statuses if x.provider_name == name), None)
            if s and s.available:
                preferred = name
                break

        available_count = sum(1 for s in statuses if s.available)
        return ProviderDoctorReport(
            generated_at=utcnow_iso(),
            statuses=statuses,
            preferred_available_provider=preferred,
            summary={
                "total_providers": len(statuses),
                "available_providers": available_count,
                "missing_providers": len(statuses) - available_count,
            },
        )

    def check_one(
        self, provider_name: str, run_test_query: bool = False
    ) -> ProviderSecretStatus:
        envs = self._envs.get(provider_name, [])
        return _check_provider(provider_name, envs, run_test_query)

    def detect_preferred_search(self) -> str | None:
        """Return the name of the first available search provider."""
        for name in SEARCH_PROVIDER_PRIORITY:
            envs = self._envs.get(name, [])
            if all(has_env(v) for v in envs):
                return name
        return None