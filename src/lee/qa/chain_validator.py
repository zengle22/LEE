"""RELEASE -> TESTPLAN -> TASK chain validation for QA execution entry."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from lee.orchestrator.execution.artifacts.manager import ArtifactManager
from lee.orchestrator.execution.artifacts.models import ArtifactMetadata
from lee.orchestrator.execution.artifacts.ssot_files import parse_front_matter
from lee.orchestrator.execution.artifacts.types import ArtifactStatus, ArtifactType

from .cache import TTLCache
from .error_codes import QAEntryErrorCode
from .schemas import ChainValidationResult


class ChainValidator:
    """Validate a QA execution chain against the SSOT registry."""

    _VALID_RELEASE_STATUSES = {"active", "frozen"}
    _VALID_TESTPLAN_STATUSES = {"active", "frozen", "committed", "in_progress"}
    _VALID_TASK_STATUSES = {"active", "frozen", "todo", "doing", "in_progress"}

    def __init__(self, artifact_manager: ArtifactManager, ttl_seconds: int = 60) -> None:
        self.artifact_manager = artifact_manager
        self.cache = TTLCache[ChainValidationResult](ttl_seconds=ttl_seconds)

    async def validate_chain(self, task_ref: str) -> ChainValidationResult:
        """Validate the full task -> testplan -> release chain."""

        cached = self.cache.get(task_ref)
        if cached:
            return cached

        errors: List[str] = []
        task = self._resolve_artifact(task_ref)
        if not task:
            result = self._result(errors=[QAEntryErrorCode.TASK_NOT_FOUND.value])
            self.cache.set(task_ref, result)
            return result

        task_parent = self._parent_id(task)
        if not task_parent or not task_parent.startswith("TESTPLAN-REL-"):
            result = self._result(task_exists=True, errors=[QAEntryErrorCode.TASK_PARENT_INVALID.value])
            self.cache.set(task_ref, result)
            return result

        testplan = self._resolve_artifact(task_parent)
        if not testplan:
            result = self._result(
                task_exists=True,
                errors=[QAEntryErrorCode.TESTPLAN_NOT_FOUND.value],
            )
            self.cache.set(task_ref, result)
            return result

        release_ref = self._parent_id(testplan)
        if not release_ref or not release_ref.startswith("REL-"):
            result = self._result(
                task_exists=True,
                testplan_exists=True,
                errors=[QAEntryErrorCode.TESTPLAN_PARENT_INVALID.value],
            )
            self.cache.set(task_ref, result)
            return result

        release = self._resolve_artifact(release_ref)
        if not release:
            result = self._result(
                task_exists=True,
                testplan_exists=True,
                errors=[QAEntryErrorCode.RELEASE_NOT_FOUND.value],
            )
            self.cache.set(task_ref, result)
            return result

        if self._status_of(release) not in self._VALID_RELEASE_STATUSES:
            errors.append(QAEntryErrorCode.RELEASE_STATUS_INVALID.value)
        if self._status_of(testplan) not in self._VALID_TESTPLAN_STATUSES:
            errors.append(QAEntryErrorCode.TESTPLAN_STATUS_INVALID.value)
        if self._status_of(task) not in self._VALID_TASK_STATUSES:
            errors.append(QAEntryErrorCode.TASK_STATUS_INVALID.value)
        if not self._has_valid_delivery_trace(task):
            errors.append("TASK_DERIVED_FROM_INVALID")

        result = self._result(
            task_exists=True,
            testplan_exists=True,
            release_exists=True,
            task_status_valid=QAEntryErrorCode.TASK_STATUS_INVALID.value not in errors,
            testplan_status_valid=QAEntryErrorCode.TESTPLAN_STATUS_INVALID.value not in errors,
            release_status_valid=QAEntryErrorCode.RELEASE_STATUS_INVALID.value not in errors,
            errors=errors,
        )
        self.cache.set(task_ref, result)
        return result

    def resolve_artifact(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """Resolve an artifact from the registry or checked-in SSOT files."""

        return self._resolve_artifact(artifact_id)

    def _resolve_artifact(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        artifact = self.artifact_manager.registry.get(artifact_id)
        if artifact:
            return artifact
        return self._load_from_disk(artifact_id)

    def _load_from_disk(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        pattern = f"{artifact_id}__*.md"
        for path in self.artifact_manager.project_root.rglob(pattern):
            front_matter, _ = parse_front_matter(path)
            if front_matter.get("id") != artifact_id:
                continue
            properties = dict(front_matter.get("properties") or {})
            properties["parent_id"] = front_matter.get("parent_id")
            properties["derived_from_ids"] = front_matter.get("derived_from_ids", [])
            properties["source_refs"] = front_matter.get("source_refs", [])
            properties["ssot_type"] = front_matter.get("ssot_type")
            return ArtifactMetadata(
                id=artifact_id,
                type=ArtifactType.DOCUMENT,
                category="ssot_object",
                status=ArtifactStatus(front_matter.get("status", "active").upper()),
                path=path.relative_to(self.artifact_manager.project_root).as_posix(),
                path_root=".",
                run_id="",
                title=front_matter.get("title", artifact_id),
                properties=properties,
            )
        return None

    def _parent_id(self, artifact: ArtifactMetadata) -> Optional[str]:
        return (artifact.properties or {}).get("parent_id")

    def _status_of(self, artifact: ArtifactMetadata) -> str:
        explicit = (artifact.properties or {}).get("plan_status") or (artifact.properties or {}).get("task_state")
        if explicit:
            return str(explicit).lower()
        return artifact.status.value.lower()

    def _has_valid_delivery_trace(self, artifact: ArtifactMetadata) -> bool:
        derived_from_ids = (artifact.properties or {}).get("derived_from_ids", [])
        normalized = [item.get("id") if isinstance(item, dict) else item for item in derived_from_ids]
        return any(str(item).startswith(("FEAT-", "TESTSET-")) for item in normalized if item)

    def _result(
        self,
        *,
        task_exists: bool = False,
        testplan_exists: bool = False,
        release_exists: bool = False,
        task_status_valid: bool = False,
        testplan_status_valid: bool = False,
        release_status_valid: bool = False,
        errors: Optional[List[str]] = None,
    ) -> ChainValidationResult:
        payload_errors = errors or []
        return ChainValidationResult(
            passed=len(payload_errors) == 0,
            task_exists=task_exists,
            testplan_exists=testplan_exists,
            release_exists=release_exists,
            task_status_valid=task_status_valid,
            testplan_status_valid=testplan_status_valid,
            release_status_valid=release_status_valid,
            errors=payload_errors,
        )
