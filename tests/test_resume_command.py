import sqlite3
from pathlib import Path

from click.testing import CliRunner

import lee.cli.commands.resume as resume_module
import lee.cli.main as main_module
from lee.cli.main import cli


def _prepare_resume_db(tmp_path: Path) -> Path:
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
            current_step TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    return db_path


def test_resume_command_uses_explicit_workflow_id(monkeypatch, tmp_path: Path) -> None:
    _prepare_resume_db(tmp_path)
    calls = []

    def fake_pm_workflow(action: str, **kwargs):
        calls.append((action, kwargs))
        assert action == "resume"
        return {"message": "Workflow wf_task_1 resumed"}

    monkeypatch.setattr(resume_module, "pm_workflow", fake_pm_workflow)
    main_module._register_commands()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["resume", "wf_task_1", "--project-dir", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert "resumed" in result.output
    assert calls[0][1]["workflow_id"] == "wf_task_1"


def test_resume_command_picks_latest_paused_workflow(monkeypatch, tmp_path: Path) -> None:
    db_path = _prepare_resume_db(tmp_path)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO workflow_instances (id, status, current_step, created_at) VALUES (?, ?, ?, ?)",
        [
            ("wf_old", "paused", "step_old", "2026-03-11T10:00:00"),
            ("wf_new", "blocked", "step_new", "2026-03-12T10:00:00"),
        ],
    )
    conn.commit()
    conn.close()

    calls = []

    def fake_pm_workflow(action: str, **kwargs):
        calls.append((action, kwargs))
        return {"message": f"Workflow {kwargs['workflow_id']} resumed"}

    monkeypatch.setattr(resume_module, "pm_workflow", fake_pm_workflow)
    main_module._register_commands()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["resume", "--project-dir", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert calls[0][1]["workflow_id"] == "wf_new"
