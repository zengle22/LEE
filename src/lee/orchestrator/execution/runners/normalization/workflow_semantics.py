from __future__ import annotations

import re
from typing import Any, List, Optional


class WorkflowSemanticValidator:
    @classmethod
    def validate_feat_bundle_epic_semantics(
        cls,
        *,
        runner_cls,
        project_root: str,
        business_output: Any,
    ) -> Optional[str]:
        if not isinstance(business_output, dict):
            return None
        epic_ref = business_output.get("epic_ref")
        feat_specs = business_output.get("feat_specs")
        if not isinstance(epic_ref, str) or not epic_ref.strip():
            return None
        if not isinstance(feat_specs, list) or not feat_specs:
            return None

        for feat_spec in feat_specs:
            field_error = cls._validate_feat_spec_inputs(feat_spec)
            if field_error:
                return field_error

        epic_markdown = runner_cls._load_ssot_markdown(project_root, epic_ref.strip())
        if not isinstance(epic_markdown, str) or not epic_markdown.strip():
            return None
        epic_families = runner_cls._extract_topic_families(epic_markdown)
        if not epic_families:
            return None

        feat_text = cls._collect_feat_fragments(feat_specs)
        feat_families = runner_cls._extract_topic_families(feat_text)
        if feat_families and epic_families.isdisjoint(feat_families):
            return (
                f"FEAT bundle semantics drift from {epic_ref}: "
                f"epic topic families={sorted(epic_families)}, "
                f"feat topic families={sorted(feat_families)}"
            )
        return None

    @classmethod
    def validate_pm_planner_task_semantics(
        cls,
        *,
        runner_cls,
        project_root: str,
        business_output: Any,
    ) -> Optional[str]:
        if not isinstance(business_output, dict):
            return None
        task_specs = business_output.get("task_specs")
        if not isinstance(task_specs, list) or not task_specs:
            return None

        source_feats = cls._resolve_source_feats(business_output, task_specs)
        if not source_feats:
            return None

        feat_markdowns = cls._load_source_feat_markdowns(
            runner_cls=runner_cls,
            project_root=project_root,
            source_feats=source_feats,
        )
        if not feat_markdowns:
            return None

        source_text = "\n".join(feat_markdowns)
        source_families = runner_cls._extract_topic_families(source_text)
        governance_scope = bool(source_families & {"governance"}) or any(
            runner_cls._text_contains_keyword(source_text, keyword)
            for keyword in (
                "workflow",
                "pipeline",
                "freeze",
                "gate",
                "registry",
                "run spec",
                "migration guide",
                "调用文档",
                "契约",
                "文档",
                "模板",
            )
        )
        if not governance_scope:
            return None

        task_text = cls._collect_task_fragments(task_specs)
        source_allows_ui = any(
            runner_cls._text_contains_keyword(source_text, keyword)
            for keyword in runner_cls.FEAT_UI_KEYWORDS
        )
        source_allows_tech = bool(
            re.search(r"trace hints:\s*[^\n]*\btech\b", source_text, re.IGNORECASE)
            or re.search(r"trace hints:\s*[^\n]*技术", source_text, re.IGNORECASE)
        )
        drift_hits = cls._collect_pm_drift_hits(
            runner_cls=runner_cls,
            task_text=task_text,
            source_text=source_text,
            source_allows_ui=source_allows_ui,
            source_allows_tech=source_allows_tech,
        )
        if drift_hits:
            return (
                "TASK bundle semantics drift from source FEAT scope: "
                f"unexpected topics={sorted(set(drift_hits))}, source_feats={source_feats}"
            )

        max_expected_tasks = max(len(source_feats) * 2, 8)
        if len(task_specs) > max_expected_tasks:
            return (
                "TASK bundle overscoped for workflow/governance FEATs: "
                f"task_count={len(task_specs)}, max_expected={max_expected_tasks}, source_feats={source_feats}"
            )
        return None

    @staticmethod
    def _is_placeholder_input_value(value: Any) -> bool:
        normalized = str(value or "").strip().lower()
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

    @classmethod
    def _validate_feat_spec_inputs(cls, feat_spec: Any) -> Optional[str]:
        if not isinstance(feat_spec, dict):
            return None
        feat_id = str(feat_spec.get("feat_id") or feat_spec.get("title") or "unknown").strip()
        inputs = feat_spec.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            return f"FEAT {feat_id} is missing concrete inputs"
        if any(cls._is_placeholder_input_value(item) for item in inputs):
            return f"FEAT {feat_id} uses placeholder inputs and cannot drive downstream design"

        input_contract = feat_spec.get("input_contract")
        if not isinstance(input_contract, dict):
            return f"FEAT {feat_id} is missing input_contract"
        required_artifacts = input_contract.get("required_artifacts")
        required_fields = input_contract.get("required_fields")
        consumption_rules = input_contract.get("consumption_rules")
        if not isinstance(required_artifacts, list) or not required_artifacts:
            return f"FEAT {feat_id} is missing input_contract.required_artifacts"
        if not isinstance(required_fields, list) or not required_fields:
            return f"FEAT {feat_id} is missing input_contract.required_fields"
        if any(cls._is_placeholder_input_value(item) for item in required_fields):
            return f"FEAT {feat_id} uses placeholder required_fields and cannot drive downstream design"
        if not isinstance(consumption_rules, list) or not consumption_rules:
            return f"FEAT {feat_id} is missing input_contract.consumption_rules"
        return None

    @staticmethod
    def _collect_feat_fragments(feat_specs: List[Any]) -> str:
        feat_fragments: List[str] = []
        for feat_spec in feat_specs:
            if not isinstance(feat_spec, dict):
                continue
            for key in ("title", "goal", "user_value"):
                value = feat_spec.get(key)
                if isinstance(value, str) and value.strip():
                    feat_fragments.append(value.strip())
            for key in ("inputs", "processing", "outputs", "acceptance_criteria", "dependencies", "non_goals"):
                value = feat_spec.get(key)
                if isinstance(value, list):
                    feat_fragments.extend(str(item).strip() for item in value if str(item).strip())
        return "\n".join(feat_fragments)

    @staticmethod
    def _resolve_source_feats(business_output: Any, task_specs: List[Any]) -> List[str]:
        source_feats = [
            str(item).strip()
            for item in (business_output.get("source_feats") or [])
            if isinstance(item, str) and str(item).strip()
        ]
        if source_feats:
            return source_feats
        return list(
            dict.fromkeys(
                str(item.get("source_feat")).strip()
                for item in task_specs
                if isinstance(item, dict) and isinstance(item.get("source_feat"), str) and item.get("source_feat").strip()
            )
        )

    @staticmethod
    def _load_source_feat_markdowns(*, runner_cls, project_root: str, source_feats: List[str]) -> List[str]:
        feat_markdowns: List[str] = []
        for feat_id in source_feats:
            markdown = runner_cls._load_ssot_markdown(project_root, feat_id)
            if isinstance(markdown, str) and markdown.strip():
                feat_markdowns.append(markdown)
        return feat_markdowns

    @staticmethod
    def _collect_task_fragments(task_specs: List[Any]) -> str:
        task_fragments: List[str] = []
        for task_spec in task_specs:
            if not isinstance(task_spec, dict):
                continue
            for key in (
                "task_id",
                "title",
                "objective",
                "description",
                "source_feat",
                "workstream",
                "task_kind",
                "responsible_role",
                "milestone",
                "estimated_effort",
            ):
                value = task_spec.get(key)
                if isinstance(value, str) and value.strip():
                    task_fragments.append(value.strip())
            for key in ("definition_of_done", "prerequisites", "dependencies"):
                value = task_spec.get(key)
                if isinstance(value, list):
                    task_fragments.extend(str(item).strip() for item in value if str(item).strip())
            for mapping in task_spec.get("acceptance_criteria_mapping") or []:
                if not isinstance(mapping, dict):
                    continue
                for key in ("feat", "ac", "description"):
                    value = mapping.get(key)
                    if isinstance(value, str) and value.strip():
                        task_fragments.append(value.strip())
            rollback_strategy = task_spec.get("rollback_strategy")
            if isinstance(rollback_strategy, dict):
                mode = rollback_strategy.get("mode")
                if isinstance(mode, str) and mode.strip():
                    task_fragments.append(mode.strip())
                restore_targets = rollback_strategy.get("restore_targets")
                if isinstance(restore_targets, list):
                    task_fragments.extend(str(item).strip() for item in restore_targets if str(item).strip())
        return "\n".join(task_fragments)

    @staticmethod
    def _collect_pm_drift_hits(
        *,
        runner_cls,
        task_text: str,
        source_text: str,
        source_allows_ui: bool,
        source_allows_tech: bool,
    ) -> List[str]:
        drift_hits: List[str] = []
        for family, keywords in runner_cls.PM_TASK_DRIFT_KEYWORDS.items():
            if family == "product_ui" and source_allows_ui:
                continue
            if family == "infra_storage" and source_allows_tech:
                continue
            for keyword in keywords:
                if runner_cls._text_contains_keyword(task_text, keyword) and not runner_cls._text_contains_keyword(source_text, keyword):
                    drift_hits.append(keyword)
        return drift_hits
