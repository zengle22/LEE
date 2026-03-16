"""Shared workflow registry resolution for CLI commands."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml


REGISTRY_FILE_NAME = "workflow-registry.yaml"


def get_workflow_registry_path() -> Path:
    """Return the framework-managed workflow registry path.

    Resolution order:
    1) LEE_WORKFLOW_REGISTRY (explicit registry file path)
    2) LEE_FRAMEWORK_ROOT/config/workflow-registry.yaml
    3) walk up from current module and find */config/workflow-registry.yaml
    """
    env_registry = (os.getenv("LEE_WORKFLOW_REGISTRY") or "").strip()
    if env_registry:
        registry_path = Path(env_registry).expanduser().resolve()
        if registry_path.exists():
            return registry_path

    env_framework_root = (os.getenv("LEE_FRAMEWORK_ROOT") or "").strip()
    if env_framework_root:
        registry_path = (Path(env_framework_root).expanduser().resolve() / "config" / REGISTRY_FILE_NAME)
        if registry_path.exists():
            return registry_path

    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        registry_path = parent / "config" / REGISTRY_FILE_NAME
        if registry_path.exists():
            return registry_path

    raise FileNotFoundError(
        "Workflow registry not found. Tried: "
        "LEE_WORKFLOW_REGISTRY, LEE_FRAMEWORK_ROOT/config/workflow-registry.yaml, "
        f"and parents of {module_path}"
    )


def _resolve_relative_to_registry_root(registry_path: Path, relative_path: Path) -> Path:
    root = registry_path.parent.parent
    candidate = (root / relative_path).resolve()
    if candidate.exists():
        return candidate

    # Packaged layout keeps specs at <package>/data/spec-global.
    if relative_path.parts and relative_path.parts[0] == "spec-global":
        relative_under_spec_global = Path(*relative_path.parts[1:])
        packaged_candidate = (root / "data" / "spec-global" / relative_under_spec_global).resolve()
        if packaged_candidate.exists():
            return packaged_candidate

    return candidate


def load_workflow_registry() -> Dict[str, Any]:
    registry_path = get_workflow_registry_path()
    with open(registry_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_workflow_template_path(template_path: str | Path) -> Path:
    path = Path(template_path)
    if path.is_absolute():
        return path
    registry_path = get_workflow_registry_path()
    return _resolve_relative_to_registry_root(registry_path, path)
