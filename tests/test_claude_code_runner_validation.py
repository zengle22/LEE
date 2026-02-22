from __future__ import annotations

from lee.orchestrator.execution.runners.llm_runner import ClaudeCodeRunner


def test_validate_success_criteria_missing_required_command():
    error = ClaudeCodeRunner._validate_success_criteria(
        output={"commands_run": [{"cmd": "git status"}]},
        criteria={"require_commands": ["git commit"]},
        workspace=".",
        head_before=None,
    )
    assert error is not None
    assert "Missing required command" in error


def test_validate_success_criteria_detects_head_unchanged(monkeypatch):
    monkeypatch.setattr(
        ClaudeCodeRunner,
        "_git_head",
        staticmethod(lambda _workspace: "abc12345"),
    )
    error = ClaudeCodeRunner._validate_success_criteria(
        output={"commands_run": [{"cmd": "git commit -m 'x'"}]},
        criteria={"require_commands": ["git commit"], "require_new_commit": True},
        workspace=".",
        head_before="abc12345",
    )
    assert error is not None
    assert "No new commit detected" in error


def test_validate_success_criteria_pass(monkeypatch):
    monkeypatch.setattr(
        ClaudeCodeRunner,
        "_git_head",
        staticmethod(lambda _workspace: "def67890"),
    )
    error = ClaudeCodeRunner._validate_success_criteria(
        output={"commands_run": [{"cmd": "git commit -m 'x'"}]},
        criteria={"require_commands": ["git commit"], "require_new_commit": True},
        workspace=".",
        head_before="abc12345",
    )
    assert error is None
