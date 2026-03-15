from __future__ import annotations

from typing import Any, Dict, List, Optional

from lee.orchestrator.execution.runners.base import StepRunnerBase

from .review_semantics_delivery import DeliveryPlanReviewSemantics


class ReviewSemanticValidator:
    @classmethod
    def expected_feat_review_subject_refs(
        cls,
        *,
        runner_cls,
        instance_data: Dict[str, Any],
    ) -> List[str]:
        step_outputs = instance_data.get("step_outputs", {}) if isinstance(instance_data, dict) else {}
        feat_spec_output = step_outputs.get("feat_spec_generation")
        if not isinstance(feat_spec_output, dict):
            return []

        materialized = cls._materialized_feat_ids(feat_spec_output.get("ssot_materialized"))
        if materialized:
            return materialized

        feat_payload = cls._feat_payload_from_spec_output(
            runner_cls=runner_cls,
            feat_spec_output=feat_spec_output,
        )
        if not isinstance(feat_payload, dict):
            return []

        bundle_specs = feat_payload.get("feat_specs")
        if isinstance(bundle_specs, list):
            feat_ids = [
                item.get("feat_id")
                for item in bundle_specs
                if isinstance(item, dict) and isinstance(item.get("feat_id"), str) and item.get("feat_id").strip()
            ]
            if feat_ids:
                return feat_ids

        feat_id = feat_payload.get("feat_id")
        return [feat_id] if isinstance(feat_id, str) and feat_id.strip() else []

    @staticmethod
    def validate_feat_review_subject_refs(
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        if not expected_subject_refs:
            return None
        if not isinstance(review_payload, dict):
            return "FEAT review output is not a structured object"
        subject_refs = review_payload.get("subject_refs")
        if not isinstance(subject_refs, list):
            return "FEAT review output missing subject_refs list"

        expected = {ref for ref in expected_subject_refs if isinstance(ref, str) and ref.strip()}
        actual = {ref for ref in subject_refs if isinstance(ref, str) and ref.strip()}
        if not expected.issubset(actual):
            return (
                "FEAT review subject_refs must include the reviewed FEAT ID(s): "
                + ", ".join(sorted(expected))
            )
        return None

    @classmethod
    def validate_feat_review_semantics(
        cls,
        *,
        runner_cls,
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        if not isinstance(review_payload, dict):
            return "FEAT review output is not a structured object"
        if review_payload.get("review_type") != "feat_review":
            return "FEAT review output must set review_type=feat_review"

        summary = review_payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            return "FEAT review output must include a non-empty summary"

        decision = review_payload.get("decision")
        if decision not in {"pass", "revise", "reject"}:
            return "FEAT review output decision must be one of: pass, revise, reject"

        field_error = cls._validate_review_string_arrays(review_payload, "FEAT review")
        if field_error:
            return field_error

        subject_refs = review_payload.get("subject_refs")
        if not isinstance(subject_refs, list):
            return "FEAT review output missing subject_refs list"
        expected = [ref for ref in expected_subject_refs if isinstance(ref, str) and ref.strip()]
        actual = [ref for ref in subject_refs if isinstance(ref, str) and ref.strip()]
        if expected and sorted(actual) != sorted(expected):
            return (
                "FEAT review subject_refs must exactly match the reviewed FEAT ID(s): "
                + ", ".join(sorted(expected))
            )

        findings = review_payload.get("findings") or []
        if decision == "pass":
            if findings and any(
                runner_cls._contains_feat_review_negative_signal(item)
                for item in findings
                if isinstance(item, str) and item.strip()
            ):
                return "FEAT review output with decision=pass must not include findings"
            if runner_cls._contains_feat_review_negative_signal(summary):
                return "FEAT review summary conflicts with decision=pass"
            return None
        if decision in {"revise", "reject"} and not findings:
            return f"FEAT review output with decision={decision} must include at least one finding"
        if decision == "revise":
            return "FEAT review requires revision before freeze"
        if decision == "reject":
            return "FEAT review rejected the generated FEAT bundle"
        return None

    @classmethod
    def expected_delivery_plan_subject_refs(
        cls,
        *,
        runner_cls,
        instance_data: Optional[Dict[str, Any]],
        business_output: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        return DeliveryPlanReviewSemantics.expected_subject_refs(
            runner_cls=runner_cls,
            instance_data=instance_data,
            business_output=business_output,
        )

    @staticmethod
    def validate_delivery_plan_review_subject_refs(
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        return DeliveryPlanReviewSemantics.validate_subject_refs(
            review_payload,
            expected_subject_refs,
        )

    @classmethod
    def load_task_plan_business_output(
        cls,
        *,
        runner_cls,
        instance_data: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        return DeliveryPlanReviewSemantics.load_task_plan_business_output(
            runner_cls=runner_cls,
            instance_data=instance_data,
        )

    @staticmethod
    def review_clean_text(value: Any) -> str:
        return DeliveryPlanReviewSemantics.review_clean_text(value)

    @classmethod
    def delivery_plan_has_persisted_tasks(
        cls,
        *,
        project_root: str,
        task_plan: Optional[Dict[str, Any]],
    ) -> bool:
        return DeliveryPlanReviewSemantics.has_persisted_tasks(
            project_root=project_root,
            task_plan=task_plan,
        )

    @classmethod
    def delivery_plan_has_structural_spec_coverage(
        cls,
        *,
        runner_cls,
        project_root: str,
        task_plan: Optional[Dict[str, Any]],
    ) -> bool:
        return DeliveryPlanReviewSemantics.has_structural_spec_coverage(
            runner_cls=runner_cls,
            project_root=project_root,
            task_plan=task_plan,
        )

    @classmethod
    def contains_delivery_plan_false_positive(cls, text: str) -> bool:
        return DeliveryPlanReviewSemantics.contains_false_positive(text)

    @classmethod
    def sanitize_delivery_plan_review_payload(
        cls,
        *,
        runner_cls,
        review_payload: Dict[str, Any],
        instance_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return DeliveryPlanReviewSemantics.sanitize_payload(
            runner_cls=runner_cls,
            review_payload=review_payload,
            instance_data=instance_data,
        )

    @classmethod
    def validate_delivery_plan_review_semantics(
        cls,
        *,
        runner_cls,
        project_root: str,
        review_payload: Any,
        instance_data: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        return DeliveryPlanReviewSemantics.validate_semantics(
            runner_cls=runner_cls,
            project_root=project_root,
            review_payload=review_payload,
            instance_data=instance_data,
        )

    @staticmethod
    def _materialized_feat_ids(ssot_materialized: Any) -> List[str]:
        if not isinstance(ssot_materialized, dict):
            return []
        feat_entry = ssot_materialized.get("feat")
        if isinstance(feat_entry, dict):
            feat_id = feat_entry.get("id")
            return [feat_id] if isinstance(feat_id, str) and feat_id.strip() else []
        if isinstance(feat_entry, list):
            return [
                item.get("id")
                for item in feat_entry
                if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("id").strip()
            ]
        return []

    @staticmethod
    def _feat_payload_from_spec_output(*, runner_cls, feat_spec_output: Dict[str, Any]) -> Any:
        feat_payload: Any = feat_spec_output.get("business_output")
        generated_text = feat_spec_output.get("generated_text", "")
        try:
            parsed_output = StepRunnerBase._parse_structured_output(generated_text)
        except Exception:
            parsed_output = None
        if isinstance(parsed_output, dict):
            nested = parsed_output.get("business_output")
            return nested if isinstance(nested, dict) else parsed_output
        if isinstance(feat_payload, dict):
            return feat_payload
        fallback_payload = runner_cls._parse_structured_output_if_possible(generated_text)
        if isinstance(fallback_payload, dict):
            nested = fallback_payload.get("business_output")
            return nested if isinstance(nested, dict) else fallback_payload
        return None

    @staticmethod
    def _validate_review_string_arrays(review_payload: Dict[str, Any], prefix: str) -> Optional[str]:
        for field_name in ("findings", "risks", "recommendations"):
            value = review_payload.get(field_name)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                return f"{prefix} output field '{field_name}' must be a string array"
        return None
