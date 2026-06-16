"""Shared HTTP fetch helper with timeout, retry, and exponential backoff."""
from __future__ import annotations

import time
from typing import Any, Callable

import httpx
from pydantic import BaseModel


class HTTPFetchError(BaseModel):
    status_code: int | None = None
    error_type: str          # network | timeout | rate_limit | access_denied | http_error | unknown
    message: str


def _classify_error(exc: Exception, status_code: int | None = None) -> str:
    if status_code == 429:
        return "rate_limit"
    if status_code == 403:
        return "access_denied"
    if status_code is not None and status_code >= 400:
        return "http_error"
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.NetworkError):
        return "network"
    return "unknown"


def http_get_with_retry(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 15,
    max_retries: int = 2,
    backoff_base: float = 1.5,
    http_client: httpx.Client | None = None,
) -> tuple[dict[str, Any] | None, list[HTTPFetchError]]:
    """GET ``url`` with retry/backoff. Returns (json_data, errors).

    ``json_data`` is None on failure; errors list is populated.
    """
    errors: list[HTTPFetchError] = []

    def _do_request() -> httpx.Response:
        if http_client is not None:
            return http_client.get(url, params=params, headers=headers)
        with httpx.Client(timeout=timeout) as client:
            return client.get(url, params=params, headers=headers)

    for attempt in range(max_retries + 1):
        try:
            resp = _do_request()
            if resp.status_code in (429, 403):
                err = HTTPFetchError(
                    status_code=resp.status_code,
                    error_type=_classify_error(Exception(), resp.status_code),
                    message=f"HTTP {resp.status_code} from {url}",
                )
                errors.append(err)
                # Don't retry on 403; retry once on 429
                if resp.status_code == 403 or attempt >= max_retries:
                    return None, errors
                wait = backoff_base ** attempt
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json(), []
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            code = getattr(getattr(exc, "response", None), "status_code", None)
            err = HTTPFetchError(
                status_code=code,
                error_type=_classify_error(exc, code),
                message=f"{type(exc).__name__}: {exc}",
            )
            errors.append(err)
            if attempt < max_retries:
                time.sleep(backoff_base ** attempt)
        except Exception as exc:
            errors.append(HTTPFetchError(error_type="unknown", message=str(exc)))
            return None, errors

    return None, errors