from __future__ import annotations

import re
from typing import Any, Dict, List

import yaml


SOURCE_NORMALIZATION_DRIFT_MARKERS = (
    "原始输入归一化",
    "合同复用",
    "前置目标分析",
    "raw input intake",
    "input intake",
    "source normalization",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _meaningful_text(value: Any) -> str | None:
    text = _clean_text(value)
    if not text or text.upper() in {"SRC", "UNTITLED SRC"}:
        return None
    return text


def derive_src_title_from_business_output(business_output: Any) -> str:
    if not isinstance(business_output, dict):
        return "SRC"

    normalized_content = business_output.get("normalized_content")
    normalized_content = normalized_content if isinstance(normalized_content, dict) else {}
    metadata = business_output.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    src_structure = business_output.get("src_structure")
    src_structure = src_structure if isinstance(src_structure, dict) else {}
    product_goal = business_output.get("product_goal")
    product_goal = product_goal if isinstance(product_goal, dict) else {}
    contract_info = business_output.get("contract_info")
    contract_info = contract_info if isinstance(contract_info, dict) else {}
    core_goal = business_output.get("core_goal")
    core_goal = core_goal if isinstance(core_goal, dict) else {}
    primary_goal = core_goal.get("primary_goal")
    primary_goal = primary_goal if isinstance(primary_goal, dict) else {}

    for candidate in (
        business_output.get("title"),
        normalized_content.get("title"),
        business_output.get("name"),
        normalized_content.get("name"),
        normalized_content.get("problem_statement"),
        normalized_content.get("summary"),
        business_output.get("problem_statement"),
        business_output.get("summary"),
        src_structure.get("title"),
        src_structure.get("problem_statement"),
        product_goal.get("title"),
        product_goal.get("essence"),
        contract_info.get("title"),
        primary_goal.get("description"),
        business_output.get("trigger_context"),
    ):
        title = _meaningful_text(candidate)
        if title:
            return title

    source_ref = _meaningful_text(metadata.get("source_ref") or business_output.get("source_ref"))
    domain = _meaningful_text(metadata.get("domain"))
    if source_ref and domain:
        return f"{source_ref} {domain}".replace("_", " ")
    if source_ref:
        return source_ref
    if domain:
        return domain.replace("_", " ")

    src_id = _meaningful_text(business_output.get("src_id"))
    return src_id or "SRC"


def _is_semantic_drift(candidate: Any) -> bool:
    if not isinstance(candidate, str):
        return False
    normalized = re.sub(r"\s+", " ", candidate).strip().lower()
    return bool(normalized) and any(marker in normalized for marker in SOURCE_NORMALIZATION_DRIFT_MARKERS)


def _validate_source_normalization_output(*, business_output: Dict[str, Any], output: Dict[str, Any]) -> None:
    normalized_content = business_output.get("normalized_content")
    normalized_content = normalized_content if isinstance(normalized_content, dict) else {}
    contract_info = business_output.get("contract_info")
    contract_info = contract_info if isinstance(contract_info, dict) else {}
    product_goal = business_output.get("product_goal")
    product_goal = product_goal if isinstance(product_goal, dict) else {}
    src_structure = business_output.get("src_structure")
    src_structure = src_structure if isinstance(src_structure, dict) else {}

    for candidate in (
        output.get("title"),
        business_output.get("title"),
        normalized_content.get("title"),
        normalized_content.get("problem_statement"),
        business_output.get("problem_statement"),
        contract_info.get("title"),
        product_goal.get("title"),
        src_structure.get("title"),
        src_structure.get("problem_statement"),
    ):
        if _is_semantic_drift(candidate):
            raise ValueError(
                "source_normalization semantic drift detected: output rewrote the source problem into intake/workflow methodology"
            )


def normalize_source_normalization_ssot_contract(
    *,
    runner_cls,
    workflow_id: str,
    business_output: Dict[str, Any],
    structured_payload: Any,
) -> Dict[str, Any]:
    payload = runner_cls._ensure_structured_envelope(
        business_output=business_output,
        structured_payload=structured_payload,
    )
    source_refs = runner_cls._derive_source_refs_from_business_output(business_output)
    default_output = {
        "key": "src",
        "identity_kind": "ssot",
        "ssot_type": "src",
        "title": derive_src_title_from_business_output(business_output),
        "content": yaml.safe_dump(business_output, allow_unicode=True, sort_keys=False),
    }
    if source_refs:
        default_output["source_refs"] = source_refs

    existing_contract = payload.get("ssot_output_contract")
    if not isinstance(existing_contract, dict):
        _validate_source_normalization_output(business_output=business_output, output=default_output)
        payload["ssot_output_contract"] = {
            "contract_version": "1.0",
            "run_id": workflow_id,
            "outputs": [default_output],
        }
        return payload

    existing_src_outputs: List[Dict[str, Any]] = []
    for raw_output in existing_contract.get("outputs", []) or []:
        if not isinstance(raw_output, dict):
            continue
        output = dict(raw_output)
        if (
            str(output.get("key") or "").strip().lower() != "src"
            and str(output.get("ssot_type") or "").strip().lower() != "src"
        ):
            raise ValueError("source_normalization must emit exactly one src output")
        existing_src_outputs.append(output)

    if len(existing_src_outputs) > 1:
        raise ValueError("source_normalization must emit exactly one src output")

    merged_output = dict(default_output)
    if existing_src_outputs:
        merged_output.update(existing_src_outputs[0])
    title = str(merged_output.get("title") or "").strip()
    if not title or title.upper() in {"SRC", "UNTITLED SRC"}:
        merged_output["title"] = default_output["title"]
    if source_refs and not runner_cls._filter_materializable_refs(merged_output.get("source_refs")):
        merged_output["source_refs"] = source_refs
    _validate_source_normalization_output(business_output=business_output, output=merged_output)

    payload["ssot_output_contract"] = {
        **dict(existing_contract),
        "contract_version": "1.0",
        "run_id": str(existing_contract.get("run_id") or workflow_id),
        "outputs": [merged_output],
    }
    return payload
