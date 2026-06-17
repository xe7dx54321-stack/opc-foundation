"""Test SourceDiagnosticsReport and SourceYieldMetrics."""
from opc_foundation.sources_v2 import SourceDiagnosticsReport, build_diagnostics_report
from opc_foundation.sources_v2.source_yield_metrics import SourceYieldMetrics


def test_build_report():
    report = build_diagnostics_report(
        source_id="tavily_search",
        source_category="search_discovery",
        total_items=50,
        unique_urls=45,
        text_extracted=40,
        failed=2,
        text_lengths=[500, 1200, 800],
        run_status="success",
    )
    assert report.source_id == "tavily_search"
    assert report.total_items == 50
    assert report.unique_urls == 45
    assert report.text_extracted == 40
    assert report.run_status == "success"
    assert abs(report.avg_text_chars - 833.33) < 1


def test_downstream_backfill():
    report = build_diagnostics_report(source_id="s1", run_status="success")
    report.downstream_metric_name = "pain_extraction_yield"
    report.downstream_yield_rate = 0.43
    assert report.downstream_metric_name == "pain_extraction_yield"
    # Foundation schema accepts it but does not interpret it
    assert report.downstream_yield_rate == 0.43


def test_report_auto_fields():
    report = build_diagnostics_report(source_id="s2", run_status="failed")
    assert report.report_id.startswith("diag_")
    assert report.generated_at != ""


def test_yield_metrics():
    m = SourceYieldMetrics(
        source_id="s1", run_id="run_001",
        total_fetched=100, total_after_dedupe=80, total_extracted=70,
    )
    assert m.total_fetched == 100
    assert m.recorded_at != ""
    # Downstream backfill
    m.downstream_metric_name = "pain_yield"
    m.downstream_positive_count = 30
    m.downstream_yield_rate = 0.43
    assert m.downstream_yield_rate == 0.43