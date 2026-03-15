from __future__ import annotations

from typing import Any, Dict, Optional


class ProductReviewNormalizer:
    @staticmethod
    def normalize(
        *,
        runner_cls,
        step,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        normalized_business = dict(business_output)
        if (
            getattr(step, "agent_id", "") == "agent.product.feat_reviewer"
            and normalized_business.get("review_type") is None
        ):
            normalized_business["review_type"] = "feat_review"
            normalized_business.setdefault("summary", normalized_business.get("review_summary") or "")
            feat_reviews = normalized_business.get("feat_reviews")
            if isinstance(feat_reviews, list):
                normalized_business.setdefault(
                    "subject_refs",
                    [
                        str(item.get("feat_id")).strip()
                        for item in feat_reviews
                        if isinstance(item, dict) and str(item.get("feat_id") or "").strip()
                    ],
                )
                if "findings" not in normalized_business:
                    findings = [
                        str(item.get("notes")).strip()
                        for item in feat_reviews
                        if isinstance(item, dict)
                        and str(item.get("status") or "").strip().lower()
                        not in {"approved", "pass", "passed", "approved_with_notes", "approved_with_recommendations"}
                        and str(item.get("notes") or "").strip()
                    ]
                    normalized_business["findings"] = findings
                if not isinstance(normalized_business.get("recommendations"), list):
                    normalized_business["recommendations"] = []
                for item in feat_reviews:
                    if not isinstance(item, dict):
                        continue
                    item_status = str(item.get("status") or "").strip().lower()
                    note = str(item.get("notes") or "").strip()
                    if item_status in {"approved_with_notes", "approved_with_recommendations"} and note:
                        normalized_business["recommendations"].append(note)
            recommendations = normalized_business.get("recommendations")
            if not isinstance(recommendations, list):
                normalized_business["recommendations"] = []
            normalized_business.setdefault("risks", [])
            status_text = str(normalized_business.get("status") or "").strip().lower()
            if normalized_business.get("decision") not in {"pass", "revise", "reject"}:
                if status_text in {"approved", "approved_with_recommendations", "approved_with_notes"}:
                    normalized_business["decision"] = "pass"
                elif status_text in {"revise", "needs_revision", "changes_requested"}:
                    normalized_business["decision"] = "revise"
                elif status_text in {"rejected", "reject", "failed"}:
                    normalized_business["decision"] = "reject"
            if "findings" not in normalized_business:
                normalized_business["findings"] = []

        review_type = normalized_business.get("review_type")
        if review_type not in {"source_review", "epic_review", "feat_review", "delivery_plan_review"}:
            return business_output, structured_payload

        if review_type == "delivery_plan_review":
            expected_subject_refs = runner_cls._expected_delivery_plan_subject_refs(
                instance_data,
                normalized_business,
            )
            if expected_subject_refs and not normalized_business.get("subject_refs"):
                normalized_business["subject_refs"] = expected_subject_refs
        elif review_type == "feat_review":
            expected_subject_refs = runner_cls._expected_feat_review_subject_refs(
                instance_data or {},
            )
            actual_subject_refs = normalized_business.get("subject_refs")
            actual_subject_ref_set = {
                str(item).strip()
                for item in actual_subject_refs
                if isinstance(actual_subject_refs, list) and str(item).strip()
            }
            expected_subject_ref_set = {
                str(item).strip()
                for item in expected_subject_refs
                if isinstance(item, str) and item.strip()
            }
            if expected_subject_ref_set and not expected_subject_ref_set.issubset(actual_subject_ref_set):
                normalized_business["subject_refs"] = expected_subject_refs

        if normalized_business.get("decision") not in {"pass", "revise", "reject"}:
            candidate = (
                normalized_business.get("status")
                or normalized_business.get("review_status")
                or normalized_business.get("approval_decision")
            )
            decision_map = {
                "pass": "pass",
                "passed": "pass",
                "approved": "pass",
                "approve": "pass",
                "success": "pass",
                "ok": "pass",
                "revise": "revise",
                "revision_required": "revise",
                "needs_revision": "revise",
                "needs_revise": "revise",
                "changes_requested": "revise",
                "approved_with_recommendations": "pass",
                "approved_with_notes": "pass",
                "reject": "reject",
                "rejected": "reject",
                "fail": "reject",
                "failed": "reject",
            }
            normalized_candidate = str(candidate or "").strip().lower()
            normalized_decision = decision_map.get(normalized_candidate)
            if normalized_decision:
                normalized_business["decision"] = normalized_decision
        if not isinstance(normalized_business.get("summary"), str):
            normalized_business["summary"] = str(
                normalized_business.get("review_summary")
                or normalized_business.get("summary")
                or ""
            ).strip()
        for field_name in ("subject_refs", "findings", "risks", "recommendations"):
            value = normalized_business.get(field_name)
            if isinstance(value, list):
                normalized_business[field_name] = [str(item).strip() for item in value if str(item).strip()]
            elif field_name == "subject_refs":
                normalized_business[field_name] = []
            else:
                normalized_business[field_name] = []

        if review_type == "feat_review":
            normalized_business = runner_cls._sanitize_feat_review_payload(
                review_payload=normalized_business,
                instance_data=instance_data,
            )
        elif review_type == "delivery_plan_review":
            normalized_business = runner_cls._sanitize_delivery_plan_review_payload(
                review_payload=normalized_business,
                instance_data=instance_data,
            )

        normalized_structured = structured_payload
        if (
            isinstance(structured_payload, dict)
            and isinstance(structured_payload.get("business_output"), dict)
        ):
            normalized_structured = dict(structured_payload)
            normalized_structured["business_output"] = normalized_business

        return normalized_business, normalized_structured
