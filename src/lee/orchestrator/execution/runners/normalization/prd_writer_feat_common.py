from __future__ import annotations
from typing import Any, Dict, List, Optional
def clean_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_priority(value: Any) -> str:
    normalized = clean_text(value).upper()
    if normalized in {"P0", "P1", "P2"}:
        return normalized
    if normalized in {"HIGH", "CRITICAL"}:
        return "P0"
    if normalized in {"MEDIUM", "NORMAL"}:
        return "P1"
    if normalized in {"LOW"}:
        return "P2"
    if normalized in {"0", "1", "2"}:
        return f"P{normalized}"
    if normalized.startswith("P") and len(normalized) > 1 and normalized[1:].isdigit():
        return normalized if normalized in {"P0", "P1", "P2"} else "P1"
    return "P1"
def normalize_lifecycle_status(value: Any) -> str:
    normalized = clean_text(value).lower()
    mapping = {
        "draft": "draft",
        "active": "active",
        "frozen": "frozen",
        "archived": "archived",
        "completed": "active",
        "complete": "active",
        "success": "active",
        "done": "active",
        "specified": "draft",
    }
    return mapping.get(normalized, "draft")
def normalize_string_list(values: Any, *, fallback: Optional[List[str]] = None) -> List[str]:
    items = values if isinstance(values, list) else [values] if values is not None else []
    normalized_items: List[str] = []
    for item in items:
        if isinstance(item, dict):
            candidate = (
                item.get("description")
                or item.get("criterion")
                or item.get("title")
                or item.get("id")
            )
        else:
            candidate = item
        text = clean_text(candidate)
        if text:
            normalized_items.append(text)
    if normalized_items:
        return normalized_items
    return [text for text in (fallback or []) if clean_text(text)]
def normalize_dependency_ids(values: Any) -> List[str]:
    items = values if isinstance(values, list) else [values] if values is not None else []
    normalized_dependencies: List[str] = []
    for item in items:
        if isinstance(item, dict):
            candidate = item.get("id") or item.get("feat_id") or item.get("epic_id") or item.get("title")
        else:
            candidate = item
        text = clean_text(candidate)
        if text:
            normalized_dependencies.append(text)
    return normalized_dependencies
def normalize_acceptance_criteria(values: Any, *, title: str, goal: str) -> List[str]:
    items = values if isinstance(values, list) else [values] if values is not None else []
    normalized_criteria: List[str] = []
    for item in items:
        if isinstance(item, dict):
            candidate = item.get("description") or item.get("criterion") or item.get("validation")
        else:
            candidate = item
        text = clean_text(candidate)
        if text:
            normalized_criteria.append(text)
    if normalized_criteria:
        return normalized_criteria
    return [goal or title or "Feature is independently acceptable"]
def is_placeholder_input_value(value: Any) -> bool:
    normalized = clean_text(value).lower()
    if not normalized:
        return True
    placeholder_markers = (
        "inputs defined by epic scope",
        "input defined by epic scope",
        "same as epic",
        "tbd",
        "to be defined",
        "待补充",
        "待定义",
        "同 epic",
    )
    return any(marker in normalized for marker in placeholder_markers)
def normalize_input_entries(value: Any, *, fallback: Optional[List[Any]] = None) -> List[Any]:
    items = value if isinstance(value, list) else [value] if value is not None else []
    normalized_entries: List[Any] = []
    for item in items:
        if isinstance(item, dict):
            normalized_item: Dict[str, Any] = {}
            for raw_key, raw_value in item.items():
                key = clean_text(raw_key)
                if not key:
                    continue
                if isinstance(raw_value, dict):
                    nested: Dict[str, str] = {}
                    for nested_key, nested_value in raw_value.items():
                        normalized_nested_key = clean_text(nested_key)
                        normalized_nested_value = clean_text(nested_value)
                        if normalized_nested_key and normalized_nested_value:
                            nested[normalized_nested_key] = normalized_nested_value
                    if nested:
                        normalized_item[key] = nested
                elif isinstance(raw_value, list):
                    normalized_list = [clean_text(part) for part in raw_value if clean_text(part)]
                    if normalized_list:
                        normalized_item[key] = normalized_list
                else:
                    text_value = clean_text(raw_value)
                    if text_value:
                        normalized_item[key] = text_value
            if normalized_item:
                normalized_entries.append(normalized_item)
            continue
        text_value = clean_text(item)
        if text_value:
            normalized_entries.append(text_value)
    if normalized_entries:
        return normalized_entries
    if fallback:
        return normalize_input_entries(fallback, fallback=None)
    return []
def extract_input_field_names(inputs: List[Any]) -> List[str]:
    field_names: List[str] = []
    for item in inputs:
        if isinstance(item, str):
            if not is_placeholder_input_value(item):
                field_names.append(item)
            continue
        if not isinstance(item, dict):
            continue
        for raw_key, raw_value in item.items():
            key = clean_text(raw_key)
            if not key:
                continue
            if isinstance(raw_value, dict) and raw_value:
                for nested_key in raw_value.keys():
                    normalized_nested_key = clean_text(nested_key)
                    if normalized_nested_key:
                        field_names.append(f"{key}.{normalized_nested_key}")
            else:
                field_names.append(key)
    return list(dict.fromkeys(field_names))
def normalize_input_contract(
    contract_value: Any,
    *,
    inputs: List[Any],
    source_refs: List[str],
    epic_ref: Optional[str],
) -> Dict[str, Any]:
    existing = contract_value if isinstance(contract_value, dict) else {}
    required_artifacts = normalize_string_list(
        existing.get("required_artifacts"),
        fallback=source_refs or ([f"{epic_ref}#scope"] if epic_ref else []),
    )
    required_fields = normalize_string_list(
        existing.get("required_fields"),
        fallback=extract_input_field_names(inputs),
    )
    optional_fields = normalize_string_list(existing.get("optional_fields"))
    consumption_rules = normalize_string_list(
        existing.get("consumption_rules"),
        fallback=[
            (
                f"Consume {required_artifacts[0]} and map fields "
                f"{', '.join(required_fields[:3])}"
            )
            if required_artifacts and required_fields
            else "Consume upstream FEAT context and preserve traceability"
        ],
    )
    return {
        "required_artifacts": required_artifacts,
        "required_fields": required_fields,
        "optional_fields": optional_fields,
        "consumption_rules": consumption_rules,
    }
def build_acceptance_checks(
    feat_item: Dict[str, Any],
    acceptance_criteria: List[str],
) -> List[Dict[str, Any]]:
    raw_checks = feat_item.get("acceptance_checks")
    normalized_checks: List[Dict[str, Any]] = []
    if isinstance(raw_checks, list):
        for index, item in enumerate(raw_checks[:5], start=1):
            if not isinstance(item, dict):
                normalized_checks.append(
                    {
                        "id": f"AC-{index:03d}",
                        "scenario": clean_text(item),
                        "given": "",
                        "when": "",
                        "then": "",
                        "trace_hints": ["TECH"],
                    }
                )
                continue
            normalized_item = dict(item)
            normalized_item.setdefault("id", f"AC-{index:03d}")
            normalized_item.setdefault("scenario", "")
            normalized_item.setdefault("given", "")
            normalized_item.setdefault("when", "")
            normalized_item.setdefault("then", "")
            trace_hints = normalized_item.get("trace_hints")
            if not isinstance(trace_hints, list) or not trace_hints:
                normalized_item["trace_hints"] = ["TECH"]
            normalized_checks.append(normalized_item)
    if normalized_checks:
        return normalized_checks

    scenario_seed = acceptance_criteria[:5]
    if len(scenario_seed) == 1:
        scenario_seed.append(f"{feat_item.get('title') or 'Feature'} remains traceable")
    if not scenario_seed:
        scenario_seed = [
            feat_item.get("goal") or feat_item.get("title") or "Feature behavior is verifiable",
            f"{feat_item.get('title') or 'Feature'} outputs remain stable",
        ]

    synthesized_checks: List[Dict[str, Any]] = []
    for index, criterion in enumerate(scenario_seed[:5], start=1):
        synthesized_checks.append(
            {
                "id": f"AC-{index:03d}",
                "scenario": criterion,
                "given": feat_item.get("title") or "",
                "when": "the feature workflow runs",
                "then": criterion,
                "trace_hints": ["TECH"],
            }
        )
    return synthesized_checks
def extract_breakdown_feature_candidates(
    payload: Dict[str, Any],
    fallback_epic_ref: Optional[str],
) -> tuple[Optional[List[Any]], Optional[str]]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    resolved_epic_ref = (
        clean_text(payload.get("epic_ref"))
        or clean_text(metadata.get("epic_id"))
        or fallback_epic_ref
    )
    for key in ("features", "feats", "feat_candidates", "feat_specifications"):
        if isinstance(payload.get(key), list):
            return payload.get(key), resolved_epic_ref

    epic_breakdowns = payload.get("epic_breakdowns")
    if not isinstance(epic_breakdowns, list):
        return None, resolved_epic_ref

    selected_breakdown: Optional[Dict[str, Any]] = None
    if resolved_epic_ref:
        for item in epic_breakdowns:
            if isinstance(item, dict) and clean_text(item.get("epic_id")).lower() == resolved_epic_ref.lower():
                selected_breakdown = item
                break
    if selected_breakdown is None:
        for item in epic_breakdowns:
            if isinstance(item, dict) and isinstance(item.get("features"), list):
                selected_breakdown = item
                break
    if not isinstance(selected_breakdown, dict):
        return None, resolved_epic_ref

    resolved_epic_ref = clean_text(selected_breakdown.get("epic_id")) or resolved_epic_ref
    if isinstance(selected_breakdown.get("features"), list):
        return selected_breakdown.get("features"), resolved_epic_ref
    return None, resolved_epic_ref
def _candidate_context(candidate: Dict[str, Any]) -> Dict[str, Any]:
    interface_spec = candidate.get("interface_spec") if isinstance(candidate.get("interface_spec"), dict) else {}
    return {
        "business_context": candidate.get("business_context") if isinstance(candidate.get("business_context"), dict) else {},
        "scope_boundary": candidate.get("scope_boundary") if isinstance(candidate.get("scope_boundary"), dict) else {},
        "requirement": candidate.get("requirement") if isinstance(candidate.get("requirement"), dict) else {},
        "interface_spec": interface_spec,
        "input_schema": interface_spec.get("input_schema") if isinstance(interface_spec.get("input_schema"), dict) else {},
        "output_schema": interface_spec.get("output_schema") if isinstance(interface_spec.get("output_schema"), dict) else {},
        "state_machine": candidate.get("state_machine") if isinstance(candidate.get("state_machine"), dict) else {},
        "dependency_block": candidate.get("dependencies") if isinstance(candidate.get("dependencies"), dict) else {},
    }


def _candidate_goal_fields(candidate: Dict[str, Any], context: Dict[str, Any], title: str) -> Dict[str, str]:
    requirement = context["requirement"]
    business_context = context["business_context"]
    description = clean_text(candidate.get("description"))
    rich_description = clean_text(requirement.get("description"))
    return {
        "description": description,
        "rich_description": rich_description,
        "goal": clean_text(candidate.get("goal")) or rich_description or description or title,
        "user_value": (
            clean_text(candidate.get("user_value"))
            or clean_text(business_context.get("problem"))
            or rich_description
            or description
            or title
        ),
    }


def _candidate_io_fields(
    candidate: Dict[str, Any],
    context: Dict[str, Any],
    *,
    title: str,
    rich_description: str,
    description: str,
) -> Dict[str, List[Any]]:
    input_schema = context["input_schema"]
    output_schema = context["output_schema"]
    state_machine = context["state_machine"]
    scope_boundary = context["scope_boundary"]
    return {
        "inputs": normalize_input_entries(
            candidate.get("inputs")
            or candidate.get("input")
            or [
                field.get("name")
                for field in (input_schema.get("fields") if isinstance(input_schema.get("fields"), list) else [])
                if isinstance(field, dict) and clean_text(field.get("name"))
            ]
            or scope_boundary.get("in_scope"),
            fallback=[],
        ),
        "processing": normalize_string_list(
            candidate.get("processing")
            or [
                transition.get("trigger")
                for transition in (state_machine.get("transitions") if isinstance(state_machine.get("transitions"), list) else [])
                if isinstance(transition, dict) and clean_text(transition.get("trigger"))
            ],
            fallback=[rich_description or description or f"Deliver {title} capability"],
        ),
        "outputs": normalize_string_list(
            candidate.get("outputs")
            or candidate.get("output")
            or [
                field.get("name")
                for field in (output_schema.get("fields") if isinstance(output_schema.get("fields"), list) else [])
                if isinstance(field, dict) and clean_text(field.get("name"))
            ]
            or candidate.get("acceptance_boundary"),
            fallback=[f"{title} FEAT specification"],
        ),
    }


def _candidate_governance_fields(
    candidate: Dict[str, Any],
    context: Dict[str, Any],
    *,
    goal: str,
    title: str,
    epic_ref: Optional[str],
) -> Dict[str, Any]:
    scope_boundary = context["scope_boundary"]
    requirement = context["requirement"]
    dependency_block = context["dependency_block"]
    parent_workflow = clean_text(candidate.get("parent_workflow"))
    category = clean_text(candidate.get("category"))
    normalized_epic_ref = epic_ref or clean_text(candidate.get("parent_epic"))
    source_refs = normalize_string_list(
        candidate.get("source_refs"),
        fallback=[f"{normalized_epic_ref}#scope"] if normalized_epic_ref else [],
    )
    return {
        "acceptance_criteria": normalize_acceptance_criteria(
            candidate.get("acceptance_criteria")
            or requirement.get("acceptance_criteria")
            or candidate.get("acceptance_boundaries"),
            title=title,
            goal=goal,
        ),
        "non_goals": normalize_string_list(candidate.get("non_goals") or scope_boundary.get("out_of_scope")),
        "priority": normalize_priority(candidate.get("priority")),
        "parent_workflow": parent_workflow,
        "category": category,
        "delivery_slice": clean_text(candidate.get("delivery_slice")) or parent_workflow or category or "core",
        "normalized_epic_ref": normalized_epic_ref,
        "source_refs": source_refs,
        "dependencies": normalize_dependency_ids(
            candidate.get("dependencies")
            if not isinstance(candidate.get("dependencies"), dict)
            else dependency_block.get("upstream")
        ),
    }


def synthesize_feat_spec(candidate: Dict[str, Any], epic_ref: Optional[str]) -> Dict[str, Any]:
    title = clean_text(candidate.get("title")) or "Untitled FEAT"
    feat_id = clean_text(candidate.get("feat_id") or candidate.get("id"))
    if not feat_id:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").upper()
        feat_id = f"FEAT-{slug}" if slug else "FEAT-AUTO"
    context = _candidate_context(candidate)
    goal_fields = _candidate_goal_fields(candidate, context, title)
    io_fields = _candidate_io_fields(
        candidate,
        context,
        title=title,
        rich_description=goal_fields["rich_description"],
        description=goal_fields["description"],
    )
    governance_fields = _candidate_governance_fields(
        candidate,
        context,
        goal=goal_fields["goal"],
        title=title,
        epic_ref=epic_ref,
    )

    synthesized = {
        "feat_id": feat_id,
        "title": title,
        "goal": goal_fields["goal"],
        "user_value": goal_fields["user_value"],
        "inputs": io_fields["inputs"],
        "input_contract": normalize_input_contract(
            candidate.get("input_contract"),
            inputs=io_fields["inputs"],
            source_refs=governance_fields["source_refs"],
            epic_ref=governance_fields["normalized_epic_ref"],
        ),
        "processing": io_fields["processing"],
        "outputs": io_fields["outputs"],
        "acceptance_criteria": governance_fields["acceptance_criteria"],
        "dependencies": governance_fields["dependencies"],
        "non_goals": governance_fields["non_goals"],
        "priority": governance_fields["priority"],
        "delivery_slice": governance_fields["delivery_slice"],
        "lifecycle_status": normalize_lifecycle_status(
            candidate.get("lifecycle_status") or candidate.get("status")
        ),
        "source_refs": governance_fields["source_refs"],
        "ssot": {
            "identity_kind": "ssot",
            "ssot_type": "FEAT",
            "parent": governance_fields["normalized_epic_ref"],
            "derived_from": governance_fields["normalized_epic_ref"],
        },
        "testability_seed": {
            "risk_notes": governance_fields["non_goals"],
            "integration_points": [
                value
                for value in [governance_fields["parent_workflow"], governance_fields["category"]]
                if value
            ],
            "priority_hint": governance_fields["priority"],
        },
    }
    synthesized["acceptance_checks"] = build_acceptance_checks(
        synthesized,
        governance_fields["acceptance_criteria"],
    )
    return synthesized


def normalize_user_story_item(item: Any) -> Optional[Dict[str, str]]:
    if not isinstance(item, dict):
        return None
    as_a = clean_text(item.get("as_a") or item.get("role") or item.get("actor"))
    i_want = clean_text(item.get("i_want") or item.get("action") or item.get("need"))
    so_that = clean_text(
        item.get("so_that")
        or item.get("benefit")
        or item.get("value")
        or item.get("outcome")
    )
    if not (as_a and i_want and so_that):
        return None
    return {"as_a": as_a, "i_want": i_want, "so_that": so_that}
