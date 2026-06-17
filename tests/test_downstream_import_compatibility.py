"""Verify backward compatibility: all Phase 0-1 / 1.1-1.2 public imports still work."""


def test_version():
    from opc_foundation import __version__
    assert __version__ == "0.1.3"


def test_config():
    from opc_foundation.config import load_yaml_config, load_json_config, load_config, FoundationConfig
    assert callable(load_config)


def test_storage():
    from opc_foundation.storage import JsonlStore, CsvStore
    assert JsonlStore


def test_run():
    from opc_foundation.run import (
        RunContext, RunLog, Checkpoint, new_id, new_run_id, create_run_id,
        utcnow_iso, ArtifactManifestBuilder, ArtifactManifest
    )
    assert callable(create_run_id)


def test_sources_v1():
    from opc_foundation.sources import SourceDefinition, SourceQuery, FetchResult, SourceRegistry
    from opc_foundation.sources.connectors import (
        ManualUrlConnector, ManualURLConnector,
        HackerNewsConnector, GitHubIssuesConnector,
        RssConnector, RSSConnector,
    )
    assert ManualUrlConnector is ManualURLConnector


def test_signals():
    from opc_foundation.signals import (
        RawSignal, dedupe_raw_signals, DedupeResult,
        QualityGate, SeenStore, SeenSignalRecord
    )
    assert RawSignal


def test_web():
    from opc_foundation.web import (
        TrafilaturaExtractor, ExtractedPage,
        WebExtractionRequest, WebExtractionResult, extract_page
    )
    assert WebExtractionRequest


def test_llm():
    from opc_foundation.llm import (
        LLMRequest, LLMResponse, LLMCache, PromptMetadata,
        StructuredRunner, StructuredRunResult
    )
    assert StructuredRunner


def test_reports():
    from opc_foundation.reports import MarkdownBuilder, ReportSection
    assert MarkdownBuilder


def test_providers_new():
    from opc_foundation.providers import ProviderDoctor, ProviderSecretStatus, ProviderDoctorReport
    assert ProviderDoctor


def test_search_new():
    from opc_foundation.search import (
        SearchQuery, SearchResult, SearchRunResult,
        SearchProviderRegistry, TavilyClient, BraveClient, normalize_results
    )
    assert SearchProviderRegistry


def test_sources_v2_new():
    from opc_foundation.sources_v2 import (
        SourceDefinitionV2, SourceRegistryV2,
        SourceRunResult, SourceRuntime,
        SourceDiagnosticsReport, SourceYieldMetrics
    )
    assert SourceDefinitionV2