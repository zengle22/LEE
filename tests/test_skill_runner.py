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
from lee.orchestrator.ir.models import StepKind, VariableIR
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


def test_spec_global_parser_preserves_explicit_step_config():
    parser = SpecGlobalParser()
    step = parser._parse_step(
        {
            "id": "review_gate",
            "kind": "gate",
            "config": {
                "gate": {
                    "type": "auto_check",
                    "check": "blocker_count == 0",
                }
            },
        },
        stage_id="review_gate",
    )

    assert step.config["gate"]["type"] == "auto_check"
    assert step.config["gate"]["check"] == "blocker_count == 0"


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
    assert execute_step.input["commit_plan"] == ".workflow/workspace-cleanup/commit-plan.yaml"
    assert execute_step.on_failure is not None
    assert execute_step.on_failure["retry"] == 2
    assert FailureHandler.has_policy(execute_step) is True
    assert execute_step.config["success_criteria"]["require_new_commit"] is True


def test_workspace_cleanup_template_parses_runtime_cleanup_step_as_skill():
    manager = TemplateManager(template_dir="spec-global")
    template = manager.get_template("workflow.office.workspace_cleanup")
    assert template is not None

    cleanup_step = next(step for step in template.steps if step.id == "s5_4_cleanup_runtime_state")
    assert cleanup_step.kind == "skill"
    assert cleanup_step.skill_id == "skill.office.runtime_state_cleanup"
    assert cleanup_step.depends_on == ["s5_3_execute_commits"]


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


@pytest.mark.asyncio
async def test_skill_runner_ignores_workflow_executor_override_for_shell_skill(tmp_path: Path):
    shell_executor = MagicMock()
    shell_executor.execute = AsyncMock(
        return_value={"status": "completed", "return_code": 0, "stdout": "", "stderr": ""}
    )

    ctx = _make_ctx(
        shell_executor=shell_executor,
        params={"workspace_path": str(tmp_path), "remote": "origin", "branch": "main"},
        project_root=Path.cwd(),
    )
    ctx.store.get_workflow.return_value = SimpleNamespace(
        data={
            "params": {"workspace_path": str(tmp_path), "remote": "origin", "branch": "main"},
            "run_id": "RUN-TEST",
            "executor_override": "qwen_chat",
        }
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
    assert ctx.executor_factory.create.call_args_list[0].args[0] == "shell"


def test_skill_runner_resolve_param_value_handles_variable_ir():
    value = VariableIR(
        reference="$outputs.s1_1_analyze_files.gitignore_recommendations",
        source_type="context",
        path=["outputs", "s1_1_analyze_files", "gitignore_recommendations"],
    )

    resolved = SkillRunner._resolve_param_value(value, workflow_params={})
    assert resolved == "$outputs.s1_1_analyze_files.gitignore_recommendations"


@pytest.mark.asyncio
async def test_workspace_cleanup_gitignore_skill_does_not_fail_on_variable_ir_input(tmp_path: Path):
    manager = TemplateManager(template_dir="spec-global")
    template = manager.get_template("workflow.office.workspace_cleanup")
    assert template is not None
    gitignore_step = next(step for step in template.steps if step.id == "s2_1_update_gitignore")

    shell_executor = MagicMock()
    shell_executor.execute = AsyncMock(
        return_value={"status": "completed", "return_code": 0, "stdout": "", "stderr": ""}
    )

    ctx = _make_ctx(
        shell_executor=shell_executor,
        params={"workspace_path": str(tmp_path)},
        project_root=Path.cwd(),
    )

    runner = SkillRunner()
    result = await runner.execute("wf-test", gitignore_step, ctx)

    assert result.status == "success"
    created_execution = ctx.store.create_task_execution.await_args.args[0]
    assert created_execution.input_data["patterns_to_add"] == "$outputs.s1_1_analyze_files.gitignore_recommendations"


@pytest.mark.asyncio
async def test_skill_runner_loads_runtime_cleanup_skill_commands(tmp_path: Path):
    shell_executor = MagicMock()
    shell_executor.execute = AsyncMock(
        return_value={"status": "completed", "return_code": 0, "stdout": "", "stderr": ""}
    )

    ctx = _make_ctx(
        shell_executor=shell_executor,
        params={"workspace_path": str(tmp_path)},
        project_root=Path.cwd(),
    )
    step = MockStep(
        id="s5_4_cleanup_runtime_state",
        skill_id="skill.office.runtime_state_cleanup",
        input={"workspace_path": "${{ params.workspace_path }}"},
    )

    runner = SkillRunner()
    result = await runner.execute("wf-test", step, ctx)

    assert result.status == "success"
    commands = [call.args[0]["command"] for call in shell_executor.execute.await_args_list]
    assert any("rm -f .lee/chat_history.txt .lee/cli.lock input.mode" in cmd for cmd in commands)
    assert any("find .lee/pm_agent_sessions -type f -name '*.json' -delete" in cmd for cmd in commands)
    assert all(cmd.startswith(f"cd {tmp_path}") for cmd in commands)


# ============================================
# BUG-2026-0051: runtime configuration tests
# ============================================


class TestBuildSkillCommandsRuntimeConfig:
    """Tests for _build_skill_commands with runtime config (BUG-2026-0051)"""

    def test_build_skill_commands_execution_command(self):
        """Test that execution.command still works"""
        step = MockStep()
        skill_spec = {
            "execution": {
                "command": "echo hello"
            }
        }
        input_data = {}

        commands = SkillRunner._build_skill_commands(
            step, skill_spec, input_data, None
        )

        assert commands == ["echo hello"]

    def test_build_skill_commands_execution_steps(self):
        """Test that execution.steps[].command works"""
        step = MockStep()
        skill_spec = {
            "execution": {
                "steps": [
                    {"command": "echo step1"},
                    {"command": "echo step2"},
                ]
            }
        }
        input_data = {}

        commands = SkillRunner._build_skill_commands(
            step, skill_spec, input_data, None
        )

        assert commands == ["echo step1", "echo step2"]

    def test_build_skill_commands_runtime_config(self):
        """Test runtime.command + runtime.args_template format (BUG-2026-0051)"""
        step = MockStep()
        skill_spec = {
            "runtime": {
                "type": "cli",
                "command": "lee",
                "args_template": "test-runner run-e2e --env {env}"
            }
        }
        input_data = {"env": "test"}

        commands = SkillRunner._build_skill_commands(
            step, skill_spec, input_data, None
        )

        assert len(commands) == 1
        assert "lee" in commands[0]
        assert "test-runner" in commands[0]
        assert "run-e2e" in commands[0]
        assert "--env test" in commands[0]

    def test_build_skill_commands_runtime_with_full_args(self):
        """Test runtime with full arguments"""
        step = MockStep()
        skill_spec = {
            "runtime": {
                "type": "cli",
                "command": "lee",
                "args_template": "test-runner run-e2e --suite {suite} --env {env} --test-set {test_set_path} --out-dir {artifacts_dir}"
            }
        }
        input_data = {
            "suite": "smoke",
            "env": "staging",
            "test_set_path": "qa/test-sets/login.yaml",
            "artifacts_dir": "qa/test-runs/TR-001/evidence"
        }

        commands = SkillRunner._build_skill_commands(
            step, skill_spec, input_data, None
        )

        assert len(commands) == 1
        cmd = commands[0]
        assert cmd.startswith("lee")
        assert "--suite smoke" in cmd
        assert "--env staging" in cmd
        assert "--test-set" in cmd
        assert "--out-dir" in cmd

    def test_build_skill_commands_runtime_fallback_to_execution(self):
        """Test that execution.command takes priority over runtime"""
        step = MockStep()
        skill_spec = {
            "execution": {
                "command": "echo from_execution"
            },
            "runtime": {
                "command": "echo from_runtime",
                "args_template": "should not be used"
            }
        }
        input_data = {}

        commands = SkillRunner._build_skill_commands(
            step, skill_spec, input_data, None
        )

        assert commands == ["echo from_execution"]

    def test_build_skill_commands_runtime_missing_args(self):
        """Test runtime with missing args_template"""
        step = MockStep()
        skill_spec = {
            "runtime": {
                "command": "lee"
                # args_template is missing
            }
        }
        input_data = {}

        commands = SkillRunner._build_skill_commands(
            step, skill_spec, input_data, None
        )

        assert commands == []

    def test_build_skill_commands_runtime_missing_command(self):
        """Test runtime with missing command"""
        step = MockStep()
        skill_spec = {
            "runtime": {
                "type": "cli",
                "args_template": "some args"
                # command is missing
            }
        }
        input_data = {}

        commands = SkillRunner._build_skill_commands(
            step, skill_spec, input_data, None
        )

        assert commands == []

    def test_build_skill_commands_runtime_with_workspace_path(self):
        """Test runtime config with workspace_path placeholder"""
        step = MockStep()
        skill_spec = {
            "runtime": {
                "command": "cd {workspace_path} && lee test",
                "args_template": "--flag"
            }
        }
        input_data = {"workspace_path": "/path/to/workspace"}

        commands = SkillRunner._build_skill_commands(
            step, skill_spec, input_data, "/project/root"
        )

        assert len(commands) == 1
        assert "/path/to/workspace" in commands[0]

    def test_build_skill_commands_step_config_overrides_runtime(self):
        """Test that step.config.execution.command overrides runtime"""
        step = MockStep()
        step.config = {
            "execution": {
                "command": "echo from_step_config"
            }
        }
        skill_spec = {
            "runtime": {
                "command": "echo from_runtime",
                "args_template": "should not be used"
            }
        }
        input_data = {}

        commands = SkillRunner._build_skill_commands(
            step, skill_spec, input_data, None
        )

        assert commands == ["echo from_step_config"]
