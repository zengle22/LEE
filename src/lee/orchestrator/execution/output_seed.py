from __future__ import annotations

from pathlib import Path
from typing import Any, List, Sequence


def normalize_declared_output_files(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []

    normalized: List[str] = []
    seen = set()
    for value in values:
        path = str(value or "").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        normalized.append(path)
    return normalized


def seed_declared_output_files(*, workspace: str, output_files: Sequence[str]) -> List[str]:
    workspace_root = Path(workspace).resolve()
    seeded: List[str] = []

    for raw_path in normalize_declared_output_files(list(output_files)):
        candidate = Path(raw_path)
        resolved = (
            candidate.resolve()
            if candidate.is_absolute()
            else (workspace_root / candidate).resolve()
        )
        try:
            relative = resolved.relative_to(workspace_root)
        except ValueError:
            continue

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            if not resolved.exists():
                resolved.touch()
        except OSError:
            continue

        seeded.append(str(relative).replace("\\", "/"))

    return seeded
