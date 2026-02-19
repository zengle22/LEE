import sqlite3
from pathlib import Path

from lee.cli.commands.run import _get_progress_snapshot


def test_get_progress_snapshot_reads_counts(tmp_path: Path) -> None:
    db_dir = tmp_path / ".workflow"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "orchestrator.db"

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE workflow_instances (
            id TEXT PRIMARY KEY,
            status TEXT,
            current_step TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE task_executions (
            id TEXT PRIMARY KEY,
            workflow_id TEXT,
            status TEXT
        )
        """
    )
    cur.execute(
        "INSERT INTO workflow_instances (id, status, current_step) VALUES (?, ?, ?)",
        ("wf_task_x", "running", "s1"),
    )
    cur.executemany(
        "INSERT INTO task_executions (id, workflow_id, status) VALUES (?, ?, ?)",
        [
            ("t1", "wf_task_x", "completed"),
            ("t2", "wf_task_x", "completed"),
            ("t3", "wf_task_x", "running"),
            ("t4", "wf_task_x", "failed"),
        ],
    )
    conn.commit()
    conn.close()

    snap = _get_progress_snapshot(tmp_path, "wf_task_x")
    assert snap is not None
    assert snap["status"] == "running"
    assert snap["current_step"] == "s1"
    assert snap["completed"] == 2
    assert snap["running"] == 1
    assert snap["failed"] == 1
