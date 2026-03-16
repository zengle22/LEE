from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class PmPlannerContext:
    runner_cls: Any
    workflow_id: str
    instance_data: Optional[Dict[str, Any]]
    feat_alias_map: Dict[str, str]
    project_root: Optional[Path]

    @classmethod
    def from_instance(
        cls,
        *,
        runner_cls: Any,
        workflow_id: str,
        instance_data: Optional[Dict[str, Any]],
    ) -> "PmPlannerContext":
        return cls(
            runner_cls=runner_cls,
            workflow_id=workflow_id,
            instance_data=instance_data,
            feat_alias_map=build_feat_alias_map(instance_data),
            project_root=resolve_project_root(instance_data),
        )

    def clean_text(self, value: Any) -> str:
        return str(value or "").strip()

    def normalize_list(self, values: Any) -> List[str]:
        items = values if isinstance(values, list) else [values] if values is not None else []
        return [self.clean_text(item) for item in items if self.clean_text(item)]

    def normalize_priority(self, value: Any) -> str:
        normalized = self.clean_text(value).upper()
        if normalized in {"P0", "P1", "P2"}:
            return normalized
        lowered = self.clean_text(value).lower()
        if lowered in {"critical", "high"}:
            return "P0"
        if lowered in {"medium", "normal"}:
            return "P1"
        if lowered in {"low", "minor"}:
            return "P2"
        return "P1"

    def normalize_role(self, value: Any) -> str:
        normalized = self.clean_text(value).lower().replace("_", "-").replace(" ", "-")
        return normalized or "workflow-runtime-owner"

    def normalize_workstream(self, task: Dict[str, Any], role: str) -> str:
        explicit = self.clean_text(task.get("workstream"))
        if explicit:
            return explicit
        combined = " ".join(
            [
                self.clean_text(task.get("task_id")).lower(),
                self.clean_text(task.get("title")).lower(),
                self.clean_text(task.get("description")).lower(),
            ]
        )
        if any(token in combined for token in ("migration", "registry", "compatibility", "文档", "迁移")):
            return "governance-spec"
        if role.startswith("qa"):
            return "qa-seed"
        if role.startswith("technical-writer"):
            return "governance-docs"
        return "workflow-runtime"

    def infer_task_kind(self, task: Dict[str, Any], role: str, workstream: str) -> str:
        combined = " ".join(
            [
                self.clean_text(task.get("title")).lower(),
                self.clean_text(task.get("description")).lower(),
                role.lower(),
                workstream.lower(),
            ]
        )
        if any(token in combined for token in ("migration", "迁移")):
            return "migration"
        if any(token in combined for token in ("governance", "registry", "compatibility", "文档")):
            return "governance"
        if role.startswith("qa") or "test" in combined or "验证" in combined:
            return "validation"
        if any(token in combined for token in ("ux", "design", "ui")):
            return "ux"
        if "refactor" in combined:
            return "refactor"
        return "implementation"

    def resolve_parent_epic(self, epic_candidate: str, feat_ids: List[str]) -> str:
        for feat_id in feat_ids:
            resolved = self.runner_cls._resolve_feat_parent_epic(feat_id, self.instance_data)
            if resolved:
                return resolved
        return epic_candidate or "EPIC-001"

    def formal_acceptance_checks(self, feat_id: str) -> List[Dict[str, Any]]:
        if not isinstance(self.project_root, Path):
            return []
        return self.runner_cls._load_feat_acceptance_checks(str(self.project_root), feat_id)

    def formal_feat_title(self, feat_id: str) -> str:
        if not isinstance(self.project_root, Path):
            return ""
        features_dir = self.project_root / "spec" / "requirements" / "features"
        if not features_dir.exists():
            return ""
        for candidate in sorted(features_dir.glob(f"{feat_id}__*.md")):
            frontmatter = self.runner_cls._load_yaml_frontmatter(candidate) or {}
            title = self.clean_text(frontmatter.get("title"))
            if title:
                return title
        return ""


def resolve_project_root(instance_data: Optional[Dict[str, Any]]) -> Optional[Path]:
    if not isinstance(instance_data, dict):
        return None
    params = instance_data.get("params") if isinstance(instance_data.get("params"), dict) else {}
    feat_ref_path = params.get("feat_freeze_ref")
    if isinstance(feat_ref_path, str) and feat_ref_path.strip():
        candidate_path = Path(feat_ref_path.strip())
        if candidate_path.exists():
            for parent in [candidate_path.parent, *candidate_path.parents]:
                if parent.name == "spec":
                    return parent.parent
    feat_freeze = params.get("feat_freeze")
    if isinstance(feat_freeze, str) and feat_freeze.strip():
        candidate = Path(feat_freeze.strip())
        for parent in [candidate, *candidate.parents]:
            if parent.name == ".workflow":
                return parent.parent
    return None


def build_feat_alias_map(instance_data: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not isinstance(instance_data, dict):
        return {}
    params = instance_data.get("params") if isinstance(instance_data.get("params"), dict) else {}
    feat_freeze_path = params.get("feat_freeze")
    if not isinstance(feat_freeze_path, str) or not feat_freeze_path.strip():
        return {}
    source_title_map = extract_source_feat_title_map(feat_freeze_path)
    canonical_title_map = extract_canonical_title_map(resolve_project_root(instance_data))
    alias_map: Dict[str, str] = {}
    for source_feat_id, title in source_title_map.items():
        canonical_id = canonical_title_map.get(title_key(title))
        if canonical_id:
            alias_map[source_feat_id] = canonical_id
    return alias_map


def extract_source_feat_title_map(feat_freeze_path: str) -> Dict[str, str]:
    freeze_path = Path(feat_freeze_path)
    if not freeze_path.exists():
        return {}
    try:
        payload = yaml.safe_load(freeze_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    candidates = payload.get("feat_specifications")
    if not isinstance(candidates, list):
        candidates = payload.get("feat_specs")
    if not isinstance(candidates, list):
        return {}
    return {
        str(item.get("feat_id")).strip(): str(item.get("title")).strip()
        for item in candidates
        if isinstance(item, dict)
        and str(item.get("feat_id") or "").strip()
        and str(item.get("title") or "").strip()
    }


def extract_canonical_title_map(project_root: Optional[Path]) -> Dict[str, str]:
    if project_root is None:
        return {}
    features_dir = project_root / "spec" / "requirements" / "features"
    if not features_dir.exists():
        return {}
    title_map: Dict[str, str] = {}
    for path in sorted(features_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        try:
            _, frontmatter, _ = text.split("---", 2)
            metadata = yaml.safe_load(frontmatter) or {}
        except Exception:
            continue
        if not isinstance(metadata, dict):
            continue
        title = str(metadata.get("title") or "").strip()
        canonical_id = str(metadata.get("id") or "").strip()
        if title and canonical_id:
            title_map[title_key(title)] = canonical_id
    return title_map


def title_key(value: Any) -> str:
    lowered = str(value or "").strip().lower()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", lowered)
