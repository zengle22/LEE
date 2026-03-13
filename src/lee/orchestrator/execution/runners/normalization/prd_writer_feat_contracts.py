from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def format_list_section(title: str, values: Any) -> str:
    normalized_values = [str(item).strip() for item in (values or []) if str(item).strip()]
    if not normalized_values:
        return f"# {title}\n\n- None\n"
    lines = "\n".join(f"- {item}" for item in normalized_values)
    return f"# {title}\n\n{lines}\n"


def format_acceptance_checks_section(checks: Any) -> str:
    if not isinstance(checks, list) or not checks:
        return "# Acceptance Checks\n\n- None\n"

    blocks: List[str] = []
    for index, item in enumerate(checks, start=1):
        if not isinstance(item, dict):
            blocks.append(f"## AC-{index:03d}\n\n{item}\n")
            continue
        trace_hints = item.get("trace_hints") or []
        trace_text = ", ".join(str(hint).strip() for hint in trace_hints if str(hint).strip()) or "None"
        blocks.append(
            f"## {item.get('id') or f'AC-{index:03d}'}\n\n"
            f"- Scenario: {item.get('scenario', '')}\n"
            f"- Given: {item.get('given', '')}\n"
            f"- When: {item.get('when', '')}\n"
            f"- Then: {item.get('then', '')}\n"
            f"- Trace Hints: {trace_text}\n"
        )
    return "# Acceptance Checks\n\n" + "\n".join(blocks).rstrip() + "\n"


def build_feat_markdown(feat_item: Dict[str, Any]) -> str:
    sections = [
        f"# Goal\n\n{feat_item.get('goal', '').strip()}\n",
        f"# User Value\n\n{feat_item.get('user_value', '').strip()}\n",
        format_list_section("Inputs", feat_item.get("inputs")),
        format_list_section("Processing", feat_item.get("processing")),
        format_list_section("Outputs", feat_item.get("outputs")),
        format_list_section("Acceptance", feat_item.get("acceptance_criteria")),
        format_acceptance_checks_section(feat_item.get("acceptance_checks")),
        format_list_section("Dependencies", feat_item.get("dependencies")),
        format_list_section("Non Goals", feat_item.get("non_goals")),
    ]
    return "\n".join(section.rstrip() for section in sections).strip() + "\n"


def build_contract_outputs(*, runner_cls, feat_specs: List[Dict[str, Any]], epic_ref: Optional[str]) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    use_single_key = len(feat_specs) == 1
    for index, feat_item in enumerate(feat_specs, start=1):
        if not isinstance(feat_item, dict):
            continue
        feat_id = str(feat_item.get("feat_id") or "").strip()
        feat_title = str(feat_item.get("title") or feat_id or f"FEAT {index}").strip()
        feat_ssot = feat_item.get("ssot") if isinstance(feat_item.get("ssot"), dict) else {}
        source_refs = runner_cls._filter_materializable_refs(feat_item.get("source_refs"))
        parent_ref = feat_ssot.get("parent") or epic_ref
        if not runner_cls._is_literal_ssot_ref(parent_ref):
            parent_ref = None
        output_key = "feat" if use_single_key else f"feat_{index:03d}"
        output_item = {
            "key": output_key,
            "identity_kind": "ssot",
            "ssot_type": "feat",
            "title": feat_title,
            "content": build_feat_markdown(feat_item),
            "properties": {
                "formal_id": feat_id,
                "feat_id": feat_id,
                "epic_ref": epic_ref,
            },
        }
        if parent_ref:
            output_item["parent"] = parent_ref
        if source_refs:
            output_item["source_refs"] = source_refs
        outputs.append(output_item)
    return outputs


def rewrite_specs_for_actual_epic_ref(*, feat_specs: List[Any], actual_epic_ref: str) -> List[Any]:
    rewritten_specs: List[Any] = []
    for item in feat_specs:
        if not isinstance(item, dict):
            rewritten_specs.append(item)
            continue
        normalized_item = dict(item)
        normalized_item["source_refs"] = [f"{actual_epic_ref}#scope"]
        ssot = normalized_item.get("ssot") if isinstance(normalized_item.get("ssot"), dict) else {}
        normalized_item["ssot"] = {
            **dict(ssot),
            "identity_kind": "ssot",
            "ssot_type": "FEAT",
            "parent": actual_epic_ref,
            "derived_from": actual_epic_ref,
        }
        rewritten_specs.append(normalized_item)
    return rewritten_specs


def remap_canonical_feat_ids(*, feat_specs: List[Any], project_root: Optional[Path]) -> List[Any]:
    if project_root is None:
        return feat_specs

    generated_ids = _next_canonical_feat_ids(project_root=project_root, count=len(feat_specs))
    feat_id_alias_map = _build_feat_id_alias_map(feat_specs=feat_specs, generated_ids=generated_ids)
    if not feat_id_alias_map:
        return feat_specs

    rewritten_specs: List[Any] = []
    for feat_item in feat_specs:
        if not isinstance(feat_item, dict):
            rewritten_specs.append(feat_item)
            continue
        normalized_item = dict(feat_item)
        current_id = _clean_text(normalized_item.get("feat_id"))
        rewritten_id = feat_id_alias_map.get(current_id, current_id)
        if rewritten_id:
            normalized_item["feat_id"] = rewritten_id
        _rewrite_dependencies(normalized_item, feat_id_alias_map)
        _rewrite_source_refs(normalized_item, feat_id_alias_map)
        _rewrite_required_artifacts(normalized_item, feat_id_alias_map)
        _rewrite_acceptance_check_trace_hints(normalized_item, feat_id_alias_map)
        rewritten_specs.append(normalized_item)
    return rewritten_specs


def normalize_existing_contract_outputs(
    *,
    runner_cls,
    outputs: List[Any],
    normalized_business: Dict[str, Any],
    actual_epic_ref: Optional[str],
) -> List[Any]:
    normalized_outputs = []
    for item in outputs:
        if not isinstance(item, dict):
            normalized_outputs.append(item)
            continue
        normalized_item = dict(item)
        normalized_item.setdefault("identity_kind", "ssot")
        if normalized_item.get("key") == "feat":
            normalized_item.setdefault("ssot_type", "feat")
            if normalized_business.get("title"):
                normalized_item.setdefault("title", normalized_business["title"])
            parent = normalized_business.get("ssot", {}).get("parent")
            if runner_cls._is_literal_ssot_ref(parent):
                normalized_item.setdefault("parent", parent)
            source_refs = runner_cls._filter_materializable_refs(normalized_business.get("source_refs"))
            if source_refs:
                normalized_item.setdefault("source_refs", source_refs)
        if actual_epic_ref and runner_cls._is_literal_ssot_ref(actual_epic_ref):
            normalized_item["parent"] = actual_epic_ref
            normalized_item["source_refs"] = [f"{actual_epic_ref}#scope"]
        else:
            parent_ref = normalized_item.get("parent")
            if not runner_cls._is_literal_ssot_ref(parent_ref):
                normalized_item.pop("parent", None)
            filtered_refs = runner_cls._filter_materializable_refs(normalized_item.get("source_refs"))
            if filtered_refs:
                normalized_item["source_refs"] = filtered_refs
            else:
                normalized_item.pop("source_refs", None)
        properties = normalized_item.get("properties") if isinstance(normalized_item.get("properties"), dict) else {}
        normalized_item["properties"] = {
            **properties,
            "epic_ref": actual_epic_ref or normalized_business.get("epic_ref"),
        }
        normalized_outputs.append(normalized_item)
    return normalized_outputs


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _is_canonical_feat_id(value: str) -> bool:
    return bool(re.fullmatch(r"FEAT-\d{3}", value))


def _next_canonical_feat_ids(*, project_root: Path, count: int) -> List[str]:
    if count <= 0:
        return []
    highest = 0
    features_dir = project_root / "spec" / "requirements" / "features"
    if features_dir.exists():
        for path in features_dir.glob("FEAT-*.md"):
            match = re.match(r"FEAT-(\d{3})__", path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return [f"FEAT-{highest + index:03d}" for index in range(1, count + 1)]


def _build_feat_id_alias_map(*, feat_specs: List[Any], generated_ids: List[str]) -> Dict[str, str]:
    remap_candidates: List[tuple[str, str]] = []
    for index, feat_item in enumerate(feat_specs):
        if not isinstance(feat_item, dict):
            continue
        current_id = _clean_text(feat_item.get("feat_id"))
        if current_id and _is_canonical_feat_id(current_id):
            continue
        target_id = generated_ids[index] if index < len(generated_ids) else ""
        if current_id and target_id:
            remap_candidates.append((current_id, target_id))
    return {
        source_id: target_id
        for source_id, target_id in remap_candidates
        if source_id != target_id
    }


def _rewrite_dependencies(normalized_item: Dict[str, Any], feat_id_alias_map: Dict[str, str]) -> None:
    dependencies = normalized_item.get("dependencies")
    if isinstance(dependencies, list):
        normalized_item["dependencies"] = [
            feat_id_alias_map.get(_clean_text(dep), _clean_text(dep))
            for dep in dependencies
            if _clean_text(dep)
        ]


def _rewrite_ref_list(values: List[Any], feat_id_alias_map: Dict[str, str]) -> List[Any]:
    rewritten: List[Any] = []
    for ref in values:
        if isinstance(ref, str) and "#" in ref and ref.split("#", 1)[0] in feat_id_alias_map:
            rewritten.append(
                f"{feat_id_alias_map.get(ref.split('#', 1)[0], ref.split('#', 1)[0])}#{ref.split('#', 1)[1]}"
            )
        else:
            rewritten.append(ref)
    return rewritten


def _rewrite_source_refs(normalized_item: Dict[str, Any], feat_id_alias_map: Dict[str, str]) -> None:
    source_refs = normalized_item.get("source_refs")
    if isinstance(source_refs, list):
        normalized_item["source_refs"] = _rewrite_ref_list(source_refs, feat_id_alias_map)


def _rewrite_required_artifacts(normalized_item: Dict[str, Any], feat_id_alias_map: Dict[str, str]) -> None:
    input_contract = normalized_item.get("input_contract")
    if not isinstance(input_contract, dict):
        return
    required_artifacts = input_contract.get("required_artifacts")
    if isinstance(required_artifacts, list):
        normalized_item["input_contract"] = {
            **input_contract,
            "required_artifacts": _rewrite_ref_list(required_artifacts, feat_id_alias_map),
        }


def _rewrite_acceptance_check_trace_hints(normalized_item: Dict[str, Any], feat_id_alias_map: Dict[str, str]) -> None:
    acceptance_checks = normalized_item.get("acceptance_checks")
    if not isinstance(acceptance_checks, list):
        return
    rewritten_checks = []
    for item in acceptance_checks:
        if not isinstance(item, dict):
            rewritten_checks.append(item)
            continue
        trace_hints = item.get("trace_hints")
        rewritten_checks.append(
            {
                **item,
                "trace_hints": [
                    feat_id_alias_map.get(_clean_text(hint), _clean_text(hint))
                    for hint in trace_hints
                    if _clean_text(hint)
                ] if isinstance(trace_hints, list) else trace_hints,
            }
        )
    normalized_item["acceptance_checks"] = rewritten_checks
