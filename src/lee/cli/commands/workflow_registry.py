"""Shared workflow registry resolution for CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


FRAMEWORK_ROOT = Path(__file__).resolve().parents[4]
FRAMEWORK_REGISTRY_PATH = FRAMEWORK_ROOT / "config" / "workflow-registry.yaml"


def get_workflow_registry_path() -> Path:
    """Return the framework-managed workflow registry path."""
    if not FRAMEWORK_REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Workflow registry not found: {FRAMEWORK_REGISTRY_PATH}")
    return FRAMEWORK_REGISTRY_PATH


def load_workflow_registry() -> Dict[str, Any]:
    registry_path = get_workflow_registry_path()
    with open(registry_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_workflow_template_path(template_path: str | Path) -> Path:
    path = Path(template_path)
    if path.is_absolute():
        return path
    registry_path = get_workflow_registry_path()
    return (registry_path.parent.parent / path).resolve()
