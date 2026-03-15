"""Helpers for turning ``--spec`` files into workflow params."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable

import click
import yaml

from lee.orchestrator.execution.artifacts.ssot_files import parse_front_matter


def load_spec_option_as_params(spec_path: str) -> Dict[str, Any]:
    """Load a YAML/JSON spec file as workflow params."""
    path = Path(spec_path).resolve()
    if not path.exists():
        raise click.ClickException(f"Spec file not found: {path}")

    try:
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise click.ClickException(f"Failed to parse spec file '{path}': {exc}") from exc


def load_spec_option(spec_path: str) -> Dict[str, Any]:
    """
    Resolve ``--spec`` into workflow params.

    Default behavior:
    - object-like YAML/JSON -> merge as params
    - everything else -> keep as {"spec": "<absolute-path>"}
    """
    path = Path(spec_path).resolve()
    if not path.exists():
        raise click.ClickException(f"Spec file not found: {path}")

    if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
        return {"spec": str(path)}

    loaded = load_spec_option_as_params(str(path))
    if isinstance(loaded, dict):
        return loaded
    return {"spec": str(path)}


def load_spec_option_for_workflow(spec_path: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve ``--spec`` into workflow params with workflow-specific adaptation.

    Product raw-input workflows can opt into loading plain-text specs as actual
    params. Formal ADR markdown is adapted into a structured ``adr`` payload and
    a concise ``raw_requirement`` summary.
    """
    path = Path(spec_path).resolve()
    if not path.exists():
        raise click.ClickException(f"Spec file not found: {path}")

    if path.suffix.lower() in {".json", ".yaml", ".yml"}:
        loaded = load_spec_option_as_params(str(path))
        if isinstance(loaded, dict):
            return loaded
        return {"spec": str(path)}

    if not entry.get("load_spec_as_params"):
        return {"spec": str(path)}

    candidate_params = set(entry.get("required_params", []) or [])
    candidate_params.update(entry.get("optional_params", []) or [])

    adr_payload = _build_adr_input_payload(path)
    if adr_payload is not None:
        adapted: Dict[str, Any] = {}
        if "adr" in candidate_params:
            adapted["adr"] = adr_payload
        if "raw_requirement" in candidate_params:
            adapted["raw_requirement"] = adr_payload["raw_requirement"]
        if adapted:
            return adapted

    if "raw_requirement" in candidate_params:
        return {"raw_requirement": path.read_text(encoding="utf-8")}

    return {"spec": str(path)}


def _build_adr_input_payload(path: Path) -> Dict[str, Any] | None:
    try:
        front_matter, body = parse_front_matter(path)
    except Exception:
        return None

    if str(front_matter.get("ssot_type") or "").strip().lower() != "adr":
        return None

    artifact_id = str(front_matter.get("id") or path.stem.split("__", 1)[0]).strip()
    title = str(front_matter.get("title") or artifact_id or path.stem).strip()
    decision_summary = _extract_section(body, ["1. Decision", "Decision"])
    problem_summary = _extract_section(body, ["3. Problem", "Problem"])
    follow_up_summary = _extract_section(body, ["11. Follow-Up", "Follow-Up"])

    return {
        "artifact_id": artifact_id,
        "ssot_type": "ADR",
        "title": title,
        "status": str(front_matter.get("status") or "").strip(),
        "version": str(front_matter.get("version") or "").strip(),
        "path": str(path),
        "source_ref": artifact_id,
        "decision_summary": decision_summary,
        "problem_summary": problem_summary,
        "follow_up_summary": follow_up_summary,
        "raw_requirement": _synthesize_adr_raw_requirement(
            artifact_id=artifact_id,
            title=title,
            body=body,
            decision_summary=decision_summary,
            problem_summary=problem_summary,
            follow_up_summary=follow_up_summary,
        ),
    }


def _extract_section(body: str, headings: Iterable[str]) -> str:
    if not body:
        return ""
    pattern = "|".join(re.escape(item) for item in headings if item)
    if not pattern:
        return ""
    match = re.search(rf"(?ms)^##\s+(?:{pattern})\s*\n(.*?)(?=^##\s+|\Z)", body)
    if not match:
        return ""
    return _compact_markdown(match.group(1), limit=900)


def _synthesize_adr_raw_requirement(
    *,
    artifact_id: str,
    title: str,
    body: str,
    decision_summary: str,
    problem_summary: str,
    follow_up_summary: str,
) -> str:
    sections = [
        (f"{artifact_id} {title}".strip(), None),
        ("Decision", decision_summary),
        ("Problem", problem_summary),
        ("Follow-Up", follow_up_summary),
    ]
    lines = [header for header, summary in sections if summary is None and header]
    for header, summary in sections[1:]:
        if summary:
            lines.append(f"{header}:")
            lines.append(summary)
    if len(lines) == 1:
        lines.append("Context:")
        lines.append(_compact_markdown(body, limit=1400))
    return "\n".join(lines).strip()


def _compact_markdown(text: str, *, limit: int) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    compact = "\n".join(lines)
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 4)].rstrip() + "\n..."
