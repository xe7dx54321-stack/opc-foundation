# Provider Setup Guide

## Overview

`opc-foundation` supports multiple search providers. Configure them via environment variables.

## Supported Providers

| Provider | Env Var | Priority |
|---|---|---|
| Tavily | `TAVILY_API_KEY` | 1 (highest) |
| Brave | `BRAVE_SEARCH_API_KEY` | 2 |
| SerpAPI | `SERPAPI_API_KEY` | 3 |
| Bing | `BING_SEARCH_API_KEY` | 4 |
| Google CSE | `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID` | 5 |
| GitHub | `GITHUB_TOKEN` | (connector auth only) |

## Setup

1. Copy `.env.example` to `.env`
2. Fill in your API keys
3. `.env` is gitignored — never commit real keys

```bash
cp .env.example .env
```

## Check provider availability

```bash
opc-foundation provider doctor
```

## Detect preferred search provider

```bash
opc-foundation provider detect-search
```

## Using in code

```python
from opc_foundation.providers import ProviderDoctor
from opc_foundation.providers.env_loader import load_env_file

load_env_file(".env")   # optional – sets env vars from .env

doctor = ProviderDoctor()
report = doctor.check_all()
print(report.preferred_available_provider)
```

## Security rules

- Never print or log real API keys.
- Foundation uses `mask_key()` for safe logging.
- Never commit `.env` to git.