"""Test that all documented public API exports work correctly."""


def test_top_level_version():
    from opc_foundation import __version__
    assert __version__


def test_config_exports():
    from opc_foundation.config import load_yaml_config, load_json_config, load_config, FoundationConfig
    assert callable(load_yaml_config)
    assert callable(load_json_config)
    assert callable(load_config)
    assert FoundationConfig


def test_storage_exports():
    from opc_foundation.storage import JsonlStore, CsvStore
    assert JsonlStore
    assert CsvStore


def test_run_exports():
    from opc_foundation.run import RunContext, RunLog, create_run_id, new_id, new_run_id
    from opc_foundation.run import ArtifactManifestBuilder, ArtifactManifest
    assert RunContext
    assert callable(create_run_id)
    assert callable(new_id)
    assert ArtifactManifestBuilder


def test_sources_exports():
    from opc_foundation.sources import (
        SourceDefinition, SourceQuery, FetchResult, SourceRegistry, SourceConnector
    )
    assert SourceDefinition
    assert SourceQuery
    assert FetchResult
    assert SourceRegistry


def test_connector_aliases():
    from opc_foundation.sources.connectors import (
        ManualUrlConnector, ManualURLConnector,
        HackerNewsConnector,
        GitHubIssuesConnector,
        RssConnector, RSSConnector,
    )
    # Both spellings resolve to the same class
    assert ManualUrlConnector is ManualURLConnector
    assert RssConnector is RSSConnector


def test_signals_exports():
    from opc_foundation.signals import (
        RawSignal, DedupeResult, dedupe_raw_signals, QualityGate, SeenStore, SeenSignalRecord
    )
    assert RawSignal
    assert SeenStore
    assert SeenSignalRecord


def test_web_exports():
    from opc_foundation.web import TrafilaturaExtractor, ExtractedPage
    assert TrafilaturaExtractor
    assert ExtractedPage


def test_llm_exports():
    from opc_foundation.llm import (
        LLMRequest, LLMResponse, LLMCache, PromptMetadata, StructuredRunner, StructuredRunResult
    )
    assert LLMRequest
    assert StructuredRunner
    assert StructuredRunResult


def test_reports_exports():
    from opc_foundation.reports import MarkdownBuilder, ReportSection
    assert MarkdownBuilder
    assert ReportSection