"""OPC Foundation CLI – quick validation and fetch utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(name="opc-foundation", help="OPC Foundation infrastructure CLI.")


@app.command("version")
def show_version() -> None:
    """Print the installed opc-foundation version."""
    from opc_foundation import __version__
    typer.echo(f"opc-foundation {__version__}")


@app.command("validate-source-registry")
def validate_source_registry(
    path: str = typer.Option("examples/source_registry.example.yaml", help="Path to registry YAML"),
) -> None:
    """Validate a source registry YAML file."""
    from opc_foundation.sources.source_registry import SourceRegistry

    registry = SourceRegistry.from_yaml(path)
    errors = registry.validate_registry()
    sources = registry.get_enabled_sources()
    if errors:
        typer.echo(f"[ERRORS] {errors}", err=True)
        raise typer.Exit(1)
    typer.echo(f"OK – {len(sources)} enabled source(s):")
    for s in sources:
        typer.echo(f"  • {s.source_id} ({s.connector})")


@app.command("fetch-source")
def fetch_source(
    source_id: str = typer.Argument(..., help="Source ID from registry"),
    query: str = typer.Option(..., help="Search query string"),
    registry: str = typer.Option("examples/source_registry.example.yaml"),
    max_items: int = typer.Option(10),
    output: Optional[str] = typer.Option(None, help="Output JSONL path"),
) -> None:
    """Fetch signals from a single source."""
    from opc_foundation.sources.source_registry import SourceRegistry
    from opc_foundation.sources.source_schema import SourceQuery
    from opc_foundation.sources.connectors import (
        HackerNewsConnector, GitHubIssuesConnector, RssConnector, ManualUrlConnector,
    )
    from opc_foundation.run.run_context import RunContext
    from opc_foundation.run.id_generator import new_id
    from opc_foundation.storage.jsonl_store import JsonlStore

    reg = SourceRegistry.from_yaml(registry)
    source_def = reg.get_source(source_id)
    if not source_def:
        typer.echo(f"Source '{source_id}' not found.", err=True)
        raise typer.Exit(1)

    connector_map = {
        "hacker_news": HackerNewsConnector(),
        "github_issues": GitHubIssuesConnector(),
        "rss": RssConnector(),
        "manual_url": ManualUrlConnector(),
    }
    connector = connector_map.get(source_def.connector)
    if not connector:
        typer.echo(f"No connector for '{source_def.connector}'", err=True)
        raise typer.Exit(1)

    sq = SourceQuery(query_id=new_id("q_"), source_id=source_id, query=query, max_items=max_items)
    ctx = RunContext(pipeline_name="cli-fetch")
    result = connector.fetch(sq, source_def, ctx)

    typer.echo(f"Fetched {len(result.raw_signals)} signal(s), {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
    for w in result.warnings:
        typer.echo(f"  [WARN] {w}")
    for e in result.errors:
        typer.echo(f"  [ERR] {e}", err=True)

    if output:
        JsonlStore.write_records(output, result.raw_signals)
        typer.echo(f"Written to {output}")
    else:
        for sig in result.raw_signals:
            typer.echo(f"  • [{sig.source_type}] {sig.title or sig.source_url}")


@app.command("fetch-all-sources")
def fetch_all_sources(
    query: str = typer.Option(..., help="Search query string"),
    registry: str = typer.Option("examples/source_registry.example.yaml"),
    max_items: int = typer.Option(10),
    output: Optional[str] = typer.Option(None),
) -> None:
    """Fetch from all enabled sources."""
    from opc_foundation.sources.source_registry import SourceRegistry
    from opc_foundation.sources.source_schema import SourceQuery
    from opc_foundation.sources.connectors import (
        HackerNewsConnector, GitHubIssuesConnector, RssConnector, ManualUrlConnector,
    )
    from opc_foundation.run.run_context import RunContext
    from opc_foundation.run.id_generator import new_id
    from opc_foundation.storage.jsonl_store import JsonlStore
    from opc_foundation.signals.raw_signal_schema import RawSignal

    reg = SourceRegistry.from_yaml(registry)
    connector_map = {
        "hacker_news": HackerNewsConnector(),
        "github_issues": GitHubIssuesConnector(),
        "rss": RssConnector(),
        "manual_url": ManualUrlConnector(),
    }
    ctx = RunContext(pipeline_name="cli-fetch-all")
    all_signals: list[RawSignal] = []

    for source_def in reg.get_enabled_sources():
        connector = connector_map.get(source_def.connector)
        if not connector:
            typer.echo(f"[SKIP] No connector for {source_def.connector}")
            continue
        sq = SourceQuery(query_id=new_id("q_"), source_id=source_def.source_id, query=query, max_items=max_items)
        result = connector.fetch(sq, source_def, ctx)
        typer.echo(f"[{source_def.source_id}] {len(result.raw_signals)} signal(s)")
        all_signals.extend(result.raw_signals)

    typer.echo(f"Total: {len(all_signals)} signal(s)")
    if output:
        JsonlStore.write_records(output, all_signals)
        typer.echo(f"Written to {output}")


@app.command("extract-url")
def extract_url(
    url: str = typer.Argument(..., help="URL to extract text from"),
) -> None:
    """Extract text from a URL using Trafilatura."""
    from opc_foundation.web.trafilatura_extractor import TrafilaturaExtractor

    extractor = TrafilaturaExtractor()
    page = extractor.extract(url)
    typer.echo(f"Title: {page.title}")
    typer.echo(f"Length: {len(page.text)} chars")
    if page.errors:
        for e in page.errors:
            typer.echo(f"[ERR] {e}", err=True)
    else:
        typer.echo(page.text[:500])


@app.command("dedupe-signals")
def dedupe_signals(
    input_path: str = typer.Argument(..., help="Input JSONL path"),
    output_path: str = typer.Argument(..., help="Output JSONL path"),
    by: str = typer.Option("url", help="Dedupe strategy: url|content|both"),
) -> None:
    """Deduplicate RawSignal records from a JSONL file."""
    from opc_foundation.storage.jsonl_store import JsonlStore
    from opc_foundation.signals.raw_signal_schema import RawSignal
    from opc_foundation.signals.dedupe import dedupe_raw_signals

    signals: list[RawSignal] = JsonlStore.load_records(input_path, model=RawSignal)  # type: ignore
    result = dedupe_raw_signals(signals, by=by)
    JsonlStore.write_records(output_path, result.unique_signals)
    typer.echo(f"Unique: {len(result.unique_signals)}, Duplicates removed: {result.duplicate_count}")


@app.command("seen-store-stats")
def seen_store_stats(
    path: str = typer.Argument(..., help="Path to seen store JSONL file"),
) -> None:
    """Show statistics for a SeenStore JSONL file."""
    from opc_foundation.signals.seen_store import SeenStore

    store = SeenStore(path)
    records = store.load()
    if not records:
        typer.echo("SeenStore is empty.")
        return
    seen_once = sum(1 for r in records if r.seen_count == 1)
    seen_multi = sum(1 for r in records if r.seen_count > 1)
    sources = set(r.source_id for r in records)
    typer.echo(f"Total records : {len(records)}")
    typer.echo(f"Seen once     : {seen_once}")
    typer.echo(f"Seen multiple : {seen_multi}")
    typer.echo(f"Sources       : {', '.join(sorted(sources))}")


@app.command("build-artifact-manifest")
def build_artifact_manifest(
    run_id: str = typer.Option(..., help="Run ID"),
    pipeline: str = typer.Option("default", help="Pipeline name"),
    output: str = typer.Option("artifact_manifest.json", help="Output JSON path"),
) -> None:
    """Build an empty artifact manifest skeleton for a run."""
    from opc_foundation.run.artifact_manifest import ArtifactManifestBuilder

    builder = ArtifactManifestBuilder(run_id=run_id, pipeline_name=pipeline)
    p = builder.write(output)
    typer.echo(f"Manifest written to {p}")


if __name__ == "__main__":
    app()