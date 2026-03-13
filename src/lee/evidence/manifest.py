from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List

import yaml

from lee.orchestrator.evidence_collector import EvidenceEntry


class EvidenceManifestBuilder:
    """Build and persist canonical evidence manifests."""

    @staticmethod
    def load(manifest_path: Path) -> List[dict]:
        if not manifest_path.exists():
            return []
        with open(manifest_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        return data if isinstance(data, list) else []

    @staticmethod
    def append(manifest_path: Path, entry: EvidenceEntry) -> List[dict]:
        entries = EvidenceManifestBuilder.load(manifest_path)
        entries.append(asdict(entry))
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            yaml.dump(entries, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return entries

    @staticmethod
    def dedupe_artifacts(artifacts: Iterable[str]) -> List[str]:
        deduped: List[str] = []
        for artifact in artifacts:
            if artifact and artifact not in deduped:
                deduped.append(artifact)
        return deduped
