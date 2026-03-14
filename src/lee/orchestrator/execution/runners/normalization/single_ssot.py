from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


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
            formal_epic_id = business_output.get("epic_id")
            if not source_refs and isinstance(derived_from, str) and runner_cls._is_literal_ssot_ref(derived_from):
                source_refs = [f"{derived_from}#scope"]
            payload = runner_cls._ensure_structured_envelope(
                business_output=business_output,
                structured_payload=structured_payload,
            )
            epic_output = {
                "key": "epic",
                "identity_kind": "ssot",
                "ssot_type": "epic",
                "title": str(business_output.get("title") or "EPIC").strip() or "EPIC",
                "content": yaml.safe_dump(business_output, allow_unicode=True, sort_keys=False),
            }
            if source_refs:
                epic_output["source_refs"] = source_refs
            if isinstance(derived_from, str) and derived_from.strip():
                if explicit_source_refs and explicit_source_refs[0].split("#", 1)[0] == derived_from.strip():
                    epic_output["derived_from"] = [derived_from.strip()]
                else:
                    epic_output["derived_from"] = derived_from.strip()
            if isinstance(formal_epic_id, str) and formal_epic_id.strip():
                epic_output["properties"] = {"formal_id": formal_epic_id.strip()}
            payload["ssot_output_contract"] = {
                "contract_version": "1.0",
                "run_id": workflow_id,
                "outputs": [epic_output],
            }
            return business_output, payload

        if step_id == "source_normalization":
            payload = runner_cls._ensure_structured_envelope(
                business_output=business_output,
                structured_payload=structured_payload,
            )
            source_refs = runner_cls._derive_source_refs_from_business_output(business_output)
            src_output = {
                "key": "src",
                "identity_kind": "ssot",
                "ssot_type": "src",
                "title": runner_cls._derive_src_title_from_business_output(business_output),
                "content": yaml.safe_dump(business_output, allow_unicode=True, sort_keys=False),
            }
            if source_refs:
                src_output["source_refs"] = source_refs
            payload["ssot_output_contract"] = {
                "contract_version": "1.0",
                "run_id": workflow_id,
                "outputs": [src_output],
            }
            return business_output, payload

        return business_output, structured_payload
