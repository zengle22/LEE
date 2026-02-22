
from click.testing import CliRunner
import click
import re
from lee.cli.commands.chat import (
    chat,
    LeeChatREPL,
    _timestamped_echo,
)
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace
from pathlib import Path
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

import pytest

def test_chat_help():
    runner = CliRunner()
    result = runner.invoke(chat, ['--help'])
    assert result.exit_code == 0
    assert "Start Lee Chat" in result.output

@patch('lee.cli.commands.chat.LeeChatREPL.run_loop', new_callable=AsyncMock)
def test_chat_run(mock_loop):
    runner = CliRunner()
    result = runner.invoke(chat)
    assert result.exit_code == 0
    mock_loop.assert_called_once()


@pytest.mark.asyncio
async def test_chat_decision_engine_uses_direct_api(monkeypatch, tmp_path: Path):
    repl = object.__new__(LeeChatREPL)
    repl.project_dir = tmp_path
    repl.session_id = "test-session"
    repl.runtime = SimpleNamespace(
        process_input=AsyncMock(
            return_value={
                "status": "success",
                "action": "run_workflow",
                "data": {
                    "template_id": "workflow.office.workspace_cleanup",
                    "template_input": "workspace_cleanup",
                    "template_resolved": "workflow.office.workspace_cleanup",
                    "workflow_id": "wf_task_1",
                },
                "reasoning": "",
                "confidence": 0.9,
            }
        )
    )
    repl._display_result_data = lambda *_a, **_k: None
    repl._print_error = lambda *_a, **_k: None
    repl._print_success = lambda *_a, **_k: None
    repl._print_warning = lambda *_a, **_k: None
    repl._show_available_templates = AsyncMock()
    echoed = []
    monkeypatch.setattr(
        "click.echo",
        lambda message="", *args, **kwargs: echoed.append(str(message)),
    )

    await repl._handle_with_decision_engine("run workflow")
    assert any("⚡ 执行动作" in line for line in echoed)
    assert any("模板解析" in line for line in echoed)


def test_display_result_data_for_pause_resume(monkeypatch):
    repl = object.__new__(LeeChatREPL)
    echoed = []
    monkeypatch.setattr(
        "click.echo",
        lambda message="", *args, **kwargs: echoed.append(str(message)),
    )

    repl._display_result_data(
        {"workflow_id": "wf_task_1", "message": "Workflow wf_task_1 paused"}
    )

    assert any("Workflow wf_task_1 paused" in line for line in echoed)
    assert any("Workflow: wf_task_1" in line for line in echoed)


def test_display_result_data_for_reject_gate(monkeypatch):
    repl = object.__new__(LeeChatREPL)
    echoed = []
    monkeypatch.setattr(
        "click.echo",
        lambda message="", *args, **kwargs: echoed.append(str(message)),
    )

    repl._display_result_data(
        {
            "gate_id": "gate_review",
            "workflow_id": "wf_task_1",
            "decision": "rejected",
            "action": "rollback",
            "target_step": "step_fix",
            "new_workflow_id": "wf_task_retry_1",
        }
    )

    assert any("gate_review -> rejected" in line for line in echoed)
    assert any("Action: rollback" in line for line in echoed)
    assert any("Target step: step_fix" in line for line in echoed)
    assert any("New workflow: wf_task_retry_1" in line for line in echoed)


def test_display_result_data_for_gates_includes_decision_info(monkeypatch):
    repl = object.__new__(LeeChatREPL)
    echoed = []
    monkeypatch.setattr(
        "click.echo",
        lambda message="", *args, **kwargs: echoed.append(str(message)),
    )

    repl._display_result_data(
        {
            "gates": [
                {
                    "gate_id": "gate_review",
                    "status": "rejected",
                    "workflow_id": "wf_task_1",
                    "step_id": "step_review",
                    "decision_action": "rollback",
                    "target_step": "step_fix",
                    "approver": "alice",
                    "comments": "Need revision",
                    "issues": ["missing tests"],
                    "structured_feedback": {"severity": "high"},
                    "decided_at": "2026-02-22T10:00:00",
                }
            ],
            "total": 1,
        }
    )

    assert any("gate_review [rejected]" in line for line in echoed)
    assert any("decision_action: rollback" in line for line in echoed)
    assert any("target_step: step_fix" in line for line in echoed)
    assert any("comments: Need revision" in line for line in echoed)
    assert any("issues: ['missing tests']" in line for line in echoed)
    assert any("structured_feedback: {'severity': 'high'}" in line for line in echoed)
    assert any("decided_at: 2026-02-22T10:00:00" in line for line in echoed)


def test_display_result_data_for_run_result_progress(monkeypatch):
    repl = object.__new__(LeeChatREPL)
    echoed = []
    monkeypatch.setattr(
        "click.echo",
        lambda message="", *args, **kwargs: echoed.append(str(message)),
    )

    repl._display_result_data(
        {
            "run_result": {
                "total_steps": 10,
                "completed_steps": 3,
                "status": "running",
            }
        }
    )

    assert any("进度: 3/10 步骤已完成" in line for line in echoed)
    assert any("状态: running" in line for line in echoed)


def test_display_result_data_does_not_render_none_step_id(monkeypatch):
    repl = object.__new__(LeeChatREPL)
    echoed = []
    monkeypatch.setattr(
        "click.echo",
        lambda message="", *args, **kwargs: echoed.append(str(message)),
    )

    repl._display_result_data(
        {
            "workflow_id": "wf_task_1",
            "step_id": None,
            "message": "No ready steps available (workflow_status=failed)",
        }
    )

    assert not any("Step executed: None" in line for line in echoed)
    assert any("No ready steps available" in line for line in echoed)


def test_prompt_auto_suggest_bool_is_normalized():
    class _Buffer:
        def __init__(self):
            self.auto_suggest = True

    class _Session:
        def __init__(self):
            self.default_buffer = _Buffer()

    repl = object.__new__(LeeChatREPL)
    repl.session = _Session()
    repl._ensure_prompt_auto_suggest()

    assert isinstance(repl.session.default_buffer.auto_suggest, AutoSuggestFromHistory)


def test_timestamped_echo_prefixes_messages(monkeypatch):
    captured = []
    monkeypatch.setattr(
        "click.echo",
        lambda message="", *args, **kwargs: captured.append(str(message)),
    )

    with _timestamped_echo():
        click.echo("hello")

    assert len(captured) == 1
    assert re.match(r"^\[\d{2}:\d{2}:\d{2}\] hello$", captured[0])


@pytest.mark.asyncio
async def test_chat_shows_gate_block_hint(monkeypatch, tmp_path: Path):
    repl = object.__new__(LeeChatREPL)
    repl.project_dir = tmp_path
    repl.session_id = "test-session"
    repl.runtime = SimpleNamespace(
        process_input=AsyncMock(
            return_value={
                "status": "success",
                "action": "run_workflow",
                "data": {
                    "template_id": "workflow.office.workspace_cleanup",
                    "workflow_id": "wf_task_1",
                    "run_result": {"status": "blocked", "blocked_at": "step_review"},
                },
                "reasoning": "",
                "confidence": 0.9,
            }
        )
    )
    repl._display_result_data = lambda *_a, **_k: None
    repl._print_error = lambda *_a, **_k: None
    repl._print_success = lambda *_a, **_k: None
    repl._print_warning = lambda *_a, **_k: None
    repl._show_available_templates = AsyncMock()

    async def _fake_list_gates(project_dir, workflow_id, status):
        return {
            "total": 1,
            "gates": [
                {
                    "gate_id": "gate_review",
                    "workflow_id": workflow_id,
                    "step_id": "step_review",
                    "status": "pending",
                    "created_at": "2026-02-22T12:00:00",
                }
            ],
        }

    monkeypatch.setattr("lee.orchestrator.api.api_list_gates", _fake_list_gates)
    echoed = []
    monkeypatch.setattr(
        "click.echo",
        lambda message="", *args, **kwargs: echoed.append(str(message)),
    )

    await repl._handle_with_decision_engine("运行 workflow")
    assert any("工作流已在门禁处阻塞" in line for line in echoed)
    assert any("Pending gate: gate_review" in line for line in echoed)
    assert any("批准 gate_review" in line for line in echoed)
