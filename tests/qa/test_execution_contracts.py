import asyncio
from pathlib import Path

from lee.qa import (
    AuditAction,
    AuditEntry,
    BypassBlocker,
    BypassScenario,
    ChainValidator,
    EntrySource,
    EntryRouter,
    ExecutionPath,
    ExecutionRequest,
    ExecutionResponse,
    ExecutionStatus,
    QAEntryErrorCode,
    SSOTAxisBinding,
    get_error_definition,
    is_known_error_code,
)
from lee.orchestrator.execution.artifacts.manager import ArtifactManager
from lee.orchestrator.execution.artifacts.types import SSOTType


def test_execution_request_requires_taskplan_scoped_task_ref():
    request = ExecutionRequest(
        task_ref="TASK-TESTPLAN-REL-1.4.0-001",
        triggered_by="qa-user",
        entry_source=EntrySource.CLI,
    )

    assert request.validate() is None


def test_execution_request_rejects_feat_scoped_task_ref():
    request = ExecutionRequest(
        task_ref="TASK-FEAT-143-001",
        triggered_by="qa-user",
        entry_source=EntrySource.CLI,
    )

    assert request.validate() == QAEntryErrorCode.INVALID_TASK_REF_FORMAT


def test_execution_request_rejects_missing_task_ref():
    request = ExecutionRequest(
        task_ref="",
        triggered_by="qa-user",
        entry_source=EntrySource.API,
    )

    assert request.validate() == QAEntryErrorCode.MISSING_TASK_REF


def test_execution_response_blocked_marks_request_as_blocked():
    response = ExecutionResponse.blocked(
        QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED,
        error_message="detected bypass",
    )

    assert response.success is False
    assert response.status == ExecutionStatus.BLOCKED
    assert response.error_code == QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED


def test_audit_entry_captures_three_axis_binding_and_path():
    entry = AuditEntry.create(
        entry_id="AUDIT-001",
        entry_source=EntrySource.UI,
        triggered_by="operator",
        action=AuditAction.EXECUTE,
        result="SUCCESS",
        path=ExecutionPath(
            release_ref="REL-1.4.0",
            testplan_ref="TESTPLAN-REL-1.4.0",
            task_ref="TASK-TESTPLAN-REL-1.4.0-001",
        ),
        axis_binding=SSOTAxisBinding(
            requirement_refs=["FEAT-143"],
            delivery_refs=["REL-1.4.0", "TESTPLAN-REL-1.4.0", "TASK-TESTPLAN-REL-1.4.0-001"],
            evidence_refs=["REPORT-REL-1.4.0-TEST-001"],
        ),
        execution_status=ExecutionStatus.RUNNING,
    )

    assert entry.path.as_list() == [
        "REL-1.4.0",
        "TESTPLAN-REL-1.4.0",
        "TASK-TESTPLAN-REL-1.4.0-001",
    ]
    assert entry.axis_binding.requirement_refs == ["FEAT-143"]
    assert entry.execution_status == ExecutionStatus.RUNNING
    assert entry.timestamp.endswith("+00:00")


def test_error_registry_exposes_canonical_metadata():
    definition = get_error_definition("QA-ENTRY-011")

    assert definition.code == QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED
    assert definition.slug == "BYPASS_ATTEMPT_DETECTED"
    assert is_known_error_code("QA-ENTRY-012") is True
    assert is_known_error_code("QA-ENTRY-999") is False


def test_bypass_blocker_detects_explicit_bypass_flag():
    blocker = BypassBlocker()
    request = ExecutionRequest(
        task_ref="TASK-TESTPLAN-REL-1.4.0-001",
        triggered_by="qa-user",
        entry_source=EntrySource.CLI,
        metadata={"skip_chain_validation": True},
    )

    detection = blocker.detect(request)

    assert detection is not None
    assert detection.scenario == BypassScenario.EXPLICIT_BYPASS_FLAG
    assert detection.error_code == QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED


def test_entry_router_blocks_feat_scoped_task_request():
    router = EntryRouter()
    request = ExecutionRequest(
        task_ref="TASK-FEAT-143-001",
        triggered_by="qa-user",
        entry_source=EntrySource.API,
    )

    response = asyncio.run(router.route(request))

    assert response.success is False
    assert response.status == ExecutionStatus.BLOCKED
    assert response.error_code == QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED


def test_entry_router_returns_ready_for_valid_taskplan_task():
    router = EntryRouter()
    request = ExecutionRequest(
        task_ref="TASK-TESTPLAN-REL-1.4.0-001",
        triggered_by="qa-user",
        entry_source=EntrySource.CLI,
    )

    response = asyncio.run(router.route(request))

    assert response.success is True
    assert response.status == ExecutionStatus.READY
    assert response.path.release_ref == "REL-1.4.0"
    assert response.path.testplan_ref == "TESTPLAN-REL-1.4.0"


def test_chain_validator_passes_for_valid_release_plan_task_chain(tmp_path: Path):
    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)
    manager.create_ssot(
        ssot_type=SSOTType.RELEASE,
        title="Release 1.4.0",
        content="# release",
        run_id="qa-chain",
        formal_id="REL-1.4.0",
        properties={"release_version": "1.4.0"},
        derived_from=[{"id": "FEAT-143", "version": "v1"}],
    )
    manager.create_ssot(
        ssot_type=SSOTType.TESTPLAN,
        title="Test plan 1.4.0",
        content="# testplan",
        run_id="qa-chain",
        formal_id="TESTPLAN-REL-1.4.0",
        parent_id="REL-1.4.0",
        derived_from=[
            {"id": "FEAT-143", "version": "v1"},
            {"id": "TESTSET-FEAT-143", "version": "v1"},
        ],
        properties={"environment_matrix": ["staging"]},
    )
    manager.create_ssot(
        ssot_type=SSOTType.TASK,
        title="Task 001",
        content="# task",
        run_id="qa-chain",
        formal_id="TASK-TESTPLAN-REL-1.4.0-001",
        parent_id="TESTPLAN-REL-1.4.0",
        derived_from=[{"id": "FEAT-143", "version": "v1"}],
        properties={"slice_key": "qa-entry"},
    )
    validator = ChainValidator(manager)

    result = asyncio.run(validator.validate_chain("TASK-TESTPLAN-REL-1.4.0-001"))

    assert result.passed is True
    assert result.release_exists is True
    assert result.testplan_exists is True
    assert result.task_exists is True


def test_chain_validator_uses_disk_fallback_when_registry_misses_task(tmp_path: Path):
    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)
    spec_dir = tmp_path / "spec" / "delivery" / "testplans"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "spec" / "delivery" / "releases").mkdir(parents=True, exist_ok=True)
    task_dir = tmp_path / "spec" / "tasks" / "TESTPLAN-REL-1.4.0"
    task_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "spec" / "delivery" / "releases" / "REL-1.4.0__release.md").write_text(
        "---\nid: REL-1.4.0\nssot_type: release\ntitle: Release\nstatus: frozen\nversion: v1\nparent_id: null\nderived_from_ids:\n- id: FEAT-143\n  version: v1\nsource_refs: []\nproperties:\n  release_version: 1.4.0\n---\n",
        encoding="utf-8",
    )
    (spec_dir / "TESTPLAN-REL-1.4.0__plan.md").write_text(
        "---\nid: TESTPLAN-REL-1.4.0\nssot_type: testplan\ntitle: Plan\nstatus: frozen\nversion: v1\nparent_id: REL-1.4.0\nderived_from_ids:\n- id: FEAT-143\n  version: v1\n- id: TESTSET-FEAT-143\n  version: v1\nsource_refs: []\nproperties:\n  environment_matrix:\n  - staging\n---\n",
        encoding="utf-8",
    )
    (task_dir / "TASK-TESTPLAN-REL-1.4.0-001__task.md").write_text(
        "---\nid: TASK-TESTPLAN-REL-1.4.0-001\nssot_type: task\ntitle: Task\nstatus: active\nversion: v1\nparent_id: TESTPLAN-REL-1.4.0\nderived_from_ids:\n- id: FEAT-143\n  version: v1\nsource_refs: []\nproperties:\n  slice_key: qa-entry\n---\n",
        encoding="utf-8",
    )
    validator = ChainValidator(manager)

    result = asyncio.run(validator.validate_chain("TASK-TESTPLAN-REL-1.4.0-001"))

    assert result.passed is True


def test_chain_validator_rejects_task_without_testplan_parent(tmp_path: Path):
    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)
    manager.create_ssot(
        ssot_type=SSOTType.TASK,
        title="Bad task",
        content="# task",
        run_id="qa-chain",
        formal_id="TASK-FEAT-143-001",
        parent_id="FEAT-143",
        derived_from=[{"id": "FEAT-143", "version": "v1"}],
        properties={"slice_key": "qa-entry"},
    )
    validator = ChainValidator(manager)

    result = asyncio.run(validator.validate_chain("TASK-FEAT-143-001"))

    assert result.passed is False
    assert QAEntryErrorCode.TASK_PARENT_INVALID.value in result.errors


def test_chain_validator_rejects_invalid_release_testplan_and_task_states(tmp_path: Path):
    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)
    manager.create_ssot(
        ssot_type=SSOTType.RELEASE,
        title="Release 1.4.1",
        content="# release",
        run_id="qa-chain",
        formal_id="REL-1.4.1",
        properties={"release_version": "1.4.1", "plan_status": "draft"},
        derived_from=[{"id": "FEAT-143", "version": "v1"}],
    )
    manager.create_ssot(
        ssot_type=SSOTType.TESTPLAN,
        title="Plan 1.4.1",
        content="# plan",
        run_id="qa-chain",
        formal_id="TESTPLAN-REL-1.4.1",
        parent_id="REL-1.4.1",
        derived_from=[
            {"id": "FEAT-143", "version": "v1"},
            {"id": "TESTSET-FEAT-143", "version": "v1"},
        ],
        properties={"environment_matrix": ["staging"], "plan_status": "draft"},
    )
    manager.create_ssot(
        ssot_type=SSOTType.TASK,
        title="Task 1.4.1",
        content="# task",
        run_id="qa-chain",
        formal_id="TASK-TESTPLAN-REL-1.4.1-001",
        parent_id="TESTPLAN-REL-1.4.1",
        derived_from=[{"id": "FEAT-143", "version": "v1"}],
        properties={"slice_key": "qa-entry", "task_state": "blocked"},
    )
    validator = ChainValidator(manager)

    result = asyncio.run(validator.validate_chain("TASK-TESTPLAN-REL-1.4.1-001"))

    assert result.passed is False
    assert QAEntryErrorCode.RELEASE_STATUS_INVALID.value in result.errors
    assert QAEntryErrorCode.TESTPLAN_STATUS_INVALID.value in result.errors
    assert QAEntryErrorCode.TASK_STATUS_INVALID.value in result.errors
