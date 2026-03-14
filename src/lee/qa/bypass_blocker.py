"""Bypass detection rules for QA execution entry enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from lee.orchestrator.execution.artifacts.id_parser import parse_id

from .error_codes import QAEntryErrorCode, get_error_definition
from .schemas import ExecutionRequest


class BypassScenario(str, Enum):
    """Canonical bypass detection scenarios for FEAT-143."""

    MISSING_TASK_REF = "BYPASS-001"
    INVALID_TASK_REF = "BYPASS-002"
    NON_TESTPLAN_TASK = "BYPASS-003"
    EXPLICIT_BYPASS_FLAG = "BYPASS-004"


@dataclass(frozen=True)
class BypassDetection:
    """Structured bypass detection result."""

    scenario: BypassScenario
    error_code: QAEntryErrorCode
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class BypassBlocker:
    """Detect requests that attempt to bypass the canonical QA entry path."""

    _BYPASS_METADATA_KEYS = {
        "bypass_validation",
        "direct_execution",
        "skip_chain_validation",
        "force_run",
        "raw_case_ref",
        "testset_ref",
        "feat_ref",
        "tc_ref",
    }

    def detect(self, request: ExecutionRequest) -> Optional[BypassDetection]:
        """Return a structured detection when the request violates entry rules."""

        if not request.task_ref or not request.task_ref.strip():
            return self._build_detection(
                BypassScenario.MISSING_TASK_REF,
                QAEntryErrorCode.MISSING_TASK_REF,
            )

        parsed = parse_id(request.task_ref.strip())
        if not parsed.is_valid or parsed.prefix != "TASK":
            return self._build_detection(
                BypassScenario.INVALID_TASK_REF,
                QAEntryErrorCode.INVALID_TASK_REF_FORMAT,
                task_ref=request.task_ref,
            )

        if not parsed.parent_scope or not parsed.parent_scope.startswith("TESTPLAN-REL-"):
            return self._build_detection(
                BypassScenario.NON_TESTPLAN_TASK,
                QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED,
                task_ref=request.task_ref,
                parent_scope=parsed.parent_scope,
            )

        bypass_key = self._first_bypass_metadata_key(request.metadata)
        if bypass_key:
            return self._build_detection(
                BypassScenario.EXPLICIT_BYPASS_FLAG,
                QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED,
                task_ref=request.task_ref,
                bypass_key=bypass_key,
            )

        return None

    def _first_bypass_metadata_key(self, metadata: Dict[str, Any]) -> Optional[str]:
        for key in self._BYPASS_METADATA_KEYS:
            if key in metadata and metadata.get(key):
                return key
        return None

    def _build_detection(
        self,
        scenario: BypassScenario,
        error_code: QAEntryErrorCode,
        **details: Any,
    ) -> BypassDetection:
        definition = get_error_definition(error_code)
        return BypassDetection(
            scenario=scenario,
            error_code=error_code,
            message=definition.message,
            details=details,
        )
