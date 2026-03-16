"""
SSOT agent output contract materializer.

将 agent/contract 声明的 outputs[*] 实例化为正式 SSOT 对象或普通 artifact。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.execution.validators.schema_validator import SchemaValidator

from .manager import ArtifactManager
from .models import ArtifactMetadata
from .placement import resolve_src_root_id
from .types import ArtifactType, GovernanceKind, SSOTType


FRAMEWORK_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SSOT_CONTRACT_SCHEMA = (
    FRAMEWORK_ROOT
    / "spec-global"
    / "core"
    / "contracts"
    / "ssot-agent-output"
    / "v1"
    / "schema.json"
)


@dataclass
class MaterializedOutput:
    key: str
    identity_kind: str
    artifact: ArtifactMetadata


class SSOTContractMaterializer:
    """
    Validate and materialize agent output contracts into real artifacts.
    """

    def __init__(
        self,
        manager: ArtifactManager,
        schema_path: Optional[Path] = None,
        upstream_step_outputs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.manager = manager
        self.schema_path = Path(schema_path or DEFAULT_SSOT_CONTRACT_SCHEMA)
        self._validator = SchemaValidator(project_dir=str(FRAMEWORK_ROOT))
        self._legacy_sequences: Dict[str, int] = {}
        self._upstream_step_outputs = upstream_step_outputs or {}

    def validate_contract(self, contract_data: Dict[str, Any]) -> None:
        """Validate a contract payload against the SSOT output schema."""
        result = self._validator.validate(
            contract_data,
            {"schema_path": str(self.schema_path)},
        )
        if not result.passed:
            message = "; ".join(error.message for error in result.errors)
            raise ValueError(f"Invalid SSOT contract: {message}")

    def materialize(self, contract_data: Dict[str, Any]) -> Dict[str, MaterializedOutput]:
        """
        Materialize contract outputs to the filesystem and registry.
        """
        self.validate_contract(contract_data)

        outputs = contract_data.get("outputs", [])
        run_id = contract_data["run_id"]
        pending = {output["key"]: output for output in outputs}
        materialized: Dict[str, MaterializedOutput] = {}

        while pending:
            progress = False
            for key in list(pending.keys()):
                output = pending[key]
                if not self._can_materialize(output, materialized):
                    continue
                materialized[key] = self._materialize_one(output, run_id, materialized)
                del pending[key]
                progress = True

            if not progress:
                unresolved = ", ".join(sorted(pending.keys()))
                raise ValueError(f"Unresolved contract dependencies: {unresolved}")

        return materialized

    def _can_materialize(
        self,
        output: Dict[str, Any],
        materialized: Dict[str, MaterializedOutput],
    ) -> bool:
        refs = []
        if output.get("parent"):
            refs.append(output["parent"])
        refs.extend(output.get("derived_from", []))
        refs.extend(ref["id"] for ref in output.get("derived_from_ids", []) if isinstance(ref, dict) and ref.get("id"))
        refs.extend(self._extract_local_keys(output.get("source_refs", [])))
        refs.extend(output.get("verifies", []))
        refs.extend(output.get("implements", []))
        local_refs = [ref for ref in refs if isinstance(ref, str) and ref.isidentifier()]

        for ref in local_refs:
            if ref in materialized:
                continue
            if self._is_literal_id(ref):
                continue
            if ref not in materialized:
                return False
        return True

    def _materialize_one(
        self,
        output: Dict[str, Any],
        run_id: str,
        materialized: Dict[str, MaterializedOutput],
    ) -> MaterializedOutput:
        identity_kind = output["identity_kind"]
        title = output["title"]
        content = output.get("content") or f"# {title}\n"
        tags = output.get("tags", [])
        properties = {
            "contract_key": output["key"],
            "identity_kind": identity_kind,
        }

        if identity_kind == "ssot":
            formal_id = None
            raw_properties = output.get("properties")
            if isinstance(raw_properties, dict):
                for candidate_key in ("formal_id", "task_id"):
                    candidate_value = raw_properties.get(candidate_key)
                    if isinstance(candidate_value, str) and candidate_value.strip():
                        formal_id = candidate_value.strip()
                        break
            formal_id = self._normalize_explicit_formal_id(output, formal_id)
            if formal_id is None and self._should_use_legacy_formal_id(output):
                formal_id = self._next_legacy_formal_id(output)
            artifact = self.manager.create_ssot(
                ssot_type=SSOTType(output["ssot_type"]),
                title=title,
                content=content,
                run_id=run_id,
                formal_id=formal_id,
                parent_id=self._resolve_optional_id(output.get("parent"), materialized),
                derived_from=self._resolve_versioned_refs(
                    output.get("derived_from_ids"),
                    materialized,
                ) or self._resolve_ids(output.get("derived_from", []), materialized),
                source_refs=self._resolve_source_refs(output.get("source_refs", []), materialized),
                verifies=self._resolve_ids(output.get("verifies", []), materialized),
                implements=self._resolve_ids(output.get("implements", []), materialized),
                owner=output.get("owner"),
                tags=tags,
                version=output.get("version", "v1"),
                properties=properties,
            )
        else:
            artifact = self.manager.create(
                artifact_type=ArtifactType(output.get("artifact_type", "DOCUMENT")),
                category=output.get("category", "readme"),
                content=content,
                run_id=run_id,
                title=title,
                description=output.get("description", ""),
                tags=tags,
                governance_kind=GovernanceKind(output.get("governance_kind", "knowledge")),
                depends_on=self._resolve_ids(output.get("depends_on", []), materialized),
                derived_from=self._resolve_optional_id(output.get("derived_from_one"), materialized),
                verifies=self._resolve_ids(output.get("verifies", []), materialized),
                implements=self._resolve_ids(output.get("implements", []), materialized),
                properties=properties,
            )

        return MaterializedOutput(
            key=output["key"],
            identity_kind=identity_kind,
            artifact=artifact,
        )

    def _normalize_explicit_formal_id(
        self,
        output: Dict[str, Any],
        formal_id: Optional[str],
    ) -> Optional[str]:
        if not isinstance(formal_id, str) or not formal_id.strip():
            return None
        if output.get("identity_kind") != "ssot":
            return formal_id.strip()
        try:
            ssot_type = SSOTType(output["ssot_type"])
        except Exception:
            return formal_id.strip()
        if ssot_type not in (SSOTType.EPIC, SSOTType.FEAT):
            return formal_id.strip()

        normalized_formal_id = formal_id.strip()
        src_root_id = resolve_src_root_id(
            artifact_id=None,
            parent_id=output.get("parent"),
            source_refs=output.get("source_refs"),
            properties=output.get("properties"),
        )
        if not src_root_id:
            return normalized_formal_id

        if resolve_src_root_id(artifact_id=normalized_formal_id) == src_root_id:
            return normalized_formal_id

        return None

    def _should_use_legacy_formal_id(self, output: Dict[str, Any]) -> bool:
        if output.get("identity_kind") != "ssot":
            return False
        try:
            ssot_type = SSOTType(output["ssot_type"])
        except Exception:
            return False
        if ssot_type not in (SSOTType.EPIC, SSOTType.FEAT):
            return True

        src_root_id = resolve_src_root_id(
            artifact_id=None,
            parent_id=output.get("parent"),
            source_refs=output.get("source_refs"),
            properties=output.get("properties"),
        )
        return not bool(src_root_id)

    def _next_legacy_formal_id(self, output: Dict[str, Any]) -> Optional[str]:
        if output.get("identity_kind") != "ssot":
            return None
        try:
            ssot_type = SSOTType(output["ssot_type"])
        except Exception:
            return None
        if ssot_type not in (SSOTType.EPIC, SSOTType.FEAT):
            return None

        cache_key = ssot_type.value
        if cache_key not in self._legacy_sequences:
            base_dir = self.manager.project_root / (
                "spec/requirements/epics" if ssot_type == SSOTType.EPIC else "spec/requirements/features"
            )
            max_seq = 0
            if base_dir.exists():
                prefix = ssot_type.value.upper()
                for path in base_dir.glob(f"{prefix}-*__*.md"):
                    object_id = path.name.split("__", 1)[0]
                    match = re.fullmatch(rf"{prefix}-(\d+)", object_id)
                    if match:
                        max_seq = max(max_seq, int(match.group(1)))
            self._legacy_sequences[cache_key] = max_seq

        self._legacy_sequences[cache_key] += 1
        return f"{ssot_type.value.upper()}-{self._legacy_sequences[cache_key]:03d}"

    def _resolve_optional_id(
        self,
        value: Optional[str],
        materialized: Dict[str, MaterializedOutput],
    ) -> Optional[str]:
        if not value:
            return None
        return self._resolve_single_ref(value, materialized)

    def _resolve_ids(
        self,
        values: List[str],
        materialized: Dict[str, MaterializedOutput],
    ) -> List[str]:
        return [self._resolve_single_ref(value, materialized) for value in values]

    def _resolve_versioned_refs(
        self,
        values: Optional[List[Dict[str, Any]]],
        materialized: Dict[str, MaterializedOutput],
    ) -> List[Dict[str, Any]]:
        resolved: List[Dict[str, Any]] = []
        for value in values or []:
            if not isinstance(value, dict):
                continue
            item = dict(value)
            if item.get("id"):
                item["id"] = self._resolve_single_ref(item["id"], materialized)
            resolved.append(item)
        return resolved

    def _resolve_source_refs(
        self,
        values: List[str],
        materialized: Dict[str, MaterializedOutput],
    ) -> List[str]:
        resolved = []
        for value in values:
            if "#" in value:
                key, anchor = value.split("#", 1)
                if key in materialized:
                    resolved.append(f"{materialized[key].artifact.id}#{anchor}")
                else:
                    resolved.append(value)
            else:
                resolved.append(self._resolve_single_ref(value, materialized))
        return resolved

    def _resolve_single_ref(
        self,
        value: str,
        materialized: Dict[str, MaterializedOutput],
    ) -> str:
        if value in materialized:
            return materialized[value].artifact.id
        # Also check upstream step outputs for symbol resolution
        if value in self._upstream_step_outputs:
            upstream_output = self._upstream_step_outputs[value]
            # Extract artifact ID from upstream output
            # Try business_output first, then structured_payload
            if isinstance(upstream_output, dict):
                business_output = upstream_output.get("business_output", {})
                if isinstance(business_output, dict):
                    artifact_id = business_output.get("src_id") or business_output.get("epic_id") or business_output.get("feat_id")
                    if artifact_id:
                        return artifact_id
                # Try structured_payload
                structured = upstream_output.get("structured_payload", {})
                if isinstance(structured, dict):
                    artifact_id = structured.get("src_id") or structured.get("epic_id") or structured.get("feat_id")
                    if artifact_id:
                        return artifact_id
        return value

    def _extract_local_keys(self, values: List[str]) -> List[str]:
        keys = []
        for value in values:
            if "#" in value:
                key = value.split("#", 1)[0]
                if key:
                    keys.append(key)
            else:
                keys.append(value)
        return keys

    def _is_literal_id(self, value: str) -> bool:
        prefixes = {item.value.upper() for item in SSOTType}
        prefixes.add("ART")
        return value.split("-", 1)[0].upper() in prefixes

    @classmethod
    def load_contract_file(cls, path: Path) -> Dict[str, Any]:
        text = Path(path).read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            return json.loads(text)
        import yaml

        return yaml.safe_load(text) or {}
