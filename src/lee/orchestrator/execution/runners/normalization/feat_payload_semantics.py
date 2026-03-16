from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List


_META_OUTPUT_PATTERNS = (
    re.compile(r"\bfeat specification\b", re.IGNORECASE),
    re.compile(r"\bspecification itself\b", re.IGNORECASE),
    re.compile(r"\bself\b", re.IGNORECASE),
    re.compile(r"规格(本身|说明|文档)$", re.IGNORECASE),
)

_SCHEMA_CONFLICT_PATTERNS = (
    re.compile(r"最终\s*schema", re.IGNORECASE),
    re.compile(r"完整\s*schema", re.IGNORECASE),
    re.compile(r"schema\s*字段名", re.IGNORECASE),
)

_TRACE_HINT_ORDER = ("UI", "TECH", "TASK", "TESTSET")
_UI_SCOPE_PATTERNS = (
    re.compile(r"\bui\b", re.IGNORECASE),
    re.compile(r"\bpage\b", re.IGNORECASE),
    re.compile(r"\bscreen\b", re.IGNORECASE),
    re.compile(r"\bportal\b", re.IGNORECASE),
    re.compile(r"\bdashboard\b", re.IGNORECASE),
    re.compile(r"\bquery interface\b", re.IGNORECASE),
    re.compile(r"界面"),
    re.compile(r"页面"),
    re.compile(r"前端"),
    re.compile(r"查询接口"),
    re.compile(r"展示"),
)
_GENERIC_INPUT_PATTERNS = (
    re.compile(r"schema", re.IGNORECASE),
    re.compile(r"配置"),
    re.compile(r"规则"),
    re.compile(r"指南"),
    re.compile(r"清单"),
    re.compile(r"文档"),
    re.compile(r"定义"),
)
_QUALIFIED_ARTIFACT_PATTERNS = (
    re.compile(r"\bdraft\b", re.IGNORECASE),
    re.compile(r"\bbaseline\b", re.IGNORECASE),
    re.compile(r"\bfrozen\b", re.IGNORECASE),
    re.compile(r"\bformal\b", re.IGNORECASE),
    re.compile(r"草案"),
    re.compile(r"基线"),
    re.compile(r"冻结"),
)


def refine_feat_outputs(
    outputs: Iterable[str],
    *,
    title: str,
    goal: str,
    acceptance_criteria: Iterable[str],
    processing: Iterable[str],
) -> List[str]:
    normalized = _normalize_list(outputs)
    if normalized and not all(_looks_meta_output(item) for item in normalized):
        return normalized[:5]

    candidates: List[str] = []
    candidates.extend(_outputs_from_acceptance_criteria(acceptance_criteria))
    candidates.extend(_outputs_from_processing(processing))
    candidates.extend(_outputs_from_title_and_goal(title=title, goal=goal))

    deduped = _dedupe(candidates)
    if deduped:
        return deduped[:5]
    fallback_title = title.strip() or goal.strip() or "FEAT"
    return [f"{fallback_title} deliverable"]


def align_required_artifacts(
    required_artifacts: Iterable[str],
    non_goals: Iterable[str],
) -> List[str]:
    artifacts = _normalize_list(required_artifacts)
    non_goal_text = " ".join(_normalize_list(non_goals)).lower()
    if not artifacts or not non_goal_text:
        return artifacts

    normalized: List[str] = []
    for artifact in artifacts:
        rewritten = artifact
        lowered = artifact.lower()
        if "schema" in lowered and any(pattern.search(non_goal_text) for pattern in _SCHEMA_CONFLICT_PATTERNS):
            if "version pin" in lowered:
                rewritten = _ensure_suffix(artifact, "基线")
            elif "bridge" in lowered:
                rewritten = _replace_schema_word(artifact, "schema 基线")
            else:
                rewritten = _replace_schema_word(artifact, "schema 草案")
        normalized.append(rewritten)
    return _dedupe(normalized)


def align_inputs_with_required_artifacts(
    inputs: Iterable[str],
    required_artifacts: Iterable[str],
) -> List[str]:
    normalized_inputs = _normalize_list(inputs)
    artifacts = _normalize_list(required_artifacts)
    if not normalized_inputs or not artifacts:
        return normalized_inputs

    aligned: List[str] = []
    for input_text in normalized_inputs:
        replacement = _match_specific_artifact(input_text, artifacts)
        aligned.append(replacement or input_text)
    return _dedupe(aligned)


def refine_acceptance_checks(
    acceptance_checks: Iterable[Any],
    *,
    title: str,
    goal: str,
    outputs: Iterable[str],
    processing: Iterable[str],
    derived_object_expectations: Dict[str, Any] | None,
) -> List[Any]:
    normalized_checks = list(acceptance_checks or [])
    if not normalized_checks:
        return normalized_checks

    base_hints = _derive_scope_trace_hints(
        title=title,
        goal=goal,
        outputs=outputs,
        processing=processing,
        derived_object_expectations=derived_object_expectations or {},
    )
    refined: List[Any] = []
    for item in normalized_checks:
        if not isinstance(item, dict):
            refined.append(item)
            continue
        existing_hints = item.get("trace_hints")
        merged_hints = _merge_trace_hints(existing_hints, base_hints)
        refined.append({**item, "trace_hints": merged_hints})
    return refined


def _normalize_list(values: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    for item in values or []:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _dedupe(values: Iterable[str]) -> List[str]:
    deduped: List[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(text)
    return deduped


def _looks_meta_output(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return True
    return any(pattern.search(text) for pattern in _META_OUTPUT_PATTERNS)


def _outputs_from_acceptance_criteria(criteria: Iterable[str]) -> List[str]:
    derived: List[str] = []
    for item in _normalize_list(criteria):
        match = re.search(r"输出(?P<tail>.+)", item)
        if match:
            tail = match.group("tail").strip(" ：:，,。.")
            if tail:
                derived.append(tail)
                continue
        match = re.search(r"包含(?P<tail>.+?)(字段|对象|结果|日志|配置)", item)
        if match:
            tail = match.group("tail").strip(" ：:，,。.")
            if tail:
                suffix = item[match.end(1): match.end()].strip(" ：:，,。.")
                derived.append(f"{tail}{suffix}")
                continue
        if "schema 校验" in item:
            derived.append("schema validation result")
        if "日志" in item:
            derived.append("execution audit log")
    return derived


def _outputs_from_processing(processing: Iterable[str]) -> List[str]:
    derived: List[str] = []
    for item in _normalize_list(processing):
        if "日志" in item:
            derived.append("execution audit log")
        if "校验" in item:
            derived.append("validation result")
        if "建立" in item and "关系" in item:
            derived.append("traceability link record")
    return derived


def _outputs_from_title_and_goal(*, title: str, goal: str) -> List[str]:
    text = f"{title} {goal}".lower()
    derived: List[str] = []
    if any(token in text for token in ("规则", "rule", "判断", "decision")):
        derived.append("bridge trigger decision result")
        derived.append("trigger rule catalog")
    if any(token in text for token in ("标识", "schema", "bridge src")):
        derived.append("bridge SRC schema baseline")
        derived.append("bridge SRC tagged object")
    if any(token in text for token in ("流程", "workflow", "适配", "route", "router")):
        derived.append("workflow routing configuration")
        derived.append("ADR input adapter result")
    if any(token in text for token in ("version pin", "pin", "交付轴", "release", "devplan", "testplan", "task")):
        derived.append("src_version_ref binding record")
        derived.append("delivery object validation rule")
    return derived


def _replace_schema_word(text: str, replacement: str) -> str:
    updated = re.sub(r"schema\s*定义", replacement, text, flags=re.IGNORECASE)
    if updated != text:
        return updated
    return re.sub(r"schema", replacement, text, flags=re.IGNORECASE)


def _ensure_suffix(text: str, suffix: str) -> str:
    stripped = text.strip()
    if stripped.endswith(suffix):
        return stripped
    return f"{stripped} {suffix}"


def _match_specific_artifact(input_text: str, artifacts: List[str]) -> str | None:
    lowered = input_text.lower()
    if not any(pattern.search(input_text) for pattern in _GENERIC_INPUT_PATTERNS):
        return None
    if any(pattern.search(input_text) for pattern in _QUALIFIED_ARTIFACT_PATTERNS):
        return None

    input_tokens = set(_semantic_tokens(input_text))
    best_artifact = None
    best_score = 0
    for artifact in artifacts:
        artifact_tokens = set(_semantic_tokens(artifact))
        if not artifact_tokens:
            continue
        overlap = len(input_tokens & artifact_tokens)
        if overlap > best_score:
            best_score = overlap
            best_artifact = artifact

    return best_artifact if best_score > 0 else None


def _semantic_tokens(text: str) -> List[str]:
    raw_tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", text)
    return [
        token.lower()
        for token in raw_tokens
        if token.lower() not in {"schema", "定义", "文档", "配置", "规则", "指南", "清单"}
    ]


def _derive_scope_trace_hints(
    *,
    title: str,
    goal: str,
    outputs: Iterable[str],
    processing: Iterable[str],
    derived_object_expectations: Dict[str, Any],
) -> List[str]:
    hints = {"TASK", "TESTSET"}
    if derived_object_expectations.get("tech_optional") is not True:
        hints.add("TECH")

    scope_text = " ".join(
        _normalize_list([title, goal]) + _normalize_list(outputs) + _normalize_list(processing)
    )
    if any(pattern.search(scope_text) for pattern in _UI_SCOPE_PATTERNS):
        hints.add("UI")

    return [hint for hint in _TRACE_HINT_ORDER if hint in hints]


def _merge_trace_hints(existing_hints: Any, base_hints: List[str]) -> List[str]:
    merged = [str(item).strip().upper() for item in existing_hints or [] if str(item).strip()]
    for hint in base_hints:
        if hint not in merged:
            merged.append(hint)
    return [hint for hint in _TRACE_HINT_ORDER if hint in merged]
