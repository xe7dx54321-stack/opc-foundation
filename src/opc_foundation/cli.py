"""OPC Foundation CLI."""
from __future__ import annotations
import json as _json
from pathlib import Path
from typing import Optional
import typer

app = typer.Typer(name="opc-foundation", help="OPC Foundation infrastructure CLI.")
provider_app = typer.Typer(help="Provider detection and health commands.")
app.add_typer(provider_app, name="provider")


# 鈹€鈹€ version 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
@app.command("version")
def show_version() -> None:
    """Print the opc-foundation version."""
    from opc_foundation import __version__
    typer.echo(f"opc-foundation {__version__}")


# 鈹€鈹€ provider doctor 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
@provider_app.command("doctor")
def provider_doctor(
    test_query: bool = typer.Option(False, help="Run a live test query per provider"),
) -> None:
    """Check availability of configured providers."""
    from opc_foundation.providers import ProviderDoctor
    doctor = ProviderDoctor()
    report = doctor.check_all(run_test_query=test_query)
    typer.echo(f"\nProvider Doctor Report  [{report.generated_at}]")
    typer.echo(f"Preferred search provider: {report.preferred_available_provider or 'none'}\n")
    for s in report.statuses:
        avail = "[OK]" if s.available else "[--]"
        typer.echo(f"  [{avail}] {s.provider_name}")
        typer.echo(f"       required env : {', '.join(s.required_env_vars)}")
        if s.missing_env_vars:
            typer.echo(f"       missing      : {', '.join(s.missing_env_vars)}")
        if s.test_query_supported:
            tq = "PASS" if s.test_query_success else f"FAIL ({s.test_error_type})"
            typer.echo(f"       test query   : {tq}")


# 鈹€鈹€ provider detect-search 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
@provider_app.command("detect-search")
def detect_search() -> None:
    """Detect the preferred available search provider."""
    from opc_foundation.providers import ProviderDoctor
    doctor = ProviderDoctor()
    preferred = doctor.detect_preferred_search()
    if preferred:
        typer.echo(f"Preferred search provider: {preferred}")
    else:
        typer.echo("No search provider available. Set TAVILY_API_KEY or BRAVE_SEARCH_API_KEY.")
        raise typer.Exit(1)


# 鈹€鈹€ search 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    provider: Optional[str] = typer.Option(None, help="Provider name (tavily|brave)"),
    max_results: int = typer.Option(5, help="Max results"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run a search query via the configured provider."""
    from opc_foundation.search import SearchProviderRegistry, SearchQuery, normalize_results
    reg = SearchProviderRegistry.from_env()
    sq = SearchQuery(query=query, provider=provider, max_results=max_results)
    result = reg.search(sq, provider_name=provider)

    if result.errors:
        for e in result.errors:
            typer.echo(f"[ERROR] {e}", err=True)

    if as_json:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"\nSearch: {query!r}  provider={result.provider}  results={len(result.results)}")
    for r in result.results:
        typer.echo(f"  [{r.rank}] {r.title or '(no title)'}")
        typer.echo(f"       {r.url}")
        if r.snippet:
            typer.echo(f"       {r.snippet[:120]}")


# 鈹€鈹€ source-registry validate 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
@app.command("source-registry-validate")
def source_registry_validate(
    path: str = typer.Argument(..., help="Path to source registry YAML (v1 or v2)"),
    v2: bool = typer.Option(False, "--v2", help="Use SourceRegistryV2 schema"),
) -> None:
    """Validate a source registry YAML file."""
    if v2:
        from opc_foundation.sources_v2 import SourceRegistryV2
        reg = SourceRegistryV2.from_yaml(path)
        errors = reg.validate_registry()
        enabled = reg.get_enabled()
        if errors:
            for e in errors:
                typer.echo(f"[ERROR] {e}", err=True)
            raise typer.Exit(1)
        typer.echo(f"OK (v2) 鈥?{len(enabled)} enabled source(s):")
        for s in enabled:
            typer.echo(f"  鈥?{s.source_id} [{s.source_type}] trust={s.trust_tier}")
    else:
        from opc_foundation.sources import SourceRegistry
        reg = SourceRegistry.from_yaml(path)
        errors = reg.validate_registry()
        if errors:
            for e in errors:
                typer.echo(f"[ERROR] {e}", err=True)
            raise typer.Exit(1)
        sources = reg.get_enabled_sources()
        typer.echo(f"OK 鈥?{len(sources)} enabled source(s):")
        for s in sources:
            typer.echo(f"  鈥?{s.source_id} ({s.connector})")


# 鈹€鈹€ validate-source-registry (original command kept for compat) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
@app.command("validate-source-registry")
def validate_source_registry(
    path: str = typer.Option("examples/source_registry.example.yaml"),
) -> None:
    """Validate a source registry YAML file (v1 compat alias)."""
    from opc_foundation.sources import SourceRegistry
    registry = SourceRegistry.from_yaml(path)
    errors = registry.validate_registry()
    sources = registry.get_enabled_sources()
    if errors:
        typer.echo(f"[ERRORS] {errors}", err=True)
        raise typer.Exit(1)
    typer.echo(f"OK 鈥?{len(sources)} enabled source(s):")
    for s in sources:
        typer.echo(f"  鈥?{s.source_id} ({s.connector})")


# 鈹€鈹€ source-run diagnose 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
@app.command("source-run-diagnose")
def source_run_diagnose(
    source_id: str = typer.Argument(..., help="Source ID"),
    total: int = typer.Option(0), unique: int = typer.Option(0),
    extracted: int = typer.Option(0), failed: int = typer.Option(0),
    status: str = typer.Option("unknown"),
) -> None:
    """Generate a diagnostics report for a source run."""
    from opc_foundation.sources_v2 import build_diagnostics_report
    report = build_diagnostics_report(
        source_id=source_id,
        total_items=total, unique_urls=unique,
        text_extracted=extracted, failed=failed,
        run_status=status,
    )
    typer.echo(report.model_dump_json(indent=2))


# 鈹€鈹€ original commands (kept for backward compat) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
@app.command("fetch-source")
def fetch_source(
    source_id: str = typer.Argument(...),
    query: str = typer.Option(...),
    registry: str = typer.Option("examples/source_registry.example.yaml"),
    max_items: int = typer.Option(10),
    output: Optional[str] = typer.Option(None),
) -> None:
    """Fetch signals from a single source."""
    from opc_foundation.sources import SourceRegistry, SourceQuery
    from opc_foundation.sources.connectors import HackerNewsConnector, GitHubIssuesConnector, RssConnector, ManualUrlConnector
    from opc_foundation.run import RunContext, new_id
    from opc_foundation.storage import JsonlStore

    reg = SourceRegistry.from_yaml(registry)
    source_def = reg.get_source(source_id)
    if not source_def:
        typer.echo(f"Source '{source_id}' not found.", err=True); raise typer.Exit(1)
    connector_map = {"hacker_news": HackerNewsConnector(), "github_issues": GitHubIssuesConnector(),
                     "rss": RssConnector(), "manual_url": ManualUrlConnector()}
    connector = connector_map.get(source_def.connector)
    if not connector:
        typer.echo(f"No connector for '{source_def.connector}'", err=True); raise typer.Exit(1)
    sq = SourceQuery(query_id=new_id("q_"), source_id=source_id, query=query, max_items=max_items)
    ctx = RunContext(pipeline_name="cli-fetch")
    result = connector.fetch(sq, source_def, ctx)
    typer.echo(f"Fetched {len(result.raw_signals)} signal(s), {len(result.errors)} error(s).")
    if output:
        JsonlStore.write_records(output, result.raw_signals)
        typer.echo(f"Written to {output}")


@app.command("fetch-all-sources")
def fetch_all_sources(
    query: str = typer.Option(...),
    registry: str = typer.Option("examples/source_registry.example.yaml"),
    max_items: int = typer.Option(10),
    output: Optional[str] = typer.Option(None),
) -> None:
    """Fetch from all enabled sources."""
    from opc_foundation.sources import SourceRegistry, SourceQuery
    from opc_foundation.sources.connectors import HackerNewsConnector, GitHubIssuesConnector, RssConnector, ManualUrlConnector
    from opc_foundation.run import RunContext, new_id
    from opc_foundation.storage import JsonlStore

    reg = SourceRegistry.from_yaml(registry)
    connector_map = {"hacker_news": HackerNewsConnector(), "github_issues": GitHubIssuesConnector(),
                     "rss": RssConnector(), "manual_url": ManualUrlConnector()}
    ctx = RunContext(pipeline_name="cli-fetch-all")
    all_signals = []
    for sd in reg.get_enabled_sources():
        c = connector_map.get(sd.connector)
        if not c:
            continue
        sq = SourceQuery(query_id=new_id("q_"), source_id=sd.source_id, query=query, max_items=max_items)
        r = c.fetch(sq, sd, ctx)
        typer.echo(f"[{sd.source_id}] {len(r.raw_signals)} signal(s)")
        all_signals.extend(r.raw_signals)
    typer.echo(f"Total: {len(all_signals)}")
    if output:
        JsonlStore.write_records(output, all_signals)
        typer.echo(f"Written to {output}")


@app.command("extract-url")
def extract_url(url: str = typer.Argument(...)) -> None:
    """Extract text from a URL using Trafilatura."""
    from opc_foundation.web import TrafilaturaExtractor
    page = TrafilaturaExtractor().extract(url)
    typer.echo(f"Title: {page.title}\nLength: {len(page.text)} chars")
    if page.errors:
        for e in page.errors: typer.echo(f"[ERR] {e}", err=True)
    else:
        typer.echo(page.text[:500])


@app.command("dedupe-signals")
def dedupe_signals(
    input_path: str = typer.Argument(...),
    output_path: str = typer.Argument(...),
    by: str = typer.Option("url"),
) -> None:
    """Deduplicate RawSignal records."""
    from opc_foundation.storage import JsonlStore
    from opc_foundation.signals import RawSignal, dedupe_raw_signals
    signals = JsonlStore.load_records(input_path, model=RawSignal)  # type: ignore
    result = dedupe_raw_signals(signals, by=by)
    JsonlStore.write_records(output_path, result.unique_signals)
    typer.echo(f"Unique: {len(result.unique_signals)}, Removed: {result.duplicate_count}")


@app.command("seen-store-stats")
def seen_store_stats(path: str = typer.Argument(...)) -> None:
    """Show SeenStore statistics."""
    from opc_foundation.signals.seen_store import SeenStore
    store = SeenStore(path)
    records = store.load()
    if not records:
        typer.echo("SeenStore is empty."); return
    typer.echo(f"Total: {len(records)}  |  seen_once: {sum(1 for r in records if r.seen_count==1)}  |  seen_multi: {sum(1 for r in records if r.seen_count>1)}")


@app.command("build-artifact-manifest")
def build_artifact_manifest(
    run_id: str = typer.Option(...),
    pipeline: str = typer.Option("default"),
    output: str = typer.Option("artifact_manifest.json"),
) -> None:
    """Build an artifact manifest skeleton."""
    from opc_foundation.run import ArtifactManifestBuilder
    builder = ArtifactManifestBuilder(run_id=run_id, pipeline_name=pipeline)
    p = builder.write(output)
    typer.echo(f"Manifest written to {p}")


if __name__ == "__main__":
    app()