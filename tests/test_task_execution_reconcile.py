from datetime import datetime
import asyncio

from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    WorkflowInstance,
    WorkflowLevel,
    WorkflowStatus,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore


def test_fail_running_task_executions_updates_only_running(tmp_path):
    async def _run() -> None:
        db_path = tmp_path / "orchestrator.db"
        store = SQLiteStore(str(db_path))
        await store.connect()

        wf = WorkflowInstance(
            id="wf_task_reconcile",
            level=WorkflowLevel.TASK,
            template_id="demo",
            status=WorkflowStatus.RUNNING,
        )
        await store.create_workflow(wf)

        await store.create_task_execution(
            TaskExecution(
                id="exec_running",
                workflow_id=wf.id,
                step_name="s1",
                executor_type="claude_code",
                status=TaskExecutionStatus.RUNNING,
                started_at=datetime.now(),
            )
        )
        await store.create_task_execution(
            TaskExecution(
                id="exec_completed",
                workflow_id=wf.id,
                step_name="s0",
                executor_type="claude_code",
                status=TaskExecutionStatus.COMPLETED,
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )
        )

        changed = await store.fail_running_task_executions(
            wf.id,
            error_message="Workflow paused; interrupted",
        )
        assert changed == 1

        executions = await store.get_task_executions(wf.id)
        by_id = {e.id: e for e in executions}
        assert by_id["exec_running"].status == TaskExecutionStatus.FAILED
        assert "paused" in (by_id["exec_running"].error_message or "").lower()
        assert by_id["exec_running"].completed_at is not None
        assert by_id["exec_completed"].status == TaskExecutionStatus.COMPLETED

        await store.close()

    asyncio.run(_run())
