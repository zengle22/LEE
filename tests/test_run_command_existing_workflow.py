from pathlib import Path
from typing import Any, Dict, List

from click.testing import CliRunner

import lee.cli.commands.run as run_module


def _make_registry(template_path: Path) -> Dict[str, Any]:
    return {
        "workflows": {
            "office.workspace-cleanup": {
                "path": str(template_path),
                "required_params": [],
            }
        }
    }


def test_run_continue_existing_workflow(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")

    calls: List[Dict[str, Any]] = []

    monkeypatch.setattr(run_module, "_load_registry", lambda: _make_registry(template))
    monkeypatch.setattr(
        run_module,
        "_list_conflicting_workflows",
        lambda *_args, **_kwargs: [
            {
                "id": "wf_old_001",
                "status": "paused",
                "current_step": "s1_1_analyze_files",
                "created_at": "2026-02-18T21:00:00",
                "concurrency_scope": "project:demo",
            }
        ],
    )
    monkeypatch.setattr(
        run_module,
        "_select_existing_workflow_action",
        lambda _existing, _scope_info: ("continue", "wf_old_001"),
    )
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_args, **_kwargs: {
            "status": "blocked",
            "blocked_at": "s1_1_analyze_files",
            "completed_steps": 0,
        },
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_args, **_kwargs: None)

    def fake_pm_workflow(action: str, **kwargs):
        calls.append({"action": action, "kwargs": kwargs})
        if action == "resume":
            return {"message": "ok"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["office.workspace-cleanup", "--project-dir", str(tmp_path), "--skip-plan"],
    )

    assert result.exit_code == 0, result.output
    assert any(c["action"] == "resume" for c in calls)
    assert all(c["action"] != "create" for c in calls)


def test_run_restart_existing_workflow(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: workflow\nid: y\nversion: '1.0'\n", encoding="utf-8")

    calls: List[Dict[str, Any]] = []

    monkeypatch.setattr(run_module, "_load_registry", lambda: _make_registry(template))
    monkeypatch.setattr(
        run_module,
        "_list_conflicting_workflows",
        lambda *_args, **_kwargs: [
            {
                "id": "wf_old_001",
                "status": "running",
                "current_step": "s1_1_analyze_files",
                "created_at": "2026-02-18T21:00:00",
                "concurrency_scope": "project:demo",
            },
            {
                "id": "wf_old_000",
                "status": "paused",
                "current_step": "s1_1_analyze_files",
                "created_at": "2026-02-18T20:00:00",
                "concurrency_scope": "project:demo",
            },
        ],
    )
    monkeypatch.setattr(
        run_module,
        "_select_existing_workflow_action",
        lambda _existing, _scope_info: ("restart", "wf_old_001"),
    )
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_args, **_kwargs: rendered)
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_args, **_kwargs: {
            "status": "completed",
            "completed_steps": 1,
            "blocked_at": None,
        },
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_args, **_kwargs: None)

    def fake_pm_workflow(action: str, **kwargs):
        calls.append({"action": action, "kwargs": kwargs})
        if action == "pause":
            return {"message": "paused"}
        if action == "create":
            return {"workflow_id": "wf_new_001"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["office.workspace-cleanup", "--project-dir", str(tmp_path), "--skip-plan"],
    )

    assert result.exit_code == 0, result.output
    pause_calls = [c for c in calls if c["action"] == "pause"]
    create_calls = [c for c in calls if c["action"] == "create"]
    assert len(pause_calls) == 2
    assert len(create_calls) == 1
