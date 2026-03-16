"""QA entry error code registry for FEAT-143."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class QAEntryErrorCode(str, Enum):
    """Canonical QA entry enforcement error codes."""

    MISSING_TASK_REF = "QA-ENTRY-001"
    INVALID_TASK_REF_FORMAT = "QA-ENTRY-002"
    TASK_NOT_FOUND = "QA-ENTRY-003"
    TASK_PARENT_INVALID = "QA-ENTRY-004"
    TESTPLAN_NOT_FOUND = "QA-ENTRY-005"
    TESTPLAN_PARENT_INVALID = "QA-ENTRY-006"
    RELEASE_NOT_FOUND = "QA-ENTRY-007"
    RELEASE_STATUS_INVALID = "QA-ENTRY-008"
    TESTPLAN_STATUS_INVALID = "QA-ENTRY-009"
    TASK_STATUS_INVALID = "QA-ENTRY-010"
    BYPASS_ATTEMPT_DETECTED = "QA-ENTRY-011"
    AUDIT_LOG_FAILURE = "QA-ENTRY-012"


@dataclass(frozen=True)
class QAEntryErrorDefinition:
    """Structured metadata for a single QA entry error code."""

    code: QAEntryErrorCode
    slug: str
    message: str
    retryable: bool = False


ERROR_REGISTRY: Dict[QAEntryErrorCode, QAEntryErrorDefinition] = {
    QAEntryErrorCode.MISSING_TASK_REF: QAEntryErrorDefinition(
        code=QAEntryErrorCode.MISSING_TASK_REF,
        slug="MISSING_TASK_REF",
        message="执行请求缺少必需的 task_ref 参数",
    ),
    QAEntryErrorCode.INVALID_TASK_REF_FORMAT: QAEntryErrorDefinition(
        code=QAEntryErrorCode.INVALID_TASK_REF_FORMAT,
        slug="INVALID_TASK_REF_FORMAT",
        message="task_ref 格式无效，应为 TASK-TESTPLAN-REL-{semver}-*",
    ),
    QAEntryErrorCode.TASK_NOT_FOUND: QAEntryErrorDefinition(
        code=QAEntryErrorCode.TASK_NOT_FOUND,
        slug="TASK_NOT_FOUND",
        message="指定的 task 在 SSOT Registry 中不存在",
    ),
    QAEntryErrorCode.TASK_PARENT_INVALID: QAEntryErrorDefinition(
        code=QAEntryErrorCode.TASK_PARENT_INVALID,
        slug="TASK_PARENT_INVALID",
        message="task 的 parent_id 不指向有效的 TESTPLAN",
    ),
    QAEntryErrorCode.TESTPLAN_NOT_FOUND: QAEntryErrorDefinition(
        code=QAEntryErrorCode.TESTPLAN_NOT_FOUND,
        slug="TESTPLAN_NOT_FOUND",
        message="TESTPLAN 在 SSOT Registry 中不存在",
    ),
    QAEntryErrorCode.TESTPLAN_PARENT_INVALID: QAEntryErrorDefinition(
        code=QAEntryErrorCode.TESTPLAN_PARENT_INVALID,
        slug="TESTPLAN_PARENT_INVALID",
        message="testplan 的 parent_id 不指向有效的 RELEASE",
    ),
    QAEntryErrorCode.RELEASE_NOT_FOUND: QAEntryErrorDefinition(
        code=QAEntryErrorCode.RELEASE_NOT_FOUND,
        slug="RELEASE_NOT_FOUND",
        message="RELEASE 在 SSOT Registry 中不存在",
    ),
    QAEntryErrorCode.RELEASE_STATUS_INVALID: QAEntryErrorDefinition(
        code=QAEntryErrorCode.RELEASE_STATUS_INVALID,
        slug="RELEASE_STATUS_INVALID",
        message="RELEASE 状态不满足执行条件 (需 active/frozen)",
        retryable=True,
    ),
    QAEntryErrorCode.TESTPLAN_STATUS_INVALID: QAEntryErrorDefinition(
        code=QAEntryErrorCode.TESTPLAN_STATUS_INVALID,
        slug="TESTPLAN_STATUS_INVALID",
        message="TESTPLAN 状态不满足执行条件 (需 committed/in_progress)",
        retryable=True,
    ),
    QAEntryErrorCode.TASK_STATUS_INVALID: QAEntryErrorDefinition(
        code=QAEntryErrorCode.TASK_STATUS_INVALID,
        slug="TASK_STATUS_INVALID",
        message="TASK 状态不满足执行条件 (非 blocked/dropped)",
        retryable=True,
    ),
    QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED: QAEntryErrorDefinition(
        code=QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED,
        slug="BYPASS_ATTEMPT_DETECTED",
        message="检测到旁路执行尝试，请求已阻断",
    ),
    QAEntryErrorCode.AUDIT_LOG_FAILURE: QAEntryErrorDefinition(
        code=QAEntryErrorCode.AUDIT_LOG_FAILURE,
        slug="AUDIT_LOG_FAILURE",
        message="审计日志记录失败",
        retryable=True,
    ),
}


def get_error_definition(code: str | QAEntryErrorCode) -> QAEntryErrorDefinition:
    """Return canonical metadata for a QA entry error code."""

    normalized = code if isinstance(code, QAEntryErrorCode) else QAEntryErrorCode(code)
    return ERROR_REGISTRY[normalized]


def is_known_error_code(code: str) -> bool:
    """Whether the provided code belongs to the QA entry registry."""

    try:
        QAEntryErrorCode(code)
    except ValueError:
        return False
    return True
