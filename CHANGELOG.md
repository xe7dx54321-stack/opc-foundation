# Changelog

All notable changes to `opc-foundation` are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## v0.1.1 (Phase 1.1-1.2) — 2026-06-16

### Added
- `version.py` – explicit `__version__` export
- `CHANGELOG.md`
- Stable public API exports across all modules
- `src/opc_foundation/sources/http_utils.py` – shared HTTP retry/backoff helper
- `src/opc_foundation/signals/seen_store.py` – incremental dedupe / SeenStore
- `src/opc_foundation/run/artifact_manifest.py` – ArtifactManifest / ArtifactManifestBuilder
- `docs/contracts/connector_reliability_policy.md`
- Contract test harness: `tests/test_connector_contracts.py`
- Test fixtures: `tests/fixtures/`

### Changed (non-breaking)
- All four connectors (manual_url, hacker_news, github_issues, rss) hardened:
  timeout, max_retries, exponential backoff, 403/429 rate-limit handling
- `StructuredRunner` replaced with hardened version:
  JSON fence extraction, JSON repair (trim), validation retry, `StructuredRunResult`
- `LLMCache` key verified to include prompt_version / run_scope / config_version
- `connectors/__init__.py` adds alias exports (`ManualURLConnector`, `HackerNewsConnector`,
  `GitHubIssuesConnector`, `RSSConnector`) for name-consistency with import examples
- CLI adds `version`, `seen-store-stats` commands

### No breaking changes
All v0.1.0 imports remain valid.

---

## v0.1.0 (Phase 0-1) — 2026-06-16

Initial reusable foundation release.

### Added
- Config loader (YAML/JSON), `FoundationConfig` schema
- `JsonlStore`, `CsvStore`, `path_utils`
- `RunContext`, `RunLog`, `Checkpoint`, `id_generator`, `time_utils`
- `SourceRegistry` (YAML-based)
- `RawSignal` schema with validation
- `ManualUrlConnector`, `HackerNewsConnector`, `GitHubIssuesConnector`, `RssConnector`
- `TrafilaturaExtractor`, `ExtractedPage`, `html_cleaner`
- Dedupe (url / content / both), `QualityGate`
- LLM clients (OpenAI-compatible, Anthropic-compatible), `LLMCache`, `PromptMetadata`
- `MarkdownBuilder`, `table_builder`, `ReportSection`
- CLI: validate-source-registry, fetch-source, fetch-all-sources, extract-url, dedupe-signals
- 15 test files, 67 tests