"""ArtifactManifest – track every file artifact produced by a pipeline run."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..run.time_utils import utcnow_iso
from ..storage.path_utils import ensure_parent


class ArtifactRecord(BaseModel):
    name: str
    path: str
    artifact_type: str  # jsonl | csv | markdown | json | log | other
    count: int | None = None
    created_at: str
    metadata: dict[str, Any] = {}


class ArtifactManifest(BaseModel):
    run_id: str
    project_id: str | None = None
    pipeline_name: str
    created_at: str
    artifacts: list[ArtifactRecord] = []
    metadata: dict[str, Any] = {}


class ArtifactManifestBuilder:
    """Build and persist an ArtifactManifest for a pipeline run."""

    def __init__(
        self,
        run_id: str,
        pipeline_name: str,
        project_id: str | None = None,
    ) -> None:
        self._run_id = run_id
        self._pipeline_name = pipeline_name
        self._project_id = project_id
        self._created_at = utcnow_iso()
        self._artifacts: list[ArtifactRecord] = []

    def add_artifact(
        self,
        name: str,
        path: str | Path,
        artifact_type: str,
        count: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._artifacts.append(
            ArtifactRecord(
                name=name,
                path=str(path),
                artifact_type=artifact_type,
                count=count,
                created_at=utcnow_iso(),
                metadata=metadata or {},
            )
        )

    def build(self) -> ArtifactManifest:
        return ArtifactManifest(
            run_id=self._run_id,
            pipeline_name=self._pipeline_name,
            project_id=self._project_id,
            created_at=self._created_at,
            artifacts=list(self._artifacts),
        )

    def write(self, path: str | Path) -> Path:
        """Serialize manifest to JSON and return the written path."""
        p = ensure_parent(path)
        manifest = self.build()
        p.write_text(
            json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return p

    @staticmethod
    def load(path: str | Path) -> ArtifactManifest:
        """Load a previously written manifest JSON."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return ArtifactManifest.model_validate(data)