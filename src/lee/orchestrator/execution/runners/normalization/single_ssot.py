from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .source_normalization_ssot import normalize_source_normalization_ssot_contract


class SingleSSOTNormalizer:
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
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        agent_id = getattr(step, "agent_id", "") or ""
        step_id = getattr(step, "id", "") or ""
        if step_id in {"ui_design", "tech_design"}:
            payload = runner_cls._ensure_structured_envelope(
                business_output=business_output,
                structured_payload=structured_payload,
            )
            metadata = business_output.get("metadata") if isinstance(business_output.get("metadata"), dict) else {}
            feat_id = None
            for candidate in (
                business_output.get("parent"),
                business_output.get("feat_id"),
                metadata.get("feat_id"),
                metadata.get("feature_id"),
                metadata.get("parent"),
            ):
                if isinstance(candidate, str) and runner_cls._is_literal_ssot_ref(candidate):
                    feat_id = candidate.strip()
                    break
            if feat_id is None and isinstance(instance_data, dict):
                params = instance_data.get("params") if isinstance(instance_data.get("params"), dict) else {}
                for candidate in (
                    params.get("feat_freeze"),
                    params.get("feat_freeze_ref"),
                ):
                    if isinstance(candidate, str) and runner_cls._is_literal_ssot_ref(candidate):
                        feat_id = candidate.strip()
                        break
                    if isinstance(candidate, dict):
                        artifact_id = candidate.get("artifact_id")
                        if isinstance(artifact_id, str) and runner_cls._is_literal_ssot_ref(artifact_id):
                            feat_id = artifact_id.strip()
                            break
                if feat_id is None:
                    feat_freeze_path = runner_cls._extract_feat_freeze_path(instance_data)
                    if isinstance(feat_freeze_path, str) and feat_freeze_path.strip():
                        frontmatter = runner_cls._load_yaml_frontmatter(Path(feat_freeze_path.strip()))
                        candidate = frontmatter.get("id")
                        if isinstance(candidate, str) and runner_cls._is_literal_ssot_ref(candidate):
                            feat_id = candidate.strip()
            default_title = (
                str(
                    business_output.get("title")
                    or metadata.get("feature_title")
                    or metadata.get("title")
                    or getattr(step, "name", "")
                    or step_id
                ).strip()
                or step_id
            )
            default_output = {
                "key": "ui_prototype" if step_id == "ui_design" else "tech_spec",
                "identity_kind": "ssot",
                "ssot_type": "ui" if step_id == "ui_design" else "tech",
                "title": default_title,
                "content": runner_cls._extract_step_written_markdown(step_id, payload)
                or yaml.safe_dump(business_output, allow_unicode=True, sort_keys=False),
            }
            output_item = {
                **default_output,
            }
            if feat_id:
                output_item["parent"] = feat_id
                output_item["implements"] = [feat_id]

            existing_contract = payload.get("ssot_output_contract")
            if isinstance(existing_contract, dict):
                normalized_contract = dict(existing_contract)
                raw_outputs = normalized_contract.get("outputs")
                normalized_outputs: List[Dict[str, Any]] = []
                if isinstance(raw_outputs, list):
                    for raw_output in raw_outputs:
                        if not isinstance(raw_output, dict):
                            continue
                        merged_output = {**default_output, **dict(raw_output)}
                        if feat_id:
                            current_parent = merged_output.get("parent")
                            if not (
                                isinstance(current_parent, str)
                                and runner_cls._is_literal_ssot_ref(current_parent)
                            ):
                                merged_output["parent"] = feat_id
                            implements = merged_output.get("implements")
                            if not isinstance(implements, list) or not implements:
                                merged_output["implements"] = [feat_id]
                        normalized_outputs.append(merged_output)
                if not normalized_outputs:
                    normalized_outputs = [output_item]
                normalized_contract["contract_version"] = "1.0"
                normalized_contract["run_id"] = str(normalized_contract.get("run_id") or workflow_id)
                normalized_contract["outputs"] = normalized_outputs
                payload["ssot_output_contract"] = normalized_contract
            else:
                payload["ssot_output_contract"] = {
                    "contract_version": "1.0",
                    "run_id": workflow_id,
                    "outputs": [output_item],
                }
            return business_output, payload

        if step_id == "source_normalization":
            payload = normalize_source_normalization_ssot_contract(
                runner_cls=runner_cls,
                workflow_id=workflow_id,
                business_output=business_output,
                structured_payload=structured_payload,
            )
            return business_output, payload

        if isinstance(structured_payload, dict) and isinstance(structured_payload.get("ssot_output_contract"), dict):
            return business_output, structured_payload

        if agent_id == "agent.product.epic_designer":
            explicit_source_refs = runner_cls._derive_source_refs_from_business_output(
                business_output,
                allowed_prefixes=["SRC"],
            )
            source_refs = list(explicit_source_refs)
            ssot_meta = business_output.get("ssot") if isinstance(business_output.get("ssot"), dict) else {}
            derived_from = ssot_meta.get("derived_from")
            source_problem = ssot_meta.get("source_problem")
            canonical_source_ref = runner_cls._resolve_source_ref_from_instance_data(instance_data)
            if not source_refs and isinstance(source_problem, str) and runner_cls._is_literal_ssot_ref(source_problem):
                source_refs = [f"{source_problem}#scope"]
            if not derived_from and isinstance(source_problem, str) and runner_cls._is_literal_ssot_ref(source_problem):
                derived_from = source_problem
            if not source_refs and canonical_source_ref:
                source_refs = [f"{canonical_source_ref}#scope"]
            if not derived_from and canonical_source_ref:
                derived_from = canonical_source_ref
            elif canonical_source_ref and (
                not isinstance(derived_from, str) or not runner_cls._is_literal_ssot_ref(derived_from)
            ):
                derived_from = canonical_source_ref
            if not source_refs and isinstance(derived_from, str) and runner_cls._is_literal_ssot_ref(derived_from):
                source_refs = [f"{derived_from}#scope"]
            normalized_business = dict(business_output)
            normalized_ssot = dict(ssot_meta)
            normalized_ssot["identity_kind"] = "ssot"
            normalized_ssot["ssot_type"] = "EPIC"
            if canonical_source_ref:
                normalized_ssot["parent"] = canonical_source_ref
            if canonical_source_ref:
                normalized_ssot["derived_from"] = canonical_source_ref
            elif isinstance(derived_from, str) and runner_cls._is_literal_ssot_ref(derived_from):
                normalized_ssot["derived_from"] = derived_from.strip()
            normalized_business["ssot"] = normalized_ssot
            if source_refs:
                normalized_business["source_refs"] = source_refs
            payload = runner_cls._ensure_structured_envelope(
                business_output=normalized_business,
                structured_payload=structured_payload,
            )
            formal_epic_id = normalized_business.get("epic_id")
            if not (
                isinstance(formal_epic_id, str)
                and runner_cls._is_literal_ssot_ref(formal_epic_id)
            ):
                output_item = {
                    "key": "epic",
                    "identity_kind": "ssot",
                    "ssot_type": "epic",
                    "title": str(normalized_business.get("title") or step_id or "Untitled Epic").strip() or "Untitled Epic",
                    "source_refs": source_refs,
                }
                normalized_derived_from = normalized_business.get("ssot", {}).get("derived_from")
                if isinstance(normalized_derived_from, str) and runner_cls._is_literal_ssot_ref(normalized_derived_from):
                    output_item["derived_from"] = [normalized_derived_from]
                payload["ssot_output_contract"] = {
                    "contract_version": "1.0",
                    "run_id": workflow_id,
                    "outputs": [output_item],
                }
            return normalized_business, payload

        return business_output, structured_payload
