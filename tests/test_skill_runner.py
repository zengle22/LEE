from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from lee.orchestrator.execution.runners.shell_runner import SkillRunner
from lee.orchestrator.execution.spec_global_parser import SpecGlobalParser
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.execution.failure_handler import FailureHandler
from lee.orchestrator.ir.models import StepKind
from lee.orchestrator.storage.models import StepResult, TaskExecutionStatus


@dataclass
class MockStep:
    id: str = "s6_1_push_commits"
    kind: str = "skill"
    executor_type: str = "shell"
    input: Dict[str, Any] = field(default_factory=dict)
    outputs: List[Any] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    skill_id: str = "skill.office.git_push"


def _make_ctx(shell_executor: Any, params: Dict[str, Any], project_root: Path):
    instance = SimpleNamespace(data={"params": params, "run_id": "RUN-TEST"})

    store = MagicMock()
    store.get_workflow = AsyncMock(return_value=instance)
    store.create_task_execution = AsyncMock()
    store.update_task_execution = AsyncMock()
    store.update_workflow_data = AsyncMock()

    state_machine = MagicMock()
    state_machine.complete_step = AsyncMock(
        return_value=StepResult(
            status="success",
            step_id="s6_1_push_commits",
            workflow_id="wf-test",
            message="ok",
            output={},
        )
    )
    state_machine.fail_step = AsyncMock()

    executor_factory = MagicMock()
    executor_factory.create = MagicMock(return_value=shell_executor)

    ctx = SimpleNamespace(
        store=store,
        state_machine=state_machine,
        executor_factory=executor_factory,
        project_root=str(project_root),
        verifier_engine=MagicMock(),
        evidence_collector=MagicMock(),
        event_log=MagicMock(),
    )
    return ctx


def test_spec_global_parser_infers_skill_from_run_prefix():
    parser = SpecGlobalParser()
    step = parser._parse_step(
        {
            "id": "s6_1_push_commits",
            "run": "skill.office.git_push",
        },
        stage_id="s6_push_remote",
    )
    assert step.kind == StepKind.SKILL
    assert step.skill_id == "skill.office.git_push"
    assert step.agent_id is None


def test_workspace_cleanup_template_parses_push_step_as_skill():
    manager = TemplateManager(template_dir="spec-global")
    template = manager.get_template("workflow.office.workspace_cleanup")
    assert template is not None

    push_step = next(step for step in template.steps if step.id == "s6_1_push_commits")
    assert push_step.kind == "skill"
    assert push_step.skill_id == "skill.office.git_push"
    assert push_step.executor_type == "shell"


def test_workspace_cleanup_execute_step_preserves_constants_and_retry_policy():
    manager = TemplateManager(template_dir="spec-global")
    template = manager.get_template("workflow.office.workspace_cleanup")
    assert template is not None

    execute_step = next(step for step in template.steps if step.id == "s5_3_execute_commits")
    assert execute_step.input["mode"] == "execute"
    assert execute_step.input["commit_plan"] == "workspace-cleanup/commit-plan.yaml"
    assert execute_step.on_failure is not None
    assert execute_step.on_failure["retry"] == 2
    assert FailureHandler.has_policy(execute_step) is True
    assert execute_step.config["success_criteria"]["require_new_commit"] is True


@pytest.mark.asyncio
async def test_skill_runner_loads_skill_commands_and_executes_push(tmp_path: Path):
    shell_executor = MagicMock()
    shell_executor.execute = AsyncMock(
        return_value={"status": "completed", "return_code": 0, "stdout": "", "stderr": ""}
    )

    ctx = _make_ctx(
        shell_executor=shell_executor,
        params={"workspace_path": str(tmp_path), "remote": "origin", "branch": "main"},
        project_root=Path.cwd(),
    )
    step = MockStep(
        input={
            "workspace_path": "${{ params.workspace_path }}",
            "remote": "${{ params.remote }}",
            "branch": "${{ params.branch }}",
        }
    )

    runner = SkillRunner()
    result = await runner.execute("wf-test", step, ctx)

    assert result.status == "success"
    commands = [call.args[0]["command"] for call in shell_executor.execute.await_args_list]
    assert any("git push origin main" in cmd for cmd in commands)
    assert all(cmd.startswith(f"cd {tmp_path}") for cmd in commands)
    ctx.state_machine.fail_step.assert_not_called()


@pytest.mark.asyncio
async def test_skill_runner_marks_step_failed_when_push_command_fails(tmp_path: Path):
    async def _exec(input_data: Dict[str, Any]) -> Dict[str, Any]:
        command = input_data["command"]
        if "git push" in command:
            return {"status": "failed", "return_code": 1, "stdout": "", "stderr": "push rejected"}
        return {"status": "completed", "return_code": 0, "stdout": "", "stderr": ""}

    shell_executor = MagicMock()
    shell_executor.execute = AsyncMock(side_effect=_exec)

    ctx = _make_ctx(
        shell_executor=shell_executor,
        params={"workspace_path": str(tmp_path), "remote": "origin", "branch": "main"},
        project_root=Path.cwd(),
    )
    step = MockStep(
        input={
            "workspace_path": "${{ params.workspace_path }}",
            "remote": "${{ params.remote }}",
            "branch": "${{ params.branch }}",
        }
    )

    runner = SkillRunner()
    result = await runner.execute("wf-test", step, ctx)

    assert result.status == "failed"
    assert "push rejected" in result.message
    ctx.state_machine.complete_step.assert_not_called()
    ctx.state_machine.fail_step.assert_called_once()

    statuses = [call.args[1] for call in ctx.store.update_task_execution.await_args_list]
    assert TaskExecutionStatus.FAILED in statuses


@pytest.mark.asyncio
async def test_skill_runner_uses_skill_defaults_when_workflow_params_missing():
    shell_executor = MagicMock()
    shell_executor.execute = AsyncMock(
        return_value={"status": "completed", "return_code": 0, "stdout": "", "stderr": ""}
    )

    ctx = _make_ctx(
        shell_executor=shell_executor,
        params={},
        project_root=Path.cwd(),
    )
    step = MockStep(
        input={
            "workspace_path": "${{ params.workspace_path }}",
            "remote": "${{ params.remote }}",
            "branch": "${{ params.branch }}",
        }
    )

    runner = SkillRunner()
    result = await runner.execute("wf-test", step, ctx)

    assert result.status == "success"
    commands = [call.args[0]["command"] for call in shell_executor.execute.await_args_list]
    assert any("git push origin $(git branch --show-current)" in cmd for cmd in commands)
