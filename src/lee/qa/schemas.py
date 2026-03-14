"""Execution entry contracts and SSOT audit models for FEAT-143."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from lee.orchestrator.execution.artifacts.id_parser import parse_id

from .error_codes import QAEntryErrorCode


class EntrySource(str, Enum):
    """Supported execution entry sources."""

    CLI = "CLI"
    API = "API"
    UI = "UI"


class ExecutionStatus(str, Enum):
    """Lifecycle states for a single execution request."""

    PENDING = "pending"
    VALIDATING = "validating"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class AuditAction(str, Enum):
    """Actions that must be auditable for entry enforcement."""

    EXECUTE = "EXECUTE"
    VALIDATE = "VALIDATE"
    BYPASS_ATTEMPT = "BYPASS_ATTEMPT"


@dataclass(frozen=True)
class ExecutionPath:
    """Canonical RELEASE -> TESTPLAN -> TASK chain for a request."""

    release_ref: Optional[str] = None
    testplan_ref: Optional[str] = None
    task_ref: Optional[str] = None

    def as_list(self) -> List[str]:
        """Return the path as an ordered non-empty reference list."""

        return [item for item in (self.release_ref, self.testplan_ref, self.task_ref) if item]


@dataclass(frozen=True)
class SSOTAxisBinding:
    """Traceability binding across requirement, delivery, and evidence axes."""

    requirement_refs: List[str] = field(default_factory=list)
    delivery_refs: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChainValidationResult:
    """Execution chain validation outcome."""

    passed: bool
    task_exists: bool = False
    testplan_exists: bool = False
    release_exists: bool = False
    task_status_valid: bool = False
    testplan_status_valid: bool = False
    release_status_valid: bool = False
    errors: List[str] = field(default_factory=list)


@dataclass
class ExecutionRequest:
    """Normalized QA execution request contract."""

    task_ref: str
    triggered_by: str
    entry_source: EntrySource
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> Optional[QAEntryErrorCode]:
        """Perform contract-level validation before routing."""

        if not self.task_ref or not self.task_ref.strip():
            return QAEntryErrorCode.MISSING_TASK_REF
        parsed = parse_id(self.task_ref.strip())
        if not parsed.is_valid or parsed.prefix != "TASK":
            return QAEntryErrorCode.INVALID_TASK_REF_FORMAT
        if not parsed.parent_scope or not parsed.parent_scope.startswith("TESTPLAN-REL-"):
            return QAEntryErrorCode.INVALID_TASK_REF_FORMAT
        return None


@dataclass
class ExecutionResponse:
    """Normalized response returned by the QA entry gateway."""

    success: bool
    run_id: Optional[str]
    status: ExecutionStatus
    error_code: Optional[QAEntryErrorCode] = None
    error_message: Optional[str] = None
    audit_log_ref: Optional[str] = None
    validation_result: Optional[ChainValidationResult] = None
    path: ExecutionPath = field(default_factory=ExecutionPath)
    axis_binding: SSOTAxisBinding = field(default_factory=SSOTAxisBinding)

    @classmethod
    def blocked(
        cls,
        error_code: QAEntryErrorCode,
        *,
        error_message: str,
        audit_log_ref: Optional[str] = None,
        path: Optional[ExecutionPath] = None,
    ) -> "ExecutionResponse":
        """Create a blocked response for a rejected request."""

        return cls(
            success=False,
            run_id=None,
            status=ExecutionStatus.BLOCKED,
            error_code=error_code,
            error_message=error_message,
            audit_log_ref=audit_log_ref,
            path=path or ExecutionPath(),
        )


@dataclass
class AuditEntry:
    """Audit log payload for execution entry traceability."""

    entry_id: str
    timestamp: str
    entry_source: EntrySource
    triggered_by: str
    action: AuditAction
    result: str
    path: ExecutionPath
    axis_binding: SSOTAxisBinding
    error_code: Optional[QAEntryErrorCode] = None
    execution_status: Optional[ExecutionStatus] = None
    client_info: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        entry_id: str,
        entry_source: EntrySource,
        triggered_by: str,
        action: AuditAction,
        result: str,
        path: ExecutionPath,
        axis_binding: SSOTAxisBinding,
        error_code: Optional[QAEntryErrorCode] = None,
        execution_status: Optional[ExecutionStatus] = None,
        client_info: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AuditEntry":
        """Create an audit entry with a normalized UTC timestamp."""

        return cls(
            entry_id=entry_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            entry_source=entry_source,
            triggered_by=triggered_by,
            action=action,
            result=result,
            path=path,
            axis_binding=axis_binding,
            error_code=error_code,
            execution_status=execution_status,
            client_info=client_info or {},
            metadata=metadata or {},
        )
