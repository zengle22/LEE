"""Evidence Collector

Collects step outputs into project-level evidence directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List
import shutil
import yaml


@dataclass
class EvidenceEntry:
    run_id: str
    step_id: str
    collected_at: str
    artifacts: List[str]


class EvidenceCollector:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()

    def collect(self, run_id: str, step_id: str, artifacts: Iterable[str]) -> List[str]:
        artifacts = [a for a in artifacts if a]
        if not artifacts:
            return []

        evidence_dir = self.project_root / "evidence" / run_id
        evidence_dir.mkdir(parents=True, exist_ok=True)

        copied: List[str] = []
        for artifact in artifacts:
            src = Path(artifact)
            if not src.exists():
                continue

            rel_path = self._relative_to_project(src)

            # Skip if artifact is already inside the current evidence directory
            # to prevent infinite nesting (e.g., evidence/RUN-x/evidence/RUN-x/...)
            try:
                src_resolved = src.resolve()
                evidence_dir_resolved = evidence_dir.resolve()
                # Check if src is already under evidence_dir
                if str(src_resolved).startswith(str(evidence_dir_resolved)):
                    # Already in the correct evidence directory, skip copying
                    copied.append(str(src_resolved))
                    continue
            except Exception:
                pass  # Fall through to normal copy logic

            dest = evidence_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)

            if src.is_dir():
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)

            copied.append(str(dest))

        if copied:
            self._append_manifest(evidence_dir, EvidenceEntry(
                run_id=run_id,
                step_id=step_id,
                collected_at=datetime.now().isoformat(),
                artifacts=copied,
            ))

        return copied

    def _relative_to_project(self, path: Path) -> Path:
        try:
            return path.resolve().relative_to(self.project_root)
        except ValueError:
            # Not under project root; fallback to basename
            return Path(path.name)

    def _append_manifest(self, evidence_dir: Path, entry: EvidenceEntry) -> None:
        manifest_path = evidence_dir / "manifest.yaml"
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                existing = yaml.safe_load(f) or []
        else:
            existing = []

        if not isinstance(existing, list):
            existing = []

        existing.append({
            "run_id": entry.run_id,
            "step_id": entry.step_id,
            "collected_at": entry.collected_at,
            "artifacts": entry.artifacts,
        })

        with open(manifest_path, "w", encoding="utf-8") as f:
            yaml.dump(existing, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
