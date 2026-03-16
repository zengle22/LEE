from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _first_text(*values: Any) -> str:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return ""


def _string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [_clean_text(item) for item in value if _clean_text(item)]
    if isinstance(value, str):
        text = _clean_text(value)
        return [text] if text else []
    return []


def _dedupe_strings(items: List[Any]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        text = _clean_text(item)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _is_adr_ref(value: str) -> bool:
    return value.startswith("ADR-")


def _extract_adr_refs(*values: Any) -> List[str]:
    refs: List[str] = []
    for value in values:
        for match in re.findall(r"ADR-\d{3}", _clean_text(value), flags=re.IGNORECASE):
            refs.append(match.upper())
    return _dedupe_strings(refs)


def _infer_expected_downstream_objects(payload: Dict[str, Any], change_scope: str) -> List[str]:
    normalized = f"{change_scope}\n{payload}".lower()
    candidates = ["EPIC", "FEAT"]
    if "release" in normalized or "交付" in normalized:
        candidates.append("RELEASE")
    if "tech" in normalized or "技术" in normalized:
        candidates.append("TECH")
    if "task" in normalized or "任务" in normalized:
        candidates.append("TASK")
    return candidates


def infer_bridge_src_fields(
    payload: Dict[str, Any],
    *,
    source_refs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    contract_info = _as_dict(payload.get("contract_info"))
    metadata = _as_dict(payload.get("metadata"))
    src_structure = _as_dict(payload.get("src_structure"))
    governance_refs = _as_dict(payload.get("governance_refs"))
    requirement_overview = _as_dict(payload.get("requirement_overview"))
    key_designs = _as_dict(payload.get("key_designs"))
    core_goal = _as_dict(key_designs.get("core_goal"))
    primary_goal = _as_dict(core_goal.get("primary_goal"))
    risks_and_boundaries = _as_dict(key_designs.get("risks_and_boundaries"))
    explicit_bridge = _as_dict(payload.get("bridge_context"))

    explicit_kind = _clean_text(payload.get("source_kind"))
    adr_refs = _dedupe_strings([
        *_string_list(explicit_bridge.get("governed_by_adrs")),
        *_string_list(payload.get("governing_adrs")),
        *_string_list(payload.get("decision_refs")),
        *_string_list(governance_refs.get("governing_adrs")),
        *_extract_adr_refs(
            contract_info.get("contract_id"),
            contract_info.get("title"),
            requirement_overview.get("context"),
            requirement_overview.get("description"),
            primary_goal.get("description"),
        ),
        contract_info.get("source_adr"),
        payload.get("source_adr"),
        metadata.get("source_ref"),
        *[ref for ref in (source_refs or []) if _is_adr_ref(_clean_text(str(ref).split("#", 1)[0]))],
    ])
    if explicit_kind != "governance_bridge_src" and not explicit_bridge and not adr_refs:
        return {"source_kind": explicit_kind} if explicit_kind else {}

    change_scope = _first_text(
        explicit_bridge.get("change_scope"),
        src_structure.get("change_scope"),
        src_structure.get("summary"),
        requirement_overview.get("description"),
        primary_goal.get("description"),
        payload.get("problem_statement"),
        payload.get("summary"),
    )
    expected_downstream_objects = _dedupe_strings(
        _string_list(explicit_bridge.get("expected_downstream_objects"))
        or _string_list(payload.get("expected_downstream_objects"))
        or _infer_expected_downstream_objects(payload, change_scope)
    )
    acceptance_impact = _dedupe_strings(
        _string_list(explicit_bridge.get("acceptance_impact"))
        or _string_list(primary_goal.get("success_criteria"))
        or _string_list(primary_goal.get("metrics"))
        or _string_list(risks_and_boundaries.get("in_scope"))
        or _string_list(payload.get("constraints"))
        or [change_scope]
    )
    non_goals = _dedupe_strings(
        _string_list(explicit_bridge.get("non_goals"))
        or _string_list(risks_and_boundaries.get("out_of_scope"))
        or _string_list(payload.get("non_goals"))
    )
    return {
        "source_kind": "governance_bridge_src",
        "bridge_context": {
            "governed_by_adrs": adr_refs,
            "change_scope": change_scope,
            "expected_downstream_objects": expected_downstream_objects,
            "acceptance_impact": acceptance_impact,
            "non_goals": non_goals,
        },
    }


def build_src_markdown(
    payload: Dict[str, Any],
    *,
    title: str,
    source_refs: Optional[List[str]] = None,
) -> str:
    src_structure = _as_dict(payload.get("src_structure"))
    requirement_overview = _as_dict(payload.get("requirement_overview"))
    key_designs = _as_dict(payload.get("key_designs"))
    core_goal = _as_dict(key_designs.get("core_goal"))
    primary_goal = _as_dict(core_goal.get("primary_goal"))
    risks_and_boundaries = _as_dict(key_designs.get("risks_and_boundaries"))
    bridge_fields = infer_bridge_src_fields(payload, source_refs=source_refs)

    problem_statement = _first_text(
        src_structure.get("problem_statement"),
        requirement_overview.get("description"),
        payload.get("problem_statement"),
        payload.get("summary"),
    )
    target_user = _dedupe_strings(
        _string_list(payload.get("target_user"))
        or _string_list(requirement_overview.get("target_users"))
    )
    business_motivation = _first_text(
        src_structure.get("business_motivation"),
        payload.get("business_motivation"),
        primary_goal.get("rationale"),
    )
    constraints = _dedupe_strings(
        _string_list(payload.get("constraints"))
        or _string_list(risks_and_boundaries.get("dependencies"))
    )

    lines = [f"# {title}", ""]
    if problem_statement:
        lines.extend(["## 问题陈述", "", problem_statement, ""])
    if target_user:
        lines.extend(["## 目标用户", ""])
        lines.extend([f"- {item}" for item in target_user])
        lines.append("")
    if business_motivation:
        lines.extend(["## 业务动因", "", business_motivation, ""])
    if constraints:
        lines.extend(["## 关键约束", ""])
        lines.extend([f"- {item}" for item in constraints])
        lines.append("")

    bridge_context = _as_dict(bridge_fields.get("bridge_context"))
    if bridge_context:
        lines.extend(["## Bridge Context", ""])
        if bridge_context.get("governed_by_adrs"):
            lines.append(f"- governed_by_adrs: {', '.join(bridge_context['governed_by_adrs'])}")
        if bridge_context.get("change_scope"):
            lines.append(f"- change_scope: {bridge_context['change_scope']}")
        if bridge_context.get("expected_downstream_objects"):
            lines.append(
                "- expected_downstream_objects: "
                + ", ".join(bridge_context["expected_downstream_objects"])
            )
        lines.append("")
        if bridge_context.get("acceptance_impact"):
            lines.extend(["## 验收与交付影响", ""])
            lines.extend([f"- {item}" for item in bridge_context["acceptance_impact"]])
            lines.append("")
        if bridge_context.get("non_goals"):
            lines.extend(["## 非目标", ""])
            lines.extend([f"- {item}" for item in bridge_context["non_goals"]])
            lines.append("")

    return "\n".join(lines)
