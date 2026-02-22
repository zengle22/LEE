from pathlib import Path

import click
from click.testing import CliRunner

import lee.cli.commands.gates_cmd as gates_module


def test_resolve_gate_ref_accepts_step_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        gates_module,
        "_load_gates_from_db",
        lambda *_a, **_k: [
            {"gate_id": "gate_s5_2_review_commits", "step_id": "s5_2_review_commits", "status": "pending"}
        ],
    )
    resolved = gates_module._resolve_gate_ref(
        tmp_path, "wf_task_x", "s5_2_review_commits", pending_only=True
    )
    assert resolved == "gate_s5_2_review_commits"


def test_resolve_gate_ref_ambiguous_step_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        gates_module,
        "_load_gates_from_db",
        lambda *_a, **_k: [
            {"gate_id": "gate_a", "step_id": "s5_2_review_commits", "status": "pending"},
            {"gate_id": "gate_b", "step_id": "s5_2_review_commits", "status": "pending"},
        ],
    )
    try:
        gates_module._resolve_gate_ref(tmp_path, "wf_task_x", "s5_2_review_commits", pending_only=True)
        assert False, "expected ClickException"
    except click.ClickException as e:
        assert "multiple gates" in str(e).lower()


def test_gates_approve_maps_step_id_before_api_call(monkeypatch, tmp_path: Path) -> None:
    calls = []
    monkeypatch.setattr(
        gates_module,
        "_load_gates_from_db",
        lambda *_a, **_k: [
            {"gate_id": "gate_s5_2_review_commits", "step_id": "s5_2_review_commits", "status": "pending"}
        ],
    )
    monkeypatch.setattr(click, "confirm", lambda *_a, **_k: True)

    def fake_pm_workflow(action: str, **kwargs):
        calls.append((action, kwargs))
        return {"message": "ok"}

    monkeypatch.setattr(gates_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        gates_module.gates,
        [
            "approve",
            "wf_task_x",
            "s5_2_review_commits",
            "--approver",
            "zeng",
            "--project-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls
    action, kwargs = calls[0]
    assert action == "approve_gate"
    assert kwargs["gate_id"] == "gate_s5_2_review_commits"

