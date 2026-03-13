from __future__ import annotations

import re
from typing import Any, Dict, List

import yaml

from .pm_planner_task_context import PmPlannerContext


def finalize_payload(
    normalized_business: Dict[str, Any],
    structured_payload: Any,
    ctx: PmPlannerContext,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    source_feat_ids = _normalize_source_feats(normalized_business, ctx)
    normalized_business["parent_epic"] = ctx.resolve_parent_epic(
        ctx.clean_text(normalized_business.get("parent_epic")),
        [item for item in source_feat_ids if isinstance(item, str)],
    )
    ensure_structural_governance_task(normalized_business, ctx)
    normalize_task_directory(normalized_business, source_feat_ids, ctx)
    enrich_delivery_plan_structure(normalized_business, ctx)
    normalized_structured = ctx.runner_cls._ensure_structured_envelope(
        business_output=normalized_business,
        structured_payload=structured_payload,
    )
    normalized_structured["ssot_output_contract"] = {
        "contract_version": "1.0",
        "run_id": ctx.workflow_id,
        "outputs": build_task_outputs(normalized_business, ctx),
    }
    return normalized_business, normalized_structured


def _normalize_source_feats(normalized_business: Dict[str, Any], ctx: PmPlannerContext) -> List[str]:
    source_feat_ids = normalized_business.get("source_feats") if isinstance(normalized_business.get("source_feats"), list) else []
    if not source_feat_ids and isinstance(normalized_business.get("task_specs"), list):
        source_feat_ids = [
            ctx.clean_text(item.get("source_feat"))
            for item in normalized_business.get("task_specs") or []
            if isinstance(item, dict) and ctx.clean_text(item.get("source_feat"))
        ]
    normalized_business["source_feats"] = [ctx.feat_alias_map.get(item, item) for item in source_feat_ids if item]
    return normalized_business.get("source_feats") if isinstance(normalized_business.get("source_feats"), list) else []


def ensure_structural_governance_task(normalized_business: Dict[str, Any], ctx: PmPlannerContext) -> None:
    task_specs = normalized_business.get("task_specs")
    source_feats = normalized_business.get("source_feats")
    if not isinstance(task_specs, list) or not task_specs or not isinstance(source_feats, list) or not source_feats:
        return
    primary_feat = ctx.clean_text(source_feats[0]) or "FEAT-001"
    structural_checks = [
        check for check in ctx.formal_acceptance_checks(primary_feat)
        if ctx.runner_cls._is_structural_acceptance_check(check)
    ]
    if not _requires_structural_governance_task(structural_checks, ctx):
        return
    if any(_task_is_structural(task_spec, ctx) for task_spec in task_specs if isinstance(task_spec, dict)):
        return
    governance_theme = _classify_structural_governance_theme(ctx.formal_feat_title(primary_feat), structural_checks, ctx)
    governance_task = _build_governance_task(primary_feat, structural_checks, governance_theme, ctx)
    if not governance_task:
        return
    task_specs.insert(0, governance_task)
    _inject_governance_dependencies(task_specs, governance_task, ctx)
    _inject_governance_metadata(normalized_business, governance_task, governance_theme)


def _requires_structural_governance_task(structural_checks: List[Dict[str, Any]], ctx: PmPlannerContext) -> bool:
    markers = ("rule-", "状态机", "链路", "路径", "旁路", "入口", "bypass", "stage order", "phase order", "schema", "template", "错误码", "优先级", "priority", "来源", "source", "cli_override")
    for check in structural_checks:
        if not isinstance(check, dict):
            continue
        text = " ".join(ctx.clean_text(check.get(key)) for key in ("scenario", "given", "when", "then", "raw_text"))
        if any(ctx.runner_cls._text_contains_keyword(text, marker) for marker in markers):
            return True
    return False


def _task_is_structural(task_spec: Dict[str, Any], ctx: PmPlannerContext) -> bool:
    workstream = ctx.clean_text(task_spec.get("workstream")).lower()
    task_kind = ctx.clean_text(task_spec.get("task_kind")).lower()
    if workstream in {"governance-spec", "governance-docs"} or task_kind in {"governance", "specification", "template"}:
        return True
    if task_kind == "implementation":
        return False
    combined = " ".join([ctx.clean_text(task_spec.get("title")), ctx.clean_text(task_spec.get("objective")), ctx.clean_text(task_spec.get("description"))])
    keywords = ("governance", "specification", "template", "schema", "contract", "错误码映射", "状态机", "规则定义", "规则集", "规范文档", "规范冻结")
    return any(ctx.runner_cls._text_contains_keyword(combined, keyword) for keyword in keywords)


def _classify_structural_governance_theme(feat_title: str, structural_checks: List[Dict[str, Any]], ctx: PmPlannerContext) -> Dict[str, str]:
    combined_text = " ".join(
        ctx.clean_text(item.get(key))
        for item in structural_checks
        if isinstance(item, dict)
        for key in ("scenario", "given", "when", "then", "raw_text")
    )
    combined_text = f"{feat_title} {combined_text}".strip()
    if any(ctx.runner_cls._text_contains_keyword(combined_text, marker) for marker in ("优先级", "priority", "来源", "source", "executor", "执行器", "cli_override", "config_file", "default")):
        return {"title": "执行器配置优先级与验证规则规范", "objective": "冻结执行器类型选择、优先级判定、来源追踪与错误处理边界，作为实现任务的前置规范基线", "description": "在正式实现前冻结执行器配置规范，覆盖执行器类型白名单、CLI/环境变量/配置文件/默认值的优先级规则、来源追踪字段和错误信息模板，避免结构性规则散落在实现代码中。", "responsible_role": "executor-config-governance-owner", "milestone_name": "配置规范冻结", "milestone_acceptance": "执行器类型、优先级规则和错误处理边界已冻结"}
    if any(ctx.runner_cls._text_contains_keyword(combined_text, marker) for marker in ("入口", "链路", "路径", "旁路", "bypass", "状态机")):
        return {"title": "执行入口链路规则与状态机规范", "objective": "冻结执行入口链路规则、状态机边界和错误处理约束，作为实现任务的前置规范基线", "description": "在正式实现前冻结执行入口规范，覆盖路径校验边界、状态转换约束、旁路阻断规则和错误码映射，避免结构性规则直接埋入实现代码。", "responsible_role": "workflow-governance-owner", "milestone_name": "规则规范冻结", "milestone_acceptance": "执行链路规则、状态机和错误码边界已冻结"}
    return {"title": f"{feat_title or '结构性规则'}规范冻结任务", "objective": "冻结结构性规则、约束边界和模板契约，作为实现任务的前置规范基线", "description": "在正式实现前冻结结构性规则，覆盖关键约束、契约边界、模板要求和错误处理基线，避免规范含义在实现过程中漂移。", "responsible_role": "governance-owner", "milestone_name": "规范冻结", "milestone_acceptance": "结构性规则和契约边界已冻结"}


def _build_governance_task(primary_feat: str, structural_checks: List[Dict[str, Any]], governance_theme: Dict[str, str], ctx: PmPlannerContext) -> Dict[str, Any]:
    mapped_checks = [
        {"feat": primary_feat, "ac": str(check.get("id")).strip(), "description": ctx.clean_text(check.get("then") or check.get("scenario") or check.get("raw_text"))}
        for check in structural_checks
        if isinstance(check, dict) and str(check.get("id") or "").strip()
    ]
    if not mapped_checks:
        return {}
    return {
        "task_id": f"TASK-{primary_feat}-000",
        "title": governance_theme["title"],
        "objective": governance_theme["objective"],
        "description": governance_theme["description"],
        "source_feat": primary_feat,
        "workstream": "governance-spec",
        "task_kind": "governance",
        "responsible_role": governance_theme["responsible_role"],
        "acceptance_criteria_mapping": mapped_checks,
        "prerequisites": [],
        "dependencies": [],
        "definition_of_done": ["结构性规则和契约边界文档已冻结", "规范任务已覆盖相关结构性 Acceptance Checks", "实现任务已明确引用该规范任务作为前置依赖"],
        "priority": "P0",
        "milestone": "M0-Governance-Baseline",
        "estimated_effort": "2 days",
        "lifecycle_status": "planned",
        "observability": {"execution_unit": "task", "log_scope": "task-execution", "audit_fields": ["run_id", "changed_files", "evidence_refs", "review_refs"]},
        "evidence_requirements": {"required_refs": [primary_feat], "review_required": True},
        "rollback_strategy": {"mode": "revert", "restore_targets": ["spec/tasks", "spec/contracts", "spec-global/departments/product/workflows"]},
        "source_refs": [f"{primary_feat}#delivery"] if ctx.runner_cls._is_literal_ssot_ref(primary_feat) else [],
        "ssot": {"identity_kind": "ssot", "ssot_type": "TASK", "parent": primary_feat, "derived_from": f"{primary_feat}#delivery"},
    }


def _inject_governance_dependencies(task_specs: List[Dict[str, Any]], governance_task: Dict[str, Any], ctx: PmPlannerContext) -> None:
    structural_task_id = governance_task["task_id"]
    for task_spec in task_specs[1:]:
        if not isinstance(task_spec, dict):
            continue
        dependencies = ctx.normalize_list(task_spec.get("dependencies"))
        if structural_task_id not in dependencies:
            dependencies.insert(0, structural_task_id)
        prerequisites = ctx.normalize_list(task_spec.get("prerequisites"))
        if governance_task["title"] not in prerequisites:
            prerequisites.insert(0, governance_task["title"])
        task_spec["dependencies"] = dependencies
        task_spec["prerequisites"] = prerequisites


def _inject_governance_metadata(normalized_business: Dict[str, Any], governance_task: Dict[str, Any], governance_theme: Dict[str, str]) -> None:
    milestones = normalized_business.get("milestones")
    if isinstance(milestones, list):
        milestones.insert(0, {"id": "M0-Governance-Baseline", "name": governance_theme["milestone_name"], "task_ids": [governance_task["task_id"]], "acceptance_criteria": governance_theme["milestone_acceptance"]})
    dependency_graph = normalized_business.get("dependency_graph")
    if isinstance(dependency_graph, dict) and isinstance(dependency_graph.get("critical_path"), list):
        dependency_graph["critical_path"].insert(0, governance_task["task_id"])
    resource_allocation = normalized_business.get("resource_allocation")
    if isinstance(resource_allocation, dict):
        role = governance_theme["responsible_role"]
        resource_allocation.setdefault(role, {"tasks": []})
        if governance_task["task_id"] not in resource_allocation[role]["tasks"]:
            resource_allocation[role]["tasks"].insert(0, governance_task["task_id"])


def normalize_task_directory(normalized_business: Dict[str, Any], source_feat_ids: List[str], ctx: PmPlannerContext) -> None:
    planning_metadata = normalized_business.get("planning_metadata")
    if not isinstance(planning_metadata, dict):
        return
    task_directory = ctx.clean_text(planning_metadata.get("task_directory"))
    primary_feat = next((ctx.clean_text(item) for item in source_feat_ids if isinstance(item, str) and ctx.clean_text(item)), "")
    if not primary_feat and isinstance(normalized_business.get("task_specs"), list):
        primary_feat = next((ctx.clean_text(item.get("source_feat")) for item in normalized_business.get("task_specs") or [] if isinstance(item, dict) and ctx.clean_text(item.get("source_feat"))), "")
    canonical_task_directory = f"spec/tasks/{primary_feat or 'FEAT-001'}"
    normalized_task_directory = task_directory.replace("\\", "/") if task_directory else ""
    if normalized_task_directory.startswith("spec/requirements/tasks/") or not task_directory or "<FEAT-ID>" in task_directory:
        task_directory = canonical_task_directory
    normalized_business["planning_metadata"] = {**planning_metadata, "task_directory": task_directory}


def enrich_delivery_plan_structure(normalized_business: Dict[str, Any], ctx: PmPlannerContext) -> None:
    task_specs = normalized_business.get("task_specs")
    if not isinstance(task_specs, list) or not task_specs:
        return
    task_index = {ctx.clean_text(task_spec.get("task_id")): task_spec for task_spec in task_specs if isinstance(task_spec, dict) and ctx.clean_text(task_spec.get("task_id"))}
    _normalize_task_links(task_specs, task_index, ctx)
    _build_dependency_matrix(normalized_business, task_specs, task_index, ctx)
    _enrich_risk_mitigation(normalized_business, ctx)


def _normalize_task_links(task_specs: List[Dict[str, Any]], task_index: Dict[str, Dict[str, Any]], ctx: PmPlannerContext) -> None:
    for task_spec in task_specs:
        if not isinstance(task_spec, dict):
            continue
        task_kind = ctx.clean_text(task_spec.get("task_kind")).lower()
        prerequisites = [item for item in ctx.normalize_list(task_spec.get("prerequisites")) if item in task_index]
        dependencies = [item for item in ctx.normalize_list(task_spec.get("dependencies")) if item in task_index]
        if task_kind == "validation" and not dependencies and prerequisites:
            dependencies = list(dict.fromkeys(prerequisites))
        if dependencies:
            task_spec["dependencies"] = list(dict.fromkeys(dependencies))
        if prerequisites:
            task_spec["prerequisites"] = list(dict.fromkeys(prerequisites))


def _build_dependency_matrix(normalized_business: Dict[str, Any], task_specs: List[Dict[str, Any]], task_index: Dict[str, Dict[str, Any]], ctx: PmPlannerContext) -> None:
    dependency_graph = normalized_business.get("dependency_graph") if isinstance(normalized_business.get("dependency_graph"), dict) else {}
    dependency_graph["dependency_matrix"] = [
        {"task_id": ctx.clean_text(task_spec.get("task_id")), "depends_on": [item for item in ctx.normalize_list(task_spec.get("dependencies")) if item in task_index]}
        for task_spec in task_specs
        if isinstance(task_spec, dict) and ctx.clean_text(task_spec.get("task_id"))
    ]
    if not isinstance(dependency_graph.get("critical_path"), list):
        dependency_graph["critical_path"] = [item.get("task_id") for item in dependency_graph["dependency_matrix"][:1] if isinstance(item, dict) and item.get("task_id")]
    normalized_business["dependency_graph"] = dependency_graph


def _enrich_risk_mitigation(normalized_business: Dict[str, Any], ctx: PmPlannerContext) -> None:
    risk_mitigation = normalized_business.get("risk_mitigation")
    if not isinstance(risk_mitigation, list):
        return
    for risk in risk_mitigation:
        if not isinstance(risk, dict):
            continue
        mitigation = ctx.clean_text(risk.get("mitigation"))
        if "直接磁盘读取" in mitigation and "审计一致性" not in mitigation:
            risk["mitigation"] = mitigation.rstrip("。") + "，并要求在降级模式下继续写入审计事件与路径链校验结果，保证审计一致性。"


def build_task_outputs(normalized_business: Dict[str, Any], ctx: PmPlannerContext) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    for index, task_spec in enumerate(normalized_business.get("task_specs") or [], start=1):
        if not isinstance(task_spec, dict):
            continue
        task_id = ctx.clean_text(task_spec.get("task_id")) or f"TASK-{index:03d}"
        title = ctx.clean_text(task_spec.get("title")) or task_id
        source_feat = ctx.clean_text(task_spec.get("source_feat")) or "FEAT-001"
        output_item = {
            "key": re.sub(r"[^a-z0-9_]+", "_", task_id.lower()).strip("_") or f"task_{index:03d}",
            "identity_kind": "ssot",
            "ssot_type": "task",
            "title": title,
            "parent": source_feat,
            "content": build_task_markdown(task_spec, ctx),
            "properties": {"feat_id": source_feat, "task_id": task_id, "slice_key": ctx.clean_text(task_spec.get("task_kind")) or "implementation", "workstream": ctx.clean_text(task_spec.get("workstream")) or "workflow-runtime"},
        }
        if ctx.runner_cls._is_literal_ssot_ref(source_feat):
            output_item["source_refs"] = [f"{source_feat}#delivery"]
            output_item["verifies"] = [source_feat]
        outputs.append(output_item)
    return outputs


def build_task_markdown(task_spec: Dict[str, Any], ctx: PmPlannerContext) -> str:
    lines = [f"# Objective\n\n{ctx.clean_text(task_spec.get('objective'))}\n", f"# Description\n\n{ctx.clean_text(task_spec.get('description'))}\n"]
    lines.extend(_format_acceptance_mapping(task_spec))
    lines.extend(_format_string_list_section("Prerequisites", task_spec.get("prerequisites"), ctx))
    lines.extend(_format_string_list_section("Dependencies", task_spec.get("dependencies"), ctx))
    lines.extend(_format_dict_section("Observability", task_spec.get("observability")))
    lines.extend(_format_dict_section("Evidence Requirements", task_spec.get("evidence_requirements")))
    lines.extend(_format_dict_section("Rollback Strategy", task_spec.get("rollback_strategy")))
    lines.extend(_format_string_list_section("Definition Of Done", task_spec.get("definition_of_done"), ctx))
    return "\n".join(lines).strip() + "\n"


def _format_acceptance_mapping(task_spec: Dict[str, Any]) -> List[str]:
    mapping = task_spec.get("acceptance_criteria_mapping")
    if not isinstance(mapping, list) or not mapping:
        return []
    lines = ["## Acceptance Mapping"]
    for item in mapping:
        if isinstance(item, dict):
            lines.append(f"- {item.get('feat', '')} / {item.get('ac', '')}: {item.get('description', '')}")
    lines.append("")
    return lines


def _format_string_list_section(heading: str, values: Any, ctx: PmPlannerContext) -> List[str]:
    if not isinstance(values, list) or not values:
        return []
    lines = [f"## {heading}"]
    for item in values:
        lines.append(f"- {ctx.clean_text(item)}")
    lines.append("")
    return lines


def _format_dict_section(heading: str, value: Any) -> List[str]:
    if not isinstance(value, dict) or not value:
        return []
    yaml_text = yaml.safe_dump(value, allow_unicode=True, sort_keys=False).strip()
    if not yaml_text:
        return []
    return [f"## {heading}", "```yaml", yaml_text, "```", ""]
