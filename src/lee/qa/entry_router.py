"""Canonical QA execution entry router."""

from __future__ import annotations

import inspect
import uuid
from typing import Awaitable, Callable, Optional, Union

from lee.orchestrator.execution.artifacts.id_parser import parse_parent

from .bypass_blocker import BypassBlocker
from .error_codes import QAEntryErrorCode, get_error_definition
from .schemas import (
    AuditAction,
    AuditEntry,
    ChainValidationResult,
    ExecutionPath,
    ExecutionRequest,
    ExecutionResponse,
    ExecutionStatus,
    SSOTAxisBinding,
)

Validator = Callable[[str], Union[Awaitable[ChainValidationResult], ChainValidationResult]]
AuditSink = Callable[[AuditEntry], Union[Awaitable[Optional[str]], Optional[str]]]


class EntryRouter:
    """Route QA execution requests through the canonical TASK entry."""

    def __init__(
        self,
        *,
        bypass_blocker: Optional[BypassBlocker] = None,
        validator: Optional[Validator] = None,
        audit_sink: Optional[AuditSink] = None,
    ) -> None:
        self.bypass_blocker = bypass_blocker or BypassBlocker()
        self.validator = validator
        self.audit_sink = audit_sink

    async def route(self, request: ExecutionRequest) -> ExecutionResponse:
        """Validate and route a QA execution request."""

        path = self._derive_path(request.task_ref)
        detection = self.bypass_blocker.detect(request)
        if detection:
            audit_log_ref = await self._emit_audit(
                request=request,
                action=AuditAction.BYPASS_ATTEMPT,
                result="BLOCKED",
                path=path,
                error_code=detection.error_code,
            )
            return ExecutionResponse.blocked(
                detection.error_code,
                error_message=detection.message,
                audit_log_ref=audit_log_ref,
                path=path,
            )

        validation_result = await self._validate_chain(request.task_ref)
        validation_error_code = self._resolve_validation_error_code(validation_result)
        audit_log_ref = await self._emit_audit(
            request=request,
            action=AuditAction.VALIDATE,
            result="SUCCESS" if validation_result.passed else "FAILURE",
            path=path,
            error_code=validation_error_code,
        )
        status = ExecutionStatus.READY if validation_result.passed else ExecutionStatus.FAILED
        error_message = None
        if validation_error_code:
            error_message = get_error_definition(validation_error_code).message
        return ExecutionResponse(
            success=validation_result.passed,
            run_id=None,
            status=status,
            error_code=validation_error_code,
            error_message=error_message,
            audit_log_ref=audit_log_ref,
            validation_result=validation_result,
            path=path,
            axis_binding=SSOTAxisBinding(delivery_refs=path.as_list()),
        )

    async def _validate_chain(self, task_ref: str) -> ChainValidationResult:
        if not self.validator:
            return ChainValidationResult(passed=True)
        result = self.validator(task_ref)
        return await result if inspect.isawaitable(result) else result

    async def _emit_audit(
        self,
        *,
        request: ExecutionRequest,
        action: AuditAction,
        result: str,
        path: ExecutionPath,
        error_code,
    ) -> Optional[str]:
        if not self.audit_sink:
            return None
        audit_entry = AuditEntry.create(
            entry_id=f"AUDIT-{request.task_ref or 'UNKNOWN'}-{uuid.uuid4().hex[:8].upper()}",
            entry_source=request.entry_source,
            triggered_by=request.triggered_by,
            action=action,
            result=result,
            path=path,
            axis_binding=SSOTAxisBinding(delivery_refs=path.as_list()),
            error_code=error_code,
            execution_status=ExecutionStatus.BLOCKED if result == "BLOCKED" else ExecutionStatus.VALIDATING,
            client_info={"session_id": request.session_id or ""},
            metadata=request.metadata,
        )
        sink_result = self.audit_sink(audit_entry)
        return await sink_result if inspect.isawaitable(sink_result) else sink_result

    def _derive_path(self, task_ref: str) -> ExecutionPath:
        if not task_ref:
            return ExecutionPath()
        testplan_ref = parse_parent(task_ref)
        release_ref = parse_parent(testplan_ref) if testplan_ref else None
        return ExecutionPath(
            release_ref=release_ref,
            testplan_ref=testplan_ref,
            task_ref=task_ref,
        )

    @staticmethod
    def _resolve_validation_error_code(
        validation_result: ChainValidationResult,
    ) -> Optional[QAEntryErrorCode]:
        for error in validation_result.errors:
            try:
                return QAEntryErrorCode(error)
            except ValueError:
                continue
        return None
