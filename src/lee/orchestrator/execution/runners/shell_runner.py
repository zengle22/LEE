"""
LEE Orchestrator — Shell/Skill Step Runners

包含:
  - SkillRunner: 处理技能步骤 (kind=skill)
  - OrchestratorCLIRunner: 处理 Orchestrator CLI 步骤 (kind=orchestrator_cli)

从 step_runners.py 提取，保持原有逻辑不变。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)
from lee.orchestrator.execution.runners.base import StepRunnerBase, RunnerContext


class SkillRunner(StepRunnerBase):
    """Skill 步骤运行器"""

    def can_handle(self, step_kind: str) -> bool:
        return step_kind == "skill"

    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """
        运行 Skill 步骤

        v1.5: 添加 task_execution 记录
        v1.4: 从 inputs.params 和 config.execution 构建命令
        """
        # 构建输入数据
        raw_input = step.input if step.input else {}
        if isinstance(raw_input, dict):
            params = raw_input.get("params", raw_input)
        elif isinstance(raw_input, list):
            params = {}
            for item in raw_input:
                if isinstance(item, dict):
                    params.update(item)
        else:
            params = {}

        execution_config = step.config.get("execution", {}) if step.config else {}
        input_data = {**params, **execution_config}

        demo_mode = self._demo_mode_enabled()
        used_fallback_command = False

        # 创建 task_execution 记录
        execution_id = uuid.uuid4().hex
        execution = TaskExecution(
            id=execution_id,
            workflow_id=workflow_id,
            step_name=step.id,
            executor_type=step.executor_type or "shell",
            input_data=input_data,
            status=TaskExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
        await ctx.store.create_task_execution(execution)

        try:
            # 根据配置构建命令
            if "commands" in input_data:
                # 多命令执行
                results = []
                for env, command in input_data["commands"].items():
                    command_input = {
                        "command": command,
                        "timeout": input_data.get("timeout", 600),
                    }
                    result = await ctx.executor_factory.create("shell").execute(command_input)
                    results.append(result)

                combined_output = "\n".join([
                    f"=== {env} ===\n{r.get('stdout', '')}" for r in results
                ])
                output = {"stdout": combined_output, "status": "completed"}
            else:
                # 单命令执行
                if "command" not in input_data:
                    input_data["command"] = "true"
                    used_fallback_command = True
                executor = ctx.executor_factory.create(step.executor_type or "shell")
                output = await executor.execute(input_data)

            # Demo/兜底模式：确保输出产物存在
            if demo_mode or used_fallback_command:
                self._ensure_output_artifacts(step.outputs, ctx.project_root)

            # Verifiers (if configured)
            verifier_results = await self._run_verifiers(ctx, workflow_id, step)
            if verifier_results is not None and not self._verifiers_passed(ctx, verifier_results):
                await ctx.state_machine.fail_step(workflow_id, step.id, "Verifier failed")
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="Verifier failed",
                    output={"verifiers": [r.__dict__ for r in verifier_results]},
                )

            # 完成步骤
            result = await ctx.state_machine.complete_step(
                workflow_id, step.id, output
            )

            # 收集证据（基于 outputs 规格）
            evidence_paths = self._resolve_output_paths(step.outputs, ctx.project_root)
            if evidence_paths:
                await self._collect_evidence(ctx, workflow_id, step.id, evidence_paths)

            await ctx.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.COMPLETED,
                output_data=output,
                completed_at=datetime.now()
            )

            return result

        except Exception as e:
            await ctx.state_machine.fail_step(workflow_id, step.id, str(e))
            await ctx.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.FAILED,
                error_message=str(e),
                completed_at=datetime.now()
            )
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Unexpected error: {e}",
            )


class OrchestratorCLIRunner(StepRunnerBase):
    """Orchestrator CLI 步骤运行器"""

    def can_handle(self, step_kind: str) -> bool:
        return step_kind == "orchestrator_cli"

    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """
        运行 Orchestrator CLI 步骤

        由 Orchestrator 直接执行，AI 无法干预。
        用于环境探测、证据收集等安全敏感操作。
        """
        from lee.orchestrator.tools.check_env import run_check_env

        # 获取工作流上下文
        instance = await ctx.store.get_workflow(workflow_id)
        workflow_context = {
            "workflow_id": workflow_id,
            "data": instance.data if instance else {},
        }

        step_config = step.config or {}
        run_command = getattr(step, "run", None) or step_config.get("run", "")

        try:
            if run_command == "check_env":
                # 环境检查
                checks = []
                inputs = step.input or []
                for inp in inputs:
                    if isinstance(inp, dict) and "checks" in inp:
                        checks = inp["checks"]
                        break

                run_id = instance.data.get("run_id", "RUN-UNKNOWN") if instance else "RUN-UNKNOWN"
                output_path = str(Path(ctx.project_root or ".") / f".workflow/env-check/{run_id}-{step.id}.json")

                result = run_check_env(checks, output_path)

                output_data = {
                    "all_passed": result.all_passed,
                    "failures": result.failures,
                    "output_path": output_path,
                    "source": "orchestrator",
                }

                step_result = await ctx.state_machine.complete_step(
                    workflow_id, step.id, output_data
                )

                await self._collect_evidence(ctx, workflow_id, step.id, [output_path])

                if not result.all_passed:
                    step_result.message = f"Environment check failed: {', '.join(result.failures)}"

                return step_result

            else:
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Unknown orchestrator CLI command: {run_command}",
                )

        except Exception as e:
            await ctx.state_machine.fail_step(workflow_id, step.id, str(e))
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Orchestrator CLI execution failed: {e}",
            )
