from pathlib import Path

import lee.cli.commands.run as run_module


def test_run_until_settled_with_gates_waits_and_continues(monkeypatch, tmp_path: Path) -> None:
    summaries = [
        {"status": "blocked", "blocked_at": "s5_2_review_commits", "completed_steps": 5},
        {"status": "completed", "blocked_at": None, "completed_steps": 6},
    ]

    monkeypatch.setattr(
        run_module,
        "_run_until_blocked_with_interrupt_guard",
        lambda *_a, **_k: summaries.pop(0),
    )
    monkeypatch.setattr(
        run_module,
        "_get_gate_wait_snapshot",
        lambda *_a, **_k: {
            "status": "paused",
            "current_step": "s5_2_review_commits",
            "pending_gates": [{"gate_id": "gate_s5_2_review_commits", "step_id": "s5_2_review_commits"}],
        },
    )
    monkeypatch.setattr(
        run_module,
        "_wait_for_gate_resolution",
        lambda *_a, **_k: {
            "status": "running",
            "current_step": None,
            "pending_gates": [],
        },
    )

    result = run_module._run_until_settled_with_gates(tmp_path, "wf_task_x", 10)
    assert result["status"] == "completed"
    assert summaries == []

