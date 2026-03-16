"""Utilities for resolving declared external workflow inputs."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


def resolve_declared_external_input(
    item: Optional[Dict[str, Any]],
    data: Dict[str, Any],
    params: Dict[str, Any],
    *,
    transform: Optional[Callable[[Any], Any]] = None,
) -> Any:
    """Resolve ``source: external`` against declared input type names."""
    if not isinstance(item, dict):
        return None

    raw_types = item.get("type", [])
    if isinstance(raw_types, str):
        raw_types = [raw_types]

    for type_name in raw_types:
        if not isinstance(type_name, str):
            continue
        if type_name in data:
            return transform(data[type_name]) if transform else data[type_name]
        if type_name in params:
            return transform(params[type_name]) if transform else params[type_name]
    return None
