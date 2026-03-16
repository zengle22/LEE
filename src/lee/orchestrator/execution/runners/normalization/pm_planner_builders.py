from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from .pm_planner_task_context import PmPlannerContext


def normalize_task_payload(payload: Dict[str, Any], ctx: PmPlannerContext) -> Dict[str, Any]:
    if isinstance(payload.get("task_specs"), list) and payload.get("task_specs"):
        return _normalize_existing_task_specs(payload, ctx)
    return _build_legacy_task_plan(payload, ctx)


def _normalize_existing_task_specs(payload: Dict[str, Any], ctx: PmPlannerContext) -> Dict[str, Any]:
    normalized_business = dict(payload)
    normalized_business["source_feats"] = [
        ctx.feat_alias_map.get(ctx.clean_text(item), ctx.clean_text(item))
        for item in (payload.get("source_feats") or [])
        if ctx.clean_text(item)
    ]
    remapped_specs: List[Dict[str, Any]] = []
    for task_spec in payload.get("task_specs") or []:
        if isinstance(task_spec, dict):
            remapped_specs.append(_remap_existing_task_spec(task_spec, ctx))
    normalized_business["task_specs"] = remapped_specs
    return normalized_business


def _remap_existing_task_spec(task_spec: Dict[str, Any], ctx: PmPlannerContext) -> Dict[str, Any]:
    remapped_task = dict(task_spec)
    raw_source_feat = ctx.clean_text(task_spec.get("source_feat"))
    canonical_source_feat = ctx.feat_alias_map.get(raw_source_feat, raw_source_feat) or "FEAT-001"
    formal_checks = ctx.formal_acceptance_checks(canonical_source_feat)
    remapped_task["source_feat"] = canonical_source_feat
    if isinstance(task_spec.get("source_refs"), list):
        remapped_task["source_refs"] = [
            f"{canonical_source_feat}#delivery"
            if isinstance(ref, str) and ref == f"{raw_source_feat}#delivery" and canonical_source_feat
            else ref
            for ref in task_spec.get("source_refs") or []
        ]
    if isinstance(task_spec.get("ssot"), dict):
        remapped_task["ssot"] = _remap_ssot_block(task_spec["ssot"], raw_source_feat, canonical_source_feat, ctx)
    if isinstance(task_spec.get("acceptance_criteria_mapping"), list):
        remapped_task["acceptance_criteria_mapping"] = _remap_acceptance_mapping(
            task_spec.get("acceptance_criteria_mapping") or [],
            canonical_source_feat,
            formal_checks,
            ctx,
        )
    return _normalize_task_path_refs(remapped_task, canonical_source_feat)


def _remap_ssot_block(
    ssot_block: Dict[str, Any],
    raw_source_feat: str,
    canonical_source_feat: str,
    ctx: PmPlannerContext,
) -> Dict[str, Any]:
    remapped_ssot = dict(ssot_block or {})
    remapped_ssot["parent"] = canonical_source_feat
    derived_from = ctx.clean_text(remapped_ssot.get("derived_from"))
    if raw_source_feat and derived_from == f"{raw_source_feat}#delivery":
        remapped_ssot["derived_from"] = f"{canonical_source_feat}#delivery"
    return remapped_ssot


def _remap_acceptance_mapping(
    mappings: List[Dict[str, Any]],
    feat_id: str,
    formal_checks: List[Dict[str, Any]],
    ctx: PmPlannerContext,
) -> List[Dict[str, Any]]:
    formal_ids = [str(item.get("id")).strip() for item in formal_checks if str(item.get("id") or "").strip()]
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(mappings, start=1):
        if not isinstance(item, dict):
            continue
        raw_ac = ctx.clean_text(item.get("ac"))
        selected_ac = _select_acceptance_id(raw_ac, formal_ids, index)
        normalized.append(
            {
                "feat": feat_id,
                "ac": selected_ac,
                "description": ctx.clean_text(item.get("description")) or ctx.clean_text(item.get("ac")) or selected_ac,
            }
        )
    return normalized


def _select_acceptance_id(raw_ac: str, formal_ids: List[str], index: int) -> str:
    if raw_ac in formal_ids:
        return raw_ac
    if raw_ac:
        import re

        suffix_match = re.search(r"(\d{3})$", raw_ac)
        if suffix_match:
            for candidate in formal_ids:
                if candidate.endswith(suffix_match.group(1)):
                    return candidate
    if formal_ids:
        return formal_ids[min(index - 1, len(formal_ids) - 1)]
    return raw_ac or f"AC-{index:03d}"


def _build_legacy_task_plan(payload: Dict[str, Any], ctx: PmPlannerContext) -> Dict[str, Any]:
    epic_ref = ctx.clean_text(payload.get("parent_epic") or payload.get("epic_ref"))
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if not epic_ref:
        epic_ref = ctx.clean_text(metadata.get("epic_id"))

    feat_tasks = payload.get("feat_tasks") if isinstance(payload.get("feat_tasks"), list) else []
    plan_tasks = payload.get("tasks") if isinstance(payload.get("tasks"), list) else []
    source_feats = [
        ctx.feat_alias_map.get(ctx.clean_text(item.get("feat_id")), ctx.clean_text(item.get("feat_id")))
        for item in feat_tasks
        if isinstance(item, dict) and ctx.clean_text(item.get("feat_id"))
    ]
    task_specs, milestones_map, resource_allocation, critical_path = _build_primary_task_specs(
        feat_tasks,
        plan_tasks,
        payload,
        source_feats,
        ctx,
    )
    if not task_specs:
        task_specs = _build_hierarchy_task_specs(
            payload,
            source_feats,
            milestones_map,
            resource_allocation,
            critical_path,
            ctx,
        )
    return {
        "parent_epic": epic_ref or "EPIC-001",
        "source_feats": source_feats or ["FEAT-001"],
        "planning_metadata": {
            "planning_timestamp": ctx.clean_text(payload.get("created_at")) or datetime.now().strftime("%Y-%m-%d"),
            "project_profile": "legacy_task_planning_view",
            "task_directory": f"spec/tasks/{(source_feats or ['FEAT-001'])[0]}",
        },
        "task_specs": task_specs,
        "milestones": list(milestones_map.values()) or [_default_milestone(task_specs)],
        "dependency_graph": {"critical_path": critical_path or _critical_path_seed(task_specs)},
        "resource_allocation": resource_allocation or {"workflow-runtime-owner": {"tasks": []}},
        "risk_mitigation": _build_risk_mitigation(payload, critical_path, task_specs, ctx),
    }


def _build_primary_task_specs(
    feat_tasks: List[Dict[str, Any]],
    plan_tasks: List[Dict[str, Any]],
    payload: Dict[str, Any],
    source_feats: List[str],
    ctx: PmPlannerContext,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], List[str]]:
    task_specs: List[Dict[str, Any]] = []
    milestones_map: Dict[str, Dict[str, Any]] = {}
    resource_allocation: Dict[str, Dict[str, Any]] = {}
    critical_path: List[str] = []
    _build_feat_task_specs(feat_tasks, task_specs, milestones_map, resource_allocation, critical_path, ctx)
    if not task_specs and plan_tasks:
        _build_plan_task_specs(plan_tasks, payload, source_feats, task_specs, milestones_map, resource_allocation, critical_path, ctx)
    return task_specs, milestones_map, resource_allocation, critical_path


def _build_feat_task_specs(
    feat_tasks: List[Dict[str, Any]],
    task_specs: List[Dict[str, Any]],
    milestones_map: Dict[str, Dict[str, Any]],
    resource_allocation: Dict[str, Dict[str, Any]],
    critical_path: List[str],
    ctx: PmPlannerContext,
) -> None:
    for feat_entry in feat_tasks:
        if not isinstance(feat_entry, dict):
            continue
        feat_id = ctx.feat_alias_map.get(ctx.clean_text(feat_entry.get("feat_id")), ctx.clean_text(feat_entry.get("feat_id")))
        phases = feat_entry.get("implementation_plan", {}).get("phases") if isinstance(feat_entry.get("implementation_plan"), dict) else []
        for phase in phases if isinstance(phases, list) else []:
            if not isinstance(phase, dict):
                continue
            milestone = ensure_milestone(milestones_map, ctx.clean_text(phase.get("phase_id")), ctx.clean_text(phase.get("name")), f"{feat_id} {ctx.clean_text(phase.get('name'))}".strip())
            for task in phase.get("tasks") if isinstance(phase.get("tasks"), list) else []:
                task_spec = build_task_spec(task, feat_id, feat_entry.get("priority"), milestone["id"], ctx)
                task_specs.append(task_spec)
                register_task(task_spec, milestone, resource_allocation, critical_path, ctx)


def _build_plan_task_specs(
    plan_tasks: List[Dict[str, Any]],
    payload: Dict[str, Any],
    source_feats: List[str],
    task_specs: List[Dict[str, Any]],
    milestones_map: Dict[str, Dict[str, Any]],
    resource_allocation: Dict[str, Dict[str, Any]],
    critical_path: List[str],
    ctx: PmPlannerContext,
) -> None:
    seen_source_feats: set[str] = set(source_feats)
    group_lookup = build_group_lookup(payload, milestones_map, ctx)
    for task in plan_tasks:
        if not isinstance(task, dict):
            continue
        feat_id = resolve_task_feat(task, source_feats, seen_source_feats, ctx)
        milestone_info = group_lookup.get(ctx.clean_text(task.get("task_id")), {})
        milestone = ensure_milestone(
            milestones_map,
            ctx.clean_text(milestone_info.get("milestone_id")),
            ctx.clean_text(milestone_info.get("milestone_name")),
            f"{ctx.clean_text(milestone_info.get('milestone_name')) or 'M'} completed",
        )
        prerequisite_ids = ctx.normalize_list((task.get("dependencies") or {}).get("upstream")) if isinstance(task.get("dependencies"), dict) else []
        task_spec = build_task_spec(task, feat_id, task.get("priority"), milestone["id"], ctx, prerequisites=prerequisite_ids, dependencies=prerequisite_ids)
        task_specs.append(task_spec)
        register_task(task_spec, milestone, resource_allocation, critical_path, ctx)


def _build_hierarchy_task_specs(
    payload: Dict[str, Any],
    source_feats: List[str],
    milestones_map: Dict[str, Dict[str, Any]],
    resource_allocation: Dict[str, Dict[str, Any]],
    critical_path: List[str],
    ctx: PmPlannerContext,
) -> List[Dict[str, Any]]:
    task_specs: List[Dict[str, Any]] = []
    seen_source_feats: set[str] = set(source_feats)
    for phase in payload.get("task_hierarchy") if isinstance(payload.get("task_hierarchy"), list) else []:
        if not isinstance(phase, dict):
            continue
        milestone = ensure_milestone(milestones_map, ctx.clean_text(phase.get("phase_id")), ctx.clean_text(phase.get("phase")) or ctx.clean_text(phase.get("name")), "completed")
        for task in phase.get("tasks") if isinstance(phase.get("tasks"), list) else []:
            feat_id = resolve_task_feat(task, source_feats, seen_source_feats, ctx, keys=("related_feat", "source_feat", "feat_id"))
            task_spec = build_task_spec(task, feat_id, task.get("priority"), milestone["id"], ctx)
            task_specs.append(task_spec)
            register_task(task_spec, milestone, resource_allocation, critical_path, ctx)
    return task_specs


def build_group_lookup(payload: Dict[str, Any], milestones_map: Dict[str, Dict[str, Any]], ctx: PmPlannerContext) -> Dict[str, Dict[str, str]]:
    lookup: Dict[str, Dict[str, str]] = {}
    overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
    for group in overview.get("groups") if isinstance(overview.get("groups"), list) else []:
        if not isinstance(group, dict):
            continue
        milestone = ensure_milestone(milestones_map, ctx.clean_text(group.get("group_id")), ctx.clean_text(group.get("name")), "completed")
        for task_ref in group.get("tasks") if isinstance(group.get("tasks"), list) else []:
            task_key = ctx.clean_text(task_ref)
            if task_key:
                lookup[task_key] = {"milestone_id": milestone["id"], "milestone_name": milestone["name"]}
    return lookup


def resolve_task_feat(
    task: Dict[str, Any],
    source_feats: List[str],
    seen_source_feats: set[str],
    ctx: PmPlannerContext,
    keys: Tuple[str, ...] = ("feat_ref", "source_feat", "related_feat", "feat_id"),
) -> str:
    raw_feat_id = ""
    for key in keys:
        candidate = ctx.clean_text(task.get(key))
        if candidate:
            raw_feat_id = candidate
            break
    feat_id = ctx.feat_alias_map.get(raw_feat_id, raw_feat_id)
    if feat_id and feat_id not in seen_source_feats:
        source_feats.append(feat_id)
        seen_source_feats.add(feat_id)
    return feat_id


def build_task_spec(
    task: Dict[str, Any],
    feat_id: str,
    priority_source: Any,
    milestone_id: str,
    ctx: PmPlannerContext,
    *,
    prerequisites: List[str] | None = None,
    dependencies: List[str] | None = None,
) -> Dict[str, Any]:
    task_id = ctx.clean_text(task.get("task_id")) or f"{feat_id or 'FEAT-001'}-TASK-001"
    title = ctx.clean_text(task.get("title")) or task_id
    description = ctx.clean_text(task.get("description")) or title
    role = ctx.normalize_role(task.get("assignee_role") or task.get("responsible_role"))
    workstream = ctx.normalize_workstream(task, role)
    acceptance_items = ctx.normalize_list(task.get("acceptance_criteria")) or [description]
    estimated_effort = ctx.clean_text(task.get("estimated_effort") or task.get("effort"))
    if not estimated_effort and task.get("story_points") is not None:
        estimated_effort = f"{ctx.clean_text(task.get('story_points'))} points"
    return {
        "task_id": task_id,
        "title": title,
        "objective": acceptance_items[0],
        "description": description,
        "source_feat": feat_id or "FEAT-001",
        "workstream": workstream,
        "task_kind": ctx.infer_task_kind(task, role, workstream),
        "responsible_role": role,
        "acceptance_criteria_mapping": build_acceptance_mapping(acceptance_items, feat_id or "FEAT-001"),
        "prerequisites": prerequisites if prerequisites is not None else ctx.normalize_list(task.get("prerequisites")),
        "dependencies": dependencies if dependencies is not None else ctx.normalize_list(task.get("dependencies")),
        "definition_of_done": acceptance_items[:3] or [f"{title} completed"],
        "priority": ctx.normalize_priority(priority_source),
        "milestone": milestone_id,
        "estimated_effort": estimated_effort or "1 day",
        "lifecycle_status": "draft",
        "observability": {"execution_unit": "task", "log_scope": "task-execution", "audit_fields": ["run_id", "task_id", "changed_files", "evidence_refs"]},
        "evidence_requirements": {"required_refs": [feat_id] if feat_id else ["delivery-plan"], "review_required": True},
        "rollback_strategy": {"mode": "revert", "restore_targets": [workstream]},
        "source_refs": [f"{feat_id}#delivery"] if feat_id and ctx.runner_cls._is_literal_ssot_ref(feat_id) else [],
        "ssot": {"identity_kind": "ssot", "ssot_type": "TASK", "parent": feat_id or "FEAT-001", "derived_from": f"{feat_id}#delivery" if feat_id else "delivery-plan"},
    }


def build_acceptance_mapping(acceptance_items: List[str], feat_id: str) -> List[Dict[str, str]]:
    return [
        {"feat": feat_id, "ac": f"{feat_id}-AC-{index:03d}", "description": item}
        for index, item in enumerate(acceptance_items, start=1)
    ]


def ensure_milestone(milestones_map: Dict[str, Dict[str, Any]], milestone_id: str, milestone_name: str, acceptance_criteria: str) -> Dict[str, Any]:
    resolved_id = milestone_id or f"M{len(milestones_map) + 1}"
    resolved_name = milestone_name or resolved_id
    return milestones_map.setdefault(
        resolved_id,
        {"id": resolved_id, "name": resolved_name, "task_ids": [], "acceptance_criteria": acceptance_criteria or f"{resolved_name} completed"},
    )


def register_task(
    task_spec: Dict[str, Any],
    milestone: Dict[str, Any],
    resource_allocation: Dict[str, Dict[str, Any]],
    critical_path: List[str],
    ctx: PmPlannerContext,
) -> None:
    task_id = ctx.clean_text(task_spec.get("task_id"))
    milestone["task_ids"].append(task_id)
    critical_path.append(task_id)
    role = ctx.clean_text(task_spec.get("responsible_role")) or "workflow-runtime-owner"
    resource_allocation.setdefault(role, {"tasks": []})
    resource_allocation[role]["tasks"].append(task_id)


def _build_risk_mitigation(
    payload: Dict[str, Any],
    critical_path: List[str],
    task_specs: List[Dict[str, Any]],
    ctx: PmPlannerContext,
) -> List[Dict[str, Any]]:
    risks: List[Dict[str, Any]] = []
    for risk in payload.get("risks") if isinstance(payload.get("risks"), list) else []:
        if not isinstance(risk, dict):
            continue
        affected_tasks = ctx.normalize_list(risk.get("affected_tasks")) or critical_path[:2]
        if not affected_tasks and task_specs:
            affected_tasks = [str(task_specs[0].get("task_id"))]
        risks.append(
            {
                "risk": ctx.clean_text(risk.get("description") or risk.get("title") or risk.get("risk_id") or "planning-risk"),
                "mitigation": ctx.clean_text(risk.get("mitigation") or risk.get("fallback") or "Track in delivery review"),
                "affected_tasks": affected_tasks,
            }
        )
    return risks


def _default_milestone(task_specs: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "id": "M1",
        "name": "Initial Delivery Plan",
        "task_ids": [item.get("task_id") for item in task_specs[:1] if isinstance(item, dict)],
        "acceptance_criteria": "Delivery plan created",
    }


def _critical_path_seed(task_specs: List[Dict[str, Any]]) -> List[str]:
    return [item.get("task_id") for item in task_specs[:1] if isinstance(item, dict) and item.get("task_id")]


def _normalize_task_path_refs(value: Any, feat_id: str) -> Any:
    canonical_feat = feat_id or "FEAT-001"
    canonical_dir = f"spec/tasks/{canonical_feat}"
    legacy_variants = (
        f"spec/requirements/tasks/{canonical_feat}/",
        f"spec/requirements/tasks/{canonical_feat}",
        "spec/requirements/tasks/<FEAT-ID>/",
        "spec/requirements/tasks/<FEAT-ID>",
    )
    if isinstance(value, str):
        normalized = value
        for legacy in legacy_variants:
            normalized = normalized.replace(legacy, canonical_dir)
        return normalized
    if isinstance(value, list):
        return [_normalize_task_path_refs(item, feat_id) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_task_path_refs(item, feat_id) for key, item in value.items()}
    return value
