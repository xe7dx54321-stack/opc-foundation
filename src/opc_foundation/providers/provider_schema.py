"""Provider secret-status schema."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class ProviderSecretStatus(BaseModel):
    provider_name: str
    required_env_vars: list[str]
    found_env_vars: list[str]
    missing_env_vars: list[str]

    available: bool
    usable: bool | None = None

    test_query_supported: bool = False
    test_query_success: bool | None = None
    test_error_type: str | None = None
    test_error_message: str | None = None

    checked_at: str
    metadata: dict[str, Any] = {}


class ProviderDoctorReport(BaseModel):
    generated_at: str
    statuses: list[ProviderSecretStatus]
    preferred_available_provider: str | None = None
    summary: dict[str, Any] = {}