"""
Metadata inheritance helpers for formal SSOT materialization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

from .types import SSOTType


_PARENT_SOURCE_ANCHORS: Dict[str, str] = {
    SSOTType.FEAT.value: "scope",
    SSOTType.TASK.value: "delivery",
    SSOTType.UI.value: "design",
    SSOTType.TECH.value: "design",
    SSOTType.TESTSET.value: "test",
    SSOTType.TC.value: "test",
    SSOTType.BUG.value: "delivery",
    SSOTType.REPORT.value: "delivery",
}

_EXPECTED_PARENT_PREFIX: Dict[str, str] = {
    SSOTType.FEAT.value: "EPIC-",
    SSOTType.TASK.value: "FEAT-",
    SSOTType.UI.value: "FEAT-",
    SSOTType.TECH.value: "FEAT-",
    SSOTType.TESTSET.value: "FEAT-",
    SSOTType.TC.value: "TESTSET-",
    SSOTType.BUG.value: "FEAT-",
}


@dataclass
class InheritanceResult:
    parent_id: Optional[str]
    source_refs: List[str]
    derived_from_ids: List[Dict[str, Any]]


class MetadataInheritanceEngine:
    """Normalize parent/source/derived metadata before SSOT persistence."""

    def __init__(self, lookup_artifact: Callable[[str], Optional[Any]]):
        self._lookup_artifact = lookup_artifact

    def normalize(
        self,
        *,
        ssot_type: SSOTType,
        formal_id: Optional[str],
        parent_id: Optional[str],
        source_refs: Optional[Iterable[Any]],
        derived_from_ids: Optional[Iterable[Any]],
        version: str = "v1",
    ) -> InheritanceResult:
        literal_parent = self._clean_ref(parent_id)
        normalized_source_refs = self._normalize_source_refs(source_refs)
        normalized_derived = self._normalize_versioned_refs(derived_from_ids)

        if literal_parent is None:
            literal_parent = self._infer_parent_from_source_refs(ssot_type, normalized_source_refs)

        if literal_parent:
            primary_source_ref = self._build_primary_source_ref(ssot_type, literal_parent)
            if primary_source_ref:
                normalized_source_refs = self._ensure_primary_source_ref(
                    normalized_source_refs,
                    literal_parent,
                    primary_source_ref,
                )
            normalized_derived = self._ensure_parent_lineage(
                normalized_derived,
                literal_parent,
                version_hint=self._lookup_version(literal_parent) or version,
            )

        self._validate_no_cycles(
            formal_id=formal_id,
            parent_id=literal_parent,
            source_refs=normalized_source_refs,
            derived_from_ids=normalized_derived,
        )

        return InheritanceResult(
            parent_id=literal_parent,
            source_refs=normalized_source_refs,
            derived_from_ids=normalized_derived,
        )

    @staticmethod
    def _clean_ref(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    def _normalize_source_refs(self, values: Optional[Iterable[Any]]) -> List[str]:
        normalized: List[str] = []
        seen = set()
        for value in values or []:
            if not isinstance(value, str):
                continue
            ref = value.strip()
            if not ref or ref in seen:
                continue
            seen.add(ref)
            normalized.append(ref)
        return normalized

    def _normalize_versioned_refs(self, values: Optional[Iterable[Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        seen = set()
        for value in values or []:
            if isinstance(value, dict):
                ref_id = self._clean_ref(value.get("id"))
                if not ref_id:
                    continue
                version = self._clean_ref(value.get("version")) or self._lookup_version(ref_id) or "v1"
                item = {
                    "id": ref_id,
                    "version": version,
                }
                if "required" in value:
                    item["required"] = bool(value.get("required"))
                if "slice_key" in value and self._clean_ref(value.get("slice_key")):
                    item["slice_key"] = self._clean_ref(value.get("slice_key"))
            else:
                ref_id = self._clean_ref(value)
                if not ref_id:
                    continue
                item = {
                    "id": ref_id,
                    "version": self._lookup_version(ref_id) or "v1",
                    "required": True,
                }
            dedupe_key = (item["id"], item["version"])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized.append(item)
        return normalized

    def _infer_parent_from_source_refs(self, ssot_type: SSOTType, source_refs: List[str]) -> Optional[str]:
        expected_prefix = _EXPECTED_PARENT_PREFIX.get(ssot_type.value)
        if not expected_prefix:
            return None
        for ref in source_refs:
            ref_root = ref.split("#", 1)[0]
            if ref_root.upper().startswith(expected_prefix):
                return ref_root
        return None

    def _build_primary_source_ref(self, ssot_type: SSOTType, parent_id: str) -> Optional[str]:
        anchor = _PARENT_SOURCE_ANCHORS.get(ssot_type.value)
        if not anchor:
            return None
        return f"{parent_id}#{anchor}"

    @staticmethod
    def _ensure_primary_source_ref(source_refs: List[str], parent_id: str, primary_ref: str) -> List[str]:
        normalized = list(source_refs)
        has_parent_root = any(ref.split("#", 1)[0] == parent_id for ref in normalized)
        if has_parent_root:
            return normalized
        return [primary_ref, *normalized]

    @staticmethod
    def _ensure_parent_lineage(
        derived_from_ids: List[Dict[str, Any]],
        parent_id: str,
        *,
        version_hint: str,
    ) -> List[Dict[str, Any]]:
        normalized = list(derived_from_ids)
        if any(item.get("id") == parent_id for item in normalized):
            return normalized
        return [
            {
                "id": parent_id,
                "version": version_hint or "v1",
                "required": True,
            },
            *normalized,
        ]

    def _lookup_version(self, artifact_id: str) -> Optional[str]:
        artifact = self._lookup_artifact(artifact_id)
        if artifact is None:
            return None
        properties = getattr(artifact, "properties", {}) or {}
        version = properties.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
        return "v1"

    @staticmethod
    def _validate_no_cycles(
        *,
        formal_id: Optional[str],
        parent_id: Optional[str],
        source_refs: List[str],
        derived_from_ids: List[Dict[str, Any]],
    ) -> None:
        formal = (formal_id or "").strip()
        if not formal:
            return
        if parent_id == formal:
            raise ValueError(f"metadata inheritance cycle: {formal} cannot reference itself as parent")
        for ref in source_refs:
            if ref.split("#", 1)[0] == formal:
                raise ValueError(f"metadata inheritance cycle: {formal} cannot reference itself in source_refs")
        for ref in derived_from_ids:
            if ref.get("id") == formal:
                raise ValueError(f"metadata inheritance cycle: {formal} cannot reference itself in derived_from_ids")
