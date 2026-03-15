from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional


def collect_unique_publishable_candidates(
    payload: Any,
    candidate_type_fn: Callable[[Dict[str, Any]], Optional[str]],
) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            candidate_type = candidate_type_fn(node)
            if candidate_type:
                fingerprint = _fingerprint_candidate(candidate_type, node)
                if fingerprint not in seen:
                    seen.add(fingerprint)
                    collected.append(node)
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)
            return
        if isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return collected


def _fingerprint_candidate(candidate_type: str, payload: Dict[str, Any]) -> str:
    ssot = payload.get("ssot") if isinstance(payload.get("ssot"), dict) else {}
    identity = {
        "candidate_type": candidate_type,
        "title": str(payload.get("title") or "").strip(),
        "goal": str(payload.get("goal") or "").strip(),
        "problem_statement": str(payload.get("problem_statement") or "").strip(),
        "source_refs": _normalize_strings(payload.get("source_refs")),
        "scope": _normalize_strings(payload.get("scope")),
        "non_goals": _normalize_strings(payload.get("non_goals")),
        "success_metrics": _normalize_strings(payload.get("success_metrics")),
        "parent": str(ssot.get("parent") or "").strip(),
        "derived_from": str(ssot.get("derived_from") or "").strip(),
    }
    return json.dumps(identity, ensure_ascii=False, sort_keys=True)


def _normalize_strings(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]
