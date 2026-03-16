from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .prd_writer_feat_common import (
    clean_text,
    extract_breakdown_feature_candidates,
    synthesize_feat_spec,
)
from .prd_writer_feat_contracts import (
    build_contract_outputs,
    normalize_existing_contract_outputs,
    remap_canonical_feat_ids,
    rewrite_specs_for_actual_epic_ref,
)
from .prd_writer_feat_item import normalize_feat_item


class PrdWriterFeatNormalizer:
    @staticmethod
    def normalize(
        *,
        runner_cls,
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if getattr(step, "agent_id", "") != "agent.product.prd_writer":
            return business_output, structured_payload
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        actual_epic_ref = runner_cls._resolve_epic_ref_from_instance_data(instance_data)
        expects_bundle = _expects_bundle(step)
        normalized_business = _normalize_business_output(
            business_output=business_output,
            structured_payload=structured_payload,
            actual_epic_ref=actual_epic_ref,
            expects_bundle=expects_bundle,
        )
        if actual_epic_ref and isinstance(normalized_business.get("feat_specs"), list):
            normalized_business["epic_ref"] = actual_epic_ref
            normalized_business["feat_specs"] = rewrite_specs_for_actual_epic_ref(
                feat_specs=normalized_business["feat_specs"],
                actual_epic_ref=actual_epic_ref,
            )

        feat_specs = normalized_business.get("feat_specs") if isinstance(normalized_business.get("feat_specs"), list) else []
        if feat_specs:
            project_root = _resolve_project_root(instance_data)
            normalized_business["feat_specs"] = remap_canonical_feat_ids(
                feat_specs=feat_specs,
                project_root=project_root,
            )

        normalized_structured = runner_cls._ensure_structured_envelope(
            business_output=normalized_business,
            structured_payload=structured_payload,
        )
        normalized_structured["ssot_output_contract"] = _normalize_ssot_output_contract(
            runner_cls=runner_cls,
            workflow_id=workflow_id,
            normalized_business=normalized_business,
            normalized_structured=normalized_structured,
            actual_epic_ref=actual_epic_ref,
        )
        return normalized_business, normalized_structured


def _expects_bundle(step) -> bool:
    step_config = getattr(step, "config", {}) or {}
    output_contract = str(step_config.get("output_contract") or "").replace("\\", "/")
    return output_contract.endswith("feat-bundle-contract/v1/schema.json") or (
        not output_contract and getattr(step, "id", "") == "feat_spec_generation"
    )


def _normalize_business_output(
    *,
    business_output: Dict[str, Any],
    structured_payload: Any,
    actual_epic_ref: Optional[str],
    expects_bundle: bool,
) -> Dict[str, Any]:
    normalized_business = dict(business_output)
    bundle_specs = normalized_business.get("feat_specs")
    if isinstance(bundle_specs, list):
        structured_business = (
            structured_payload.get("business_output")
            if isinstance(structured_payload, dict)
            and isinstance(structured_payload.get("business_output"), dict)
            else {}
        )
        normalized = {
            "epic_ref": normalized_business.get("epic_ref"),
            "feat_specs": [
                normalize_feat_item(feat_item=item, actual_epic_ref=actual_epic_ref)
                for item in bundle_specs
            ],
        }
        if normalized["epic_ref"] is None and structured_business.get("epic_ref"):
            normalized["epic_ref"] = structured_business["epic_ref"]
        return normalized

    candidate_specs, candidate_epic_ref = extract_breakdown_feature_candidates(
        normalized_business,
        actual_epic_ref or clean_text(normalized_business.get("epic_ref")) or None,
    )
    if isinstance(candidate_specs, list) and candidate_specs:
        feat_specs = [
            normalize_feat_item(
                feat_item=synthesize_feat_spec(item, candidate_epic_ref),
                actual_epic_ref=actual_epic_ref,
            )
            for item in candidate_specs
            if isinstance(item, dict)
        ]
        if feat_specs:
            return {
                "epic_ref": candidate_epic_ref,
                "feat_specs": feat_specs,
            }

    normalized_single = normalize_feat_item(
        feat_item=normalized_business,
        actual_epic_ref=actual_epic_ref,
    )
    if expects_bundle:
        return {
            "epic_ref": actual_epic_ref or clean_text(normalized_single.get("epic_ref")) or None,
            "feat_specs": [normalized_single],
        }
    return normalized_single


def _resolve_project_root(instance_data: Optional[Dict[str, Any]]) -> Optional[Path]:
    if not isinstance(instance_data, dict):
        return None
    params = instance_data.get("params") if isinstance(instance_data.get("params"), dict) else {}
    epic_freeze = params.get("epic_freeze")
    epic_path = epic_freeze.get("path") if isinstance(epic_freeze, dict) else epic_freeze
    if not isinstance(epic_path, str) or not epic_path.strip():
        return None
    epic_candidate = Path(epic_path)
    for parent in [epic_candidate, *epic_candidate.parents]:
        if parent.name == ".workflow":
            return parent.parent
    return None


def _normalize_ssot_output_contract(
    *,
    runner_cls,
    workflow_id: str,
    normalized_business: Dict[str, Any],
    normalized_structured: Dict[str, Any],
    actual_epic_ref: Optional[str],
) -> Dict[str, Any]:
    ssot_contract = normalized_structured.get("ssot_output_contract")
    normalized_contract = dict(ssot_contract) if isinstance(ssot_contract, dict) else {}
    normalized_contract.setdefault("contract_version", "1.0")
    normalized_contract.setdefault("run_id", workflow_id)

    feat_specs = normalized_business.get("feat_specs") if isinstance(normalized_business.get("feat_specs"), list) else []
    outputs = normalized_contract.get("outputs")
    if feat_specs:
        if not isinstance(outputs, list) or not outputs:
            normalized_contract["outputs"] = build_contract_outputs(
                runner_cls=runner_cls,
                feat_specs=feat_specs,
                epic_ref=normalized_business.get("epic_ref"),
            )
        else:
            normalized_contract["outputs"] = normalize_existing_contract_outputs(
                runner_cls=runner_cls,
                outputs=outputs,
                normalized_business=normalized_business,
                actual_epic_ref=actual_epic_ref,
            )
    else:
        normalized_contract["outputs"] = normalize_existing_contract_outputs(
            runner_cls=runner_cls,
            outputs=outputs if isinstance(outputs, list) else [],
            normalized_business=normalized_business,
            actual_epic_ref=actual_epic_ref,
        )
    return normalized_contract
