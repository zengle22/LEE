"""
SSOT agent output contract materializer.

将 agent/contract 声明的 outputs[*] 实例化为正式 SSOT 对象或普通 artifact。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.execution.validators.schema_validator import SchemaValidator

from .manager import ArtifactManager
from .models import ArtifactMetadata
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
    ) -> None:
        self.manager = manager
        self.schema_path = Path(schema_path or DEFAULT_SSOT_CONTRACT_SCHEMA)
        self._validator = SchemaValidator(project_dir=str(FRAMEWORK_ROOT))

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
            artifact = self.manager.create_ssot(
                ssot_type=SSOTType(output["ssot_type"]),
                title=title,
                content=content,
                run_id=run_id,
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
