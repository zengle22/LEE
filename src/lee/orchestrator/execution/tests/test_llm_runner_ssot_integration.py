import shutil
import tempfile
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lee.orchestrator.execution.runners.base import RunnerContext, StepRunnerBase
from lee.orchestrator.execution.runners.llm_runner import ClaudeCodeRunner, LLMRunner
from lee.orchestrator.storage.models import StepResult


@pytest.fixture
def temp_project_root():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def runner():
    return LLMRunner()


@pytest.fixture
def ctx(temp_project_root):
    agent_spec = SimpleNamespace(
        contracts={
            "ssot_output_schema": str(
                (Path.cwd() / "spec-global" / "core" / "contracts" / "ssot-agent-output" / "v1" / "schema.json").resolve()
            )
        },
        governance={
            "acceptance_briefs": str((Path.cwd() / ".project" / "governance" / "ACCEPTANCE_BRIEFS").resolve()),
            "module_contracts": str((Path.cwd() / ".project" / "governance" / "MODULE_CONTRACTS").resolve()),
            "completion_template": str((Path.cwd() / ".project" / "governance" / "COMPLETION_TEMPLATE.md").resolve()),
        },
        tags=["product", "prd"],
        spec_path=str((Path.cwd() / "spec-global" / "departments" / "prd" / "agents" / "prd-writer" / "v1" / "agent.yaml").resolve()),
    )
    agent_loader = MagicMock()
    agent_loader.load.return_value = agent_spec
    agent_context_builder = SimpleNamespace(agent_loader=agent_loader)

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


def test_claude_code_runner_exposes_workspace_formal_ssot_materializer():
    runner = ClaudeCodeRunner()
    assert callable(runner._materialize_workspace_formal_ssot_markdown)


@pytest.mark.asyncio
async def test_llm_runner_prefers_instance_llm_profile_over_config_default(runner, ctx):
    step = SimpleNamespace(
        id="raw_input_intake",
        agent_id="agent.analysis.product_goal",
        executor_type="llm",
        config={},
        outputs=[],
    )

    instance = SimpleNamespace(
        data={"llm_profile": "qwen", "run_id": "run-001"},
        template_id="workflow.product.task.raw_to_src",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system",
            user_prompt="user",
            temperature=0.2,
            max_tokens=512,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.llm_config_loader = MagicMock()
    ctx.llm_config_loader.get_default_profile.return_value = "huawei_deepseek"

    executor = MagicMock()
    executor.execute = AsyncMock(return_value={"status": "failed", "error": "boom"})
    ctx.executor_factory.create.return_value = executor

    result = await runner.execute("wf-001", step, ctx)

    assert result.status == "failed"
    ctx.executor_factory.create.assert_called_once_with(
        "llm",
        profile="qwen",
        agent_id="agent.analysis.product_goal",
    )


@pytest.mark.asyncio
async def test_llm_runner_qwen_executor_defaults_to_qwen_profile(runner, ctx):
    step = SimpleNamespace(
        id="source_normalization",
        agent_id="agent.analysis.product_goal",
        executor_type="llm",
        config={},
        outputs=[],
    )

    instance = SimpleNamespace(
        data={"executor_override": "qwen", "run_id": "run-002"},
        template_id="workflow.product.task.raw_to_src",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system",
            user_prompt="user",
            temperature=0.2,
            max_tokens=512,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.llm_config_loader = MagicMock()
    ctx.llm_config_loader.get_default_profile.return_value = "huawei_deepseek"

    executor = MagicMock()
    executor.execute = AsyncMock(return_value={"status": "failed", "error": "boom"})
    ctx.executor_factory.create.return_value = executor

    result = await runner.execute("wf-002", step, ctx)

    assert result.status == "failed"
    ctx.executor_factory.create.assert_called_once_with(
        "qwen",
        profile="qwen",
        agent_id="agent.analysis.product_goal",
    )


@pytest.mark.asyncio
async def test_llm_runner_falls_back_from_qwen_for_chinese_unstructured_output(runner, ctx, monkeypatch):
    step = SimpleNamespace(
        id="source_normalization",
        agent_id="agent.analysis.product_goal",
        executor_type="llm",
        config={},
        outputs=[],
    )

    instance = SimpleNamespace(
        data={"executor_override": "qwen", "run_id": "run-zh-001"},
        template_id="workflow.product.task.raw_to_src",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.state_machine.complete_step = AsyncMock(
        return_value=StepResult(status="success", step_id=step.id, workflow_id="wf-zh-001", message="ok")
    )
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="你是产品分析助手",
            user_prompt="请把这个原始需求整理成结构化结果",
            temperature=0.2,
            max_tokens=512,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.llm_config_loader = MagicMock()
    ctx.llm_config_loader.get_default_profile.return_value = "huawei_deepseek"
    ctx.event_log.log_step_completed = MagicMock()
    ctx.event_log._compute_hash = MagicMock(return_value="hash")
    ctx.file_output_handler.handle = AsyncMock(return_value=[])
    ctx.verifier_engine.run = AsyncMock(return_value=[])

    qwen_executor = MagicMock()
    qwen_executor.execute = AsyncMock(return_value={"status": "completed", "generated_text": "这是自由文本，没有结构化结果"})
    kimi_executor = MagicMock()
    kimi_executor.execute = AsyncMock(
        return_value={
            "status": "completed",
            "generated_text": '{"business_output":{"summary":"结构化成功"}}',
            "structured_payload": {"business_output": {"summary": "结构化成功"}},
        }
    )
    ctx.executor_factory.create = MagicMock(side_effect=[qwen_executor, kimi_executor])
    monkeypatch.setattr(LLMRunner, "_resolve_qwen_fallback_target", classmethod(lambda cls, project_root: "kimi"))

    result = await runner.execute("wf-zh-001", step, ctx)

    assert result.status == "success"
    assert ctx.executor_factory.create.call_args_list[0].args[0] == "qwen"
    assert ctx.executor_factory.create.call_args_list[1].args[0] == "kimi"


@pytest.mark.asyncio
async def test_llm_runner_repairs_qwen_unstructured_output_before_fallback(runner, ctx):
    step = SimpleNamespace(
        id="source_normalization",
        agent_id="agent.analysis.product_goal",
        executor_type="llm",
        config={},
        outputs=[],
    )

    instance = SimpleNamespace(
        data={"executor_override": "qwen", "run_id": "run-qwen-repair-001"},
        template_id="workflow.product.task.raw_to_src",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.state_machine.complete_step = AsyncMock(
        return_value=StepResult(status="success", step_id=step.id, workflow_id="wf-qwen-repair-001", message="ok")
    )
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="你是产品分析助手",
            user_prompt="# Task\n请输出结构化结果\n\n## Output Contract\nReturn one machine-readable JSON object only.",
            temperature=0.2,
            max_tokens=512,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.llm_config_loader = MagicMock()
    ctx.llm_config_loader.get_default_profile.return_value = "huawei_deepseek"
    ctx.event_log.log_step_completed = MagicMock()
    ctx.event_log._compute_hash = MagicMock(return_value="hash")
    ctx.file_output_handler.handle = AsyncMock(return_value=[])
    ctx.verifier_engine.run = AsyncMock(return_value=[])

    qwen_executor = MagicMock()
    qwen_executor.execute = AsyncMock(
        side_effect=[
            {"status": "completed", "generated_text": "我是产品目标分析师，请告诉我你的需求。"},
            {
                "status": "completed",
                "generated_text": '{"business_output":{"summary":"结构化成功"}}',
                "structured_payload": {"business_output": {"summary": "结构化成功"}},
            },
        ]
    )
    ctx.executor_factory.create = MagicMock(return_value=qwen_executor)

    result = await runner.execute("wf-qwen-repair-001", step, ctx)

    assert result.status == "success"
    ctx.executor_factory.create.assert_called_once_with(
        "qwen",
        profile="qwen",
        agent_id="agent.analysis.product_goal",
    )
    assert qwen_executor.execute.await_count == 2


@pytest.mark.asyncio
async def test_llm_runner_repairs_qwen_contract_mismatch_before_fallback(runner, ctx, temp_project_root):
    schema_path = temp_project_root / "product-goal.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["contract_type", "requirement_overview"],
                "properties": {
                    "contract_type": {"type": "string"},
                    "requirement_overview": {
                        "type": "object",
                        "required": ["description", "target_users"],
                        "properties": {
                            "description": {"type": "string"},
                            "target_users": {"type": "string"},
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="source_normalization",
        agent_id="agent.analysis.product_goal",
        executor_type="llm",
        config={"output_contract": str(schema_path)},
        outputs=[],
    )
    instance = SimpleNamespace(
        data={"executor_override": "qwen_chat", "run_id": "run-qwen-contract-repair-001"},
        template_id="workflow.product.task.raw_to_src",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.state_machine.complete_step = AsyncMock(
        return_value=StepResult(status="success", step_id=step.id, workflow_id="wf-qwen-contract-repair-001", message="ok")
    )
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="你是产品分析助手",
            user_prompt="请输出 product goal contract",
            temperature=0.2,
            max_tokens=512,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.llm_config_loader = MagicMock()
    ctx.llm_config_loader.get_default_profile.return_value = "huawei_deepseek"
    ctx.event_log.log_step_completed = MagicMock()
    ctx.event_log._compute_hash = MagicMock(return_value="hash")
    ctx.file_output_handler.handle = AsyncMock(return_value=[])
    ctx.verifier_engine.run = AsyncMock(return_value=[])

    qwen_executor = MagicMock()
    qwen_executor.execute = AsyncMock(
        side_effect=[
            {
                "status": "completed",
                "generated_text": json.dumps(
                    {
                        "contract_type": "product-goal-contract",
                        "requirement_overview": {"description": "待确认"},
                    },
                    ensure_ascii=False,
                ),
                "structured_payload": {
                    "contract_type": "product-goal-contract",
                    "requirement_overview": {"description": "待确认"},
                },
            },
            {
                "status": "completed",
                "generated_text": json.dumps(
                    {
                        "contract_type": "product-goal-contract",
                        "requirement_overview": {
                            "description": "支持 qwen_chat 作为对话执行器。",
                            "target_users": "LEE 工作流维护者",
                        },
                    },
                    ensure_ascii=False,
                ),
                "structured_payload": {
                    "contract_type": "product-goal-contract",
                    "requirement_overview": {
                        "description": "支持 qwen_chat 作为对话执行器。",
                        "target_users": "LEE 工作流维护者",
                    },
                },
            },
        ]
    )
    ctx.executor_factory.create = MagicMock(return_value=qwen_executor)

    result = await runner.execute("wf-qwen-contract-repair-001", step, ctx)

    assert result.status == "success"
    assert qwen_executor.execute.await_count == 2
    completed_output = ctx.state_machine.complete_step.await_args.args[2]
    assert completed_output["schema_repair_retry"] is True
    assert completed_output["business_output"]["requirement_overview"]["target_users"] == "LEE 工作流维护者"


@pytest.mark.asyncio
async def test_llm_runner_falls_back_when_qwen_contract_repair_still_invalid(runner, ctx, temp_project_root, monkeypatch):
    schema_path = temp_project_root / "product-goal.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["contract_type", "requirement_overview"],
                "properties": {
                    "contract_type": {"type": "string"},
                    "requirement_overview": {
                        "type": "object",
                        "required": ["description", "target_users"],
                        "properties": {
                            "description": {"type": "string"},
                            "target_users": {"type": "string"},
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="source_normalization",
        agent_id="agent.analysis.product_goal",
        executor_type="llm",
        config={"output_contract": str(schema_path)},
        outputs=[],
    )
    instance = SimpleNamespace(
        data={"executor_override": "qwen_chat", "run_id": "run-qwen-contract-fallback-001"},
        template_id="workflow.product.task.raw_to_src",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.state_machine.complete_step = AsyncMock(
        return_value=StepResult(status="success", step_id=step.id, workflow_id="wf-qwen-contract-fallback-001", message="ok")
    )
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="你是产品分析助手",
            user_prompt="请输出 product goal contract",
            temperature=0.2,
            max_tokens=512,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.llm_config_loader = MagicMock()
    ctx.llm_config_loader.get_default_profile.return_value = "huawei_deepseek"
    ctx.event_log.log_step_completed = MagicMock()
    ctx.event_log._compute_hash = MagicMock(return_value="hash")
    ctx.file_output_handler.handle = AsyncMock(return_value=[])
    ctx.verifier_engine.run = AsyncMock(return_value=[])

    qwen_executor = MagicMock()
    qwen_executor.execute = AsyncMock(
        side_effect=[
            {
                "status": "completed",
                "generated_text": json.dumps(
                    {
                        "contract_type": "product-goal-contract",
                        "requirement_overview": {"description": "待确认"},
                    },
                    ensure_ascii=False,
                ),
                "structured_payload": {
                    "contract_type": "product-goal-contract",
                    "requirement_overview": {"description": "待确认"},
                },
            },
            {
                "status": "completed",
                "generated_text": json.dumps(
                    {
                        "contract_type": "product-goal-contract",
                        "requirement_overview": {"description": "待确认"},
                    },
                    ensure_ascii=False,
                ),
                "structured_payload": {
                    "contract_type": "product-goal-contract",
                    "requirement_overview": {"description": "待确认"},
                },
            },
        ]
    )
    kimi_executor = MagicMock()
    kimi_executor.execute = AsyncMock(
        return_value={
            "status": "completed",
            "generated_text": json.dumps(
                {
                    "contract_type": "product-goal-contract",
                    "requirement_overview": {
                        "description": "支持 qwen_chat 作为对话执行器。",
                        "target_users": "LEE 工作流维护者",
                    },
                },
                ensure_ascii=False,
            ),
            "structured_payload": {
                "contract_type": "product-goal-contract",
                "requirement_overview": {
                    "description": "支持 qwen_chat 作为对话执行器。",
                    "target_users": "LEE 工作流维护者",
                },
            },
        }
    )
    ctx.executor_factory.create = MagicMock(side_effect=[qwen_executor, kimi_executor])
    monkeypatch.setattr(LLMRunner, "_resolve_qwen_fallback_target", classmethod(lambda cls, project_root: "kimi"))

    result = await runner.execute("wf-qwen-contract-fallback-001", step, ctx)

    assert result.status == "success"
    assert qwen_executor.execute.await_count == 2
    assert kimi_executor.execute.await_count == 1
    completed_output = ctx.state_machine.complete_step.await_args.args[2]
    assert completed_output["fallback_triggered"] is True
    assert completed_output["fallback_reason"] == "qwen_contract_validation_failed"
    assert completed_output["business_output"]["requirement_overview"]["target_users"] == "LEE 工作流维护者"


@pytest.mark.asyncio
async def test_llm_runner_repairs_plain_llm_contract_mismatch_without_qwen_fallback(runner, ctx, temp_project_root):
    schema_path = temp_project_root / "product-goal.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["contract_type", "requirement_overview"],
                "properties": {
                    "contract_type": {"type": "string"},
                    "requirement_overview": {
                        "type": "object",
                        "required": ["description", "target_users"],
                        "properties": {
                            "description": {"type": "string"},
                            "target_users": {"type": "string"},
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="source_normalization",
        agent_id="agent.analysis.product_goal",
        executor_type="llm",
        config={"output_contract": str(schema_path)},
        outputs=[],
    )
    instance = SimpleNamespace(
        data={"executor_override": "llm", "run_id": "run-llm-contract-repair-001"},
        template_id="workflow.product.task.raw_to_src",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.state_machine.complete_step = AsyncMock(
        return_value=StepResult(status="success", step_id=step.id, workflow_id="wf-llm-contract-repair-001", message="ok")
    )
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="你是产品分析助手",
            user_prompt="请输出 product goal contract",
            temperature=0.2,
            max_tokens=512,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.llm_config_loader = MagicMock()
    ctx.llm_config_loader.get_default_profile.return_value = "huawei_deepseek"
    ctx.event_log.log_step_completed = MagicMock()
    ctx.event_log._compute_hash = MagicMock(return_value="hash")
    ctx.file_output_handler.handle = AsyncMock(return_value=[])
    ctx.verifier_engine.run = AsyncMock(return_value=[])

    llm_executor = MagicMock()
    llm_executor.execute = AsyncMock(
        side_effect=[
            {
                "status": "completed",
                "generated_text": json.dumps(
                    {
                        "contract_type": "product-goal-contract",
                        "requirement_overview": {"description": "待确认"},
                    },
                    ensure_ascii=False,
                ),
            },
            {
                "status": "completed",
                "generated_text": json.dumps(
                    {
                        "contract_type": "product-goal-contract",
                        "requirement_overview": {
                            "description": "支持 llm 执行器作为结构化后端。",
                            "target_users": "LEE 工作流维护者",
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ]
    )
    ctx.executor_factory.create = MagicMock(return_value=llm_executor)

    result = await runner.execute("wf-llm-contract-repair-001", step, ctx)

    assert result.status == "success"
    assert llm_executor.execute.await_count == 2
    completed_output = ctx.state_machine.complete_step.await_args.args[2]
    assert completed_output["contract_repair_retry"] is True
    assert "fallback_triggered" not in completed_output


def test_qwen_fallback_target_ignores_coding_fallback_and_uses_non_coding_default(tmp_path):
    config_dir = tmp_path / ".lee"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "executor:\n  default_type: llm\n  coding_fallback: kimi\n",
        encoding="utf-8",
    )

    assert LLMRunner._resolve_qwen_fallback_target(str(tmp_path)) == "llm"


def test_qwen_fallback_target_disables_unsafe_coding_executor_default(tmp_path):
    config_dir = tmp_path / ".lee"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "executor:\n  default_type: kimi\n  coding_fallback: kimi\n",
        encoding="utf-8",
    )

    assert LLMRunner._resolve_qwen_fallback_target(str(tmp_path)) is None


@pytest.mark.asyncio
async def test_llm_runner_qwen_fallback_to_llm_uses_default_non_qwen_profile(runner, ctx, temp_project_root, monkeypatch):
    schema_path = temp_project_root / "product-goal.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["contract_type", "requirement_overview"],
                "properties": {
                    "contract_type": {"type": "string"},
                    "requirement_overview": {
                        "type": "object",
                        "required": ["description", "target_users"],
                        "properties": {
                            "description": {"type": "string"},
                            "target_users": {"type": "string"},
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="source_normalization",
        agent_id="agent.analysis.product_goal",
        executor_type="llm",
        config={"output_contract": str(schema_path)},
        outputs=[],
    )
    instance = SimpleNamespace(
        data={"executor_override": "qwen_chat", "run_id": "run-qwen-llm-fallback-001"},
        template_id="workflow.product.task.raw_to_src",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.state_machine.complete_step = AsyncMock(
        return_value=StepResult(status="success", step_id=step.id, workflow_id="wf-qwen-llm-fallback-001", message="ok")
    )
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="你是产品分析助手",
            user_prompt="请输出 product goal contract",
            temperature=0.2,
            max_tokens=512,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.llm_config_loader = MagicMock()
    ctx.llm_config_loader.get_default_profile.return_value = "huawei_deepseek"
    ctx.event_log.log_step_completed = MagicMock()
    ctx.event_log._compute_hash = MagicMock(return_value="hash")
    ctx.file_output_handler.handle = AsyncMock(return_value=[])
    ctx.verifier_engine.run = AsyncMock(return_value=[])

    qwen_executor = MagicMock()
    qwen_executor.execute = AsyncMock(
        side_effect=[
            {
                "status": "completed",
                "generated_text": json.dumps(
                    {
                        "contract_type": "product-goal-contract",
                        "requirement_overview": {"description": "待确认"},
                    },
                    ensure_ascii=False,
                ),
                "structured_payload": {
                    "contract_type": "product-goal-contract",
                    "requirement_overview": {"description": "待确认"},
                },
            },
            {
                "status": "completed",
                "generated_text": json.dumps(
                    {
                        "contract_type": "product-goal-contract",
                        "requirement_overview": {"description": "待确认"},
                    },
                    ensure_ascii=False,
                ),
                "structured_payload": {
                    "contract_type": "product-goal-contract",
                    "requirement_overview": {"description": "待确认"},
                },
            },
        ]
    )
    llm_executor = MagicMock()
    llm_executor.execute = AsyncMock(
        return_value={
            "status": "completed",
            "generated_text": json.dumps(
                {
                    "contract_type": "product-goal-contract",
                    "requirement_overview": {
                        "description": "支持 qwen_chat 作为备用对话执行器。",
                        "target_users": "LEE 工作流维护者",
                    },
                },
                ensure_ascii=False,
            ),
            "structured_payload": {
                "contract_type": "product-goal-contract",
                "requirement_overview": {
                    "description": "支持 qwen_chat 作为备用对话执行器。",
                    "target_users": "LEE 工作流维护者",
                },
            },
        }
    )
    ctx.executor_factory.create = MagicMock(side_effect=[qwen_executor, llm_executor])
    monkeypatch.setattr(LLMRunner, "_resolve_qwen_fallback_target", classmethod(lambda cls, project_root: "llm"))

    result = await runner.execute("wf-qwen-llm-fallback-001", step, ctx)

    assert result.status == "success"
    assert ctx.executor_factory.create.call_args_list[0].kwargs["profile"] == "qwen"
    assert ctx.executor_factory.create.call_args_list[1].args[0] == "llm"
    assert ctx.executor_factory.create.call_args_list[1].kwargs["profile"] == "huawei_deepseek"


@pytest.mark.asyncio
async def test_llm_runner_bridges_agent_step_to_kimi_code_executor(runner, ctx, temp_project_root):
    step = SimpleNamespace(
        id="source_normalization",
        agent_id="agent.analysis.product_goal",
        executor_type="llm",
        config={"claude_code": {"allowed_commands": ["Get-ChildItem"]}},
        outputs=[],
    )

    instance = SimpleNamespace(
        data={"executor_override": "kimi", "run_id": "run-003"},
        template_id="workflow.product.task.raw_to_src",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system",
            user_prompt="user",
            temperature=0.2,
            max_tokens=512,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.llm_config_loader = MagicMock()
    ctx.llm_config_loader.get_default_profile.return_value = "huawei_deepseek"
    ctx.resolve_workdir = MagicMock(return_value=str(temp_project_root))

    executor = MagicMock()
    executor.execute = AsyncMock(return_value={"status": "failed", "error": "boom"})
    ctx.executor_factory.create.return_value = executor

    result = await runner.execute("wf-003", step, ctx)

    assert result.status == "failed"
    ctx.executor_factory.create.assert_called_once_with(
        "kimi",
        profile="kimi",
        agent_id="agent.analysis.product_goal",
    )
    execution = ctx.store.create_task_execution.await_args.args[0]
    assert execution.executor_type == "kimi"
    assert execution.input_data["goal"] == "user"
    assert execution.input_data["workspace"] == str(temp_project_root)
    assert execution.input_data["system_prompt_extra"] == "system"
    assert execution.input_data["allowed_commands"] == ["Get-ChildItem"]
    assert "prompt" not in execution.input_data


@pytest.mark.asyncio
async def test_materialize_ssot_outputs_from_agent_contract(runner, ctx, temp_project_root):
    step = SimpleNamespace(
        id="write_prd",
        agent_id="agent.product.prd_writer",
        config={},
    )

    generated_text = """
{
  "contract_version": "1.0",
  "run_id": "run-ssot-001",
  "outputs": [
    {
      "key": "epic",
      "identity_kind": "ssot",
      "ssot_type": "epic",
      "title": "增长基础设施",
      "source_refs": ["SRC-001#1.2"]
    },
    {
      "key": "feat",
      "identity_kind": "ssot",
      "ssot_type": "feat",
      "title": "用户注册",
      "parent": "epic",
      "source_refs": ["epic#scope"]
    }
  ]
}
""".strip()

    result = await runner._materialize_ssot_outputs(
        ctx=ctx,
        step=step,
        workflow_id="wf-001",
        generated_text=generated_text,
    )

    assert result is not None
    assert result["outputs"]["epic"]["id"] == "EPIC-001"
    assert result["outputs"]["feat"]["parent_id"] == "EPIC-001"
    assert len(result["materialized_files"]) == 2
    assert (temp_project_root / "spec" / "requirements" / "epics").exists()
    assert (temp_project_root / "spec" / "requirements" / "features").exists()


@pytest.mark.asyncio
async def test_materialize_ssot_outputs_from_envelope_payload(runner, ctx, temp_project_root):
    step = SimpleNamespace(
        id="write_prd",
        agent_id="agent.product.prd_writer",
        config={},
    )

    generated_text = """
{
  "business_output": {
    "metadata": {
      "is_frozen": true
    }
  },
  "ssot_output_contract": {
    "contract_version": "1.0",
    "run_id": "run-ssot-002",
    "outputs": [
      {
        "key": "feat",
        "identity_kind": "ssot",
        "ssot_type": "feat",
        "title": "用户注册"
      }
    ]
  }
}
""".strip()

    structured_payload = runner._parse_structured_output_if_possible(generated_text)
    business_output = runner._extract_business_output_payload(structured_payload, generated_text)

    assert business_output == {"metadata": {"is_frozen": True}}

    result = await runner._materialize_ssot_outputs(
        ctx=ctx,
        step=step,
        workflow_id="wf-001",
        generated_text=generated_text,
        structured_payload=structured_payload,
    )

    assert result is not None
    assert result["outputs"]["feat"]["id"] == "FEAT-001"
    assert len(result["materialized_files"]) == 1
    assert (temp_project_root / "spec" / "requirements" / "features").exists()


def test_governance_preflight_requires_anchor_when_no_formal_ssot(temp_project_root, runner):
    agent_spec = SimpleNamespace(
        contracts={},
        governance={
            "acceptance_briefs": str((Path.cwd() / ".project" / "governance" / "ACCEPTANCE_BRIEFS").resolve()),
            "module_contracts": str((Path.cwd() / ".project" / "governance" / "MODULE_CONTRACTS").resolve()),
        },
        tags=["backend", "implementation"],
        spec_path=str((Path.cwd() / "spec-global" / "core" / "agents" / "agent-spec-maintainer" / "v1" / "agent.yaml").resolve()),
    )
    step = SimpleNamespace(id="impl_step", agent_id="agent.backend.impl", config={})

    result = runner._evaluate_governance_preflight(
        step=step,
        agent_spec=agent_spec,
        project_root=str(temp_project_root),
        structured_payload={"business_output": {"ok": True}},
    )

    assert result["implementation_facing"] is True
    assert result["formal_ssot_present"] is False
    assert result["allow_full_completion"] is False
    assert result["warnings"]


def test_claude_code_runner_merges_forbidden_read_paths():
    merged = ClaudeCodeRunner._merge_forbidden_read_paths([".tmp/", "output/", "pytest-temp/"])

    assert merged == [
        "output/",
        "evidence/",
        ".workflow/claude-code/",
        "pytest-temp/",
        ".codex-worktrees/",
        ".tmp/",
    ]


def test_claude_code_runner_merges_context_files():
    merged = ClaudeCodeRunner._merge_context_files(
        ["spec/requirements/epics/EPIC-001.md"],
        ["spec/requirements/epics/EPIC-001.md", "spec/adr/ADR-007.md"],
    )

    assert merged == [
        "spec/requirements/epics/EPIC-001.md",
        "spec/adr/ADR-007.md",
    ]


def test_claude_code_runner_collects_authoritative_context_files():
    step = SimpleNamespace(
        inputs=[
            {"source": "business_opportunity", "required": True},
        ]
    )

    collected = ClaudeCodeRunner._collect_authoritative_context_files(
        step,
        {
            "params": {
                "business_opportunity": {
                    "path": "spec/adr/ADR-007__qa-department-ssot-alignment-and-workflow-reframe.md"
                }
            }
        },
    )

    assert collected == [
        "spec/adr/ADR-007__qa-department-ssot-alignment-and-workflow-reframe.md"
    ]


def test_claude_code_runner_authoritative_context_skip_keys_alias_matches_llm_runner():
    assert (
        ClaudeCodeRunner.AUTHORITATIVE_CONTEXT_SKIP_KEYS
        == LLMRunner.AUTHORITATIVE_CONTEXT_SKIP_KEYS
    )


def test_expected_feat_review_subject_refs_supports_class_level_call():
    refs = LLMRunner._expected_feat_review_subject_refs(
        {
            "step_outputs": {
                "feat_spec_generation": {
                    "generated_text": """
business_output:
  epic_ref: EPIC-001
  feat_specs:
    - feat_id: FEAT-101
      title: Demo
""".strip()
                }
            }
        }
    )

    assert refs == ["FEAT-101"]


def test_claude_code_runner_skips_nested_materialized_paths_in_frozen_inputs():
    step = SimpleNamespace(
        inputs=[
            {"source": "feat_freeze", "required": True},
        ]
    )

    collected = ClaudeCodeRunner._collect_authoritative_context_files(
        step,
        {
            "params": {
                "feat_freeze": {
                    "gate_approved": True,
                    "business_output": {"epic_ref": "EPIC-030"},
                    "frozen_inputs": {
                        "feat_specs": {
                            "ssot_materialized": {
                                "feat_001": {
                                    "path": "spec/requirements/features/FEAT-159__hexinceshiyinqing.md"
                                }
                            }
                        }
                    },
                }
            }
        },
    )

    assert collected == []


def test_source_normalization_synthesizes_src_source_refs_from_metadata(runner):
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "metadata": {
            "source_ref": "ADR-007",
        },
        "normalized_content": {
            "title": "QA workflow reframe",
        },
    }

    _, payload = runner._synthesize_single_ssot_payload(
        step=step,
        workflow_id="wf-src-001",
        business_output=business_output,
        structured_payload={},
    )

    outputs = payload["ssot_output_contract"]["outputs"]
    assert outputs[0]["source_refs"] == ["ADR-007"]


def test_source_normalization_derives_meaningful_src_title_from_problem_statement(runner):
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "title": "SRC",
        "metadata": {
            "source_ref": "ADR-012",
        },
        "normalized_content": {
            "problem_statement": "QA Department SSOT Alignment and Workflow Reframe",
        },
    }

    _, payload = runner._synthesize_single_ssot_payload(
        step=step,
        workflow_id="wf-src-002",
        business_output=business_output,
        structured_payload={},
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["title"] == "QA Department SSOT Alignment and Workflow Reframe"


def test_source_normalization_derives_meaningful_src_title_from_nested_product_goal(runner):
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "product_goal": {
            "title": "需求链一致性测试体系建设",
            "essence": "将需求链从文档审阅对象转化为可测试系统",
        },
        "src_metadata": {
            "derived_from": "ADR-011",
        },
    }

    _, payload = runner._synthesize_single_ssot_payload(
        step=step,
        workflow_id="wf-src-002b",
        business_output=business_output,
        structured_payload={},
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["title"] == "需求链一致性测试体系建设"


def test_source_normalization_rewrites_generic_src_contract_title_when_contract_already_exists(runner):
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "contract_info": {
            "title": "ADR-017 Gate 治理目标与价值分析",
        },
        "metadata": {
            "source_ref": "ADR-017",
        },
    }
    structured_payload = {
        "ssot_output_contract": {
            "contract_version": "1.0",
            "run_id": "wf-src-002c",
            "outputs": [
                {
                    "key": "src",
                    "identity_kind": "ssot",
                    "ssot_type": "src",
                    "title": "SRC",
                    "content": "title: SRC\n",
                }
            ],
        }
    }

    _, payload = runner._synthesize_single_ssot_payload(
        step=step,
        workflow_id="wf-src-002c",
        business_output=business_output,
        structured_payload=structured_payload,
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["title"] == "ADR-017 Gate 治理目标与价值分析"
    assert output["source_refs"] == ["ADR-017"]


def test_source_normalization_rejects_process_analysis_title(runner):
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "contract_info": {
            "title": "ADR 原始输入归一化与合同复用前置目标分析",
        }
    }

    with pytest.raises(ValueError, match="semantic drift"):
        runner._synthesize_single_ssot_payload(
            step=step,
            workflow_id="wf-src-drift",
            business_output=business_output,
            structured_payload={},
        )


def test_source_normalization_rejects_multiple_src_outputs(runner):
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "contract_info": {
            "title": "ADR-017 Gate 治理目标与价值分析",
        }
    }

    with pytest.raises(ValueError, match="exactly one src output"):
        runner._synthesize_single_ssot_payload(
            step=step,
            workflow_id="wf-src-multi",
            business_output=business_output,
            structured_payload={
                "ssot_output_contract": {
                    "outputs": [
                        {"key": "src", "identity_kind": "ssot", "ssot_type": "src", "title": "SRC"},
                        {"key": "note", "identity_kind": "ssot", "ssot_type": "note", "title": "bad extra"},
                    ]
                }
            },
        )


def test_source_normalization_allows_contextual_normalization_wording(runner):
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "contract_info": {
            "title": "ADR-017 Gate 治理目标与价值分析",
        },
        "requirement_overview": {
            "description": "该对象会在 source normalization 阶段作为下游输入，并沿用既有复用策略。",
        },
        "metadata": {
            "source_ref": "ADR-017",
        },
    }

    _, payload = runner._synthesize_single_ssot_payload(
        step=step,
        workflow_id="wf-src-context",
        business_output=business_output,
        structured_payload={},
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["title"] == "ADR-017 Gate 治理目标与价值分析"
    assert output["source_refs"] == ["ADR-017"]


def test_epic_designer_synthesizes_epic_source_refs_and_derived_from(runner):
    step = SimpleNamespace(id="epic_design", agent_id="agent.product.epic_designer", config={})
    business_output = {
        "title": "QA Department SSOT Alignment and Workflow Reframe",
        "source_refs": ["SRC-007", "PD-SRC-007"],
        "ssot": {
            "derived_from": "SRC-007",
        },
    }

    _, payload = runner._synthesize_single_ssot_payload(
        step=step,
        workflow_id="wf-epic-001",
        business_output=business_output,
        structured_payload={},
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["source_refs"] == ["SRC-007"]
    assert output["derived_from"] == ["SRC-007"]


def test_epic_designer_falls_back_to_derived_from_for_source_refs(runner):
    step = SimpleNamespace(id="epic_design", agent_id="agent.product.epic_designer", config={})
    business_output = {
        "title": "QA Department SSOT Alignment and Workflow Reframe",
        "ssot": {
            "derived_from": "SRC-007",
        },
    }

    _, payload = runner._synthesize_single_ssot_payload(
        step=step,
        workflow_id="wf-epic-002",
        business_output=business_output,
        structured_payload={},
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["source_refs"] == ["SRC-007#scope"]


def test_epic_designer_uses_source_problem_and_formal_epic_id(runner):
    step = SimpleNamespace(id="epic_design", agent_id="agent.product.epic_designer", config={})
    business_output = {
        "epic_id": "EPIC-012",
        "title": "Kimi Executor 接入与配置能力",
        "ssot": {
            "source_problem": "SRC-012",
        },
    }

    _, payload = runner._synthesize_single_ssot_payload(
        step=step,
        workflow_id="wf-epic-003",
        business_output=business_output,
        structured_payload={},
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["source_refs"] == ["SRC-012#scope"]
    assert output["derived_from"] == "SRC-012"
    assert output["properties"]["formal_id"] == "EPIC-012"


def test_epic_designer_uses_instance_source_freeze_when_problem_id_is_prefixed(runner):
    step = SimpleNamespace(id="epic_design", agent_id="agent.product.epic_designer", config={})
    business_output = {
        "epic_id": "EPIC-012",
        "title": "Kimi Executor 接入与配置能力",
        "source_refs": ["PD-SRC-012"],
        "ssot": {
            "derived_from": "PD-SRC-012",
        },
    }

    _, payload = runner._synthesize_single_ssot_payload(
        step=step,
        workflow_id="wf-epic-004",
        business_output=business_output,
        structured_payload={},
        instance_data={
            "params": {
                "source_freeze": {
                    "id": "SRC-012",
                    "path": "spec/source/SRC-012__src.md",
                }
            }
        },
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["source_refs"] == ["SRC-012#scope"]
    assert output["derived_from"] == "SRC-012"
    assert output["properties"]["formal_id"] == "EPIC-012"


def test_pm_planner_normalization_remaps_acceptance_ids_from_formal_feat(temp_project_root, runner):
    feat_dir = temp_project_root / "spec" / "requirements" / "features"
    feat_dir.mkdir(parents=True, exist_ok=True)
    feat_path = feat_dir / "FEAT-143__qa-entry.md"
    feat_path.write_text(
        "\n".join(
            [
                "---",
                "id: FEAT-143",
                "title: QA 执行入口规范化",
                "parent_id: EPIC-QA-SSOT-UPGRADE",
                "---",
                "",
                "## AC-003-001",
                "- Scenario: 执行入口唯一性验证",
                "- Then: 仅允许通过 TASK 触发执行",
                "",
                "## AC-003-002",
                "- Scenario: 执行路径完整性校验",
                "- Then: 系统验证 release_ref -> testplan_ref -> task_ref 链路完整且有效",
                "",
            ]
        ),
        encoding="utf-8",
    )

    business_output = {
        "parent_epic": "EPIC-QA-SSOT-UPGRADE",
        "source_feats": ["FEAT-143"],
        "task_specs": [
            {
                "task_id": "TASK-FEAT-143-001",
                "title": "实现任务",
                "objective": "实现执行入口校验",
                "description": "实现执行入口校验",
                "source_feat": "FEAT-143",
                "workstream": "qa-execution-gate",
                "task_kind": "implementation",
                "responsible_role": "qa-execution-gate-owner",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-143", "ac": "AC-143-001", "description": "唯一入口"},
                    {"feat": "FEAT-143", "ac": "AC-143-002", "description": "路径校验"},
                ],
                "prerequisites": [],
                "dependencies": [],
                "definition_of_done": ["done"],
                "priority": "P0",
                "milestone": "M1",
                "estimated_effort": "1 day",
                "lifecycle_status": "planned",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "task-execution",
                    "audit_fields": ["run_id"],
                },
                "evidence_requirements": {"required_refs": ["FEAT-143"], "review_required": True},
                "rollback_strategy": {"mode": "revert", "restore_targets": ["src/qa"]},
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-143",
                    "derived_from": "FEAT-143#delivery",
                },
            }
        ],
        "milestones": [{"id": "M1", "name": "实现", "task_ids": ["TASK-FEAT-143-001"], "acceptance_criteria": "完成"}],
        "dependency_graph": {"critical_path": ["TASK-FEAT-143-001"]},
        "resource_allocation": {"qa-execution-gate-owner": {"tasks": ["TASK-FEAT-143-001"]}},
        "risk_mitigation": [],
    }

    normalized_business, _ = runner._normalize_pm_planner_task_payload(
        step=SimpleNamespace(id="task_planning", agent_id="agent.product.pm_planner"),
        workflow_id="wf-task-001",
        business_output=business_output,
        structured_payload={},
        instance_data={"params": {"feat_freeze_ref": str(feat_path)}},
    )

    implementation_task = next(
        item for item in normalized_business["task_specs"] if item["task_id"] == "TASK-FEAT-143-001"
    )
    mapped_ids = [item["ac"] for item in implementation_task["acceptance_criteria_mapping"]]

    assert mapped_ids == ["AC-003-001", "AC-003-002"]


def test_pm_planner_normalization_injects_governance_task_for_structural_feat(temp_project_root, runner):
    feat_dir = temp_project_root / "spec" / "requirements" / "features"
    feat_dir.mkdir(parents=True, exist_ok=True)
    feat_path = feat_dir / "FEAT-143__qa-entry.md"
    feat_path.write_text(
        "\n".join(
            [
                "---",
                "id: FEAT-143",
                "title: QA 执行入口规范化",
                "parent_id: EPIC-QA-SSOT-UPGRADE",
                "---",
                "",
                "## AC-003-001",
                "- Scenario: 执行入口唯一性验证",
                "- Then: 仅允许通过 TASK 触发执行",
                "",
                "## AC-003-002",
                "- Scenario: 执行路径完整性校验",
                "- Then: 系统验证 RULE-001 到 RULE-006 链路规则和状态机边界",
                "",
                "## AC-003-003",
                "- Scenario: 旁路执行入口阻断验证",
                "- Then: 系统拒绝旁路请求并返回入口规范错误",
                "",
            ]
        ),
        encoding="utf-8",
    )

    business_output = {
        "parent_epic": "EPIC-QA-SSOT-UPGRADE",
        "source_feats": ["FEAT-143"],
        "task_specs": [
            {
                "task_id": "TASK-FEAT-143-001",
                "title": "QA 执行入口实现",
                "objective": "实现执行入口校验",
                "description": "实现链路校验代码",
                "source_feat": "FEAT-143",
                "workstream": "qa-execution-gate",
                "task_kind": "implementation",
                "responsible_role": "qa-execution-gate-owner",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-143", "ac": "AC-143-001", "description": "唯一入口"},
                    {"feat": "FEAT-143", "ac": "AC-143-002", "description": "路径校验"},
                ],
                "prerequisites": [],
                "dependencies": [],
                "definition_of_done": ["done"],
                "priority": "P0",
                "milestone": "M1",
                "estimated_effort": "1 day",
                "lifecycle_status": "planned",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "task-execution",
                    "audit_fields": ["run_id"],
                },
                "evidence_requirements": {"required_refs": ["FEAT-143"], "review_required": True},
                "rollback_strategy": {"mode": "revert", "restore_targets": ["src/qa"]},
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-143",
                    "derived_from": "FEAT-143#delivery",
                },
            }
        ],
        "milestones": [{"id": "M1", "name": "实现", "task_ids": ["TASK-FEAT-143-001"], "acceptance_criteria": "完成"}],
        "dependency_graph": {"critical_path": ["TASK-FEAT-143-001"]},
        "resource_allocation": {"qa-execution-gate-owner": {"tasks": ["TASK-FEAT-143-001"]}},
        "risk_mitigation": [],
    }

    normalized_business, _ = runner._normalize_pm_planner_task_payload(
        step=SimpleNamespace(id="task_planning", agent_id="agent.product.pm_planner"),
        workflow_id="wf-task-002",
        business_output=business_output,
        structured_payload={},
        instance_data={"params": {"feat_freeze_ref": str(feat_path)}},
    )

    governance_task = normalized_business["task_specs"][0]
    implementation_task = next(
        item for item in normalized_business["task_specs"] if item["task_id"] == "TASK-FEAT-143-001"
    )

    assert governance_task["task_kind"] == "governance"
    assert governance_task["workstream"] == "governance-spec"
    assert governance_task["task_id"] == "TASK-FEAT-143-000"
    assert governance_task["title"] == "执行入口链路规则与状态机规范"
    governance_ac_ids = [item["ac"] for item in governance_task["acceptance_criteria_mapping"]]
    assert "AC-003-003" in governance_ac_ids
    assert implementation_task["dependencies"][0] == "TASK-FEAT-143-000"


def test_pm_planner_normalization_injects_feat_specific_governance_task_for_executor_config_feat(
    temp_project_root, runner
):
    feat_dir = temp_project_root / "spec" / "requirements" / "features"
    feat_dir.mkdir(parents=True, exist_ok=True)
    feat_path = feat_dir / "FEAT-169__executor-config.md"
    feat_path.write_text(
        "\n".join(
            [
                "---",
                "id: FEAT-169",
                "title: 系统配置层支持识别并透传 qwen 执行器类型标识",
                "parent_id: EPIC-022",
                "---",
                "",
                "# Goal",
                "",
                "系统配置层能够识别并透传 qwen 执行器类型标识",
                "",
                "## AC-001",
                "- Scenario: CLI 指定执行器类型",
                "- Then: 配置层识别 executor_type 为 qwen",
                "",
                "## AC-002",
                "- Scenario: 配置文件指定执行器类型",
                "- Then: 配置层识别 executor_type 为 qwen",
                "",
                "## AC-003",
                "- Scenario: 执行器来源优先级判定",
                "- Then: 最终生效值为 qwen，并记录来源为 cli_override",
                "",
                "## AC-004",
                "- Scenario: 非法执行器配置报错",
                "- Then: 返回包含非法值与可选值列表的明确错误信息，且不进入 workflow 执行阶段",
                "",
            ]
        ),
        encoding="utf-8",
    )

    business_output = {
        "parent_epic": "EPIC-022",
        "source_feats": ["FEAT-169"],
        "planning_metadata": {"task_directory": "spec/tasks/<FEAT-ID>"},
        "task_specs": [
            {
                "task_id": "TASK-FEAT-169-001",
                "title": "ConfigResolver 配置解析器实现与验证",
                "objective": "实现 ConfigResolver 核心模块",
                "description": "实现 CLI/配置文件/默认值三级优先级配置解析与执行器类型验证",
                "source_feat": "FEAT-169",
                "workstream": "orchestrator-config-layer",
                "task_kind": "implementation",
                "responsible_role": "orchestrator-core-maintainer",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-169", "ac": "AC-001", "description": "识别 qwen"},
                    {"feat": "FEAT-169", "ac": "AC-002", "description": "识别配置文件"},
                    {"feat": "FEAT-169", "ac": "AC-003", "description": "CLI 优先级覆盖"},
                    {"feat": "FEAT-169", "ac": "AC-004", "description": "非法值报错"},
                ],
                "prerequisites": [],
                "dependencies": [],
                "definition_of_done": ["done"],
                "priority": "P0",
                "milestone": "M1",
                "estimated_effort": "2 days",
                "lifecycle_status": "planned",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "task-execution",
                    "audit_fields": ["run_id"],
                },
                "evidence_requirements": {"required_refs": ["FEAT-169"], "review_required": True},
                "rollback_strategy": {"mode": "revert", "restore_targets": ["src/lee/orchestrator"]},
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-169",
                    "derived_from": "FEAT-169#delivery",
                },
            },
            {
                "task_id": "TASK-FEAT-169-002",
                "title": "CLI 集成与配置透传路径打通",
                "objective": "修改 CLI run 命令集成 ConfigResolver",
                "description": "实现配置透传到 Orchestrator 和 ExecutorFactory",
                "source_feat": "FEAT-169",
                "workstream": "cli-orchestrator-integration",
                "task_kind": "implementation",
                "responsible_role": "cli-commands-maintainer",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-169", "ac": "AC-001", "description": "CLI 传递 qwen"},
                    {"feat": "FEAT-169", "ac": "AC-003", "description": "CLI 覆盖配置文件"},
                    {"feat": "FEAT-169", "ac": "AC-004", "description": "CLI 阻断非法值"},
                ],
                "prerequisites": ["TASK-FEAT-169-001"],
                "dependencies": [{"task_id": "TASK-FEAT-169-001", "relation": "requires"}],
                "definition_of_done": ["done"],
                "priority": "P0",
                "milestone": "M1",
                "estimated_effort": "1 day",
                "lifecycle_status": "planned",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "task-execution",
                    "audit_fields": ["run_id"],
                },
                "evidence_requirements": {"required_refs": ["FEAT-169"], "review_required": True},
                "rollback_strategy": {"mode": "revert", "restore_targets": ["src/lee/cli/commands"]},
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-169",
                    "derived_from": "FEAT-169#delivery",
                },
            },
        ],
        "milestones": [{"id": "M1", "name": "配置层实现", "task_ids": ["TASK-FEAT-169-001", "TASK-FEAT-169-002"], "acceptance_criteria": "完成"}],
        "dependency_graph": {"critical_path": ["TASK-FEAT-169-001", "TASK-FEAT-169-002"]},
        "resource_allocation": {
            "orchestrator-core-maintainer": {"tasks": ["TASK-FEAT-169-001"]},
            "cli-commands-maintainer": {"tasks": ["TASK-FEAT-169-002"]},
        },
        "risk_mitigation": [],
    }

    normalized_business, _ = runner._normalize_pm_planner_task_payload(
        step=SimpleNamespace(id="task_planning", agent_id="agent.product.pm_planner"),
        workflow_id="wf-task-169",
        business_output=business_output,
        structured_payload={},
        instance_data={"params": {"feat_freeze_ref": str(feat_path)}},
    )

    task_ids = [item["task_id"] for item in normalized_business["task_specs"]]
    governance_task = normalized_business["task_specs"][0]

    assert task_ids[:2] == ["TASK-FEAT-169-000", "TASK-FEAT-169-001"]
    assert governance_task["title"] == "执行器配置优先级与验证规则规范"
    assert governance_task["responsible_role"] == "executor-config-governance-owner"
    assert governance_task["title"] != "QA 执行入口链路规则与状态机规范"
    assert normalized_business["planning_metadata"]["task_directory"] == "spec/tasks/FEAT-169"


def test_pm_planner_normalization_injects_config_governance_task_for_priority_rules(
    temp_project_root, runner
):
    feat_dir = temp_project_root / "spec" / "requirements" / "features"
    feat_dir.mkdir(parents=True, exist_ok=True)
    feat_path = feat_dir / "FEAT-169__executor-config.md"
    feat_path.write_text(
        "\n".join(
            [
                "---",
                "id: FEAT-169",
                "title: 系统配置层支持识别并透传 qwen 执行器类型标识",
                "parent_id: EPIC-022",
                "---",
                "",
                "## AC-003",
                "- Scenario: 执行器来源优先级判定",
                "- Then: 最终生效值为 qwen，并记录来源为 cli_override",
                "",
                "## AC-004",
                "- Scenario: 非法执行器配置报错",
                "- Then: 返回包含非法值与可选值列表的明确错误信息，且不进入 workflow 执行阶段",
                "",
            ]
        ),
        encoding="utf-8",
    )

    business_output = {
        "parent_epic": "EPIC-022",
        "source_feats": ["FEAT-169"],
        "planning_metadata": {"task_directory": "spec/tasks/<FEAT-ID>"},
        "task_specs": [
            {
                "task_id": "TASK-FEAT-169-001",
                "title": "执行器类型配置核心组件与优先级解析实现",
                "objective": "实现执行器配置解析逻辑",
                "description": "实现解析逻辑",
                "source_feat": "FEAT-169",
                "workstream": "executor-config-core",
                "task_kind": "implementation",
                "responsible_role": "config-system-owner",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-169", "ac": "AC-003", "description": "优先级规则实现"},
                    {"feat": "FEAT-169", "ac": "AC-004", "description": "错误拦截实现"},
                ],
                "prerequisites": [],
                "dependencies": [],
                "definition_of_done": ["done"],
                "priority": "P0",
                "milestone": "M1",
                "estimated_effort": "2 days",
                "lifecycle_status": "planned",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "task-execution",
                    "audit_fields": ["run_id"],
                },
                "evidence_requirements": {"required_refs": ["FEAT-169"], "review_required": True},
                "rollback_strategy": {"mode": "revert", "restore_targets": ["src/lee/orchestrator"]},
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-169",
                    "derived_from": "FEAT-169#delivery",
                },
            }
        ],
        "milestones": [{"id": "M1", "name": "实现", "task_ids": ["TASK-FEAT-169-001"], "acceptance_criteria": "完成"}],
        "dependency_graph": {"critical_path": ["TASK-FEAT-169-001"]},
        "resource_allocation": {"config-system-owner": {"tasks": ["TASK-FEAT-169-001"]}},
        "risk_mitigation": [],
    }

    normalized_business, _ = runner._normalize_pm_planner_task_payload(
        step=SimpleNamespace(id="task_planning", agent_id="agent.product.pm_planner"),
        workflow_id="wf-task-169-governance",
        business_output=business_output,
        structured_payload={},
        instance_data={"params": {"feat_freeze_ref": str(feat_path)}},
    )

    governance_task = normalized_business["task_specs"][0]

    assert governance_task["task_id"] == "TASK-FEAT-169-000"
    assert governance_task["title"] == "执行器配置优先级与验证规则规范"
    assert governance_task["responsible_role"] == "executor-config-governance-owner"
    assert normalized_business["planning_metadata"]["task_directory"] == "spec/tasks/FEAT-169"


def test_governance_preflight_accepts_acceptance_brief_anchor(temp_project_root, runner):
    briefs_dir = temp_project_root / ".project" / "governance" / "ACCEPTANCE_BRIEFS"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    brief_path = briefs_dir / "AB-20260307-demo-task.md"
    brief_path.write_text(
        "\n".join(
            [
                "---",
                "brief_id: demo-task",
                "title: Demo Task",
                "status: active",
                "task_type: implementation",
                "scope_in:",
                "  - demo scope",
                "scope_out:",
                "  - out of scope",
                "human_gate_required: true",
                "evidence_required:",
                "  - changed_files",
                "---",
                "",
                "# Acceptance Brief",
            ]
        ),
        encoding="utf-8",
    )

    agent_spec = SimpleNamespace(
        contracts={},
        governance={
            "acceptance_briefs": str(briefs_dir),
            "module_contracts": str((temp_project_root / ".project" / "governance" / "MODULE_CONTRACTS").resolve()),
        },
        tags=["backend", "implementation"],
        spec_path=str((Path.cwd() / "spec-global" / "core" / "agents" / "agent-spec-maintainer" / "v1" / "agent.yaml").resolve()),
    )
    step = SimpleNamespace(
        id="impl_step",
        agent_id="agent.backend.impl",
        config={"acceptance_brief_id": "demo-task"},
    )

    result = runner._evaluate_governance_preflight(
        step=step,
        agent_spec=agent_spec,
        project_root=str(temp_project_root),
        structured_payload={"business_output": {"ok": True}},
    )

    assert result["formal_ssot_present"] is False
    assert result["acceptance_brief_found"] is True
    assert result["allow_full_completion"] is True
    assert result["acceptance_brief_metadata"]["brief_id"] == "demo-task"


def test_parse_markdown_front_matter_for_acceptance_brief(temp_project_root, runner):
    brief_path = temp_project_root / "AB-20260307-login-refactor.md"
    brief_path.write_text(
        "\n".join(
            [
                "---",
                "brief_id: login-refactor",
                "title: Login Refactor",
                "status: active",
                "human_gate_required: false",
                "---",
                "",
                "# Acceptance Brief",
            ]
        ),
        encoding="utf-8",
    )

    metadata = runner._parse_markdown_front_matter(brief_path)

    assert metadata["brief_id"] == "login-refactor"
    assert metadata["status"] == "active"


def test_build_executor_input_bridges_agent_step_to_codex(temp_project_root, runner, ctx):
    instance = SimpleNamespace(data={"run_id": "run-001"})
    step = SimpleNamespace(
        id="spec_maintenance",
        agent_id="agent.governance.spec_maintainer",
        config={
            "claude_code": {
                "max_iterations": 3,
                "allowed_commands": ["Get-ChildItem"],
            }
        },
    )
    agent_ctx = SimpleNamespace(
        system_prompt="system rules",
        user_prompt="maintain the target spec",
        temperature=0.2,
        max_tokens=1200,
    )
    ctx.resolve_workdir = MagicMock(return_value=str(temp_project_root))
    ctx.token_manager.encode_token_for_context.return_value = "encoded-token"

    input_data = runner._build_executor_input(
        executor_type="codex",
        step=step,
        ctx=ctx,
        instance=instance,
        workflow_id="wf-001",
        agent_ctx=agent_ctx,
        step_token="raw-token",
    )

    assert input_data["goal"] == "maintain the target spec"
    assert input_data["workspace"] == str(temp_project_root)
    assert input_data["system_prompt_extra"] == "system rules"
    assert input_data["allowed_commands"] == ["Get-ChildItem"]
    assert input_data["token_context"] == "encoded-token"


def test_build_executor_input_bridges_agent_step_to_kimi(temp_project_root, runner, ctx):
    instance = SimpleNamespace(data={"run_id": "run-001"})
    step = SimpleNamespace(
        id="spec_maintenance",
        agent_id="agent.governance.spec_maintainer",
        config={
            "claude_code": {
                "max_iterations": 3,
                "allowed_commands": ["Get-ChildItem"],
            }
        },
    )
    agent_ctx = SimpleNamespace(
        system_prompt="system rules",
        user_prompt="maintain the target spec",
        temperature=0.2,
        max_tokens=1200,
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

    assert input_data["goal"] == "maintain the target spec"
    assert input_data["workspace"] == str(temp_project_root)
    assert input_data["system_prompt_extra"] == "system rules"
    assert input_data["allowed_commands"] == ["Get-ChildItem"]
    assert input_data["token_context"] == "encoded-token"


def test_build_executor_input_adapts_qwen_prompt_for_structured_output(runner, ctx):
    instance = SimpleNamespace(data={"run_id": "run-001"})
    step = SimpleNamespace(
        id="raw_input_intake",
        agent_id="agent.analysis.product_goal",
        config={},
    )
    agent_ctx = SimpleNamespace(
        system_prompt="Role: 产品目标分析师",
        user_prompt="# Task\n分析需求\n\n## Output Contract\nReturn one machine-readable JSON object only.",
        temperature=0.2,
        max_tokens=1200,
    )
    ctx.token_manager.encode_token_for_context.return_value = "encoded-token"

    input_data = runner._build_executor_input(
        executor_type="qwen",
        step=step,
        ctx=ctx,
        instance=instance,
        workflow_id="wf-001",
        agent_ctx=agent_ctx,
        step_token="raw-token",
    )

    assert "workflow step" in input_data["system_message"]
    assert "Output exactly one machine-readable JSON or YAML object." in input_data["prompt"]
    assert "Do not introduce yourself" in input_data["prompt"]
    assert input_data["token_context"] == "encoded-token"


def test_claude_code_input_defaults_silence_timeout_to_executor_default(temp_project_root):
    agent_ctx = SimpleNamespace(
        system_prompt="system rules",
        user_prompt="generate feat specs",
        temperature=0.2,
        max_tokens=1200,
    )

    input_data = ClaudeCodeRunner._build_claude_code_input_data(
        agent_ctx=agent_ctx,
        claude_config={},
        workspace=str(temp_project_root),
        workflow_id="wf-claude-001",
        step_id="feat_spec_generation",
        context_files=[],
    )

    assert input_data["silence_timeout_seconds"] == ClaudeCodeRunner.DEFAULT_SILENCE_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_claude_code_runner_rejects_qwen_override_for_code_steps(temp_project_root, ctx):
    runner = ClaudeCodeRunner()
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        executor_type="claude_code",
        config={"claude_code": {}},
        outputs=[],
    )
    instance = SimpleNamespace(
        data={"executor_override": "qwen", "run_id": "run-qwen-001"},
        template_id="workflow.product.task.epic_to_feat",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system rules",
            user_prompt="拆解 EPIC",
            temperature=0.2,
            max_tokens=1024,
        )
    )
    ctx.token_manager.issue_token.return_value = None

    executor = MagicMock()
    executor.execute = AsyncMock(return_value={"status": "failed", "error": "boom"})
    ctx.executor_factory.create.return_value = executor

    ctx.resolve_workdir = MagicMock(return_value=str(temp_project_root))

    result = await runner.execute("wf-qwen-001", step, ctx)

    assert result.status == "failed"
    execution = ctx.store.create_task_execution.await_args.args[0]
    assert execution.executor_type == "claude_code"
    assert execution.input_data["goal"] == "拆解 EPIC"
    assert execution.input_data["workspace"] == str(temp_project_root)
    assert execution.input_data["system_prompt_extra"] == "system rules"
    assert "prompt" not in execution.input_data
    assert "system_message" not in execution.input_data


@pytest.mark.asyncio
async def test_claude_code_runner_builds_code_prompt_for_kimi_override(temp_project_root, ctx):
    runner = ClaudeCodeRunner()
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        executor_type="claude_code",
        config={"claude_code": {"allowed_commands": ["Get-ChildItem"]}},
        outputs=[],
    )
    instance = SimpleNamespace(
        data={"executor_override": "kimi", "run_id": "run-kimi-001"},
        template_id="workflow.product.task.epic_to_feat",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system rules",
            user_prompt="拆解 EPIC",
            temperature=0.2,
            max_tokens=1024,
        )
    )
    ctx.token_manager.issue_token.return_value = None
    ctx.resolve_workdir = MagicMock(return_value=str(temp_project_root))

    executor = MagicMock()
    executor.execute = AsyncMock(return_value={"status": "failed", "error": "boom"})
    ctx.executor_factory.create.return_value = executor

    result = await runner.execute("wf-kimi-001", step, ctx)

    assert result.status == "failed"
    execution = ctx.store.create_task_execution.await_args.args[0]
    assert execution.executor_type == "kimi"
    assert execution.input_data["goal"] == "拆解 EPIC"
    assert execution.input_data["workspace"] == str(temp_project_root)
    assert execution.input_data["system_prompt_extra"] == "system rules"
    assert execution.input_data["allowed_commands"] == ["Get-ChildItem"]
    assert "prompt" not in execution.input_data
    assert "system_message" not in execution.input_data


@pytest.mark.asyncio
async def test_claude_code_runner_fails_delivery_plan_reviewer_on_free_text_output(temp_project_root, ctx):
    runner = ClaudeCodeRunner()
    step = SimpleNamespace(
        id="delivery_plan_validation",
        agent_id="agent.product.delivery_plan_reviewer",
        executor_type="claude_code",
        config={"claude_code": {}},
        outputs=[],
    )
    instance = SimpleNamespace(
        data={
            "run_id": "run-review-001",
            "project_root": str(temp_project_root),
            "step_outputs": {
                "task_planning": {
                    "business_output": {
                        "source_feats": ["FEAT-143"],
                        "planning_metadata": {"task_directory": "spec/tasks/FEAT-143"},
                        "task_specs": [
                            {
                                "task_id": "TASK-FEAT-143-001",
                                "source_feat": "FEAT-143",
                                "task_kind": "specification",
                                "acceptance_criteria_mapping": [
                                    {"feat": "FEAT-143", "ac": "AC-003-001"},
                                ],
                            }
                        ],
                    }
                }
            },
        },
        template_id="workflow.product.task.feat_to_delivery_prep",
    )
    ctx.store.get_workflow = AsyncMock(return_value=instance)
    ctx.store.create_task_execution = AsyncMock()
    ctx.store.update_task_execution = AsyncMock()
    ctx.state_machine.fail_step = AsyncMock()
    ctx.contract_discovery.get_workflow_inputs.return_value = None
    ctx.agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system rules",
            user_prompt="review delivery plan",
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
            "raw_output": "现在我已经收集了所有需要的信息。评审结论：pass",
            "generated_text": "现在我已经收集了所有需要的信息。评审结论：pass",
            "changed_files": [],
            "commands_run": [],
            "test_results": {"passed": 0, "failed": 0},
        }
    )
    ctx.executor_factory.create.return_value = executor

    result = await runner.execute("wf-review-001", step, ctx)

    assert result.status == "failed"
    assert "Delivery plan review output" in result.message
    ctx.state_machine.fail_step.assert_awaited_once()


def test_extract_declared_output_values_reads_scalar_files(temp_project_root, runner):
    scalar_path = temp_project_root / "blocker_count"
    scalar_path.write_text("1\n", encoding="utf-8")
    text_path = temp_project_root / "review_status"
    text_path.write_text("warning\n", encoding="utf-8")
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="blocker_count"),
            SimpleNamespace(path="review_status"),
            SimpleNamespace(path="docs/reports/review.json"),
        ]
    )

    values = runner._extract_declared_output_values(
        step=step,
        written_files=[str(scalar_path), str(text_path)],
        project_root=str(temp_project_root),
    )

    assert values["blocker_count"] == 1
    assert values["review_status"] == "warning"
    assert "review" not in values


def test_extract_declared_output_values_reads_named_markdown_sections(temp_project_root, runner):
    review_text = """
### **Outputs Generated**

#### **`blocker_count`**
```
1
```

---

#### **`major_count`**
```
2
```

---

#### **`review_status`**
```
blocked
```
""".strip()
    blocker_path = temp_project_root / "blocker_count"
    major_path = temp_project_root / "major_count"
    status_path = temp_project_root / "review_status"
    blocker_path.write_text(review_text, encoding="utf-8")
    major_path.write_text(review_text, encoding="utf-8")
    status_path.write_text(review_text, encoding="utf-8")
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="blocker_count"),
            SimpleNamespace(path="major_count"),
            SimpleNamespace(path="review_status"),
        ]
    )

    values = runner._extract_declared_output_values(
        step=step,
        written_files=[str(blocker_path), str(major_path), str(status_path)],
        project_root=str(temp_project_root),
    )

    assert values["blocker_count"] == 1
    assert values["major_count"] == 2
    assert values["review_status"] == "blocked"


def test_extract_declared_output_values_reads_numbered_markdown_sections(temp_project_root, runner):
    review_text = """
**Outputs Generated:**

### 2. `review_findings`
```markdown
# Summary
blocked
```

### 3. `blocker_count`
```text
1
```

### 4. `major_count`
```text
2
```
""".strip()
    blocker_path = temp_project_root / "blocker_count"
    major_path = temp_project_root / "major_count"
    blocker_path.write_text(review_text, encoding="utf-8")
    major_path.write_text(review_text, encoding="utf-8")
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="blocker_count"),
            SimpleNamespace(path="major_count"),
        ]
    )

    values = runner._extract_declared_output_values(
        step=step,
        written_files=[str(blocker_path), str(major_path)],
        project_root=str(temp_project_root),
    )

    assert values["blocker_count"] == 1
    assert values["major_count"] == 2


def test_extract_declared_output_values_reads_numbered_list_sections(temp_project_root, runner):
    review_text = """
**Output Files Generated:**

1. **`review_findings`**
```
blocked
```

2. **`blocker_count`**
```text
1
```

3. **`major_count`**
```text
2
```
""".strip()
    blocker_path = temp_project_root / "blocker_count"
    major_path = temp_project_root / "major_count"
    blocker_path.write_text(review_text, encoding="utf-8")
    major_path.write_text(review_text, encoding="utf-8")
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="blocker_count"),
            SimpleNamespace(path="major_count"),
        ]
    )

    values = runner._extract_declared_output_values(
        step=step,
        written_files=[str(blocker_path), str(major_path)],
        project_root=str(temp_project_root),
    )

    assert values["blocker_count"] == 1
    assert values["major_count"] == 2


def test_apply_spec_writeback_writes_target_file_and_diff(temp_project_root, runner):
    target_path = temp_project_root / "spec-global" / "core" / "agents" / "demo" / "v1" / "agent.yaml"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("kind: agent\nname: old-demo\n", encoding="utf-8")

    diff_path = temp_project_root / "docs" / "reports" / "governance" / "spec-review" / "demo-spec.diff"
    step = SimpleNamespace(
        config={
            "spec_writeback": {
                "enabled": True,
                "target_path": str(target_path),
                "diff_report_path": str(diff_path),
            }
        }
    )

    result = runner._apply_spec_writeback(
        step=step,
        project_root=str(temp_project_root),
        structured_payload={
            "maintained_spec_content": "kind: agent\nname: new-demo\n",
        },
        generated_text="",
    )

    assert result is not None
    assert result["applied"] is True
    assert result["changed"] is True
    assert target_path.read_text(encoding="utf-8") == "kind: agent\nname: new-demo"
    assert diff_path.exists()
    assert "-name: old-demo" in diff_path.read_text(encoding="utf-8")
    assert "+name: new-demo" in diff_path.read_text(encoding="utf-8")


def test_apply_spec_writeback_reads_markdown_section_fallback(temp_project_root, runner):
    target_path = temp_project_root / "spec-global" / "core" / "contracts" / "demo.yaml"
    diff_path = temp_project_root / "docs" / "reports" / "governance" / "spec-review" / "demo-section.diff"
    step = SimpleNamespace(
        config={
            "spec_writeback": {
                "enabled": True,
                "target_path": str(target_path),
                "diff_report_path": str(diff_path),
            }
        }
    )
    generated_text = """
#### **`maintained_spec_content`**
```yaml
kind: contract
version: "1.0"
```
""".strip()

    result = runner._apply_spec_writeback(
        step=step,
        project_root=str(temp_project_root),
        structured_payload=None,
        generated_text=generated_text,
    )

    assert result is not None
    assert result["applied"] is True
    assert target_path.read_text(encoding="utf-8") == 'kind: contract\nversion: "1.0"'


def test_apply_spec_writeback_reads_target_path_section_fallback(temp_project_root, runner):
    target_path = temp_project_root / "spec-global" / "core" / "agents" / "demo" / "v1" / "agent.yaml"
    diff_path = temp_project_root / "docs" / "reports" / "governance" / "spec-review" / "demo-target.diff"
    step = SimpleNamespace(
        config={
            "spec_writeback": {
                "enabled": True,
                "target_path": str(target_path),
                "diff_report_path": str(diff_path),
            }
        }
    )
    generated_text = f"""
### **Output 2: `{target_path}`**
```yaml
kind: agent
name: target-path-demo
```
""".strip()

    result = runner._apply_spec_writeback(
        step=step,
        project_root=str(temp_project_root),
        structured_payload=None,
        generated_text=generated_text,
    )

    assert result is not None
    assert result["applied"] is True
    assert target_path.read_text(encoding="utf-8") == "kind: agent\nname: target-path-demo"


def test_extract_declared_output_values_falls_back_to_generated_text(runner, temp_project_root):
    generated_text = """
### 3. `blocker_count`
```text
1
```

---

### 4. `major_count`
```text
2
```
""".strip()
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="blocker_count"),
            SimpleNamespace(path="major_count"),
        ]
    )

    values = runner._extract_declared_output_values(
        step=step,
        written_files=[],
        project_root=str(temp_project_root),
        generated_text=generated_text,
    )

    assert values["blocker_count"] == 1
    assert values["major_count"] == 2


def test_completion_summary_marks_missing_fields_explicitly(runner):
    step = SimpleNamespace(id="impl_step")
    summary = runner._build_completion_summary(
        step=step,
        written_files=[],
        structured_payload={"scope_completed": "implemented login flow"},
        governance_preflight={"human_gate_required": True},
    )

    assert summary["scope_completed"] == "implemented login flow"
    assert summary["evidence"] == "missing"
    assert summary["tests_executed"] == "missing"
    assert summary["known_limitations"] == "not declared"
    assert summary["human_gate_required"] is True


def test_extract_ssot_contract_payload_from_named_section(runner):
    generated_text = """
## spec/qa/test-sets/ts-demo-module.yaml
```yaml
test_set_id: TS-DEMO-MODULE
module: demo-module
strategy:
  focus:
    - happy path
test_focus:
  positive:
    - happy path
traceability:
  feature_ids:
    - FEAT-023
  acceptance_criteria_refs:
    - AC1
```

## ssot_output_contract
```json
{
  "contract_version": "1.0",
  "run_id": "qa-run-001",
  "outputs": [
    {
      "key": "testset",
      "identity_kind": "ssot",
      "ssot_type": "testset",
      "title": "Demo Module Test Set",
      "parent": "FEAT-023",
      "verifies": ["FEAT-023"]
    }
  ]
}
```
""".strip()

    payload = runner._extract_ssot_contract_payload(
        structured_payload=None,
        generated_text=generated_text,
    )

    assert payload is not None
    assert payload["run_id"] == "qa-run-001"
    assert payload["outputs"][0]["key"] == "testset"


def test_extract_ssot_contract_payload_from_plain_label_section(runner):
    generated_text = """
spec/qa/test-sets/ts-demo-module.yaml
```yaml
test_set_id: TS-DEMO-MODULE
module: demo-module
strategy:
  focus:
    - happy path
test_focus:
  positive:
    - happy path
traceability:
  feature_ids:
    - FEAT-023
  acceptance_criteria_refs:
    - AC1
```

ssot_output_contract
```yaml
contract_version: "1.0"
run_id: "qa-run-002"
outputs:
  - key: testset
    identity_kind: ssot
    ssot_type: testset
    title: Demo Module Test Set
```
""".strip()

    payload = runner._extract_ssot_contract_payload(
        structured_payload=None,
        generated_text=generated_text,
    )

    assert payload is not None
    assert payload["run_id"] == "qa-run-002"


def test_extract_ssot_contract_payload_from_code_block_mapping(runner):
    generated_text = """
```yaml
# spec/qa/test-sets/ts-demo-module.yaml
test_set_id: TS-DEMO-MODULE
module: demo-module
strategy:
  focus:
    - happy path
test_focus:
  positive:
    - happy path
traceability:
  feature_ids:
    - FEAT-023
  acceptance_criteria_refs:
    - AC1
```

```yaml
ssot_output_contract:
  contract_version: "1.0"
  run_id: "qa-run-003"
  outputs:
    - key: testset
      identity_kind: ssot
      ssot_type: testset
      title: Demo Module Test Set
```
""".strip()

    payload = runner._extract_ssot_contract_payload(
        structured_payload=None,
        generated_text=generated_text,
    )

    assert payload is not None
    assert payload["run_id"] == "qa-run-003"


def test_normalize_ssot_contract_payload_promotes_feat_parent_from_verifies(runner):
    payload = {
        "contract_version": "1.0",
        "run_id": "qa-run-004",
        "outputs": [
            {
                "key": "testset",
                "identity_kind": "ssot",
                "ssot_type": "testset",
                "title": "Demo Module Test Set",
                "parent": "feat",
                "verifies": ["FEAT-123"],
                "properties": {"feature_id": "FEAT-123"},
            }
        ],
    }

    normalized = runner._normalize_ssot_contract_payload(payload)

    assert normalized["outputs"][0]["parent"] == "FEAT-123"


def test_normalize_ssot_contract_payload_drops_extra_keys_and_repairs_verifies(runner):
    payload = {
        "contract_version": "1.0",
        "run_id": "qa-run-005",
        "outputs": [
            {
                "key": "testset",
                "identity_kind": "ssot",
                "ssot_type": "testset",
                "title": "Demo Module Test Set",
                "parent": "FEAT-123",
                "verifies": ["feat"],
                "artifact_ref": "spec/qa/test-sets/ts-demo-module.yaml",
            }
        ],
    }

    normalized = runner._normalize_ssot_contract_payload(payload)

    assert "artifact_ref" not in normalized["outputs"][0]
    assert normalized["outputs"][0]["verifies"] == ["FEAT-123"]


def test_normalize_ssot_contract_payload_coerces_contract_version_to_string(runner):
    payload = {
        "contract_version": 1.0,
        "run_id": 20240325,
        "outputs": [],
    }

    normalized = runner._normalize_ssot_contract_payload(payload)

    assert normalized["contract_version"] == "1.0"
    assert normalized["run_id"] == "20240325"


def test_normalize_ssot_contract_payload_coerces_relation_lists(runner):
    payload = {
        "contract_version": "1.0",
        "run_id": "qa-run-006",
        "outputs": [
            {
                "key": "epic",
                "identity_kind": "ssot",
                "ssot_type": "epic",
                "title": "Kimi Executor Integration",
                "derived_from": "SRC-012",
                "source_refs": "SRC-012#scope",
                "verifies": ["", "SRC-012"],
                "depends_on": {"id": "EPIC-001"},
            }
        ],
    }

    normalized = runner._normalize_ssot_contract_payload(payload)

    output = normalized["outputs"][0]
    assert output["derived_from"] == ["SRC-012"]
    assert output["source_refs"] == ["SRC-012#scope"]
    assert output["verifies"] == ["SRC-012"]
    assert "depends_on" not in output


@pytest.mark.asyncio
async def test_llm_runner_only_sends_file_outputs_to_file_handler(temp_project_root):
    runner = LLMRunner()
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        executor_type="llm",
        config={},
        input={},
        outputs=[
            SimpleNamespace(path="", type="symbol", required=False),
            SimpleNamespace(path="spec/out.yaml", type="file", required=True),
        ],
    )
    llm_payload = {
        "status": "success",
        "provider": "test",
        "model": "test-model",
        "tokens_used": 1,
        "input_tokens": 1,
        "output_tokens": 1,
        "duration_seconds": 0.1,
        "stop_reason": "stop",
        "generated_text": "{}",
    }
    executor = MagicMock()
    executor.execute = AsyncMock(return_value=llm_payload)
    file_handler = MagicMock()
    file_handler.handle = AsyncMock(return_value=[str(temp_project_root / "spec" / "out.yaml")])
    store = MagicMock()
    store.get_workflow = AsyncMock(
        return_value=SimpleNamespace(
            data={"run_id": "run-001"},
            level="task",
            template_id="template.product.epic_to_feat",
        )
    )
    store.create_task_execution = AsyncMock()
    store.update_task_execution = AsyncMock()
    state_machine = MagicMock()
    state_machine.complete_step = AsyncMock(
        return_value=StepResult(
            status="completed",
            step_id=step.id,
            workflow_id="wf-001",
            message="ok",
        )
    )
    event_log = MagicMock()
    event_log.emit = AsyncMock()
    evidence_collector = MagicMock()
    evidence_collector.collect_task_execution = AsyncMock()
    verifier_engine = MagicMock()
    agent_loader = MagicMock()
    agent_loader.load.return_value = None
    agent_context_builder = MagicMock()
    agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system",
            user_prompt="user",
            temperature=0.1,
            max_tokens=100,
        )
    )
    agent_context_builder.agent_loader = agent_loader
    token_manager = MagicMock()
    token_manager.issue_token = MagicMock(return_value=None)
    ctx = RunnerContext(
        store=store,
        state_machine=state_machine,
        event_log=event_log,
        evidence_collector=evidence_collector,
        verifier_engine=verifier_engine,
        executor_factory=MagicMock(create=MagicMock(return_value=executor)),
        agent_context_builder=agent_context_builder,
        contract_discovery=MagicMock(get_workflow_inputs=MagicMock(return_value={})),
        file_output_handler=file_handler,
        token_manager=token_manager,
        project_root=str(temp_project_root),
    )

    await runner.execute("wf-001", step, ctx)

    passed_outputs = file_handler.handle.call_args.args[1]
    assert len(passed_outputs) == 1
    assert passed_outputs[0].path == "spec/out.yaml"


@pytest.mark.asyncio
async def test_llm_runner_does_not_fail_after_successful_schema_repair(temp_project_root):
    runner = LLMRunner()
    schema_path = temp_project_root / "review.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["review_id", "review_type", "subject_refs", "summary", "decision", "findings", "risks", "recommendations"],
                "properties": {
                    "review_id": {"type": "string"},
                    "review_type": {"type": "string"},
                    "subject_refs": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string"},
                    "decision": {"type": "string"},
                    "findings": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                },
            }
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="feat_review",
        agent_id="agent.product.feat_reviewer",
        executor_type="llm",
        config={"output_contract": str(schema_path), "strict_output_validation": True},
        input={},
        outputs=[],
    )
    llm_payload = {
        "status": "success",
        "provider": "test",
        "model": "test-model",
        "tokens_used": 1,
        "input_tokens": 1,
        "output_tokens": 1,
        "duration_seconds": 0.1,
        "stop_reason": "stop",
        "generated_text": json.dumps(
            {
                "review_id": "RVW-001",
                "review_type": "feat_review",
                "subject_refs": ["FEAT-001"],
                "summary": "ok",
                "findings": [],
                "risks": [],
                "recommendations": [],
            },
            ensure_ascii=False,
        ),
    }
    executor = MagicMock()
    executor.execute = AsyncMock(return_value=llm_payload)
    file_handler = MagicMock()
    file_handler.handle = AsyncMock(return_value=[])
    store = MagicMock()
    store.get_workflow = AsyncMock(
        return_value=SimpleNamespace(
            data={"run_id": "run-001"},
            level="task",
            template_id="template.product.epic_to_feat",
        )
    )
    store.create_task_execution = AsyncMock(return_value="exec-001")
    store.update_task_execution = AsyncMock()
    state_machine = MagicMock()
    state_machine.complete_step = AsyncMock(
        return_value=StepResult(
            status="completed",
            step_id=step.id,
            workflow_id="wf-001",
            message="ok",
        )
    )
    state_machine.fail_step = AsyncMock()
    event_log = MagicMock()
    event_log.emit = AsyncMock()
    evidence_collector = MagicMock()
    evidence_collector.collect_task_execution = AsyncMock()
    verifier_engine = MagicMock()
    agent_loader = MagicMock()
    agent_loader.load.return_value = None
    agent_context_builder = MagicMock()
    agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system",
            user_prompt="user",
            temperature=0.1,
            max_tokens=100,
        )
    )
    agent_context_builder.agent_loader = agent_loader
    token_manager = MagicMock()
    token_manager.issue_token = MagicMock(return_value=None)
    ctx = RunnerContext(
        store=store,
        state_machine=state_machine,
        event_log=event_log,
        evidence_collector=evidence_collector,
        verifier_engine=verifier_engine,
        executor_factory=MagicMock(create=MagicMock(return_value=executor)),
        agent_context_builder=agent_context_builder,
        contract_discovery=MagicMock(get_workflow_inputs=MagicMock(return_value={})),
        file_output_handler=file_handler,
        token_manager=token_manager,
        project_root=str(temp_project_root),
    )

    async def fake_attempt_schema_repair(**kwargs):
        return {
            "output": {"generated_text": json.dumps({"decision": "pass"}, ensure_ascii=False)},
            "business_output": {
                "review_id": "RVW-001",
                "review_type": "feat_review",
                "subject_refs": ["FEAT-001"],
                "summary": "ok",
                "decision": "pass",
                "findings": [],
                "risks": [],
                "recommendations": [],
            },
            "structured_payload": None,
        }

    runner._attempt_schema_repair = fake_attempt_schema_repair

    result = await runner.execute("wf-001", step, ctx)

    assert result.status == "completed"
    state_machine.fail_step.assert_not_called()
    state_machine.complete_step.assert_awaited_once()


@pytest.mark.asyncio
async def test_llm_runner_rejects_feat_bundle_semantic_drift_before_materialization(temp_project_root):
    runner = LLMRunner()
    epic_path = temp_project_root / "spec" / "requirements" / "epics" / "EPIC-001__workflow-first.md"
    epic_path.parent.mkdir(parents=True, exist_ok=True)
    epic_path.write_text(
        """---
id: EPIC-001
ssot_type: epic
title: LEE CLI Workflow-First 治理入口重构
status: draft
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

统一 CLI、workflow、SSOT 和 gate 的治理边界。
""",
        encoding="utf-8",
    )
    schema_path = temp_project_root / "feat-bundle.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["epic_ref", "feat_specs"],
                "properties": {
                    "epic_ref": {"type": "string"},
                    "feat_specs": {"type": "array"},
                },
            }
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        executor_type="llm",
        config={"output_contract": str(schema_path), "strict_output_validation": True},
        input={},
        outputs=[],
    )
    llm_payload = {
        "status": "success",
        "provider": "test",
        "model": "test-model",
        "tokens_used": 1,
        "input_tokens": 1,
        "output_tokens": 1,
        "duration_seconds": 0.1,
        "stop_reason": "stop",
        "generated_text": json.dumps(
            {
                "business_output": {
                    "epic_ref": "EPIC-001",
                    "feat_specs": [
                        {
                            "feat_id": "FEAT-001",
                            "title": "短信验证码发送服务",
                            "goal": "实现手机号登录验证码发送",
                            "user_value": "用户输入手机号即可收到短信验证码",
                            "inputs": ["手机号"],
                            "processing": ["发送短信"],
                            "outputs": ["验证码发送结果"],
                            "acceptance_criteria": ["支持短信验证码登录"],
                            "dependencies": [],
                            "non_goals": [],
                        }
                    ],
                }
            },
            ensure_ascii=False,
        ),
    }
    executor = MagicMock()
    executor.execute = AsyncMock(return_value=llm_payload)
    file_handler = MagicMock()
    file_handler.handle = AsyncMock(return_value=[])
    store = MagicMock()
    store.get_workflow = AsyncMock(
        return_value=SimpleNamespace(
            data={"run_id": "run-001"},
            level="task",
            template_id="template.product.epic_to_feat",
        )
    )
    store.create_task_execution = AsyncMock(return_value="exec-001")
    store.update_task_execution = AsyncMock()
    state_machine = MagicMock()
    state_machine.complete_step = AsyncMock()
    state_machine.fail_step = AsyncMock()
    event_log = MagicMock()
    event_log.emit = AsyncMock()
    evidence_collector = MagicMock()
    evidence_collector.collect_task_execution = AsyncMock()
    verifier_engine = MagicMock()
    agent_loader = MagicMock()
    agent_loader.load.return_value = None
    agent_context_builder = MagicMock()
    agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system",
            user_prompt="user",
            temperature=0.1,
            max_tokens=100,
        )
    )
    agent_context_builder.agent_loader = agent_loader
    token_manager = MagicMock()
    token_manager.issue_token = MagicMock(return_value=None)
    ctx = RunnerContext(
        store=store,
        state_machine=state_machine,
        event_log=event_log,
        evidence_collector=evidence_collector,
        verifier_engine=verifier_engine,
        executor_factory=MagicMock(create=MagicMock(return_value=executor)),
        agent_context_builder=agent_context_builder,
        contract_discovery=MagicMock(get_workflow_inputs=MagicMock(return_value={})),
        file_output_handler=file_handler,
        token_manager=token_manager,
        project_root=str(temp_project_root),
    )
    runner._materialize_ssot_outputs = AsyncMock(return_value=None)

    result = await runner.execute("wf-001", step, ctx)

    assert result.status == "failed"
    state_machine.fail_step.assert_awaited_once()
    runner._materialize_ssot_outputs.assert_not_awaited()


def test_extract_business_output_payload_uses_written_file_when_mixed_output(temp_project_root, runner):
    output_path = temp_project_root / "spec" / "qa" / "test-sets" / "ts-demo-module.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        """
test_set_id: TS-DEMO-MODULE
module: demo-module
strategy:
  focus:
    - happy path
test_focus:
  positive:
    - happy path
traceability:
  feature_ids:
    - FEAT-023
  acceptance_criteria_refs:
    - AC1
""".strip(),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(
                path="spec/qa/test-sets/ts-demo-module.yaml",
                type="file",
            )
        ]
    )

    payload = runner._extract_business_output_payload(
        structured_payload=None,
        fallback_text="## spec/qa/test-sets/ts-demo-module.yaml\n```yaml\nplaceholder: true\n```",
        step=step,
        written_files=[str(output_path)],
    )

    assert isinstance(payload, dict)
    assert payload["test_set_id"] == "TS-DEMO-MODULE"


def test_expected_feat_review_subject_refs_reads_generated_feat_id(runner):
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "generated_text": json.dumps(
                    {
                        "business_output": {
                            "feat_id": "FEAT-900",
                            "title": "训练计划智能调整",
                        }
                    },
                    ensure_ascii=False,
                )
            }
        }
    }

    refs = runner._expected_feat_review_subject_refs(instance_data)

    assert refs == ["FEAT-900"]


def test_expected_feat_review_subject_refs_prefers_materialized_feat_id(runner):
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "generated_text": json.dumps(
                    {
                        "business_output": {
                            "feat_id": "FEAT-1",
                            "title": "训练计划智能调整",
                        }
                    },
                    ensure_ascii=False,
                ),
                "ssot_materialized": {
                    "feat": {
                        "id": "FEAT-900",
                    }
                },
            }
        }
    }

    refs = runner._expected_feat_review_subject_refs(instance_data)

    assert refs == ["FEAT-900"]


def test_expected_feat_review_subject_refs_reads_bundle_feat_ids(runner):
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "generated_text": json.dumps(
                    {
                        "business_output": {
                            "epic_ref": "EPIC-001",
                            "feat_specs": [
                                {"feat_id": "FEAT-901", "title": "能力 A"},
                                {"feat_id": "FEAT-902", "title": "能力 B"},
                            ],
                        }
                    },
                    ensure_ascii=False,
                )
            }
        }
    }

    refs = runner._expected_feat_review_subject_refs(instance_data)

    assert refs == ["FEAT-901", "FEAT-902"]


def test_normalize_prd_writer_feat_payload_prefers_structured_bundle_when_business_output_is_malformed(runner):
    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        config={
            "output_contract": "departments/product/contracts/feat-bundle-contract/v1/schema.json",
        },
    )
    business_output = {
        "epic_ref": "EPIC-001",
        "feat_specs": [
            {
                "notes.business_output": {
                    "epic_ref": "EPIC-001",
                    "feat_specs": [
                        {"feat_id": "FEAT-001", "title": "能力 A"},
                        {"feat_id": "FEAT-002", "title": "能力 B"},
                    ],
                },
                "feat_id": "FEAT-AUTO",
                "title": "FEAT-AUTO",
            }
        ],
    }
    structured_payload = {
        "business_output": {
            "epic_ref": "EPIC-001",
            "feat_specs": [
                {
                    "feat_id": "FEAT-001",
                    "title": "能力 A",
                    "goal": "目标 A",
                    "user_value": "价值 A",
                    "inputs": ["输入 A"],
                    "processing": ["处理 A"],
                    "outputs": ["输出 A"],
                    "acceptance_criteria": ["验收 A"],
                    "dependencies": [],
                    "non_goals": [],
                },
                {
                    "feat_id": "FEAT-002",
                    "title": "能力 B",
                    "goal": "目标 B",
                    "user_value": "价值 B",
                    "inputs": ["输入 B"],
                    "processing": ["处理 B"],
                    "outputs": ["输出 B"],
                    "acceptance_criteria": ["验收 B"],
                    "dependencies": [],
                    "non_goals": [],
                },
            ],
        }
    }

    normalized_business, normalized_structured = runner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-001",
        business_output=business_output,
        structured_payload=structured_payload,
        instance_data={"params": {"epic_freeze_ref": {"artifact_id": "EPIC-001"}}},
    )

    assert [item["feat_id"] for item in normalized_business["feat_specs"]] == ["FEAT-001", "FEAT-002"]
    assert [item["feat_id"] for item in normalized_structured["business_output"]["feat_specs"]] == [
        "FEAT-001",
        "FEAT-002",
    ]


def test_normalize_business_payload_backfills_feat_identity_prepare_from_feat_spec_generation(runner):
    step = SimpleNamespace(
        id="feat_identity_prepare",
        agent_id="agent.governance.approval_reviewer",
        config={},
    )
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "business_output": {
                    "epic_ref": "EPIC-001",
                    "feat_specs": [
                        {
                            "feat_id": "FEAT-001",
                            "title": "能力 A",
                            "goal": "目标 A",
                            "user_value": "价值 A",
                            "inputs": ["输入 A"],
                            "processing": ["处理 A"],
                            "outputs": ["输出 A"],
                            "acceptance_criteria": ["验收 A"],
                            "dependencies": [],
                            "non_goals": [],
                        }
                    ],
                }
            }
        }
    }

    normalized_business, normalized_structured = runner._normalize_business_payload(
        step=step,
        workflow_id="wf-identity-001",
        business_output=None,
        structured_payload={"status": "success"},
        instance_data=instance_data,
    )

    assert normalized_business["epic_ref"] == "EPIC-001"
    assert [item["feat_id"] for item in normalized_business["feat_specs"]] == ["FEAT-001"]
    assert [item["feat_id"] for item in normalized_structured["business_output"]["feat_specs"]] == ["FEAT-001"]


def test_validate_feat_review_semantics_requires_exact_subject_refs(runner):
    payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-123"],
        "summary": "review summary",
        "findings": [],
        "decision": "pass",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_feat_review_semantics(payload, ["FEAT-900"])

    assert error == "FEAT review subject_refs must exactly match the reviewed FEAT ID(s): FEAT-900"


def test_validate_feat_review_semantics_rejects_pass_with_findings(runner):
    payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-900"],
        "summary": "review summary",
        "findings": ["acceptance checks are incomplete"],
        "decision": "pass",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_feat_review_semantics(payload, ["FEAT-900"])

    assert error == "FEAT review output with decision=pass must not include findings"


def test_validate_feat_review_semantics_rejects_pass_with_negative_summary(runner):
    payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-900"],
        "summary": "存在阻塞问题，需修订后才能通过",
        "findings": [],
        "decision": "pass",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_feat_review_semantics(payload, ["FEAT-900"])

    assert error == "FEAT review summary conflicts with decision=pass"


def test_validate_feat_review_semantics_requires_findings_for_revise(runner):
    payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-900"],
        "summary": "需要修订",
        "findings": [],
        "decision": "revise",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_feat_review_semantics(payload, ["FEAT-900"])

    assert error == "FEAT review output with decision=revise must include at least one finding"


def test_validate_feat_review_semantics_blocks_revise_decision(runner):
    payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-900"],
        "summary": "需要修订后才能进入冻结",
        "findings": ["goal 字段仍是占位文本"],
        "decision": "revise",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_feat_review_semantics(payload, ["FEAT-900"])

    assert error == "FEAT review requires revision before freeze"


def test_validate_feat_review_semantics_blocks_reject_decision(runner):
    payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-900"],
        "summary": "当前 FEAT 不可接受",
        "findings": ["关键字段缺失"],
        "decision": "reject",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_feat_review_semantics(payload, ["FEAT-900"])

    assert error == "FEAT review rejected the generated FEAT bundle"


def test_normalize_delivery_plan_review_fills_subject_refs_from_task_plan(runner):
    step = SimpleNamespace(agent_id="agent.product.delivery_plan_reviewer")
    business_output = {
        "review_id": "RVW-DELIVERY-001",
        "review_type": "delivery_plan_review",
        "subject_refs": [],
        "summary": "plan ready",
        "findings": [],
        "decision": "pass",
        "risks": [],
        "recommendations": [],
    }
    structured_payload = {"business_output": dict(business_output)}
    instance_data = {
        "step_outputs": {
            "task_planning": {
                "business_output": {
                    "source_feats": ["FEAT-SRC-009-001"],
                }
            }
        }
    }

    normalized_business, normalized_structured = runner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload=structured_payload,
        instance_data=instance_data,
    )

    assert normalized_business["subject_refs"] == ["FEAT-SRC-009-001"]
    assert normalized_structured["business_output"]["subject_refs"] == ["FEAT-SRC-009-001"]


def test_normalize_delivery_plan_review_reads_subject_refs_from_task_plan_alias(runner):
    step = SimpleNamespace(agent_id="agent.product.delivery_plan_reviewer")
    business_output = {
        "review_id": "RVW-DELIVERY-002",
        "review_type": "delivery_plan_review",
        "subject_refs": [],
        "summary": "plan ready",
        "findings": [],
        "decision": "pass",
        "risks": [],
        "recommendations": [],
    }

    normalized_business, normalized_structured = runner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "step_outputs": {
                "task_plan": {
                    "business_output": {
                        "source_feats": ["FEAT-SRC-009-002"],
                    }
                }
            }
        },
    )

    assert normalized_business["subject_refs"] == ["FEAT-SRC-009-002"]
    assert normalized_structured["business_output"]["subject_refs"] == ["FEAT-SRC-009-002"]


def test_load_task_plan_business_output_reads_generated_text_payload(runner):
    instance_data = {
        "step_outputs": {
            "task_plan": {
                "generated_text": (
                    '任务已经写入 canonical 目录。'
                    '{"business_output":{"source_feats":["FEAT-SRC-009-003"],'
                    '"task_specs":[{"task_id":"TASK-FEAT-SRC-009-003","source_feat":"FEAT-SRC-009-003"}],'
                    '"milestones":[{"id":"M1","task_ids":["TASK-FEAT-SRC-009-003"]}],'
                    '"dependency_graph":{"critical_path":["TASK-FEAT-SRC-009-003"]},'
                    '"resource_allocation":{"owner":{"tasks":["TASK-FEAT-SRC-009-003"]}}}}'
                )
            }
        }
    }

    task_plan = runner._load_task_plan_business_output(instance_data)

    assert isinstance(task_plan, dict)
    assert task_plan["source_feats"] == ["FEAT-SRC-009-003"]
    assert runner._delivery_plan_has_authoritative_plan_shape(task_plan) is True


def test_validate_delivery_plan_review_subject_refs_requires_exact_match(runner):
    payload = {
        "review_id": "RVW-DELIVERY-001",
        "review_type": "delivery_plan_review",
        "subject_refs": [],
        "summary": "plan ready",
        "findings": [],
        "decision": "pass",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_delivery_plan_review_subject_refs(
        payload,
        ["FEAT-SRC-009-001"],
    )

    assert error == (
        "Delivery plan review subject_refs must exactly match the planned FEAT ID(s): "
        "FEAT-SRC-009-001"
    )


def test_validate_delivery_plan_review_semantics_rejects_false_positive_revise_findings(
    temp_project_root, runner
):
    task_dir = temp_project_root / "spec" / "tasks" / "FEAT-143"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "TASK-FEAT-143-001__entry-spec.md").write_text("# task", encoding="utf-8")

    payload = {
        "review_type": "delivery_plan_review",
        "subject_refs": ["FEAT-143"],
        "summary": "delivery review completed",
        "decision": "revise",
        "findings": [
            "TASK-FEAT-143-001 objective exists",
            "task_directory is spec/tasks/FEAT-143 consistent with FEAT-ID",
        ],
        "risks": [],
        "recommendations": [],
    }
    instance_data = {
        "step_outputs": {
            "task_planning": {
                "business_output": {
                    "source_feats": ["FEAT-143"],
                    "planning_metadata": {"task_directory": "spec/tasks/FEAT-143"},
                    "task_specs": [{"task_id": "TASK-FEAT-143-001", "source_feat": "FEAT-143"}],
                }
            }
        }
    }

    error = runner._validate_delivery_plan_review_semantics(
        project_root=str(temp_project_root),
        review_payload=payload,
        instance_data=instance_data,
    )

    assert error == "Delivery plan review findings contain no blocking issues"


def test_validate_delivery_plan_review_semantics_rejects_false_unverified_persistence_and_spec_gap(
    temp_project_root, runner
):
    features_dir = temp_project_root / "spec" / "requirements" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / "FEAT-143__qa-entry.md").write_text(
        "\n".join(
            [
                "---",
                "id: FEAT-143",
                "title: QA 执行入口规范化",
                "parent_id: EPIC-QA-SSOT-UPGRADE",
                "---",
                "",
                "## AC-003-001",
                "- Scenario: 执行入口唯一性验证",
                "- Then: 仅允许通过 TASK 触发执行",
                "",
                "## AC-003-002",
                "- Scenario: 执行路径完整性校验",
                "- Then: 系统验证 RELEASE->PLAN->TASK 链路完整且有效",
                "",
                "## AC-003-003",
                "- Scenario: 旁路执行入口阻断验证",
                "- Then: 系统拒绝旁路请求并返回入口规范错误",
                "",
                "## AC-003-004",
                "- Scenario: 执行入口审计验证",
                "- Then: 日志中包含每次执行的入口来源、路径链、时间戳、操作用户",
            ]
        ),
        encoding="utf-8",
    )
    task_dir = temp_project_root / "spec" / "tasks" / "FEAT-143"
    task_dir.mkdir(parents=True, exist_ok=True)
    for task_id in ("TASK-FEAT-143-001", "TASK-FEAT-143-002"):
        (task_dir / f"{task_id}__demo.md").write_text("# task", encoding="utf-8")

    payload = {
        "review_type": "delivery_plan_review",
        "subject_refs": ["FEAT-143"],
        "summary": "needs revise",
        "decision": "revise",
        "findings": [
            "FEAT-143 structural AC only map to implementation tasks without explicit spec/template coverage",
            "task_plan.ssot_output_contract.outputs indicate task content generation but actual file persistence status unverified",
        ],
        "risks": [],
        "recommendations": [],
    }
    instance_data = {
        "step_outputs": {
            "task_planning": {
                "business_output": {
                    "source_feats": ["FEAT-143"],
                    "planning_metadata": {"task_directory": "spec/tasks/FEAT-143"},
                    "task_specs": [
                        {
                            "task_id": "TASK-FEAT-143-001",
                            "source_feat": "FEAT-143",
                            "task_kind": "specification",
                            "acceptance_criteria_mapping": [
                                {"feat": "FEAT-143", "ac": "AC-003-001"},
                                {"feat": "FEAT-143", "ac": "AC-003-002"},
                                {"feat": "FEAT-143", "ac": "AC-003-003"},
                                {"feat": "FEAT-143", "ac": "AC-003-004"},
                            ],
                        },
                        {
                            "task_id": "TASK-FEAT-143-002",
                            "source_feat": "FEAT-143",
                            "task_kind": "implementation",
                        },
                    ],
                }
            }
        }
    }

    error = runner._validate_delivery_plan_review_semantics(
        project_root=str(temp_project_root),
        review_payload=payload,
        instance_data=instance_data,
    )

    assert error in {
        "Delivery plan review incorrectly reports TASK persistence as unverified",
        "Delivery plan review incorrectly reports missing structural specification coverage",
    }


def test_normalize_delivery_plan_review_sanitizes_false_positive_findings_to_pass(
    temp_project_root, runner
):
    features_dir = temp_project_root / "spec" / "requirements" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / "FEAT-143__qa-entry.md").write_text(
        "\n".join(
            [
                "---",
                "id: FEAT-143",
                "title: QA 执行入口规范化",
                "parent_id: EPIC-QA-SSOT-UPGRADE",
                "---",
                "",
                "## AC-003-001",
                "- Scenario: 执行入口唯一性验证",
                "- Then: 仅允许通过 TASK 触发执行",
                "",
                "## AC-003-002",
                "- Scenario: 执行路径完整性校验",
                "- Then: 系统验证 RELEASE->PLAN->TASK 链路完整且有效",
                "",
                "## AC-003-003",
                "- Scenario: 旁路执行入口阻断验证",
                "- Then: 系统拒绝旁路请求并返回入口规范错误",
                "",
                "## AC-003-004",
                "- Scenario: 执行入口审计验证",
                "- Then: 日志中包含每次执行的入口来源、路径链、时间戳、操作用户",
            ]
        ),
        encoding="utf-8",
    )
    task_dir = temp_project_root / "spec" / "tasks" / "FEAT-143"
    task_dir.mkdir(parents=True, exist_ok=True)
    for task_id in ("TASK-FEAT-143-001", "TASK-FEAT-143-002"):
        (task_dir / f"{task_id}__demo.md").write_text("# task", encoding="utf-8")

    step = SimpleNamespace(agent_id="agent.product.delivery_plan_reviewer")
    business_output = {
        "review_type": "delivery_plan_review",
        "subject_refs": ["FEAT-143"],
        "summary": "delivery review completed",
        "decision": "revise",
        "findings": [
            "TASK-FEAT-143-001 至 TASK-FEAT-143-005 均具备 objective、description、acceptance_criteria_mapping、definition_of_done、observability、evidence_requirements、rollback_strategy 字段",
            "所有 TASK 均挂在 FEAT-143 下，task_directory 与落盘路径 spec/tasks/FEAT-143/ 一致",
            "FEAT-143 的结构性 AC（阶段顺序、状态机、契约边界）主要映射到实现任务，缺乏独立的规范或模板任务来固化契约边界",
            "task_plan.ssot_output_contract.outputs indicate task content generation but actual file persistence status unverified",
        ],
        "risks": [],
        "recommendations": [],
    }
    structured_payload = {"business_output": dict(business_output)}
    instance_data = {
        "project_root": str(temp_project_root),
        "step_outputs": {
            "task_planning": {
                "business_output": {
                    "source_feats": ["FEAT-143"],
                    "planning_metadata": {"task_directory": "spec/tasks/FEAT-143"},
                    "task_specs": [
                        {
                            "task_id": "TASK-FEAT-143-001",
                            "source_feat": "FEAT-143",
                            "task_kind": "specification",
                            "acceptance_criteria_mapping": [
                                {"feat": "FEAT-143", "ac": "AC-003-001"},
                                {"feat": "FEAT-143", "ac": "AC-003-002"},
                                {"feat": "FEAT-143", "ac": "AC-003-003"},
                                {"feat": "FEAT-143", "ac": "AC-003-004"},
                            ],
                        },
                        {
                            "task_id": "TASK-FEAT-143-002",
                            "source_feat": "FEAT-143",
                            "task_kind": "implementation",
                        },
                    ],
                }
            }
        },
    }

    normalized_business, _ = runner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload=structured_payload,
        instance_data=instance_data,
    )

    assert normalized_business["findings"] == []
    assert normalized_business["decision"] == "pass"
    assert normalized_business["summary"] == "delivery review completed"


def test_normalize_delivery_plan_review_backfills_summary_when_empty(temp_project_root, runner):
    step = SimpleNamespace(agent_id="agent.product.delivery_plan_reviewer")
    business_output = {
        "review_type": "delivery_plan_review",
        "subject_refs": ["FEAT-143"],
        "summary": "",
        "decision": "pass",
        "findings": ["FEAT-143 的结构性 AC 已映射到规范定义任务 TASK-001"],
        "risks": [],
        "recommendations": [],
    }
    structured_payload = {"business_output": dict(business_output)}
    instance_data = {
        "project_root": str(temp_project_root),
        "step_outputs": {
            "task_planning": {
                "business_output": {
                    "source_feats": ["FEAT-143"],
                    "planning_metadata": {"task_directory": "spec/tasks/FEAT-143"},
                    "task_specs": [
                        {
                            "task_id": "TASK-FEAT-143-001",
                            "source_feat": "FEAT-143",
                            "task_kind": "specification",
                            "acceptance_criteria_mapping": [
                                {"feat": "FEAT-143", "ac": "AC-003-001"},
                            ],
                        }
                    ],
                }
            }
        },
    }

    normalized_business, _ = runner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload=structured_payload,
        instance_data=instance_data,
    )

    assert normalized_business["findings"] == []
    assert normalized_business["summary"] == "Delivery plan review pass for FEAT-143"


def test_normalize_delivery_plan_review_drops_false_persistence_risks_and_recommendations(
    temp_project_root, runner
):
    task_dir = temp_project_root / "spec" / "tasks" / "FEAT-143"
    task_dir.mkdir(parents=True, exist_ok=True)
    for task_id in ("TASK-FEAT-143-001", "TASK-FEAT-143-002"):
        (task_dir / f"{task_id}__demo.md").write_text("# task", encoding="utf-8")

    step = SimpleNamespace(agent_id="agent.product.delivery_plan_reviewer")
    business_output = {
        "review_type": "delivery_plan_review",
        "subject_refs": ["FEAT-143"],
        "summary": "",
        "decision": "revise",
        "findings": [],
        "risks": [
            "TASK 文件未落盘可能导致交付追踪断裂",
            "critical_path 未完整反映 TASK-005 对 TASK-003/004 的依赖关系",
        ],
        "recommendations": [
            "立即将 2 个 TASK 文件冻结并写入 spec/requirements/tasks/FEAT-143/ 目录",
            "在 dependency_graph 中补充说明 TASK-003/004 对 critical_path 的间接影响",
        ],
    }
    structured_payload = {"business_output": dict(business_output)}
    instance_data = {
        "project_root": str(temp_project_root),
        "step_outputs": {
            "task_planning": {
                "business_output": {
                    "source_feats": ["FEAT-143"],
                    "planning_metadata": {"task_directory": "spec/tasks/FEAT-143"},
                    "task_specs": [
                        {"task_id": "TASK-FEAT-143-001", "source_feat": "FEAT-143", "task_kind": "specification"},
                        {"task_id": "TASK-FEAT-143-002", "source_feat": "FEAT-143", "task_kind": "implementation"},
                    ],
                }
            }
        },
    }

    normalized_business, _ = runner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload=structured_payload,
        instance_data=instance_data,
    )

    assert normalized_business["risks"] == [
        "critical_path 未完整反映 TASK-005 对 TASK-003/004 的依赖关系"
    ]
    assert normalized_business["recommendations"] == [
        "在 dependency_graph 中补充说明 TASK-003/004 对 critical_path 的间接影响"
    ]


def test_normalize_delivery_plan_review_drops_false_path_and_dual_coverage_findings(
    temp_project_root, runner
):
    task_dir = temp_project_root / "spec" / "tasks" / "FEAT-143"
    task_dir.mkdir(parents=True, exist_ok=True)
    for task_id in ("TASK-FEAT-143-001", "TASK-FEAT-143-002"):
        (task_dir / f"{task_id}__demo.md").write_text("# task", encoding="utf-8")

    step = SimpleNamespace(agent_id="agent.product.delivery_plan_reviewer")
    business_output = {
        "review_type": "delivery_plan_review",
        "subject_refs": ["FEAT-143"],
        "summary": "",
        "decision": "revise",
        "findings": [
            "FEAT-143 的结构性 AC 同时映射到 specification 任务和 implementation 任务，存在规范与实现双重覆盖",
            "TASK-FEAT-143-001 的 definition_of_done 未声明具体的落盘文件路径",
        ],
        "risks": [
            "TASK-FEAT-143-001 的 definition_of_done 未声明具体的落盘文件路径",
        ],
        "recommendations": [
            "为每个 TASK 的 definition_of_done 添加具体的落盘文件路径声明",
        ],
    }
    structured_payload = {"business_output": dict(business_output)}
    instance_data = {
        "project_root": str(temp_project_root),
        "step_outputs": {
            "task_planning": {
                "business_output": {
                    "source_feats": ["FEAT-143"],
                    "planning_metadata": {"task_directory": "spec/tasks/FEAT-143"},
                    "task_specs": [
                        {
                            "task_id": "TASK-FEAT-143-001",
                            "source_feat": "FEAT-143",
                            "task_kind": "specification",
                            "acceptance_criteria_mapping": [{"feat": "FEAT-143", "ac": "AC-003-001"}],
                        },
                        {
                            "task_id": "TASK-FEAT-143-002",
                            "source_feat": "FEAT-143",
                            "task_kind": "implementation",
                            "acceptance_criteria_mapping": [{"feat": "FEAT-143", "ac": "AC-003-001"}],
                        },
                    ],
                }
            }
        },
    }

    normalized_business, _ = runner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload=structured_payload,
        instance_data=instance_data,
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_business["findings"] == []
    assert normalized_business["risks"] == []
    assert normalized_business["recommendations"] == []


def test_normalize_delivery_plan_review_drops_stale_feat_review_and_plan_shape_false_positives(
    temp_project_root, runner
):
    for feat_id, task_id in (
        ("FEAT-SRC-041-016-001", "TASK-FEAT-SRC-041-016-001"),
        ("FEAT-SRC-041-016-002", "TASK-FEAT-SRC-041-016-002"),
    ):
        task_dir = temp_project_root / "spec" / "tasks" / feat_id
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / f"{task_id}__demo.md").write_text("# task", encoding="utf-8")

    step = SimpleNamespace(agent_id="agent.product.delivery_plan_reviewer")
    business_output = {
        "review_type": "delivery_plan_review",
        "subject_refs": ["FEAT-SRC-041-016-001", "FEAT-SRC-041-016-002"],
        "summary": "plan is blocked",
        "decision": "revise",
        "findings": [
            "feat_review_report.business_output 给出 decision=pass 且 findings=[]，但 feat_review_report.structured_payload 给出 decision=revise 且列出阻断性 findings，导致 delivery prep 的上游基线不具备单一、可审计的评审结论。",
            "由于计划级 dependency_graph 未作为权威对象落盘，本轮只能从各 TASK 文档中的 Dependencies 章节零散看到串联关系，不能替代实施计划所需的统一关键路径、并行分支和里程碑退出条件。",
            "EPIC-SRC-041-016 的 delivery prep 目前只有按 FEAT 拆分的 TASK SSOT 文件，未提供一个可独立审计的结构化 task plan 产物来统一承载 task_specs、milestones、dependency_graph、resource_allocation。",
        ],
        "risks": [
            "缺少显式 resource_allocation 会使规范、运行时、CLI、审计和验证责任边界继续依赖口头约定，降低执行可追责性。"
        ],
        "recommendations": [
            "补充并落盘一个面向 EPIC-SRC-041-016 的结构化 delivery-prep plan artifact，明确包含 parent_epic、source_feats、完整 task_specs、milestones、dependency_graph、resource_allocation。"
        ],
    }

    normalized_business, _ = runner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "project_root": str(temp_project_root),
            "params": {
                "feat_freeze": {
                    "frozen_inputs": {
                        "feat_review_report": {
                            "business_output": {"decision": "pass", "findings": []},
                            "structured_payload": {"decision": "revise", "findings": ["stale finding"]},
                        }
                    }
                }
            },
            "step_outputs": {
                "task_plan": {
                    "business_output": {
                        "source_feats": ["FEAT-SRC-041-016-001", "FEAT-SRC-041-016-002"],
                        "planning_metadata": {
                            "task_directories": [
                                "spec/tasks/FEAT-SRC-041-016-001",
                                "spec/tasks/FEAT-SRC-041-016-002",
                            ]
                        },
                        "task_specs": [
                            {"task_id": "TASK-FEAT-SRC-041-016-001", "source_feat": "FEAT-SRC-041-016-001"},
                            {"task_id": "TASK-FEAT-SRC-041-016-002", "source_feat": "FEAT-SRC-041-016-002"},
                        ],
                        "milestones": [{"id": "M1", "task_ids": ["TASK-FEAT-SRC-041-016-001"]}],
                        "dependency_graph": {"critical_path": ["TASK-FEAT-SRC-041-016-001"]},
                        "resource_allocation": {"owner": {"tasks": ["TASK-FEAT-SRC-041-016-001"]}},
                    }
                }
            },
        },
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_business["findings"] == []
    assert normalized_business["risks"] == []
    assert normalized_business["recommendations"] == []


def test_validate_feat_bundle_epic_semantics_accepts_governance_bundle(temp_project_root, runner):
    epic_path = temp_project_root / "spec" / "requirements" / "epics" / "EPIC-001__workflow-first.md"
    epic_path.parent.mkdir(parents=True, exist_ok=True)
    epic_path.write_text(
        """---
id: EPIC-001
ssot_type: epic
title: LEE CLI Workflow-First 治理入口重构
status: draft
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

统一 CLI、workflow、SSOT 和 gate 的治理边界。
""",
        encoding="utf-8",
    )

    error = runner._validate_feat_bundle_epic_semantics(
        project_root=str(temp_project_root),
        business_output={
            "epic_ref": "EPIC-001",
            "feat_specs": [
                    {
                        "title": "Gate 三类治理模型定义",
                        "goal": "统一 gate / review / approval / freeze 语义",
                        "user_value": "让 workflow 与 ssot 治理边界清晰",
                        "inputs": ["workflow config"],
                        "input_contract": {
                            "required_artifacts": ["EPIC-001#scope"],
                            "required_fields": ["workflow_key", "gate_rules"],
                            "consumption_rules": ["Gate review must consume the declared workflow fields directly."],
                        },
                        "processing": ["治理规则校验"],
                        "outputs": ["gate result"],
                        "acceptance_criteria": ["CLI 与 workflow 入口语义一致"],
                        "dependencies": [],
                        "non_goals": [],
                }
            ],
        },
    )

    assert error is None


def test_validate_feat_bundle_epic_semantics_rejects_auth_bundle_for_governance_epic(temp_project_root, runner):
    epic_path = temp_project_root / "spec" / "requirements" / "epics" / "EPIC-001__workflow-first.md"
    epic_path.parent.mkdir(parents=True, exist_ok=True)
    epic_path.write_text(
        """---
id: EPIC-001
ssot_type: epic
title: LEE CLI Workflow-First 治理入口重构
status: draft
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

统一 CLI、workflow、SSOT 和 gate 的治理边界。
""",
        encoding="utf-8",
    )

    error = runner._validate_feat_bundle_epic_semantics(
        project_root=str(temp_project_root),
        business_output={
            "epic_ref": "EPIC-001",
            "feat_specs": [
                {
                    "title": "短信验证码发送服务",
                    "goal": "实现手机号登录验证码发送",
                    "user_value": "用户输入手机号即可收到短信验证码",
                    "inputs": ["手机号"],
                    "input_contract": {
                        "required_artifacts": ["EPIC-001#scope"],
                        "required_fields": ["phone_number"],
                        "consumption_rules": ["The auth service must receive phone_number before issuing an SMS code."],
                    },
                    "processing": ["发送短信", "校验验证码"],
                    "outputs": ["验证码发送结果"],
                    "acceptance_criteria": ["支持短信验证码登录"],
                    "dependencies": [],
                    "non_goals": [],
                }
            ],
        },
    )

    assert error == (
        "FEAT bundle semantics drift from EPIC-001: "
        "epic topic families=['governance'], feat topic families=['auth_sms']"
    )


def test_validate_feat_bundle_epic_semantics_rejects_placeholder_inputs(temp_project_root, runner):
    epic_path = temp_project_root / "spec" / "requirements" / "epics" / "EPIC-001__workflow-first.md"
    epic_path.parent.mkdir(parents=True, exist_ok=True)
    epic_path.write_text(
        """---
id: EPIC-001
ssot_type: epic
title: LEE CLI Workflow-First 治理入口重构
status: draft
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

统一 CLI、workflow、SSOT 和 gate 的治理边界。
""",
        encoding="utf-8",
    )

    error = runner._validate_feat_bundle_epic_semantics(
        project_root=str(temp_project_root),
        business_output={
            "epic_ref": "EPIC-001",
            "feat_specs": [
                {
                    "feat_id": "FEAT-001",
                    "title": "Gate 三类治理模型定义",
                    "goal": "统一 gate / review / approval / freeze 语义",
                    "user_value": "让 workflow 与 ssot 治理边界清晰",
                    "inputs": ["Inputs defined by EPIC scope"],
                    "input_contract": {
                        "required_artifacts": ["EPIC-001#scope"],
                        "required_fields": ["formal_ssot_id"],
                        "consumption_rules": ["Downstream workflow must receive formal_ssot_id before execution."],
                    },
                    "processing": ["治理规则校验"],
                    "outputs": ["gate result"],
                    "acceptance_criteria": ["CLI 与 workflow 入口语义一致"],
                    "dependencies": [],
                    "non_goals": [],
                }
            ],
        },
    )

    assert error == "FEAT FEAT-001 uses placeholder inputs and cannot drive downstream design"


def test_validate_pm_planner_task_semantics_accepts_repo_scoped_governance_tasks(temp_project_root, runner):
    features_dir = temp_project_root / "spec" / "requirements" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / "FEAT-002__raw-to-src.md").write_text(
        """---
id: FEAT-002
ssot_type: feat
title: raw_to_src workflow 定义
status: draft
version: v1
parent_id: EPIC-001
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

新增 workflow 模板并补齐 src freeze 边界。
""",
        encoding="utf-8",
    )
    (features_dir / "FEAT-003__docs.md").write_text(
        """---
id: FEAT-003
ssot_type: feat
title: 调用文档迁移
status: draft
version: v1
parent_id: EPIC-001
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

更新 registry、run spec 和调用文档。
""",
        encoding="utf-8",
    )

    error = runner._validate_pm_planner_task_semantics(
        project_root=str(temp_project_root),
        business_output={
            "parent_epic": "EPIC-001",
            "source_feats": ["FEAT-002", "FEAT-003"],
            "task_specs": [
                {
                    "task_id": "TASK-FEAT-002-001",
                    "title": "新增 raw_to_src workflow 模板",
                    "objective": "在 spec-global 中新增 raw_to_src 模板并接入 registry",
                    "description": "修改 workflow 模板和 registry。",
                    "source_feat": "FEAT-002",
                    "workstream": "governance-spec",
                    "responsible_role": "workflow-spec-owner",
                    "acceptance_criteria_mapping": [{"feat": "FEAT-002", "ac": "AC-001", "description": "模板定义完成"}],
                    "definition_of_done": ["workflow 模板写入 spec-global", "相关测试更新"],
                    "rollback_strategy": {"mode": "revert", "restore_targets": ["spec-global/departments/product/workflows"]},
                },
                {
                    "task_id": "TASK-FEAT-003-001",
                    "title": "更新 run spec 与调用文档",
                    "objective": "补齐 run spec 和调用文档迁移说明",
                    "description": "修改 docs 和 spec 文档。",
                    "source_feat": "FEAT-003",
                    "workstream": "governance-docs",
                    "responsible_role": "technical-writer",
                    "acceptance_criteria_mapping": [{"feat": "FEAT-003", "ac": "AC-001", "description": "文档更新完成"}],
                    "definition_of_done": ["docs 更新完成"],
                    "rollback_strategy": {"mode": "revert", "restore_targets": ["docs", "spec"]},
                },
            ],
        },
    )

    assert error is None


def test_validate_pm_planner_task_semantics_rejects_infra_drift_for_governance_feats(temp_project_root, runner):
    features_dir = temp_project_root / "spec" / "requirements" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / "FEAT-002__pipeline.md").write_text(
        """---
id: FEAT-002
ssot_type: feat
title: product-main-pipeline 四段重构
status: draft
version: v1
parent_id: EPIC-001
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

调整 workflow pipeline、freeze gate 和 registry。
""",
        encoding="utf-8",
    )

    error = runner._validate_pm_planner_task_semantics(
        project_root=str(temp_project_root),
        business_output={
            "parent_epic": "EPIC-001",
            "source_feats": ["FEAT-002"],
            "task_specs": [
                {
                    "task_id": "TASK-FEAT-002-001",
                    "title": "实现 PostgreSQL 数据模型",
                    "objective": "为 pipeline 增加 PostgreSQL 数据表",
                    "description": "新增数据库 schema migration。",
                    "source_feat": "FEAT-002",
                },
                {
                    "task_id": "TASK-FEAT-002-002",
                    "title": "实现 API Gateway",
                    "objective": "新增 gateway 鉴权和 JWT 令牌",
                    "description": "接入 rate limiting 和 access token。",
                    "source_feat": "FEAT-002",
                },
            ],
        },
    )

    assert error is not None
    assert error.startswith("TASK bundle semantics drift from source FEAT scope:")
    assert "api gateway" in error
    assert "jwt" in error
    assert "postgresql" in error
    assert "schema migration" in error
    assert "source_feats=['FEAT-002']" in error


def test_validate_pm_planner_task_semantics_rejects_overscoped_governance_bundle(temp_project_root, runner):
    features_dir = temp_project_root / "spec" / "requirements" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    for feat_id in ("FEAT-002", "FEAT-003", "FEAT-004"):
        (features_dir / f"{feat_id}__workflow.md").write_text(
            f"""---
id: {feat_id}
ssot_type: feat
title: workflow 治理改造
status: draft
version: v1
parent_id: EPIC-001
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {{}}
---

# Goal

调整 workflow、gate 和文档。
""",
            encoding="utf-8",
        )

    error = runner._validate_pm_planner_task_semantics(
        project_root=str(temp_project_root),
        business_output={
            "parent_epic": "EPIC-001",
            "source_feats": ["FEAT-002", "FEAT-003", "FEAT-004"],
            "task_specs": [
                {"task_id": f"TASK-{index:03d}", "title": f"workflow task {index}", "source_feat": "FEAT-002"}
                for index in range(1, 10)
            ],
        },
    )

    assert error == (
        "TASK bundle overscoped for workflow/governance FEATs: "
        "task_count=9, max_expected=8, source_feats=['FEAT-002', 'FEAT-003', 'FEAT-004']"
    )


def test_validate_pm_planner_task_semantics_rejects_ui_drift_for_non_ui_feats(temp_project_root, runner):
    features_dir = temp_project_root / "spec" / "requirements" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / "FEAT-002__workflow.md").write_text(
        """---
id: FEAT-002
ssot_type: feat
title: raw_to_src workflow 定义
status: draft
version: v1
parent_id: EPIC-001
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

拆分 raw_to_src workflow 与 SRC freeze gate。
""",
        encoding="utf-8",
    )

    error = runner._validate_pm_planner_task_semantics(
        project_root=str(temp_project_root),
        business_output={
            "parent_epic": "EPIC-001",
            "source_feats": ["FEAT-002"],
            "task_specs": [
                {
                    "task_id": "TASK-FEAT-002-001",
                    "title": "实现 SRC 管理界面",
                    "objective": "为 workflow 拆分新增管理 UI 和操作页面",
                    "description": "补齐页面、组件和交互流程。",
                    "source_feat": "FEAT-002",
                },
            ],
        },
    )

    assert error is not None
    assert error.startswith("TASK bundle semantics drift from source FEAT scope:")
    assert "ui" in error.lower()
    assert "管理界面" in error


def test_validate_pm_planner_task_semantics_allows_ui_family_when_feat_trace_mentions_ui(temp_project_root, runner):
    features_dir = temp_project_root / "spec" / "requirements" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / "FEAT-143__qa-entry.md").write_text(
        """---
id: FEAT-143
ssot_type: feat
title: QA 执行入口规范化
status: draft
version: v1
parent_id: EPIC-001
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

收敛 QA 测试执行入口到 TESTPLAN 下的 TASK。

# Acceptance Checks

## AC-003-001

- Trace Hints: TECH, TASK, UI
""",
        encoding="utf-8",
    )

    error = runner._validate_pm_planner_task_semantics(
        project_root=str(temp_project_root),
        business_output={
            "parent_epic": "EPIC-001",
            "source_feats": ["FEAT-143"],
            "task_specs": [
                {
                    "task_id": "TASK-FEAT-143-003",
                    "title": "QA 执行入口 UI 组件与页面实现",
                    "objective": "实现路径链展示组件和页面状态",
                    "description": "补齐页面、界面和交互流程，实现入口审计展示。",
                    "source_feat": "FEAT-143",
                },
            ],
        },
    )

    assert error is None


def test_validate_pm_planner_task_semantics_allows_infra_storage_when_feat_trace_mentions_tech(
    temp_project_root, runner
):
    features_dir = temp_project_root / "spec" / "requirements" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / "FEAT-143__qa-entry.md").write_text(
        """---
id: FEAT-143
ssot_type: feat
title: QA 执行入口规范化
status: draft
version: v1
parent_id: EPIC-001
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

收敛 QA 测试执行入口到 TESTPLAN 下的 TASK。

# Acceptance Checks

## AC-003-001

- Trace Hints: TECH, TASK
""",
        encoding="utf-8",
    )

    error = runner._validate_pm_planner_task_semantics(
        project_root=str(temp_project_root),
        business_output={
            "parent_epic": "EPIC-001",
            "source_feats": ["FEAT-143"],
            "task_specs": [
                {
                    "task_id": "TASK-FEAT-143-004",
                    "title": "执行入口缓存与审计存储实现",
                    "objective": "引入 redis 缓存和 postgresql 审计存储",
                    "description": "使用 redis 作为会话缓存，postgresql 作为审计日志持久化后端。",
                    "source_feat": "FEAT-143",
                },
            ],
        },
    )

    assert error is None


def test_feat_bundle_requires_ui_detects_non_ui_bundle(tmp_path, runner):
    feat_freeze = tmp_path / "feat-freeze.yaml"
    feat_freeze.write_text(
        """
epic_ref: EPIC-001
feat_specs:
  - feat_specifications:
      - feat_id: FEAT-002
        title: raw_to_src workflow 定义
        requirement:
          description: 拆分 raw_to_src workflow 与 freeze gate，不涉及前端页面。
        acceptance_criteria:
          - description: workflow registry 完成迁移
      - feat_id: FEAT-003
        title: src_to_epic workflow 收窄
        requirement:
          description: 限制 src_to_epic 只接收 frozen SRC。
""".strip(),
        encoding="utf-8",
    )

    required = runner._feat_bundle_requires_ui(
        {"params": {"feat_freeze": str(feat_freeze)}}
    )

    assert required is False


def test_feat_bundle_requires_ui_detects_ui_bundle(tmp_path, runner):
    feat_freeze = tmp_path / "feat-freeze.yaml"
    feat_freeze.write_text(
        """
epic_ref: EPIC-001
feat_specs:
  - feat_specifications:
      - feat_id: FEAT-010
        title: 用户设置页
        requirement:
          description: 新增设置页面、组件布局和交互流程。
        acceptance_criteria:
          - description: 页面包含保存按钮和表单校验
""".strip(),
        encoding="utf-8",
    )

    required = runner._feat_bundle_requires_ui(
        {"params": {"feat_freeze": str(feat_freeze)}}
    )

    assert required is True


def test_feat_bundle_requires_ui_detects_non_ui_markdown_feat(tmp_path, runner):
    feat_markdown = tmp_path / "FEAT-169__config.md"
    feat_markdown.write_text(
        """---
id: FEAT-169
ssot_type: feat
title: 系统配置层支持识别并透传 qwen 执行器类型标识
status: active
version: v1
parent_id: EPIC-022
source_refs:
- EPIC-022#scope
---

# Goal

系统配置层能够识别并透传 qwen 执行器类型标识

# User Value

用户可以通过配置灵活切换执行器

# Inputs

- CLI 参数对象
- 配置文件对象

# Non Goals

- 不新增界面
- 不新增页面
""",
        encoding="utf-8",
    )

    required = runner._feat_bundle_requires_ui(
        {"params": {"feat_freeze_ref": str(feat_markdown)}}
    )

    assert required is False


def test_build_pm_planner_bundle_from_legacy_task_planning_specs(tmp_path, runner):
    legacy_path = tmp_path / "task-planning-specs.yaml"
    legacy_path.write_text(
        """# Task Planning Specifications
task_planning_specs:
  version: "1.0.0"
  epic_id: EPIC-012

  - task_id: TASK-012-001
    title: "Implement RawToSRCService"
    related_feature: FEAT-012-001
    implementation_scope:
      description: |
        Implement raw_to_src workflow runtime changes.
      acceptance_criteria:
        - raw_to_src template exists
        - SRC freeze handoff works

  - task_id: TASK-012-002
    title: "Update Migration Guide"
    related_features:
      - FEAT-012-006
    implementation_scope:
      description: |
        Update migration guide and registry docs.
      acceptance_criteria:
        - migration guide updated
""",
        encoding="utf-8",
    )

    bundle = runner._build_pm_planner_bundle_from_written_files([str(legacy_path)])

    assert bundle is not None
    assert bundle["metadata"]["epic_id"] == "EPIC-012"
    assert bundle["task_hierarchy"][0]["tasks"][0]["related_feat"] == "FEAT-012-001"
    assert bundle["task_hierarchy"][0]["tasks"][1]["related_feat"] == "FEAT-012-006"


def test_build_pm_planner_bundle_from_task_plan_yaml(tmp_path, runner):
    task_plan_path = tmp_path / "task-plan.yaml"
    task_plan_path.write_text(
        """
metadata:
  epic_id: EPIC-012
overview:
  groups:
    - group_id: G1
      name: 基础能力
      tasks: [T-001]
tasks:
  - task_id: T-001
    title: 实现 raw_to_src 核心服务
    feat_ref: FEAT-012-001
    assignee_role: backend_developer
    priority: high
    story_points: 3
    description: 实现 workflow 运行时主逻辑。
    acceptance_criteria:
      - raw_to_src workflow 可执行
    dependencies:
      upstream: []
""".strip(),
        encoding="utf-8",
    )

    bundle = runner._build_pm_planner_bundle_from_written_files([str(task_plan_path)])

    assert bundle is not None
    assert bundle["metadata"]["epic_id"] == "EPIC-012"
    assert bundle["tasks"][0]["feat_ref"] == "FEAT-012-001"


def test_normalize_pm_planner_payload_converts_task_plan_yaml_tasks(tmp_path, runner):
    feat_freeze = tmp_path / "feat-freeze.yaml"
    feat_freeze.write_text(
        """
epic_ref: EPIC-012
feat_specs:
  - feat_specifications:
      - feat_id: FEAT-012-001
        title: raw_to_src L3 Workflow 定义
""".strip(),
        encoding="utf-8",
    )

    step = SimpleNamespace(agent_id="agent.product.pm_planner")
    business_output = {
        "metadata": {"epic_id": "EPIC-012"},
        "overview": {
            "groups": [
                {"group_id": "G1", "name": "基础能力", "tasks": ["T-001"]},
            ]
        },
        "tasks": [
            {
                "task_id": "T-001",
                "title": "实现 raw_to_src 核心服务",
                "feat_ref": "FEAT-012-001",
                "assignee_role": "backend_developer",
                "priority": "high",
                "story_points": 3,
                "description": "实现 workflow 运行时主逻辑。",
                "acceptance_criteria": ["raw_to_src workflow 可执行"],
                "dependencies": {"upstream": []},
            }
        ],
    }

    normalized_business, normalized_structured = runner._normalize_pm_planner_task_payload(
        step,
        "wf-001",
        business_output,
        {"business_output": business_output},
        instance_data={"params": {"feat_freeze": str(feat_freeze)}},
    )

    assert normalized_business["parent_epic"] == "EPIC-012"
    assert normalized_business["task_specs"][0]["title"] == "实现 raw_to_src 核心服务"
    assert normalized_business["task_specs"][0]["source_feat"] == "FEAT-012-001"
    assert normalized_business["task_specs"][0]["milestone"] == "G1"
    assert normalized_structured["ssot_output_contract"]["outputs"]


def test_normalize_prd_writer_feat_payload_repairs_fixed_contract_fields(runner):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    business_output = {
        "feat_id": "FEAT-900",
        "title": "训练计划智能调整",
        "source_refs": ["EPIC-001#scope"],
        "ssot": {
            "parent": "EPIC-001",
            "derived_from": "EPIC-001",
        },
    }
    structured_payload = {
        "business_output": business_output,
        "ssot_output_contract": {
            "outputs": [
                {
                    "key": "feat",
                }
            ]
        },
    }

    normalized_business, normalized_structured = runner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-task-001",
        business_output=business_output,
        structured_payload=structured_payload,
    )

    assert normalized_business["ssot"]["identity_kind"] == "ssot"
    assert normalized_business["ssot"]["ssot_type"] == "FEAT"
    assert normalized_business["derived_object_expectations"]["task_required"] is True
    assert normalized_business["derived_object_expectations"]["testset_required"] is True
    assert normalized_business["derived_object_expectations"]["testset_owner"] == "qa"
    assert normalized_business["derived_object_expectations"]["qa_seed_required"] is True
    assert normalized_structured["ssot_output_contract"]["contract_version"] == "1.0"
    assert normalized_structured["ssot_output_contract"]["run_id"] == "wf-task-001"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["identity_kind"] == "ssot"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["ssot_type"] == "feat"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["parent"] == "EPIC-001"


def test_normalize_prd_writer_feat_bundle_payload_repairs_nested_feat_fields(runner):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-001",
        "epic_title": "训练能力升级",
        "feat_specs": [
            {
                "feat_id": "FEAT-900",
                "title": "训练计划智能调整",
                "source_refs": ["EPIC-001#scope"],
                "ssot": {
                    "parent": "EPIC-001",
                    "derived_from": "EPIC-001",
                },
            }
        ],
    }
    structured_payload = {
        "business_output": business_output,
        "ssot_output_contract": {
            "outputs": [
                {
                    "key": "feat",
                }
            ]
        },
    }

    normalized_business, normalized_structured = runner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-task-001",
        business_output=business_output,
        structured_payload=structured_payload,
    )

    feat = normalized_business["feat_specs"][0]
    assert set(normalized_business.keys()) == {"epic_ref", "feat_specs"}
    assert feat["ssot"]["identity_kind"] == "ssot"
    assert feat["ssot"]["ssot_type"] == "FEAT"
    assert feat["derived_object_expectations"]["task_required"] is True
    assert feat["derived_object_expectations"]["testset_required"] is True
    assert feat["derived_object_expectations"]["testset_owner"] == "qa"
    assert feat["derived_object_expectations"]["qa_seed_required"] is True
    assert normalized_structured["ssot_output_contract"]["contract_version"] == "1.0"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["key"] == "feat"


def test_normalize_prd_writer_feat_bundle_payload_maps_user_story_shape(runner):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-001",
        "feat_specs": [
            {
                "feat_id": "FEAT-900",
                "title": "训练计划智能调整",
                "goal": "根据训练反馈调整训练计划",
                "user_value": "降低人工调整成本",
                "inputs": ["训练反馈"],
                "input_contract": {
                    "required_artifacts": ["EPIC-001#scope"],
                    "required_fields": ["feedback_id"],
                    "optional_fields": [],
                    "consumption_rules": [],
                },
                "processing": ["分析反馈", "调整计划"],
                "outputs": ["调整后的训练计划"],
                "acceptance_criteria": ["训练计划会被正确调整"],
                "acceptance_checks": [
                    {
                        "id": "AC-1",
                        "scenario": "ok",
                        "given": "g",
                        "when": "w",
                        "then": "t",
                        "trace_hints": ["TECH"],
                    }
                ],
                "dependencies": [],
                "non_goals": [],
                "priority": "P0",
                "delivery_slice": "mvp",
                "lifecycle_status": "draft",
                "ssot": {
                    "parent": "EPIC-001",
                    "derived_from": "EPIC-001",
                },
                "user_stories": [
                    {
                        "role": "训练运营",
                        "action": "根据反馈自动调整计划",
                        "benefit": "减少手工维护",
                    }
                ],
            }
        ],
    }

    normalized_business, _ = runner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-task-001",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    feat = normalized_business["feat_specs"][0]
    assert feat["input_contract"]["consumption_rules"]
    assert feat["user_stories"] == [
        {
            "as_a": "训练运营",
            "i_want": "根据反馈自动调整计划",
            "so_that": "减少手工维护",
        }
    ]


def test_normalize_prd_writer_feat_bundle_payload_rebuilds_invalid_contract_keys(runner):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-004",
        "feat_specs": [
            {
                "feat_id": "FEAT-004-01",
                "title": "流式输出能力建设",
                "inputs": ["stdout"],
                "processing": ["pipe"],
                "outputs": ["terminal"],
                "acceptance_criteria": ["延迟 <= 500ms"],
                "acceptance_checks": [
                    {
                        "id": "AC-1",
                        "scenario": "ok",
                        "given": "given",
                        "when": "when",
                        "then": "then",
                        "trace_hints": ["TECH"],
                    }
                ],
                "dependencies": [],
                "non_goals": [],
                "priority": "P0",
                "delivery_slice": "mvp",
                "lifecycle_status": "draft",
                "ssot": {"parent": "EPIC-004"},
            },
            {
                "feat_id": "FEAT-004-02",
                "title": "执行状态可视化",
                "inputs": ["heartbeat"],
                "processing": ["track"],
                "outputs": ["status"],
                "acceptance_criteria": ["状态可见"],
                "acceptance_checks": [
                    {
                        "id": "AC-2",
                        "scenario": "ok",
                        "given": "given",
                        "when": "when",
                        "then": "then",
                        "trace_hints": ["UI"],
                    }
                ],
                "dependencies": [],
                "non_goals": [],
                "priority": "P0",
                "delivery_slice": "mvp",
                "lifecycle_status": "draft",
                "ssot": {"parent": "EPIC-004"},
            },
        ],
    }
    structured_payload = {
        "business_output": business_output,
        "ssot_output_contract": {
            "outputs": [
                {"key": "FEAT-004-01"},
                {"key": "FEAT-004-02"},
            ]
        },
    }

    _, normalized_structured = runner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-task-004",
        business_output=business_output,
        structured_payload=structured_payload,
    )

    outputs = normalized_structured["ssot_output_contract"]["outputs"]
    assert [item["key"] for item in outputs] == ["feat_001", "feat_002"]
    assert all(item["ssot_type"] == "feat" for item in outputs)
    assert all(item["parent"] == "EPIC-004" for item in outputs)


def test_normalize_pm_planner_payload_builds_task_markdown_content(runner):
    step = SimpleNamespace(agent_id="agent.product.pm_planner")
    business_output = {
        "parent_epic": "EPIC-004",
        "source_feats": ["FEAT-085"],
        "task_specs": [
            {
                "task_id": "TASK-FEAT-085-001",
                "title": "流式输出引擎实现",
                "objective": "实现流式输出引擎",
                "description": "建立 stdout/stderr 流式输出管道",
                "source_feat": "FEAT-085",
                "workstream": "cli-execution-runtime",
                "task_kind": "implementation",
                "responsible_role": "cli-runtime-engineer",
                "acceptance_criteria_mapping": [
                    {
                        "feat": "FEAT-085",
                        "ac": "AC-00401-001",
                        "description": "首字节输出延迟 <= 500ms",
                    }
                ],
                "dependencies": ["TASK-FEAT-000-001"],
                "definition_of_done": ["核心类实现完成"],
                "priority": "P0",
                "milestone": "M1",
                "estimated_effort": "3 days",
                "lifecycle_status": "draft",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "streaming-execution",
                    "audit_fields": ["run_id"],
                },
                "evidence_requirements": {
                    "required_refs": ["TECH-FEAT-085"],
                    "review_required": True,
                },
                "rollback_strategy": {
                    "mode": "revert",
                    "restore_targets": ["src/lee/executor/streaming"],
                },
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-085",
                    "derived_from": "FEAT-085#delivery",
                },
            }
        ],
    }

    normalized_business, normalized_structured = runner._normalize_pm_planner_task_payload(
        step=step,
        workflow_id="wf-task-004",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    assert normalized_business["task_specs"][0]["source_feat"] == "FEAT-085"
    outputs = normalized_structured["ssot_output_contract"]["outputs"]
    assert len(outputs) == 1
    assert outputs[0]["parent"] == "FEAT-085"
    assert outputs[0]["source_refs"] == ["FEAT-085#delivery"]
    assert "# Objective" in outputs[0]["content"]
    assert "## Acceptance Mapping" in outputs[0]["content"]
    assert "## Definition Of Done" in outputs[0]["content"]


def test_normalize_pm_planner_payload_repairs_parent_epic_from_feat_freeze_ref(tmp_path, runner):
    features_dir = tmp_path / "spec" / "requirements" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    feat_path = features_dir / "FEAT-143__qa-entry.md"
    feat_path.write_text(
        """---
id: FEAT-143
ssot_type: feat
title: QA 执行入口规范化
status: frozen
version: v1
parent_id: EPIC-QA-SSOT-UPGRADE
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Goal

规范 QA 执行入口。
""",
        encoding="utf-8",
    )

    step = SimpleNamespace(agent_id="agent.product.pm_planner")
    business_output = {
        "parent_epic": "EPIC-003",
        "source_feats": ["FEAT-143"],
        "task_specs": [
            {
                "task_id": "TASK-FEAT-143-001",
                "title": "定义入口契约",
                "objective": "定义入口契约",
                "description": "定义入口契约",
                "source_feat": "FEAT-143",
                "workstream": "qa-execution-runtime",
                "task_kind": "governance",
                "responsible_role": "qa-execution-runtime-owner",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-143", "ac": "AC-003-001", "description": "契约完成"}
                ],
                "definition_of_done": ["契约完成"],
                "estimated_effort": "1 day",
            }
        ],
    }

    normalized_business, _ = runner._normalize_pm_planner_task_payload(
        step=step,
        workflow_id="wf-task-143",
        business_output=business_output,
        structured_payload={"business_output": business_output},
        instance_data={"params": {"feat_freeze_ref": str(feat_path)}},
    )

    assert normalized_business["parent_epic"] == "EPIC-QA-SSOT-UPGRADE"


def test_normalize_pm_planner_payload_writes_extended_task_sections_and_directory(runner):
    step = SimpleNamespace(agent_id="agent.product.pm_planner")
    business_output = {
        "parent_epic": "EPIC-030",
        "source_feats": ["FEAT-159"],
        "planning_metadata": {
            "project_profile": "qa_chain_testing",
            "task_directory": "spec/tasks/EPIC-030",
        },
        "task_specs": [
            {
                "task_id": "TASK-FEAT-159-001",
                "title": "核心测试引擎-测试器调度框架",
                "objective": "实现测试器调度框架",
                "description": "支持动态注册与并发执行",
                "source_feat": "FEAT-159",
                "workstream": "chain-testing-engine",
                "task_kind": "implementation",
                "responsible_role": "testing-engine-owner",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-159", "ac": "AC-001-001", "description": "测试器可调度"}
                ],
                "prerequisites": ["FEAT-159 frozen"],
                "dependencies": ["TASK-FEAT-159-000"],
                "definition_of_done": ["单测通过", "文档补齐"],
                "estimated_effort": "2 days",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "task-execution",
                    "audit_fields": ["run_id", "changed_files"],
                },
                "evidence_requirements": {
                    "required_refs": ["FEAT-159"],
                    "review_required": True,
                },
                "rollback_strategy": {
                    "mode": "revert",
                    "restore_targets": ["src/chain_testing/engine"],
                },
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-159",
                    "derived_from": "FEAT-159#delivery",
                },
            }
        ],
    }

    normalized_business, normalized_structured = runner._normalize_pm_planner_task_payload(
        step=step,
        workflow_id="wf-task-sections",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    assert normalized_business["planning_metadata"]["task_directory"] == "spec/tasks/EPIC-030"
    output = normalized_structured["ssot_output_contract"]["outputs"][0]
    assert "## Prerequisites" in output["content"]
    assert "## Observability" in output["content"]
    assert "## Evidence Requirements" in output["content"]
    assert "## Rollback Strategy" in output["content"]


def test_normalize_pm_planner_payload_rewrites_requirements_tasks_directory(runner):
    step = SimpleNamespace(agent_id="agent.product.pm_planner")
    business_output = {
        "parent_epic": "EPIC-030",
        "source_feats": ["FEAT-159"],
        "planning_metadata": {
            "project_profile": "qa_chain_testing",
            "task_directory": "spec/requirements/tasks/FEAT-159",
        },
        "task_specs": [
            {
                "task_id": "TASK-FEAT-159-001",
                "title": "核心测试引擎-测试器调度框架",
                "objective": "实现测试器调度框架",
                "description": "支持动态注册与并发执行",
                "source_feat": "FEAT-159",
                "workstream": "chain-testing-engine",
                "task_kind": "implementation",
                "responsible_role": "testing-engine-owner",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-159", "ac": "AC-001-001", "description": "测试器可调度"}
                ],
                "prerequisites": ["FEAT-159 frozen"],
                "dependencies": ["TASK-FEAT-159-000"],
                "definition_of_done": ["单测通过", "文档补齐"],
                "estimated_effort": "2 days",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "task-execution",
                    "audit_fields": ["run_id", "changed_files"],
                },
                "evidence_requirements": {
                    "required_refs": ["FEAT-159"],
                    "review_required": True,
                },
                "rollback_strategy": {
                    "mode": "revert",
                    "restore_targets": ["src/chain_testing/engine"],
                },
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-159",
                    "derived_from": "FEAT-159#delivery",
                },
            }
        ],
    }

    normalized_business, _ = runner._normalize_pm_planner_task_payload(
        step=step,
        workflow_id="wf-task-rewrite-dir",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    assert normalized_business["planning_metadata"]["task_directory"] == "spec/tasks/FEAT-159"


def test_normalize_pm_planner_payload_rewrites_legacy_task_paths_inside_task_specs(runner):
    step = SimpleNamespace(agent_id="agent.product.pm_planner")
    business_output = {
        "parent_epic": "EPIC-030",
        "source_feats": ["FEAT-159"],
        "planning_metadata": {
            "project_profile": "qa_chain_testing",
            "task_directory": "spec/tasks/FEAT-159",
        },
        "task_specs": [
            {
                "task_id": "TASK-FEAT-159-001",
                "title": "核心测试引擎-测试器调度框架",
                "objective": "实现测试器调度框架",
                "description": "支持动态注册与并发执行",
                "source_feat": "FEAT-159",
                "workstream": "chain-testing-engine",
                "task_kind": "implementation",
                "responsible_role": "testing-engine-owner",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-159", "ac": "AC-001-001", "description": "测试器可调度"}
                ],
                "prerequisites": ["FEAT-159 frozen"],
                "dependencies": ["TASK-FEAT-159-000"],
                "definition_of_done": [
                    "TASK 文件已冻结并写入 spec/requirements/tasks/FEAT-159/",
                    "单测通过",
                ],
                "estimated_effort": "2 days",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "task-execution",
                    "audit_fields": ["run_id", "changed_files"],
                },
                "evidence_requirements": {
                    "required_refs": ["FEAT-159"],
                    "review_required": True,
                },
                "rollback_strategy": {
                    "mode": "revert",
                    "restore_targets": ["spec/requirements/tasks/FEAT-159/"],
                },
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-159",
                    "derived_from": "FEAT-159#delivery",
                },
            }
        ],
    }

    normalized_business, _ = runner._normalize_pm_planner_task_payload(
        step=step,
        workflow_id="wf-task-rewrite-inner-paths",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    task = normalized_business["task_specs"][0]
    assert task["definition_of_done"][0] == "TASK 文件已冻结并写入 spec/tasks/FEAT-159"
    assert task["rollback_strategy"]["restore_targets"] == ["spec/tasks/FEAT-159"]


def test_pm_planner_normalization_enriches_validation_dependencies_and_dependency_matrix(runner):
    step = SimpleNamespace(agent_id="agent.product.pm_planner")
    business_output = {
        "parent_epic": "EPIC-QA-SSOT-UPGRADE",
        "source_feats": ["FEAT-143"],
        "planning_metadata": {
            "project_profile": "qa_execution_gateway",
            "task_directory": "spec/tasks/FEAT-143",
        },
        "task_specs": [
            {
                "task_id": "TASK-FEAT-143-001",
                "source_feat": "FEAT-143",
                "task_kind": "specification",
                "dependencies": [],
                "prerequisites": [],
            },
            {
                "task_id": "TASK-FEAT-143-002",
                "source_feat": "FEAT-143",
                "task_kind": "implementation",
                "dependencies": ["TASK-FEAT-143-001"],
                "prerequisites": ["TASK-FEAT-143-001"],
            },
            {
                "task_id": "TASK-FEAT-143-006",
                "source_feat": "FEAT-143",
                "task_kind": "validation",
                "dependencies": [],
                "prerequisites": ["TASK-FEAT-143-002"],
            },
        ],
        "dependency_graph": {
            "critical_path": [
                "TASK-FEAT-143-001",
                "TASK-FEAT-143-002",
                "TASK-FEAT-143-006",
            ]
        },
        "risk_mitigation": [
            {
                "risk": "Registry 同步问题",
                "mitigation": "验证前同步检查，失败降级到直接磁盘读取",
            }
        ],
    }

    normalized_business, _ = runner._normalize_pm_planner_task_payload(
        step=step,
        workflow_id="wf-task-dependency-matrix",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    validation_task = next(
        item for item in normalized_business["task_specs"] if item["task_id"] == "TASK-FEAT-143-006"
    )
    dependency_matrix = normalized_business["dependency_graph"]["dependency_matrix"]

    assert validation_task["dependencies"] == ["TASK-FEAT-143-002"]
    assert dependency_matrix[-1] == {
        "task_id": "TASK-FEAT-143-006",
        "depends_on": ["TASK-FEAT-143-002"],
    }
    assert "审计一致性" in normalized_business["risk_mitigation"][0]["mitigation"]


def test_pm_planner_normalization_preserves_concrete_task_directory_and_injects_governance_task(
    temp_project_root, runner
):
    feat_dir = temp_project_root / "spec" / "requirements" / "features"
    feat_dir.mkdir(parents=True, exist_ok=True)
    feat_path = feat_dir / "FEAT-143__qa-entry.md"
    feat_path.write_text(
        "\n".join(
            [
                "---",
                "id: FEAT-143",
                "title: QA 执行入口规范化",
                "parent_id: EPIC-QA-SSOT-UPGRADE",
                "---",
                "",
                "## AC-003-001",
                "- Scenario: 执行入口唯一性验证",
                "- Then: 仅允许通过 TASK 触发执行",
                "",
                "## AC-003-002",
                "- Scenario: 执行路径完整性校验",
                "- Then: 系统验证 release_ref -> testplan_ref -> task_ref 链路完整且有效",
                "",
                "## AC-003-003",
                "- Scenario: 旁路执行入口阻断验证",
                "- Then: 系统拒绝旁路请求并返回入口规范错误，记录审计日志",
                "",
                "## AC-003-004",
                "- Scenario: 执行入口审计验证",
                "- Then: 日志中包含每次执行的入口来源、路径链、时间戳、操作用户",
            ]
        ),
        encoding="utf-8",
    )

    business_output = {
        "parent_epic": "EPIC-QA-SSOT-UPGRADE",
        "source_feats": ["FEAT-143"],
        "planning_metadata": {
            "project_profile": "qa_execution_gateway",
            "task_directory": "spec/tasks/FEAT-143",
        },
        "task_specs": [
            {
                "task_id": "TASK-FEAT-143-001",
                "title": "执行入口路由与路径校验规则实现",
                "objective": "实现 QA 测试执行的唯一入口路由规则",
                "description": "基于 FEAT-143 执行入口规范，实现执行请求路由层并阻断旁路请求",
                "source_feat": "FEAT-143",
                "workstream": "qa-execution-runtime",
                "task_kind": "implementation",
                "responsible_role": "qa-runtime-owner",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-143", "ac": "AC-003-001", "description": "唯一入口"},
                    {"feat": "FEAT-143", "ac": "AC-003-002", "description": "路径校验"},
                    {"feat": "FEAT-143", "ac": "AC-003-003", "description": "旁路阻断"},
                ],
                "prerequisites": [],
                "dependencies": [],
                "definition_of_done": ["入口路由实现完成"],
                "priority": "P0",
                "milestone": "M1",
                "estimated_effort": "3 days",
                "lifecycle_status": "planned",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "qa-entry-gateway",
                    "audit_fields": ["run_id"],
                },
                "evidence_requirements": {"required_refs": ["FEAT-143"], "review_required": True},
                "rollback_strategy": {"mode": "revert", "restore_targets": ["src/lee/qa/execution/gateway"]},
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-143",
                    "derived_from": "FEAT-143#delivery",
                },
            },
            {
                "task_id": "TASK-FEAT-143-002",
                "title": "审计日志与 SSOT 绑定追踪实现",
                "objective": "建立执行入口的完整审计追踪能力",
                "description": "实现审计日志结构化记录和查询接口",
                "source_feat": "FEAT-143",
                "workstream": "qa-execution-audit",
                "task_kind": "implementation",
                "responsible_role": "qa-audit-owner",
                "acceptance_criteria_mapping": [
                    {"feat": "FEAT-143", "ac": "AC-003-004", "description": "审计追溯"},
                ],
                "prerequisites": ["TASK-FEAT-143-001 入口路由规则已实现"],
                "dependencies": ["TASK-FEAT-143-001"],
                "definition_of_done": ["审计日志实现完成"],
                "priority": "P0",
                "milestone": "M1",
                "estimated_effort": "2 days",
                "lifecycle_status": "planned",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "qa-audit-trail",
                    "audit_fields": ["run_id"],
                },
                "evidence_requirements": {"required_refs": ["FEAT-143"], "review_required": True},
                "rollback_strategy": {"mode": "revert", "restore_targets": ["src/lee/qa/execution/audit"]},
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-143",
                    "derived_from": "FEAT-143#delivery",
                },
            },
        ],
        "milestones": [
            {
                "id": "M1",
                "name": "执行入口规范化",
                "task_ids": ["TASK-FEAT-143-001", "TASK-FEAT-143-002"],
                "acceptance_criteria": "FEAT-143 所有 AC 可验证",
            }
        ],
        "dependency_graph": {
            "critical_path": ["TASK-FEAT-143-001", "TASK-FEAT-143-002"],
            "dependencies": [{"from": "TASK-FEAT-143-002", "to": "TASK-FEAT-143-001", "type": "prerequisite"}],
        },
        "resource_allocation": {
            "qa-runtime-owner": {"tasks": ["TASK-FEAT-143-001"]},
            "qa-audit-owner": {"tasks": ["TASK-FEAT-143-002"]},
        },
        "risk_mitigation": [],
    }

    normalized_business, _ = runner._normalize_pm_planner_task_payload(
        step=SimpleNamespace(id="task_planning", agent_id="agent.product.pm_planner"),
        workflow_id="wf-task-143-real-shape",
        business_output=business_output,
        structured_payload={"business_output": business_output},
        instance_data={"params": {"feat_freeze_ref": str(feat_path)}},
    )

    assert normalized_business["planning_metadata"]["task_directory"] == "spec/tasks/FEAT-143"
    assert normalized_business["task_specs"][0]["task_id"] == "TASK-FEAT-143-000"
    assert normalized_business["task_specs"][0]["task_kind"] == "governance"
    governance_ac_ids = [
        item["ac"] for item in normalized_business["task_specs"][0]["acceptance_criteria_mapping"]
    ]
    assert "AC-003-003" in governance_ac_ids
    assert normalized_business["task_specs"][1]["dependencies"][0] == "TASK-FEAT-143-000"
    assert normalized_business["milestones"][0]["id"] == "M0-Governance-Baseline"


def test_synthesize_single_ssot_payload_creates_tech_contract_from_written_markdown(tmp_path, runner):
    tech_path = tmp_path / "frozen-technical-architecture-FEAT-143.md"
    tech_path.write_text("# TECH-FEAT-143\n\n架构摘要", encoding="utf-8")

    step = SimpleNamespace(id="tech_design", name="TECH 设计", agent_id="agent.dev.tech_architect")
    business_output = {
        "title": "QA 执行入口规范化 TECH 设计",
        "parent": "FEAT-143",
    }
    structured_payload = {
        "business_output": business_output,
        "written_files": [str(tech_path)],
    }

    _, normalized_structured = runner._synthesize_single_ssot_payload(
        step=step,
        workflow_id="wf-task-143",
        business_output=business_output,
        structured_payload=structured_payload,
    )

    outputs = normalized_structured["ssot_output_contract"]["outputs"]
    assert outputs[0]["ssot_type"] == "tech"
    assert outputs[0]["parent"] == "FEAT-143"
    assert "# TECH-FEAT-143" in outputs[0]["content"]


def test_claude_code_runner_exposes_workspace_ssot_materializer():
    assert hasattr(ClaudeCodeRunner, "_materialize_workspace_formal_ssot_markdown")


def test_claude_code_validation_prefers_written_business_file(temp_project_root):
    schema_path = temp_project_root / "feat.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["feat_id", "title", "ssot"],
                "properties": {
                    "feat_id": {"type": "string"},
                    "title": {"type": "string"},
                    "ssot": {"type": "object"},
                },
            }
        ),
        encoding="utf-8",
    )
    written_path = temp_project_root / "feat-spec-20250310-001.json"
    written_path.write_text(
        json.dumps(
            {
                "business_output": [
                    {
                        "feat_id": "FEAT-001",
                        "title": "基础用户认证与账户管理",
                        "ssot": {
                            "parent": "EPIC-001",
                            "derived_from": "EPIC-001#breakdown",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        config={"output_contract": str(schema_path), "strict_output_validation": True},
        outputs=[SimpleNamespace(path="feat-spec-20250310-001.json", type="file")],
    )
    output = {
        "raw_output": json.dumps(
            {
                "status": "success",
                "changed_files": ["feat-spec-20250310-001.json"],
            }
        )
    }

    business_output, structured_payload = ClaudeCodeRunner._extract_business_output_for_validation(
        step=step,
        workflow_id="wf-001",
        output=output,
        written_files=[str(written_path)],
    )
    validation = ClaudeCodeRunner._validate_step_output(step, business_output)

    assert isinstance(structured_payload, dict)
    assert isinstance(business_output, dict)
    assert business_output["feat_id"] == "FEAT-001"
    assert business_output["ssot"]["ssot_type"] == "FEAT"
    assert validation is not None
    assert validation.passed is True


def test_claude_code_validation_reads_changed_file_for_symbol_outputs(temp_project_root):
    schema_path = temp_project_root / "feat-bundle.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["epic_ref", "feat_specs"],
                "properties": {
                    "epic_ref": {"type": "string"},
                    "feat_specs": {"type": "array"},
                },
            }
        ),
        encoding="utf-8",
    )
    written_path = temp_project_root / "feat-spec-20250310-001.yaml"
    written_path.write_text(
        "\n".join(
            [
                "business_output:",
                "  epic_ref: EPIC-001",
                "  feat_specs:",
                "    - feat_id: FEAT-001",
                "      title: 基础用户认证与账户管理",
                "      goal: goal",
                "      user_value: user_value",
                "      inputs: [a]",
                "      processing: [b]",
                "      outputs: [c]",
                "      acceptance_criteria: [d]",
                "      acceptance_checks:",
                "        - id: AC-1",
                "          scenario: s",
                "          given: g",
                "          when: w",
                "          then: t",
                "          trace_hints: [UI]",
                "        - id: AC-2",
                "          scenario: s2",
                "          given: g2",
                "          when: w2",
                "          then: t2",
                "          trace_hints: [TECH]",
                "      dependencies: []",
                "      non_goals: []",
                "      priority: P0",
                "      delivery_slice: mvp",
                "      lifecycle_status: draft",
                "      ssot:",
                "        parent: EPIC-001",
                "        derived_from: EPIC-001#breakdown",
            ]
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        config={"output_contract": str(schema_path), "strict_output_validation": True},
        outputs=[SimpleNamespace(path="", type="symbol")],
    )
    output = {
        "raw_output": json.dumps(
            {
                "status": "success",
                "changed_files": ["feat-spec-20250310-001.yaml"],
            }
        )
    }

    business_output, _ = ClaudeCodeRunner._extract_business_output_for_validation(
        step=step,
        workflow_id="wf-001",
        output=output,
        written_files=[str(written_path)],
    )
    validation = ClaudeCodeRunner._validate_step_output(step, business_output)

    assert isinstance(business_output, dict)
    assert business_output["epic_ref"] == "EPIC-001"
    assert validation is not None
    assert validation.passed is True


def test_parse_structured_output_accepts_fenced_json_with_leading_prose():
    output_text = """
评审已完成。

```json
{
  "review_id": "RVW-001",
  "review_type": "feat_review",
  "subject_refs": ["FEAT-001"],
  "summary": "ok",
  "findings": [],
  "decision": "pass",
  "risks": [],
  "recommendations": []
}
```
"""

    parsed = StepRunnerBase._parse_structured_output(output_text)

    assert isinstance(parsed, dict)
    assert parsed["review_id"] == "RVW-001"
    assert parsed["decision"] == "pass"


def test_parse_structured_output_prefers_yaml_body_before_status_fence():
    output_text = """
business_output:
  epic_ref: EPIC-001
  feat_specs:
    - feat_id: FEAT-001
      title: 标题
      goal: 目标
      user_value: 用户价值
      inputs: [a]
      processing: [b]
      outputs: [c]
      acceptance_criteria: [d]
      acceptance_checks:
        - id: AC-1
          scenario: s
          given: g
          when: w
          then: t
          trace_hints: [UI]
      dependencies: []
      non_goals: []
      priority: P0
      delivery_slice: mvp
      lifecycle_status: draft
      ssot:
        parent: EPIC-001
        derived_from: EPIC-001#breakdown
ssot_output_contract:
  contract_version: "1.0"
  run_id: run-001
  outputs: []

```json
{"status":"success","changed_files":["foo.yaml"],"error":null}
```
"""

    parsed = StepRunnerBase._parse_structured_output(output_text)

    assert isinstance(parsed, dict)
    assert parsed["business_output"]["epic_ref"] == "EPIC-001"
    assert parsed["ssot_output_contract"]["run_id"] == "run-001"


def test_parse_structured_output_strips_leading_think_block():
    output_text = """<think>Now I need to output the final JSON result according to the task requirements.</think>

{
  "review_id": "RVW-001",
  "review_type": "feat_review",
  "subject_refs": ["FEAT-001"],
  "decision": "pass"
}
"""

    parsed = StepRunnerBase._parse_structured_output(output_text)

    assert isinstance(parsed, dict)
    assert parsed["review_id"] == "RVW-001"
    assert parsed["decision"] == "pass"


def test_normalize_product_review_payload_sanitizes_structured_feat_review_soft_blockers():
    step = SimpleNamespace(
        id="feat_review",
        agent_id="agent.product.feat_reviewer",
    )
    business_output = {
        "review_id": "RVW-009",
        "review_type": "feat_review",
        "decision": "revise",
        "subject_refs": ["FEAT-001"],
        "summary": "still too abstract",
        "findings": [
            "FEAT-SRC-041-016-001 未冻结 purpose 与 decision_mode 的正式枚举、允许组合矩阵以及 legacy_gate_type 到双轴模型的完备映射表，当前只能表达方向，无法独立判定新增 gate 定义是否合规。",
            "全部 FEAT 的 acceptance_checks 均包含 id、scenario、given、when、then、trace_hints，但 trace_hints 仅停留在 UI/TECH/TASK/TESTSET 标签级别，缺少可直接派生下游对象的具体追踪锚点，未满足“可支撑下游派生”的要求。",
        ],
        "risks": ["若继续基于当前 FEAT 下发实施，团队会分别补充 purpose/decision_mode、human_gate_context、gate_result 的本地解释，形成新的治理分叉。"],
        "recommendations": [],
    }

    normalized_business, normalized_structured = LLMRunner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "step_outputs": {
                "feat_spec_generation": {
                    "business_output": {
                        "epic_ref": "EPIC-001",
                        "feat_specs": [
                            {
                                "feat_id": "FEAT-001",
                                "title": "Gate Result Contract",
                                "goal": "Freeze gate result semantics",
                                "user_value": "Downstream workflows can rely on stable gate outputs",
                                "inputs": ["gate definition", "review evidence"],
                                "processing": ["normalize decision", "validate subject refs"],
                                "outputs": ["gate_result", "workflow transition"],
                                "acceptance_criteria": ["gate_result schema is stable"],
                                "input_contract": {
                                    "required_artifacts": ["gate.yaml"],
                                    "required_fields": ["purpose", "decision_mode"],
                                    "consumption_rules": ["human review consumes human_gate_context"],
                                },
                                "acceptance_checks": [
                                    {
                                        "id": "AC-001",
                                        "scenario": "approval handoff",
                                        "given": "a running workflow pauses at gate",
                                        "when": "human approves the gate",
                                        "then": "workflow resumes with deterministic transition",
                                        "trace_hints": ["gate_result.decision", "workflow.status"],
                                    }
                                ],
                                "ssot": {
                                    "parent": "EPIC-001",
                                    "derived_from": "EPIC-001#breakdown",
                                },
                            }
                        ],
                    }
                }
            }
        },
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_business["findings"] == []
    assert normalized_business["risks"] == []
    assert normalized_structured["business_output"]["decision"] == "pass"


def test_normalize_product_review_payload_updates_top_level_structured_review_payload():
    step = SimpleNamespace(
        id="feat_review",
        agent_id="agent.product.feat_reviewer",
    )
    business_output = {
        "review_id": "RVW-010",
        "review_type": "feat_review",
        "decision": "revise",
        "subject_refs": ["FEAT-001"],
        "summary": "still too abstract",
        "findings": ["trace_hints 仍然只有抽象标签，难以直接生成校验逻辑"],
        "risks": [],
        "recommendations": [],
    }

    normalized_business, normalized_structured = LLMRunner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload=dict(business_output),
        instance_data={
            "step_outputs": {
                "feat_spec_generation": {
                    "business_output": {
                        "epic_ref": "EPIC-001",
                        "feat_specs": [
                            {
                                "feat_id": "FEAT-001",
                                "title": "Gate Result Contract",
                                "goal": "Freeze gate result semantics",
                                "user_value": "Downstream workflows can rely on stable gate outputs",
                                "inputs": ["gate definition", "review evidence"],
                                "processing": ["normalize decision", "validate subject refs"],
                                "outputs": ["gate_result", "workflow transition"],
                                "acceptance_criteria": ["gate_result schema is stable"],
                                "input_contract": {
                                    "required_artifacts": ["gate.yaml"],
                                    "required_fields": ["purpose", "decision_mode"],
                                    "consumption_rules": ["human review consumes human_gate_context"],
                                },
                                "acceptance_checks": [
                                    {
                                        "id": "AC-001",
                                        "scenario": "approval handoff",
                                        "given": "a running workflow pauses at gate",
                                        "when": "human approves the gate",
                                        "then": "workflow resumes with deterministic transition",
                                        "trace_hints": ["gate_result.decision", "workflow.status"],
                                    }
                                ],
                                "ssot": {"parent": "EPIC-001", "derived_from": "EPIC-001#breakdown"},
                            }
                        ],
                    }
                }
            }
        },
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_structured["decision"] == "pass"
    assert normalized_structured["findings"] == []


def test_materialize_symbolic_workspace_outputs_writes_to_workflow_workspace(temp_project_root, runner):
    step = SimpleNamespace(
        id="feat_spec_generation",
        outputs=[SimpleNamespace(path="")],
    )

    files = runner._materialize_symbolic_workspace_outputs(
        step=step,
        workflow_id="wf-task-001",
        project_root=str(temp_project_root),
        business_output={"epic_ref": "EPIC-001", "feat_specs": []},
        structured_payload={"business_output": {"epic_ref": "EPIC-001", "feat_specs": []}},
    )

    assert len(files) >= 1
    business_path = temp_project_root / ".workflow" / "workspace" / "wf-task-001" / "feat_spec_generation" / "business_output.yaml"
    assert business_path.exists()
    assert "epic_ref: EPIC-001" in business_path.read_text(encoding="utf-8")


def test_requirement_decomposer_normalizes_rich_candidate_shape():
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        config={},
    )
    business_output = {
        "breakdown_id": "FEAT-BREAKDOWN-EPIC-017",
        "epic_ref": "WRONG-EPIC",
        "feat_candidates": [
            {
                "id": "FEAT-017-01",
                "title": "CLI命令分层架构设计与入口定义",
                "acceptance_boundary": {
                    "scope": "定义治理入口与物化原语的职责边界",
                    "constraints": "保持命名可演进",
                    "out_of_scope": "不实现具体命令逻辑",
                },
                "dependencies": {"upstream": ["FEAT-017-00"]},
                "priority": "high",
            }
        ],
    }

    normalized, envelope = LLMRunner._normalize_requirement_decomposer_payload(
        step,
        business_output,
        {"business_output": business_output},
        instance_data={
            "params": {
                "epic_freeze": {
                    "artifact_id": "EPIC-017",
                    "path": "spec/requirements/epics/EPIC-017.md",
                }
            }
        },
    )

    assert normalized["epic_ref"] == "EPIC-017"
    assert normalized["feat_candidates"][0]["user_value"] == "CLI命令分层架构设计与入口定义"
    assert normalized["feat_candidates"][0]["acceptance_boundary"] == (
        "定义治理入口与物化原语的职责边界\n保持命名可演进\n不实现具体命令逻辑"
    )
    assert normalized["feat_candidates"][0]["dependencies"] == ["FEAT-017-00"]
    assert normalized["feat_candidates"][0]["priority"] == "P1"
    assert envelope["business_output"]["epic_ref"] == "EPIC-017"


def test_requirement_decomposer_extracts_boundary_design_derived_feats():
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        config={},
    )
    business_output = {
        "breakdown_id": "BD-EPIC-017",
        "boundary_design": {
            "epic_ref": "EPIC-017",
            "derived_feats": [
                {
                    "feat_id": "FEAT-017-001",
                    "title": "CLI命令分层与高层治理入口设计",
                    "acceptance_boundary": {
                        "验收目标": "定义治理入口与物化原语职责边界",
                        "验收条件": ["文档化职责边界", "架构图完成"],
                    },
                    "out_of_scope": ["不实现具体命令逻辑"],
                    "dependencies": [],
                    "estimated_effort": "M",
                }
            ],
        },
    }

    normalized, _ = LLMRunner._normalize_requirement_decomposer_payload(
        step,
        business_output,
        {"business_output": business_output},
        instance_data={
            "params": {
                "epic_freeze": {
                    "artifact_id": "EPIC-017",
                    "path": "spec/requirements/epics/EPIC-017.md",
                }
            }
        },
    )

    assert normalized["feat_candidates"][0]["title"] == "CLI命令分层与高层治理入口设计"
    assert normalized["feat_candidates"][0]["non_goals"] == ["不实现具体命令逻辑"]
    assert "定义治理入口与物化原语职责边界" in normalized["feat_candidates"][0]["acceptance_boundary"]


def test_requirement_decomposer_maps_features_list_to_feat_breakdown():
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        config={},
    )
    business_output = {
        "features": [
            {
                "artifact_id": "FEAT-022-01",
                "title": "执行器配置通道扩展",
                "acceptance_boundary": "CLI 支持 --executor=qwen",
                "properties": {"priority": "high"},
            }
        ]
    }

    normalized, envelope = LLMRunner._normalize_requirement_decomposer_payload(
        step,
        business_output,
        {"business_output": business_output},
        instance_data={
            "params": {
                "epic_freeze": {
                    "artifact_id": "EPIC-022",
                    "path": "spec/requirements/epics/EPIC-022.md",
                }
            }
        },
    )

    assert normalized["breakdown_id"] == "FEAT-BREAKDOWN-EPIC-022"
    assert normalized["epic_ref"] == "EPIC-022"
    assert normalized["feat_candidates"][0]["title"] == "执行器配置通道扩展"
    assert normalized["feat_candidates"][0]["user_value"] == "执行器配置通道扩展"
    assert envelope["business_output"]["feat_candidates"][0]["title"] == "执行器配置通道扩展"


def test_prd_writer_normalizes_empty_inputs_and_consumption_rules():
    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        config={
            "output_contract": "departments/product/contracts/feat-bundle-contract/v1/schema.json",
        },
    )
    business_output = {
        "epic_ref": "EPIC-017",
        "feat_specs": [
            {
                "feat_id": "FEAT-017-001",
                "title": "CLI命令分层架构设计",
                "goal": "建立CLI命令分层架构",
                "user_value": "用户获得一致治理体验",
                "inputs": [],
                "input_contract": {
                    "required_artifacts": ["EPIC-017#scope"],
                    "required_fields": ["formal_ssot_id", "source_refs"],
                    "optional_fields": [],
                    "consumption_rules": [],
                },
                "processing": ["分析现有CLI命令结构"],
                "outputs": ["CLI命令分层架构设计 FEAT specification"],
                "acceptance_criteria": ["高层命令与底层命令职责边界文档化"],
                "acceptance_checks": [],
                "dependencies": ["EPIC-017"],
                "non_goals": ["不实现跨runtime同步"],
                "priority": "P0",
                "delivery_slice": "foundation",
                "lifecycle_status": "draft",
                "derived_object_expectations": {
                    "qa_seed_required": True,
                    "task_required": True,
                    "testset_required": True,
                    "testset_owner": "qa",
                },
                "ssot": {
                    "ssot_type": "FEAT",
                    "parent": "EPIC-017",
                    "derived_from": "EPIC-017",
                    "identity_kind": "ssot",
                },
            }
        ],
    }

    normalized, _ = LLMRunner._normalize_prd_writer_feat_payload(
        step,
        "wf-test",
        business_output,
        {"business_output": business_output},
        instance_data={
            "params": {
                "epic_freeze": {
                    "artifact_id": "EPIC-017",
                    "path": "spec/requirements/epics/EPIC-017.md",
                }
            }
        },
    )

    feat = normalized["feat_specs"][0]
    assert feat["inputs"] == ["EPIC-017#scope"]
    assert feat["input_contract"]["consumption_rules"] == [
        "Consume EPIC-017#scope and map fields formal_ssot_id, source_refs"
    ]
    assert len(feat["acceptance_checks"]) >= 2


def test_prd_writer_remaps_temporary_feat_ids_and_dependencies_to_canonical_ids(tmp_path, runner):
    features_dir = tmp_path / "spec" / "requirements" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / "FEAT-158__existing-feature.md").write_text(
        "---\nid: FEAT-158\ntitle: Existing Feature\n---\n",
        encoding="utf-8",
    )

    epic_freeze_path = tmp_path / ".workflow" / "workspace" / "wf-task-epic" / "epic_freeze" / "frozen_epic.yaml"
    epic_freeze_path.parent.mkdir(parents=True, exist_ok=True)
    epic_freeze_path.write_text("artifact_id: EPIC-030\n", encoding="utf-8")

    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        config={
            "output_contract": "departments/product/contracts/feat-bundle-contract/v1/schema.json",
        },
    )
    business_output = {
        "epic_ref": "EPIC-030",
        "feat_specs": [
            {
                "feat_id": "FEAT-018-001",
                "title": "核心测试引擎",
                "goal": "建立测试引擎",
                "user_value": "统一承载测试器执行",
                "inputs": ["EPIC-030#scope"],
                "processing": ["注册和调度测试器"],
                "outputs": ["测试引擎"],
                "acceptance_criteria": ["引擎可调度测试器"],
                "acceptance_checks": [],
                "dependencies": [],
                "non_goals": [],
                "priority": "P0",
                "delivery_slice": "foundation",
                "lifecycle_status": "draft",
                "ssot": {
                    "ssot_type": "FEAT",
                    "parent": "EPIC-030",
                    "derived_from": "EPIC-030",
                    "identity_kind": "ssot",
                },
            },
            {
                "feat_id": "FEAT-018-002",
                "title": "Schema测试器",
                "goal": "建立Schema测试器",
                "user_value": "验证结构一致性",
                "inputs": ["EPIC-030#scope"],
                "processing": ["执行schema校验"],
                "outputs": ["Schema测试器"],
                "acceptance_criteria": ["可检测结构错误"],
                "acceptance_checks": [],
                "dependencies": ["FEAT-018-001"],
                "non_goals": [],
                "priority": "P0",
                "delivery_slice": "foundation",
                "lifecycle_status": "draft",
                "ssot": {
                    "ssot_type": "FEAT",
                    "parent": "EPIC-030",
                    "derived_from": "EPIC-030",
                    "identity_kind": "ssot",
                },
            },
        ],
    }

    normalized, structured = LLMRunner._normalize_prd_writer_feat_payload(
        step,
        "wf-feat-remap",
        business_output,
        {"business_output": business_output},
        instance_data={
            "params": {
                "epic_freeze": {
                    "artifact_id": "EPIC-030",
                    "path": str(epic_freeze_path),
                }
            }
        },
    )

    feat_specs = normalized["feat_specs"]
    assert feat_specs[0]["feat_id"] == "FEAT-159"
    assert feat_specs[1]["feat_id"] == "FEAT-160"
    assert feat_specs[1]["dependencies"] == ["FEAT-159"]
    outputs = structured["ssot_output_contract"]["outputs"]
    assert outputs[0]["properties"]["formal_id"] == "FEAT-159"
    assert outputs[1]["properties"]["formal_id"] == "FEAT-160"
    assert "# Dependencies" in outputs[1]["content"]
    assert "- FEAT-159" in outputs[1]["content"]
