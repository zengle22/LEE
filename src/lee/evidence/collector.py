from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from lee.orchestrator.evidence_collector import (
    EvidenceCollector as OrchestratorEvidenceCollector,
    EvidenceEntry,
)

from .manifest import EvidenceManifestBuilder


class EvidenceCollector(OrchestratorEvidenceCollector):
    """Canonical evidence collector wrapper for Dev evidence-pack runtime use."""

    def collect(self, run_id: str, step_id: str, artifacts: Iterable[str]) -> List[str]:
        deduped_artifacts = EvidenceManifestBuilder.dedupe_artifacts(artifacts)
        return super().collect(run_id, step_id, deduped_artifacts)

    def collect_from_context(
        self,
        *,
        run_id: str,
        step_id: str,
        artifact_refs: Iterable[str],
        filesystem_paths: Iterable[str],
        workflow_context_refs: Iterable[str],
    ) -> List[str]:
        combined: List[str] = []
        combined.extend(str(item) for item in artifact_refs if item)
        combined.extend(str(item) for item in filesystem_paths if item)
        combined.extend(str(item) for item in workflow_context_refs if item)
        return self.collect(run_id, step_id, combined)

    def manifest_entries(self, run_id: str) -> List[dict]:
        manifest_path = Path(self.project_root) / "evidence" / run_id / "manifest.yaml"
        return EvidenceManifestBuilder.load(manifest_path)
