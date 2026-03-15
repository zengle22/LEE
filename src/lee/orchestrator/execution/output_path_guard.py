from __future__ import annotations

from pathlib import Path
from typing import List, Optional


def detect_forbidden_template_write_paths(
    *,
    paths: List[str],
    project_root: Optional[str],
) -> Optional[str]:
    if not paths:
        return None

    project_root_path = Path(project_root or ".").resolve()
    forbidden_root = (project_root_path / "spec-global").resolve()
    blocked: List[str] = []

    for raw_path in paths:
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        candidate = Path(raw_path)
        candidate = (
            (project_root_path / candidate).resolve()
            if not candidate.is_absolute()
            else candidate.resolve()
        )
        try:
            relative = candidate.relative_to(forbidden_root)
        except ValueError:
            continue

        parts = relative.parts
        for idx in range(0, len(parts) - 1):
            if parts[idx:idx + 2] == ("workflows", "templates"):
                blocked.append(str(candidate))
                break

    if blocked:
        return "Forbidden template-directory write(s): " + ", ".join(blocked)
    return None
