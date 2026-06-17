# Changelog

All notable changes to `opc-foundation` are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

## v0.1.3 (Phase 1.4) — 2026-06-17

### Added
- `.agents/skills/opc-product-validation/` – OPC Product Validation Skill Library
  - `skill_manifest.yaml` (all skills default_enabled=false, requires_user_trigger=true)
  - 6 skills: theme-validation, concierge-mvp, processize, first-customers, pricing-smoke-test, minimalist-review
  - Each skill: `SKILL.md`, `input_schema.example.json`, `output_schema.example.json`
- `src/opc_foundation/skills/` – manifest schema, loader, and file validator
- CLI: `skills list`, `skills validate`, `skills show <skill_id>`
- `docs/skills/opc_skill_library.md`
- `docs/skills/downstream_usage.md`
- `docs/skills/demand_radar_integration_note.md`

### Fixed
- `version.py` bumped to `0.1.3` – CLI `version` output now matches tag

### No breaking changes
All v0.1.2 / v0.1.1 / v0.1.0 imports remain valid.

---
## v0.1.2 (Phase 1.3) — 2026-06-17

### Added
- `providers/` module: `ProviderDoctor`, `ProviderSecretStatus`, `ProviderDoctorReport`, `env_loader`
- `search/` module: `SearchQuery`, `SearchResult`, `SearchRunResult`, `SearchProviderRegistry`, `TavilyClient`, `BraveClient`, `normalize_results`, `run_search`
- `sources_v2/` module: `SourceDefinitionV2`, `SourceRegistryV2`, `SourceRunResult`, `SourceRuntime`, `SourceDiagnosticsReport`, `SourceYieldMetrics`
- `web/extraction_interface.py`: `WebExtractionRequest`, `WebExtractionResult`, `extract_page`
- CLI commands: `provider doctor`, `provider detect-search`, `search`, `source-registry validate`, `source-run diagnose`
- `examples/source_registry_v2.example.yaml`
- `examples/search_provider.example.yaml`
- `.env.example`
- `docs/guides/provider_setup.md`
- `docs/guides/source_runtime.md`
- `docs/guides/downstream_integration_search.md`

### Fixed
- `version.py` bumped to `0.1.2` — CLI `version` command now matches git tag

### No breaking changes
All v0.1.0 / v0.1.1 imports remain valid.

---

## v0.1.1 (Phase 1.1-1.2) — 2026-06-16

### Added
- `version.py`, `CHANGELOG.md`
- Stable public API exports across all modules
- `sources/http_utils.py` – shared HTTP retry/backoff
- `signals/seen_store.py` – SeenStore incremental dedupe
- `run/artifact_manifest.py` – ArtifactManifest
- `docs/contracts/connector_reliability_policy.md`
- Contract test harness + fixtures

### Changed (non-breaking)
- All four connectors hardened: timeout, retry, backoff, rate-limit handling
- `StructuredRunner` → `run_safe()` + `StructuredRunResult`

---

## v0.1.0 (Phase 0-1) — 2026-06-16

Initial reusable foundation release.

### Added
- Config loader, `FoundationConfig`
- `JsonlStore`, `CsvStore`, `path_utils`
- `RunContext`, `RunLog`, `Checkpoint`
- `SourceRegistry`, `RawSignal`, four connectors
- `TrafilaturaExtractor`, Dedupe, `QualityGate`
- LLM clients, `LLMCache`, `MarkdownBuilder`
- CLI: validate-source-registry, fetch-source, extract-url, dedupe-signals