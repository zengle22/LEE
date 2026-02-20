import sqlite3
from pathlib import Path

from click.testing import CliRunner

import lee.cli.commands.gates_cmd as gates_module


def _prepare_db(tmp_path: Path) -> None:
    db_dir = tmp_path / ".workflow"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "orchestrator.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE gate_approvals (
            workflow_id TEXT,
            gate_id TEXT,
            step_id TEXT,
            status TEXT,
            approver TEXT,
            comments TEXT,
            created_at TEXT,
            decided_at TEXT,
            approval_criteria TEXT,
            reviewers TEXT,
            default_reject_action TEXT,
            default_reject_target TEXT
        )
        """
    )
    cur.execute(
        """
        INSERT INTO gate_approvals (
            workflow_id, gate_id, step_id, status, approver, comments,
            created_at, decided_at, approval_criteria, reviewers,
            default_reject_action, default_reject_target
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "wf_task_x",
            "gate_s1_review",
            "s1_review",
            "pending",
            None,
            None,
            "2026-02-19T15:00:00",
            None,
            '[{"name":"commit plan valid","description":"plan file exists"}]',
            '[{"id":"zeng","role":"owner"}]',
            "rollback",
            "s1_review",
        ),
    )
    conn.commit()
    conn.close()


def test_gates_decide_approve(monkeypatch, tmp_path: Path) -> None:
    _prepare_db(tmp_path)
    calls = []

    def fake_pm_workflow(action: str, **kwargs):
        calls.append((action, kwargs))
        return {"message": "ok"}

    monkeypatch.setattr(gates_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        gates_module.gates,
        ["decide", "wf_task_x", "--project-dir", str(tmp_path), "--approver", "zeng"],
        input="approve\nlooks good\n",
    )

    assert result.exit_code == 0, result.output
    assert calls
    action, kwargs = calls[0]
    assert action == "approve_gate"
    assert kwargs["workflow_id"] == "wf_task_x"
    assert kwargs["gate_id"] == "gate_s1_review"
    assert kwargs["approver"] == "zeng"

