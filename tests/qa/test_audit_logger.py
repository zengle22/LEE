import asyncio
from pathlib import Path

from lee.qa import (
    AuditAction,
    AuditEntry,
    AuditLogger,
    AuditQuery,
    EntrySource,
    ExecutionPath,
    ExecutionStatus,
    QAEntryErrorCode,
    SSOTAxisBinding,
)


def test_audit_logger_dual_writes_and_queries(tmp_path: Path):
    logger = AuditLogger(
        db_path=tmp_path / "audit" / "audit_log.db",
        archive_path=tmp_path / "audit" / "audit_log.ndjson",
    )
    entry = AuditEntry.create(
        entry_id="AUDIT-001",
        entry_source=EntrySource.CLI,
        triggered_by="qa-user",
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
        execution_status=ExecutionStatus.COMPLETED,
    )

    async def scenario():
        await logger.start()
        audit_ref = await logger.log_execution_request(entry)
        await logger._queue.join()
        by_task = await logger.query_by_task("TASK-TESTPLAN-REL-1.4.0-001")
        by_release = await logger.query(AuditQuery(release_ref="REL-1.4.0"))
        await logger.stop()
        return audit_ref, by_task, by_release

    audit_ref, by_task, by_release = asyncio.run(scenario())

    assert audit_ref == "AUDIT-001"
    assert len(by_task) == 1
    assert by_task[0].path.task_ref == "TASK-TESTPLAN-REL-1.4.0-001"
    assert len(by_release) == 1
    assert logger.archive_path.exists()
    assert logger.db_path.exists()


def test_audit_logger_restores_error_code_enum_from_storage(tmp_path: Path):
    logger = AuditLogger(
        db_path=tmp_path / "audit" / "audit_log.db",
        archive_path=tmp_path / "audit" / "audit_log.ndjson",
    )
    entry = AuditEntry.create(
        entry_id="AUDIT-ERR-001",
        entry_source=EntrySource.API,
        triggered_by="system",
        action=AuditAction.BYPASS_ATTEMPT,
        result="BLOCKED",
        path=ExecutionPath(task_ref="TASK-FEAT-143-001"),
        axis_binding=SSOTAxisBinding(delivery_refs=["TASK-FEAT-143-001"]),
        error_code=QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED,
        execution_status=ExecutionStatus.BLOCKED,
    )

    async def scenario():
        await logger.start()
        await logger.log_execution_request(entry)
        await logger._queue.join()
        rows = await logger.query(AuditQuery(execution_id="AUDIT-ERR-001"))
        await logger.stop()
        return rows

    rows = asyncio.run(scenario())

    assert rows[0].error_code == QAEntryErrorCode.BYPASS_ATTEMPT_DETECTED


def test_audit_logger_filters_by_triggered_by_and_time_range(tmp_path: Path):
    logger = AuditLogger(
        db_path=tmp_path / "audit" / "audit_log.db",
        archive_path=tmp_path / "audit" / "audit_log.ndjson",
    )
    first = AuditEntry.create(
        entry_id="AUDIT-USER-001",
        entry_source=EntrySource.CLI,
        triggered_by="alice",
        action=AuditAction.EXECUTE,
        result="SUCCESS",
        path=ExecutionPath(task_ref="TASK-TESTPLAN-REL-1.4.0-001"),
        axis_binding=SSOTAxisBinding(delivery_refs=["TASK-TESTPLAN-REL-1.4.0-001"]),
        execution_status=ExecutionStatus.COMPLETED,
    )
    second = AuditEntry.create(
        entry_id="AUDIT-USER-002",
        entry_source=EntrySource.CLI,
        triggered_by="bob",
        action=AuditAction.EXECUTE,
        result="SUCCESS",
        path=ExecutionPath(task_ref="TASK-TESTPLAN-REL-1.4.0-002"),
        axis_binding=SSOTAxisBinding(delivery_refs=["TASK-TESTPLAN-REL-1.4.0-002"]),
        execution_status=ExecutionStatus.COMPLETED,
    )

    async def scenario():
        await logger.start()
        await logger.log_execution_request(first)
        await logger.log_execution_request(second)
        await logger._queue.join()
        rows = await logger.query(
            AuditQuery(
                triggered_by="alice",
                started_at=first.timestamp,
                ended_at=second.timestamp,
            )
        )
        await logger.stop()
        return rows

    rows = asyncio.run(scenario())

    assert len(rows) == 1
    assert rows[0].triggered_by == "alice"


def test_audit_logger_keeps_distinct_entries_for_same_task(tmp_path: Path):
    logger = AuditLogger(
        db_path=tmp_path / "audit" / "audit_log.db",
        archive_path=tmp_path / "audit" / "audit_log.ndjson",
    )
    first = AuditEntry.create(
        entry_id="AUDIT-TASK-001-A",
        entry_source=EntrySource.CLI,
        triggered_by="alice",
        action=AuditAction.EXECUTE,
        result="SUCCESS",
        path=ExecutionPath(task_ref="TASK-TESTPLAN-REL-1.4.0-001"),
        axis_binding=SSOTAxisBinding(delivery_refs=["TASK-TESTPLAN-REL-1.4.0-001"]),
        execution_status=ExecutionStatus.COMPLETED,
    )
    second = AuditEntry.create(
        entry_id="AUDIT-TASK-001-B",
        entry_source=EntrySource.CLI,
        triggered_by="bob",
        action=AuditAction.EXECUTE,
        result="SUCCESS",
        path=ExecutionPath(task_ref="TASK-TESTPLAN-REL-1.4.0-001"),
        axis_binding=SSOTAxisBinding(delivery_refs=["TASK-TESTPLAN-REL-1.4.0-001"]),
        execution_status=ExecutionStatus.COMPLETED,
    )

    async def scenario():
        await logger.start()
        await logger.log_execution_request(first)
        await logger.log_execution_request(second)
        await logger._queue.join()
        rows = await logger.query_by_task("TASK-TESTPLAN-REL-1.4.0-001")
        await logger.stop()
        return rows

    rows = asyncio.run(scenario())

    assert len(rows) == 2
    assert [row.triggered_by for row in rows] == ["alice", "bob"]
