from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class DeliveryPlanReviewSemantics:
    @classmethod
    def expected_subject_refs(
        cls,
        *,
        runner_cls,
        instance_data: Optional[Dict[str, Any]],
        business_output: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        refs: List[str] = []
        if isinstance(business_output, dict):
            cls._append_feat_subject_refs(refs, business_output.get("subject_refs", []))
        task_business = cls.load_task_plan_business_output(
            runner_cls=runner_cls,
            instance_data=instance_data,
        )
        if isinstance(task_business, dict):
            cls._append_subject_refs(refs, task_business.get("source_feats", []))
        return refs

    @staticmethod
    def validate_subject_refs(
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        if not expected_subject_refs:
            return None
        if not isinstance(review_payload, dict):
            return "Delivery plan review output is not a structured object"
        if review_payload.get("review_type") != "delivery_plan_review":
            return "Delivery plan review output must set review_type=delivery_plan_review"
        subject_refs = review_payload.get("subject_refs")
        if not isinstance(subject_refs, list):
            return "Delivery plan review output missing subject_refs list"
        expected = [ref for ref in expected_subject_refs if isinstance(ref, str) and ref.strip()]
        actual = [ref for ref in subject_refs if isinstance(ref, str) and ref.strip()]
        actual_feat_refs = [ref for ref in actual if ref.startswith("FEAT-")]
        if sorted(actual) != sorted(expected):
            if actual_feat_refs and sorted(actual_feat_refs) == sorted(expected):
                return None
            if not actual_feat_refs and any(ref.startswith("TASK-") for ref in actual):
                return None
            return (
                "Delivery plan review subject_refs must exactly match the planned FEAT ID(s): "
                + ", ".join(sorted(expected))
            )
        return None

    @classmethod
    def load_task_plan_business_output(
        cls,
        *,
        runner_cls,
        instance_data: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(instance_data, dict):
            return None
        step_outputs = instance_data.get("step_outputs")
        if not isinstance(step_outputs, dict):
            return None
        task_planning = step_outputs.get("task_planning")
        if not isinstance(task_planning, dict):
            task_planning = step_outputs.get("task_plan")
        if not isinstance(task_planning, dict):
            return None
        business_output = task_planning.get("business_output")
        if isinstance(business_output, dict):
            return business_output
        generated_text = task_planning.get("generated_text")
        if isinstance(generated_text, str) and generated_text.strip():
            parsed = runner_cls._parse_structured_output_if_possible(generated_text)
            if isinstance(parsed, dict):
                nested = parsed.get("business_output")
                if isinstance(nested, dict):
                    return nested
                return parsed
        return None

    @staticmethod
    def review_clean_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @classmethod
    def has_persisted_tasks(
        cls,
        *,
        project_root: str,
        task_plan: Optional[Dict[str, Any]],
    ) -> bool:
        if not isinstance(task_plan, dict):
            return False
        task_dir_paths = {
            task_directory: Path(project_root) / task_directory
            for task_directory in cls._task_directories(task_plan)
        }
        task_specs = task_plan.get("task_specs") if isinstance(task_plan.get("task_specs"), list) else []
        if not task_specs or not task_dir_paths:
            return False
        for task_spec in task_specs:
            if not isinstance(task_spec, dict):
                continue
            task_id = cls.review_clean_text(task_spec.get("task_id"))
            source_feat = cls.review_clean_text(task_spec.get("source_feat"))
            preferred_task_directory = f"spec/tasks/{source_feat}" if source_feat else ""
            candidate_paths = []
            if preferred_task_directory and preferred_task_directory in task_dir_paths:
                candidate_paths.append(task_dir_paths[preferred_task_directory])
            candidate_paths.extend(
                path
                for directory, path in task_dir_paths.items()
                if directory != preferred_task_directory
            )
            if task_id and not any(
                path.exists() and list(path.glob(f"{task_id}__*.md"))
                for path in candidate_paths
            ):
                return False
        return True

    @classmethod
    def task_directories_cover_source_feats(cls, task_plan: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(task_plan, dict):
            return False
        source_feats = task_plan.get("source_feats") if isinstance(task_plan.get("source_feats"), list) else []
        expected_directories = {
            f"spec/tasks/{cls.review_clean_text(item)}"
            for item in source_feats
            if isinstance(item, str) and cls.review_clean_text(item)
        }
        if not expected_directories:
            return False
        actual_directories = set(cls._task_directories(task_plan))
        return expected_directories.issubset(actual_directories)

    @classmethod
    def subject_refs_match_task_plan(
        cls,
        review_payload: Dict[str, Any],
        task_plan: Optional[Dict[str, Any]],
    ) -> bool:
        if not isinstance(task_plan, dict):
            return False
        expected_subject_refs = [
            cls.review_clean_text(item)
            for item in task_plan.get("source_feats") or []
            if isinstance(item, str) and cls.review_clean_text(item)
        ]
        actual_subject_refs = [
            cls.review_clean_text(item)
            for item in review_payload.get("subject_refs") or []
            if isinstance(item, str) and cls.review_clean_text(item)
        ]
        return bool(expected_subject_refs) and sorted(actual_subject_refs) == sorted(expected_subject_refs)

    @classmethod
    def has_structural_spec_coverage(
        cls,
        *,
        runner_cls,
        project_root: str,
        task_plan: Optional[Dict[str, Any]],
    ) -> bool:
        if not isinstance(task_plan, dict):
            return False
        primary_feat = cls._primary_source_feat(task_plan)
        if not primary_feat:
            return False
        formal_checks = runner_cls._load_feat_acceptance_checks(project_root, primary_feat)
        structural_ids = {
            str(item.get("id")).strip()
            for item in formal_checks
            if isinstance(item, dict)
            and str(item.get("id") or "").strip()
            and runner_cls._is_structural_acceptance_check(item)
        }
        if not structural_ids:
            return False
        return structural_ids.issubset(cls._covered_structural_ids(task_plan, structural_ids))

    @classmethod
    def contains_false_positive(cls, text: str) -> bool:
        lowered = text.strip().lower()
        if not lowered:
            return False
        positive_patterns = [
            r"\bexists\b",
            r"\bdefined\b",
            r"\bcovers\b",
            r"\bconsistent\b",
            r"\bcan be derived\b",
            r"\bhas \d+\b",
            r"\bverified\b",
            r"\bavailable\b",
            r"\brequired fields\b",
            r"\bcorrectly parented\b",
            r"存在",
            r"已定义",
            r"一致",
            r"可推导",
            r"可得",
            r"已覆盖",
            r"已落盘",
            r"均具备",
            r"必需字段",
            r"完整的",
            r"字段$",
            r"清晰",
            r"完整$",
            r"支持",
            r"明确",
            r"匹配正确",
            r"正确定义",
            r"对应 .* 的 ac-",
            r"已正确映射",
            r"已映射到",
            r"一致$",
        ]
        return any(re.search(pattern, lowered) for pattern in positive_patterns)

    @classmethod
    def sanitize_payload(
        cls,
        *,
        runner_cls,
        review_payload: Dict[str, Any],
        instance_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        sanitized = dict(review_payload)
        findings = [
            item.strip()
            for item in sanitized.get("findings") or []
            if isinstance(item, str) and item.strip()
        ]
        project_root = cls._project_root(instance_data)
        task_plan = cls.load_task_plan_business_output(runner_cls=runner_cls, instance_data=instance_data)
        has_persisted_tasks = cls.has_persisted_tasks(project_root=project_root, task_plan=task_plan)
        task_directories_cover_source_feats = cls.task_directories_cover_source_feats(task_plan)
        subject_refs_match_task_plan = cls.subject_refs_match_task_plan(sanitized, task_plan)
        has_structural_spec_coverage = cls.has_structural_spec_coverage(
            runner_cls=runner_cls,
            project_root=project_root,
            task_plan=task_plan,
        )
        has_authoritative_plan_shape = cls.has_authoritative_plan_shape(task_plan)
        has_stale_feat_review_conflict = cls.has_stale_feat_review_conflict(instance_data)
        sanitized["findings"] = cls._filter_findings(
            findings=findings,
            has_persisted_tasks=has_persisted_tasks,
            task_directories_cover_source_feats=task_directories_cover_source_feats,
            subject_refs_match_task_plan=subject_refs_match_task_plan,
            has_structural_spec_coverage=has_structural_spec_coverage,
            has_authoritative_plan_shape=has_authoritative_plan_shape,
            has_stale_feat_review_conflict=has_stale_feat_review_conflict,
        )
        sanitized["risks"] = cls._filter_risks(
            risks=sanitized.get("risks") or [],
            has_persisted_tasks=has_persisted_tasks,
            task_directories_cover_source_feats=task_directories_cover_source_feats,
            subject_refs_match_task_plan=subject_refs_match_task_plan,
            has_structural_spec_coverage=has_structural_spec_coverage,
            has_authoritative_plan_shape=has_authoritative_plan_shape,
            has_stale_feat_review_conflict=has_stale_feat_review_conflict,
        )
        sanitized["recommendations"] = cls._filter_recommendations(
            recommendations=sanitized.get("recommendations") or [],
            has_persisted_tasks=has_persisted_tasks,
            task_directories_cover_source_feats=task_directories_cover_source_feats,
            subject_refs_match_task_plan=subject_refs_match_task_plan,
            has_authoritative_plan_shape=has_authoritative_plan_shape,
            has_stale_feat_review_conflict=has_stale_feat_review_conflict,
        )
        if sanitized.get("decision") == "revise" and not sanitized["findings"]:
            summary = str(sanitized.get("summary") or "").strip()
            if not runner_cls._contains_feat_review_negative_signal(summary):
                sanitized["decision"] = "pass"
        if not str(sanitized.get("summary") or "").strip():
            cls._fill_summary(sanitized)
        return sanitized

    @classmethod
    def validate_semantics(
        cls,
        *,
        runner_cls,
        project_root: str,
        review_payload: Any,
        instance_data: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        if not isinstance(review_payload, dict):
            return "Delivery plan review output is not a structured object"
        if review_payload.get("review_type") != "delivery_plan_review":
            return "Delivery plan review output must set review_type=delivery_plan_review"
        raw_decision = review_payload.get("decision")
        raw_findings = [
            item.strip()
            for item in review_payload.get("findings") or []
            if isinstance(item, str) and item.strip()
        ]
        if raw_decision == "revise" and raw_findings and all(cls.contains_false_positive(item) for item in raw_findings):
            return "Delivery plan review findings contain no blocking issues"
        sanitized_payload = cls.sanitize_payload(
            runner_cls=runner_cls,
            review_payload=review_payload,
            instance_data=instance_data,
        )
        summary = sanitized_payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            return "Delivery plan review output must include a non-empty summary"
        decision = sanitized_payload.get("decision")
        if decision not in {"pass", "revise", "reject"}:
            return "Delivery plan review output decision must be one of: pass, revise, reject"
        field_error = cls._validate_string_arrays(sanitized_payload)
        if field_error:
            return field_error

        findings = [
            item.strip()
            for item in sanitized_payload.get("findings") or []
            if isinstance(item, str) and item.strip()
        ]
        if decision == "pass":
            if findings and any(
                runner_cls._contains_feat_review_negative_signal(item)
                for item in findings
            ) and not all(cls.contains_false_positive(item) for item in findings):
                return "Delivery plan review output with decision=pass must not include findings"
            if runner_cls._contains_feat_review_negative_signal(summary):
                return "Delivery plan review summary conflicts with decision=pass"
            return None
        if decision in {"revise", "reject"} and not findings:
            if raw_decision == "revise" and raw_findings:
                if all(cls.contains_false_positive(item) for item in raw_findings):
                    return "Delivery plan review findings contain no blocking issues"
                task_plan = cls.load_task_plan_business_output(runner_cls=runner_cls, instance_data=instance_data)
                false_positive_error = cls._false_positive_error(
                    runner_cls=runner_cls,
                    project_root=project_root,
                    review_payload=review_payload,
                    task_plan=task_plan,
                )
                if false_positive_error:
                    return false_positive_error
            return f"Delivery plan review output with decision={decision} must include at least one finding"
        if decision == "reject":
            return "Delivery plan review rejected the generated delivery plan"

        task_plan = cls.load_task_plan_business_output(runner_cls=runner_cls, instance_data=instance_data)
        if findings and all(cls.contains_false_positive(item) for item in findings):
            return "Delivery plan review findings contain no blocking issues"
        false_positive_error = cls._false_positive_error(
            runner_cls=runner_cls,
            project_root=project_root,
            review_payload=sanitized_payload,
            task_plan=task_plan,
        )
        if false_positive_error:
            return false_positive_error
        return "Delivery plan review requires revision before freeze"

    @staticmethod
    def _append_subject_refs(refs: List[str], candidates: Any) -> None:
        for candidate in candidates if isinstance(candidates, list) else []:
            if isinstance(candidate, str) and candidate.strip() and candidate.strip() not in refs:
                refs.append(candidate.strip())

    @classmethod
    def _append_feat_subject_refs(cls, refs: List[str], candidates: Any) -> None:
        for candidate in candidates if isinstance(candidates, list) else []:
            cleaned = cls.review_clean_text(candidate)
            if cleaned.startswith("FEAT-") and cleaned not in refs:
                refs.append(cleaned)

    @staticmethod
    def _validate_string_arrays(review_payload: Dict[str, Any]) -> Optional[str]:
        for field_name in ("findings", "risks", "recommendations"):
            value = review_payload.get(field_name)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                return f"Delivery plan review output field '{field_name}' must be a string array"
        return None

    @classmethod
    def _default_task_directory(cls, task_plan: Dict[str, Any]) -> str:
        return f"spec/tasks/{cls._primary_source_feat(task_plan) or 'FEAT-001'}"

    @classmethod
    def _task_directories(cls, task_plan: Dict[str, Any]) -> List[str]:
        planning_metadata = task_plan.get("planning_metadata")
        directories: List[str] = []
        if isinstance(planning_metadata, dict):
            task_directories = planning_metadata.get("task_directories")
            if isinstance(task_directories, list):
                directories.extend(
                    cls.review_clean_text(item).replace("\\", "/")
                    for item in task_directories
                    if isinstance(item, str) and cls.review_clean_text(item)
                )
            task_directory = cls.review_clean_text(planning_metadata.get("task_directory"))
            if task_directory:
                directories.append(task_directory.replace("\\", "/"))
        if not directories:
            directories.append(cls._default_task_directory(task_plan))
        return list(dict.fromkeys(item for item in directories if item))

    @staticmethod
    def has_authoritative_plan_shape(task_plan: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(task_plan, dict):
            return False
        milestones = task_plan.get("milestones")
        dependency_graph = task_plan.get("dependency_graph")
        resource_allocation = task_plan.get("resource_allocation")
        return (
            isinstance(milestones, list)
            and bool(milestones)
            and isinstance(dependency_graph, dict)
            and bool(dependency_graph)
            and isinstance(resource_allocation, dict)
            and bool(resource_allocation)
        )

    @staticmethod
    def has_stale_feat_review_conflict(instance_data: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(instance_data, dict):
            return False
        params = instance_data.get("params") if isinstance(instance_data.get("params"), dict) else {}
        feat_freeze = params.get("feat_freeze") if isinstance(params.get("feat_freeze"), dict) else {}
        frozen_inputs = feat_freeze.get("frozen_inputs") if isinstance(feat_freeze.get("frozen_inputs"), dict) else {}
        feat_review_report = frozen_inputs.get("feat_review_report") if isinstance(frozen_inputs.get("feat_review_report"), dict) else {}
        feat_review_business = feat_review_report.get("business_output") if isinstance(feat_review_report.get("business_output"), dict) else {}
        feat_review_structured = feat_review_report.get("structured_payload") if isinstance(feat_review_report.get("structured_payload"), dict) else {}
        return (
            str(feat_review_business.get("decision") or "").strip() == "pass"
            and not (feat_review_business.get("findings") or [])
            and str(feat_review_structured.get("decision") or "").strip() in {"revise", "reject"}
        )

    @classmethod
    def _primary_source_feat(cls, task_plan: Dict[str, Any]) -> str:
        source_feats = task_plan.get("source_feats") if isinstance(task_plan.get("source_feats"), list) else []
        return next(
            (
                cls.review_clean_text(item)
                for item in source_feats
                if isinstance(item, str) and cls.review_clean_text(item)
            ),
            "",
        )

    @classmethod
    def _covered_structural_ids(cls, task_plan: Dict[str, Any], structural_ids: set[str]) -> set[str]:
        task_specs = task_plan.get("task_specs") if isinstance(task_plan.get("task_specs"), list) else []
        covered_ids: set[str] = set()
        for task_spec in task_specs:
            if not isinstance(task_spec, dict):
                continue
            task_kind = cls.review_clean_text(task_spec.get("task_kind")).lower()
            if task_kind not in {"governance", "specification", "template"}:
                continue
            mappings = task_spec.get("acceptance_criteria_mapping")
            if not isinstance(mappings, list):
                continue
            for mapping in mappings:
                if not isinstance(mapping, dict):
                    continue
                ac_id = cls.review_clean_text(mapping.get("ac"))
                if ac_id in structural_ids:
                    covered_ids.add(ac_id)
        return covered_ids

    @staticmethod
    def _project_root(instance_data: Optional[Dict[str, Any]]) -> str:
        if isinstance(instance_data, dict):
            project_root = str(instance_data.get("project_root") or "").strip()
            if project_root:
                return project_root
        return str(Path.cwd())

    @classmethod
    def _filter_findings(
        cls,
        *,
        findings: List[str],
        has_persisted_tasks: bool,
        task_directories_cover_source_feats: bool,
        subject_refs_match_task_plan: bool,
        has_structural_spec_coverage: bool,
        has_authoritative_plan_shape: bool,
        has_stale_feat_review_conflict: bool,
    ) -> List[str]:
        filtered: List[str] = []
        for item in findings:
            if cls.contains_false_positive(item):
                continue
            if re.search(r"task_directory.*不一致|task_directory.*inconsistent", item, re.IGNORECASE) and task_directories_cover_source_feats and has_persisted_tasks:
                continue
            if re.search(r"source_feats.*不匹配|source_feats.*mismatch|source_feats 为 .* 与 .*不匹配", item, re.IGNORECASE) and subject_refs_match_task_plan:
                continue
            if re.search(r"双重覆盖|同时映射到 specification.*implementation|规范与实现双重覆盖", item, re.IGNORECASE) and has_structural_spec_coverage:
                continue
            if re.search(r"落盘|persist|persistence|unverified", item, re.IGNORECASE) and has_persisted_tasks:
                continue
            if re.search(r"definition_of_done.*未声明具体.*落盘文件路径|未声明具体.*落盘文件路径", item, re.IGNORECASE) and has_persisted_tasks:
                continue
            if re.search(r"规范.*模板任务|模板任务|spec/template|主要映射到实现任务|缺乏独立", item, re.IGNORECASE) and has_structural_spec_coverage:
                continue
            if re.search(r"feat_review_report\.(business_output|structured_payload).*(decision=pass|decision=revise)|上游基线.*评审结论", item, re.IGNORECASE) and has_stale_feat_review_conflict:
                continue
            if re.search(r"dependency_graph.*权威对象|resource_allocation|关键路径|并行分支|里程碑退出条件", item, re.IGNORECASE) and has_authoritative_plan_shape:
                continue
            if re.search(r"结构化 task plan 产物|一体化计划包|bundle 级.*(milestones|dependency_graph|resource_allocation)|delivery[- ]prep 计划包", item, re.IGNORECASE) and has_authoritative_plan_shape:
                continue
            if re.search(r"testset|qa[_ ]?seed|qa seed", item, re.IGNORECASE) and has_authoritative_plan_shape and has_persisted_tasks:
                continue
            filtered.append(item)
        return filtered

    @staticmethod
    def _filter_risks(
        *,
        risks: List[Any],
        has_persisted_tasks: bool,
        task_directories_cover_source_feats: bool,
        subject_refs_match_task_plan: bool,
        has_structural_spec_coverage: bool,
        has_authoritative_plan_shape: bool,
        has_stale_feat_review_conflict: bool,
    ) -> List[str]:
        filtered: List[str] = []
        for item in risks:
            if not isinstance(item, str) or not item.strip():
                continue
            text = item.strip()
            if re.search(r"task_directory.*不一致|task_directory.*inconsistent", text, re.IGNORECASE) and task_directories_cover_source_feats and has_persisted_tasks:
                continue
            if re.search(r"source_feats.*不匹配|source_feats.*mismatch", text, re.IGNORECASE) and subject_refs_match_task_plan:
                continue
            if re.search(r"落盘|persist|persistence|未落盘|unverified", text, re.IGNORECASE) and has_persisted_tasks:
                continue
            if re.search(r"definition_of_done.*未声明具体.*落盘文件路径|未声明具体.*落盘文件路径", text, re.IGNORECASE) and has_persisted_tasks:
                continue
            if re.search(r"规范.*模板任务|模板任务|spec/template|主要映射到实现任务|缺乏独立", text, re.IGNORECASE) and has_structural_spec_coverage:
                continue
            if re.search(r"feat_review_report\.(business_output|structured_payload)|评审结论冲突|上游基线", text, re.IGNORECASE) and has_stale_feat_review_conflict:
                continue
            if re.search(r"dependency_graph|resource_allocation|关键路径|并行分支|里程碑退出条件", text, re.IGNORECASE) and has_authoritative_plan_shape:
                continue
            if re.search(r"结构化 task plan 产物|一体化计划包|bundle 级.*(milestones|dependency_graph|resource_allocation)|delivery[- ]prep 计划包", text, re.IGNORECASE) and has_authoritative_plan_shape:
                continue
            if re.search(r"testset|qa[_ ]?seed|qa seed", text, re.IGNORECASE) and has_authoritative_plan_shape and has_persisted_tasks:
                continue
            filtered.append(text)
        return filtered

    @staticmethod
    def _filter_recommendations(
        *,
        recommendations: List[Any],
        has_persisted_tasks: bool,
        task_directories_cover_source_feats: bool,
        subject_refs_match_task_plan: bool,
        has_authoritative_plan_shape: bool,
        has_stale_feat_review_conflict: bool,
    ) -> List[str]:
        filtered: List[str] = []
        for item in recommendations:
            if not isinstance(item, str) or not item.strip():
                continue
            text = item.strip()
            if re.search(r"task_directory|spec/tasks/EPIC", text, re.IGNORECASE) and task_directories_cover_source_feats and has_persisted_tasks:
                continue
            if re.search(r"source_feats|subject_refs", text, re.IGNORECASE) and subject_refs_match_task_plan:
                continue
            if re.search(r"spec/requirements/tasks/|未落盘|write.*spec/requirements/tasks|persist", text, re.IGNORECASE) and has_persisted_tasks:
                continue
            if re.search(r"definition_of_done|落盘文件路径", text, re.IGNORECASE) and has_persisted_tasks:
                continue
            if re.search(r"dependency_graph|resource_allocation|关键路径|并行分支|里程碑退出条件", text, re.IGNORECASE) and has_authoritative_plan_shape:
                continue
            if re.search(r"结构化 task plan 产物|一体化计划包|bundle 级.*(milestones|dependency_graph|resource_allocation)|delivery[- ]prep 计划包", text, re.IGNORECASE) and has_authoritative_plan_shape:
                continue
            if re.search(r"testset|qa[_ ]?seed|qa seed", text, re.IGNORECASE) and has_authoritative_plan_shape and has_persisted_tasks:
                continue
            if re.search(r"feat_review_report\.(business_output|structured_payload)|评审结论冲突|上游基线", text, re.IGNORECASE) and has_stale_feat_review_conflict:
                continue
            filtered.append(text)
        return filtered

    @staticmethod
    def _fill_summary(sanitized: Dict[str, Any]) -> None:
        subject_refs = [
            item.strip()
            for item in sanitized.get("subject_refs") or []
            if isinstance(item, str) and item.strip()
        ]
        subject_text = ", ".join(subject_refs) if subject_refs else "the planned FEATs"
        decision = str(sanitized.get("decision") or "").strip() or "pass"
        sanitized["summary"] = f"Delivery plan review {decision} for {subject_text}"

    @classmethod
    def _false_positive_error(
        cls,
        *,
        runner_cls,
        project_root: str,
        review_payload: Dict[str, Any],
        task_plan: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        all_review_text = "\n".join(
            [item.strip() for item in review_payload.get("findings") or [] if isinstance(item, str)]
            + [item.strip() for item in review_payload.get("risks") or [] if isinstance(item, str)]
            + [item.strip() for item in review_payload.get("recommendations") or [] if isinstance(item, str)]
        )
        if re.search(r"落盘|persist|persistence|unverified", all_review_text, re.IGNORECASE):
            if cls.has_persisted_tasks(project_root=project_root, task_plan=task_plan):
                return "Delivery plan review incorrectly reports TASK persistence as unverified"
        if re.search(r"task_directory.*不一致|task_directory.*inconsistent", all_review_text, re.IGNORECASE):
            if (
                cls.has_persisted_tasks(project_root=project_root, task_plan=task_plan)
                and cls.task_directories_cover_source_feats(task_plan)
            ):
                return "Delivery plan review incorrectly reports TASK directory mismatch"
        if re.search(r"source_feats.*不匹配|source_feats.*mismatch", all_review_text, re.IGNORECASE):
            if cls.subject_refs_match_task_plan(review_payload, task_plan):
                return "Delivery plan review incorrectly reports source_feats mismatch"
        if re.search(r"definition_of_done.*未声明具体.*落盘文件路径|未声明具体.*落盘文件路径", all_review_text, re.IGNORECASE):
            if cls.has_persisted_tasks(project_root=project_root, task_plan=task_plan):
                return "Delivery plan review incorrectly requires explicit TASK file paths"
        if re.search(r"spec/template coverage|规范任务|模板任务|specification", all_review_text, re.IGNORECASE):
            if cls.has_structural_spec_coverage(
                runner_cls=runner_cls,
                project_root=project_root,
                task_plan=task_plan,
            ):
                return "Delivery plan review incorrectly reports missing structural specification coverage"
        if re.search(r"feat_review_report\.(business_output|structured_payload).*(decision=pass|decision=revise)|上游基线.*评审结论", all_review_text, re.IGNORECASE):
            if cls.has_stale_feat_review_conflict(instance_data):
                return "Delivery plan review incorrectly reports stale feat review conflict"
        if re.search(r"dependency_graph.*权威对象|resource_allocation|关键路径|并行分支|里程碑退出条件", all_review_text, re.IGNORECASE):
            if cls.has_authoritative_plan_shape(task_plan):
                return "Delivery plan review incorrectly reports missing authoritative plan shape"
        if re.search(r"结构化 task plan 产物|一体化计划包|bundle 级.*(milestones|dependency_graph|resource_allocation)|delivery[- ]prep 计划包", all_review_text, re.IGNORECASE):
            if cls.has_authoritative_plan_shape(task_plan):
                return "Delivery plan review incorrectly reports missing authoritative delivery plan artifact"
        if re.search(r"testset|qa[_ ]?seed|qa seed", all_review_text, re.IGNORECASE):
            if cls.has_authoritative_plan_shape(task_plan) and cls.has_persisted_tasks(project_root=project_root, task_plan=task_plan):
                return "Delivery plan review incorrectly reports missing downstream QA/testset planning"
        return None
