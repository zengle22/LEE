import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lee.orchestrator.execution.runners.base import RunnerContext
from lee.orchestrator.execution.runners.code_executor_scope import (
    build_code_executor_io_config,
    validate_code_executor_write_scope,
)
from lee.orchestrator.execution.runners.llm_runner import ClaudeCodeRunner, LLMRunner


@pytest.fixture
def temp_project_root():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def ctx(temp_project_root):
    agent_spec = SimpleNamespace(contracts={}, governance={}, tags=[], spec_path="")
    agent_loader = MagicMock()
    agent_loader.load.return_value = agent_spec
    agent_context_builder = SimpleNamespace(agent_loader=agent_loader, build=AsyncMock())

    return RunnerContext(
        store=MagicMock(),
        state_machine=MagicMock(),
        event_log=MagicMock(),
        evidence_collector=MagicMock(),
        verifier_engine=MagicMock(),
        executor_factory=MagicMock(),
        agent_context_builder=agent_context_builder,
        contract_discovery=MagicMock(),
        file_output_handler=SimpleNamespace(project_root=temp_project_root),
        token_manager=MagicMock(),
        project_root=str(temp_project_root),
    )


def test_build_code_executor_io_config_defaults_to_step_workspace(temp_project_root):
    step = SimpleNamespace(outputs=[SimpleNamespace(type="symbol", symbol="spec_candidate", path=None)])

    config = build_code_executor_io_config(
        workspace=str(temp_project_root),
        workflow_id="wf-001",
        step_id="spec_maintenance",
        step=step,
        configured_write_scope=[],
        params={},
    )

    assert config["step_workspace"].endswith(".workflow\\workspace\\wf-001\\spec_maintenance")
    assert config["declared_output_files"] == []
    assert config["write_scope"] == [config["step_workspace"]]


def test_llm_runner_build_executor_input_uses_scoped_write_paths(temp_project_root, ctx):
    runner = LLMRunner()
    instance = SimpleNamespace(data={"run_id": "run-001"})
    agent_ctx = SimpleNamespace(system_prompt="system rules", user_prompt="maintain the target spec")
    step = SimpleNamespace(
        id="spec_maintenance",
        agent_id="agent.governance.spec_maintainer",
        outputs=[SimpleNamespace(type="symbol", symbol="spec_candidate", path=None)],
        config={"claude_code": {"allowed_commands": ["Get-ChildItem"]}},
    )
    ctx.resolve_workdir = MagicMock(return_value=str(temp_project_root))
    ctx.token_manager.encode_token_for_context.return_value = "encoded-token"

    input_data = runner._build_executor_input(
        executor_type="kimi",
        step=step,
        ctx=ctx,
        instance=instance,
        workflow_id="wf-001",
        agent_ctx=agent_ctx,
        step_token="raw-token",
    )

    assert input_data["step_workspace"].endswith(".workflow\\workspace\\wf-001\\spec_maintenance")
    assert input_data["declared_output_files"] == []
    assert input_data["write_scope"] == [input_data["step_workspace"]]
    assert input_data["token_context"] == "encoded-token"


def test_validate_code_executor_write_scope_rejects_out_of_scope_paths(temp_project_root):
    step_workspace = temp_project_root / ".workflow" / "workspace" / "wf-001" / "epic_design"
    allowed_output = "output/design-frozen/LEE-epic-freeze.yaml"
    blocked = str(temp_project_root / "departments" / "product" / "epics" / "EPIC-046.yaml")

    error = validate_code_executor_write_scope(
        changed_files=[blocked],
        project_root=str(temp_project_root),
        write_scope=[str(step_workspace), allowed_output],
    )

    assert error is not None
    assert "Unauthorized write" in error
    assert "departments\\product\\epics\\EPIC-046.yaml" in error


@pytest.mark.asyncio
async def test_claude_code_runner_rejects_unauthorized_write_scope(temp_project_root, ctx):
    runner = ClaudeCodeRunner()
    step = SimpleNamespace(
        id="epic_design",
        agent_id="agent.product.epic_designer",
        executor_type="claude_code",
        config={"claude_code": {}},
        outputs=[],
    )
    instance = SimpleNamespace(
        data={"run_id": "run-unauthorized-001"},
        template_id="workflow.product.task.src_to_epic",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system rules",
            user_prompt="design epic from source",
            temperature=0.2,
            max_tokens=1024,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.resolve_workdir = MagicMock(return_value=str(temp_project_root))

    executor = MagicMock()
    executor.execute = AsyncMock(
        return_value={
            "status": "success",
            "changed_files": ["departments/product/epics/EPIC-046.yaml"],
        }
    )
    ctx.executor_factory.create.return_value = executor

    result = await runner.execute("wf-unauthorized-001", step, ctx)

    assert result.status == "failed"
    assert "Unauthorized write" in result.message
    ctx.state_machine.fail_step.assert_awaited()
    ctx.store.update_task_execution.assert_awaited()
