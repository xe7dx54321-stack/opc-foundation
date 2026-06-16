"""Test ArtifactManifest and builder."""
import json
from pathlib import Path
from opc_foundation.run.artifact_manifest import (
    ArtifactManifestBuilder, ArtifactManifest, ArtifactRecord
)


def test_add_and_build():
    builder = ArtifactManifestBuilder(run_id="run_001", pipeline_name="test_pipeline")
    builder.add_artifact("raw_signals", "/tmp/signals.jsonl", artifact_type="jsonl", count=42)
    builder.add_artifact("report", "/tmp/report.md", artifact_type="markdown")
    manifest = builder.build()
    assert manifest.run_id == "run_001"
    assert manifest.pipeline_name == "test_pipeline"
    assert len(manifest.artifacts) == 2
    assert manifest.artifacts[0].name == "raw_signals"
    assert manifest.artifacts[0].count == 42
    assert manifest.artifacts[0].artifact_type == "jsonl"


def test_write_and_load(tmp_path):
    builder = ArtifactManifestBuilder(
        run_id="run_002", pipeline_name="acq", project_id="demand_radar"
    )
    builder.add_artifact("signals", str(tmp_path / "s.jsonl"), artifact_type="jsonl", count=10)
    out_path = tmp_path / "manifest.json"
    written = builder.write(out_path)
    assert written.exists()

    loaded = ArtifactManifestBuilder.load(written)
    assert loaded.run_id == "run_002"
    assert loaded.project_id == "demand_radar"
    assert len(loaded.artifacts) == 1
    assert loaded.artifacts[0].count == 10


def test_manifest_json_structure(tmp_path):
    builder = ArtifactManifestBuilder(run_id="run_003", pipeline_name="pipe")
    builder.add_artifact("out", "/out.csv", artifact_type="csv")
    out = tmp_path / "m.json"
    builder.write(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "run_id" in data
    assert "artifacts" in data
    assert data["artifacts"][0]["artifact_type"] == "csv"


def test_auto_creates_parent_dir(tmp_path):
    builder = ArtifactManifestBuilder(run_id="r1", pipeline_name="p")
    nested = tmp_path / "nested" / "deep" / "manifest.json"
    builder.write(nested)
    assert nested.exists()