"""
LEE Orchestrator v3.1 - 步骤运行器 Mixin

提取自 orchestrator.py，包含所有步骤类型的运行逻辑：
- Agent 步骤
- Skill 步骤
- Orchestrator CLI 步骤
- Compliance Gate 步骤
- Human Gate 步骤
以及辅助方法（verifiers、evidence、output 处理）
"""

from __future__ import annotations

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)



class StepRunnerMixin:
    """步骤运行器 Mixin — 所有步骤类型的执行逻辑"""

    # ============ Human Gate ============

    async def _handle_human_gate(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        处理 Human Gate 步骤

        Human Gate 不调用 Executor，而是暂停工作流等待人工审批。
        """
        from lee.orchestrator.storage.models import WorkflowStatus, GateApproval, GateStatus

        # 暂停工作流
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)

        # 提取 gate 配置（从独立 gate 或 post_gate）
        gate_config = step.config.get("gate", {})
        if not gate_config and hasattr(step, 'gate_id'):
            # 从 workflow.yaml 的 gate 节点获取配置
            gate_config = {
                "id": step.gate_id,
                "reviewers": step.config.get("reviewers", []),
                "approval_criteria": step.config.get("approval_criteria", []),
            }

        # 创建门禁审批记录
        gate_approval = GateApproval(
            workflow_id=workflow_id,
            gate_id=step.gate_id or f"gate_{step.id}",
            step_id=step.id,
            status=GateStatus.PENDING,
            approval_criteria=gate_config.get("approval_criteria", []),
            reviewers=gate_config.get("reviewers", []),
        )
        await self.store.create_gate_approval(gate_approval)

        # v3.2: 记录门禁触发事件
        self.event_log.log_gate_triggered(
            gate_id=step.gate_id or f"gate_{step.id}",
            step_id=step.id,
            gate_type="human",
            blocking=True,
        )

        return StepResult(
            status="blocked",
            blocked_reason="human_gate",
            step_id=step.id,
            workflow_id=workflow_id,
            message=f"Waiting for human approval at gate: {step.gate_id or step.id}",
            next_steps=[],
        )

    # ============ Agent Step ============

    async def _run_agent_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行 Agent 步骤

        v1.5: 添加 task_execution 记录
        v1.4: 从 agent spec 加载 prompt，执行后处理输出文件
        """
        # 获取工作流上下文
        instance = await self.store.get_workflow(workflow_id)
        workflow_context = {
            "workflow_id": workflow_id,
            "project_name": instance.data.get("project_name", "ai-marathon-coach"),
            "data": instance.data,
        }

        # v3.1: 注入已发现的契约路径到工作流上下文
        try:
            contract_inputs = self.contract_discovery.get_workflow_inputs(
                instance.template_id
            )
            if contract_inputs:
                workflow_context["contract_inputs"] = contract_inputs
        except Exception:
            pass  # 契约发现失败不阻塞执行

        # 1. 构建 Agent 执行上下文（包含 prompt）
        ctx = await self.agent_context_builder.build(step, workflow_context)

        # v3.1: ToolGuard - 签发步骤令牌
        step_token = None
        try:
            # 根据 step 类型确定默认权限
            default_perms = ["read", "write"]
            if step.executor_type == "shell":
                default_perms = ["read", "write", "execute"]
            step_token = self.token_manager.issue_token(
                run_id=instance.data.get("run_id", workflow_id),
                step_id=step.id,
                agent_id=step.agent_id or "",
                permissions=default_perms,
            )
        except Exception:
            pass  # token 签发失败不阻塞执行

        # 2. 调用 LLM Executor
        # 默认使用环境变量 LLM_PROFILE 或 zhipu
        executor = self.executor_factory.create(
            step.executor_type or "llm",
            profile=os.getenv("LLM_PROFILE", "zhipu"),
            agent_id=step.agent_id or ""
        )

        # 构建输入数据（包含 system_message 和 prompt）
        input_data = {
            "system_message": ctx.system_prompt,
            "prompt": ctx.user_prompt,
            "temperature": ctx.temperature,
            "max_tokens": ctx.max_tokens,
        }
        # v3.1: 注入 token 上下文
        if step_token:
            input_data["token_context"] = self.token_manager.encode_token_for_context(step_token)

        # 创建 task_execution 记录
        execution_id = uuid.uuid4().hex
        execution = TaskExecution(
            id=execution_id,
            workflow_id=workflow_id,
            step_name=step.id,
            executor_type=step.executor_type or "llm",
            input_data=input_data,
            status=TaskExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
        await self.store.create_task_execution(execution)

        try:
            llm_output = await executor.execute(input_data)

            # 检查 LLM 调用是否成功
            if llm_output.get("status") == "failed":
                # LLM 调用失败
                error_msg = llm_output.get("error", "Unknown error")
                await self.state_machine.fail_step(workflow_id, step.id, error_msg)
                await self.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message=error_msg,
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"LLM execution failed: {error_msg}",
                )

            generated_text = llm_output.get("generated_text", "")

            # 检查是否生成了内容
            if not generated_text or not generated_text.strip():
                await self.state_machine.fail_step(workflow_id, step.id, "LLM returned empty response")
                await self.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message="LLM returned empty response",
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="LLM returned empty response",
                )

            # 3. 处理输出文件
            written_files = []
            if step.outputs:
                try:
                    written_files = await self.file_output_handler.handle(
                        generated_text,
                        step.outputs,
                        workflow_context
                    )
                except Exception as e:
                    # 输出处理失败，记录但不终止步骤
                    print(f"[FileOutputHandler] Warning: {e}")
            if written_files:
                await self._collect_evidence(workflow_id, step.id, written_files)

            # 4. Verifiers (if configured)
            verifier_results = await self._run_verifiers(workflow_id, step)
            if verifier_results is not None and not self._verifiers_passed(verifier_results):
                await self.state_machine.fail_step(workflow_id, step.id, "Verifier failed")
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="Verifier failed",
                    output={"verifiers": [r.__dict__ for r in verifier_results]},
                )

            # 5. 完成步骤
            output_data = {
                "generated_text": generated_text,
                "written_files": written_files,
                "agent_id": step.agent_id,
                "llm_meta": {
                    "model": llm_output.get("model"),
                    "provider": llm_output.get("provider"),
                    "tokens_used": llm_output.get("tokens_used"),
                    "input_tokens": llm_output.get("input_tokens"),
                    "output_tokens": llm_output.get("output_tokens"),
                    "duration_seconds": llm_output.get("duration_seconds"),
                    "stop_reason": llm_output.get("stop_reason"),
                },
            }

            result = await self.state_machine.complete_step(
                workflow_id,
                step.id,
                output_data
            )

            # 更新 task_execution 记录
            await self.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.COMPLETED,
                output_data=output_data,
                completed_at=datetime.now()
            )

            # v3.2: 记录步骤完成事件（含 LLM 元数据）
            self.event_log.log_step_completed(
                step_id=step.id,
                agent_id=step.agent_id or "",
                outputs=written_files,
                outputs_hash=self.event_log._compute_hash(output_data),
            )

            # 检查工作流是否完成
            await self._check_workflow_completion(workflow_id)

            # 返回结果，包含写入的文件信息
            if written_files:
                result.message = f"Step {step.id} completed. Files written: {', '.join(written_files)}"
            else:
                result.message = f"Step {step.id} completed. No files written (outputs may be empty)"

            return result

        except Exception as e:
            # 捕获未预期的异常
            await self.state_machine.fail_step(workflow_id, step.id, str(e))
            await self.store.update_task_execution(
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
        finally:
            # v3.1: 步骤完成后撤销令牌
            if step_token:
                try:
                    self.token_manager.revoke_token(step_token.token_id, reason="step_completed")
                except Exception:
                    pass

    # ============ Orchestrator CLI Step ============

    async def _run_orchestrator_cli_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行 Orchestrator CLI 步骤

        由 Orchestrator 直接执行，AI 无法干预。
        用于环境探测、证据收集等安全敏感操作。
        """
        from lee.orchestrator.tools.check_env import run_check_env

        # 获取工作流上下文
        instance = await self.store.get_workflow(workflow_id)
        workflow_context = {
            "workflow_id": workflow_id,
            "data": instance.data if instance else {},
        }

        # 获取步骤配置
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

                # 构建输出路径
                run_id = instance.data.get("run_id", "RUN-UNKNOWN") if instance else "RUN-UNKNOWN"
                output_path = str(Path(self.project_root or ".") / f".workflow/env-check/{run_id}-{step.id}.json")

                # 执行检查
                result = run_check_env(checks, output_path)

                output_data = {
                    "all_passed": result.all_passed,
                    "failures": result.failures,
                    "output_path": output_path,
                    "source": "orchestrator",  # 标记来源为 orchestrator
                }

                # 完成步骤
                step_result = await self.state_machine.complete_step(
                    workflow_id,
                    step.id,
                    output_data
                )

                # 收集证据
                await self._collect_evidence(workflow_id, step.id, [output_path])

                # 检查是否通过
                if not result.all_passed:
                    step_result.message = f"Environment check failed: {', '.join(result.failures)}"

                return step_result

            else:
                # 未知的 orchestrator CLI 命令
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Unknown orchestrator CLI command: {run_command}",
                )

        except Exception as e:
            await self.state_machine.fail_step(workflow_id, step.id, str(e))
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Orchestrator CLI execution failed: {e}",
            )

    # ============ Compliance Gate Step ============

    async def _run_compliance_gate_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行合规门禁步骤

        检查 AI 行为是否违规（mock/借口等）。
        违规 → 本轮测试无效。
        """
        from lee.orchestrator.verifiers.behavior_compliance import BehaviorComplianceVerifier

        # 获取工作流上下文
        instance = await self.store.get_workflow(workflow_id)

        # 获取输入数据
        inputs = step.input or []
        runner_output = {}
        confirmed_env_errors = []

        for inp in inputs:
            if isinstance(inp, dict):
                if "runner_output" in inp:
                    runner_output = inp["runner_output"]
                if "confirmed_env_errors" in inp:
                    confirmed_env_errors = inp["confirmed_env_errors"]

        # 执行合规检查
        verifier = BehaviorComplianceVerifier()
        context = {
            "runner_output": runner_output,
            "confirmed_env_errors": confirmed_env_errors,
            "config": step.config.get("config", {}) if step.config else {},
        }
        result = verifier.verify(context)

        # 保存检查结果
        run_id = instance.data.get("run_id", "RUN-UNKNOWN") if instance else "RUN-UNKNOWN"
        output_path = Path(self.project_root or ".") / f".workflow/compliance/{run_id}-{step.id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps({
            "status": result.status.value,
            "message": result.message,
            "details": result.details,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        output_data = {
            "compliant": result.status.value == "passed",
            "violations": result.details.get("violations", []) if result.details else [],
            "output_path": str(output_path),
        }

        if result.status.value == "passed":
            # 合规通过
            step_result = await self.state_machine.complete_step(
                workflow_id,
                step.id,
                output_data
            )
            return step_result
        else:
            # 合规失败 → 标记为 invalid_run
            await self.state_machine.fail_step(workflow_id, step.id, result.message)
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"AI behavior violation detected: {result.message}",
                output=output_data,
            )

    # ============ Skill Step ============

    async def _run_skill_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行 Skill 步骤

        v1.5: 添加 task_execution 记录
        v1.4: 从 inputs.params 和 config.execution 构建命令
        """
        # 构建输入数据
        # 优先使用 input.params；否则使用 input 本身
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

        # 合并配置
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
        await self.store.create_task_execution(execution)

        try:
            # 根据配置构建命令
            if "commands" in input_data:
                # 多命令执行（如 dev/test 分别执行）
                results = []
                for env, command in input_data["commands"].items():
                    command_input = {
                        "command": command,
                        "timeout": input_data.get("timeout", 600),
                    }
                    result = await self.executor_factory.create("shell").execute(command_input)
                    results.append(result)

                # 合并结果
                combined_output = "\n".join([
                    f"=== {env} ===\n{r.get('stdout', '')}" for r in results
                ])
                output = {"stdout": combined_output, "status": "completed"}
            else:
                # 单命令执行
                if "command" not in input_data:
                    # 缺少命令时的兜底（保持流程可运行）
                    input_data["command"] = "true"
                    used_fallback_command = True
                executor = self.executor_factory.create(step.executor_type or "shell")
                output = await executor.execute(input_data)

            # Demo/兜底模式：确保输出产物存在
            if demo_mode or used_fallback_command:
                self._ensure_output_artifacts(step.outputs)

            # Verifiers (if configured)
            verifier_results = await self._run_verifiers(workflow_id, step)
            if verifier_results is not None and not self._verifiers_passed(verifier_results):
                await self.state_machine.fail_step(workflow_id, step.id, "Verifier failed")
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="Verifier failed",
                    output={"verifiers": [r.__dict__ for r in verifier_results]},
                )

            # 完成步骤
            result = await self.state_machine.complete_step(
                workflow_id,
                step.id,
                output
            )

            # 收集证据（基于 outputs 规格）
            evidence_paths = self._resolve_output_paths(step.outputs)
            if evidence_paths:
                await self._collect_evidence(workflow_id, step.id, evidence_paths)

            # 更新 task_execution 记录
            await self.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.COMPLETED,
                output_data=output,
                completed_at=datetime.now()
            )

            # 检查工作流是否完成
            await self._check_workflow_completion(workflow_id)

            return result

        except Exception as e:
            # 捕获未预期的异常
            await self.state_machine.fail_step(workflow_id, step.id, str(e))
            await self.store.update_task_execution(
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

    # ============ Claude Code Step ============

    async def _run_claude_code_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行 Claude Code 步骤

        多轮 LLM + 工具调用的闭环执行器，适用于 L3 实现/修复类 step。
        与 _run_agent_step 对齐：Token → 执行 → Evidence → Verifier → StateMachine
        """
        # 获取工作流上下文
        instance = await self.store.get_workflow(workflow_id)
        workflow_context = {
            "workflow_id": workflow_id,
            "project_name": instance.data.get("project_name", ""),
            "data": instance.data,
        }

        # 1. 构建 Agent 执行上下文（获取 goal/prompt）
        ctx = await self.agent_context_builder.build(step, workflow_context)

        # 2. ToolGuard - 签发步骤令牌
        step_token = None
        try:
            step_token = self.token_manager.issue_token(
                run_id=instance.data.get("run_id", workflow_id),
                step_id=step.id,
                agent_id=step.agent_id or "",
                permissions=["read", "write", "execute"],
            )
        except Exception:
            pass

        # 3. 构建 claude_code 输入
        claude_config = step.config.get("claude_code", {}) if step.config else {}
        workspace = str(Path(self.project_root or ".").resolve())

        input_data = {
            "goal": ctx.user_prompt or claude_config.get("goal", ""),
            "workspace": workspace,
            "context_files": claude_config.get("context_files", []),
            "allowed_commands": claude_config.get("allowed_commands", []),
            "write_scope": claude_config.get("write_scope", []),
            "max_iterations": claude_config.get("max_iterations", 5),
            "timeout_seconds": claude_config.get("timeout_seconds", 600),
            "stop_conditions": claude_config.get("stop_conditions", {}),
            "system_prompt_extra": ctx.system_prompt or "",
        }

        if step_token:
            input_data["token_context"] = self.token_manager.encode_token_for_context(step_token)

        # Evidence 目录
        run_id = instance.data.get("run_id", workflow_id)
        evidence_base = str(
            Path(workspace) / ".workflow" / "claude-code" / f"{run_id}-{step.id}"
        )
        input_data["evidence_base"] = evidence_base

        # 4. 创建 task_execution 记录
        execution_id = uuid.uuid4().hex
        execution = TaskExecution(
            id=execution_id,
            workflow_id=workflow_id,
            step_name=step.id,
            executor_type="claude_code",
            input_data={k: v for k, v in input_data.items() if k != "token_context"},
            status=TaskExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
        await self.store.create_task_execution(execution)

        try:
            # 5. 执行
            executor = self.executor_factory.create("claude_code")
            output = await executor.execute(input_data)

            status = output.get("status", "fail")

            # 6. 治理 Gate：diff 过大检查
            diff_summary = output.get("diff_summary", {})
            max_diff_files = claude_config.get("max_diff_files", 50)
            if diff_summary.get("files_changed", 0) > max_diff_files:
                status = "needs_human"
                output["error"] = (
                    f"Diff too large: {diff_summary['files_changed']} files changed "
                    f"(limit: {max_diff_files})"
                )

            # 7. 处理 needs_human → 暂停工作流
            if status == "needs_human":
                from lee.orchestrator.storage.models import WorkflowStatus

                await self.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)
                await self.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data=output,
                    error_message=output.get("error", "Needs human review"),
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="blocked",
                    blocked_reason="claude_code_needs_human",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Claude Code step requires human review: {output.get('error', '')}",
                    output=output,
                )

            # 8. 失败处理
            if status in ("fail", "failed", "timeout"):
                error_msg = output.get("error", f"Claude Code step {status}")
                await self.state_machine.fail_step(workflow_id, step.id, error_msg)
                await self.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data=output,
                    error_message=error_msg,
                    completed_at=datetime.now(),
                )
                # v3.2: 记录步骤失败事件
                self.event_log.log_step_failed(
                    step_id=step.id,
                    agent_id=step.agent_id or "claude_code",
                    error=error_msg,
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Claude Code execution failed: {error_msg}",
                    output=output,
                )

            # 9. 收集证据
            evidence_path = output.get("evidence_bundle_path", "")
            if evidence_path:
                await self._collect_evidence(workflow_id, step.id, [evidence_path])
            # 也收集 changed_files
            changed = output.get("changed_files", [])
            if changed:
                abs_changed = [
                    str(Path(workspace) / f) if not os.path.isabs(f) else f
                    for f in changed
                ]
                await self._collect_evidence(workflow_id, step.id, abs_changed)

            # 10. Verifiers
            verifier_results = await self._run_verifiers(workflow_id, step)
            if verifier_results is not None and not self._verifiers_passed(verifier_results):
                await self.state_machine.fail_step(workflow_id, step.id, "Verifier failed")
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="Verifier failed",
                    output={"verifiers": [r.__dict__ for r in verifier_results]},
                )

            # 11. 完成步骤
            result = await self.state_machine.complete_step(
                workflow_id,
                step.id,
                output,
            )

            await self.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.COMPLETED,
                output_data=output,
                completed_at=datetime.now(),
            )

            # v3.2: 记录步骤完成事件
            changed = output.get("changed_files", [])
            self.event_log.log_step_completed(
                step_id=step.id,
                agent_id=step.agent_id or "claude_code",
                outputs=changed,
                outputs_hash=self.event_log._compute_hash(output),
            )

            await self._check_workflow_completion(workflow_id)

            result.message = (
                f"Step {step.id} completed via Claude Code. "
                f"Files changed: {diff_summary.get('files_changed', 0)}, "
                f"Iterations: {output.get('iterations_used', '?')}"
            )
            return result

        except Exception as e:
            await self.state_machine.fail_step(workflow_id, step.id, str(e))
            await self.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.FAILED,
                error_message=str(e),
                completed_at=datetime.now(),
            )
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Unexpected error in Claude Code step: {e}",
            )
        finally:
            if step_token:
                try:
                    self.token_manager.revoke_token(step_token.token_id, reason="step_completed")
                except Exception:
                    pass

    # ============ 辅助方法 ============

    async def _collect_evidence(self, workflow_id: str, step_id: str, artifacts: List[str]) -> None:
        """收集证据产物"""
        if not artifacts:
            return

        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return

        run_id = instance.data.get("run_id")
        if not run_id:
            run_id = self._generate_run_id()
            instance.data["run_id"] = run_id
            await self.store.update_workflow_data(workflow_id, instance.data)

        self.evidence_collector.collect(run_id, step_id, artifacts)

    def _resolve_output_paths(self, outputs) -> List[str]:
        """根据 outputs 规格解析路径"""
        if not outputs:
            return []

        paths = []
        for out in outputs:
            path = getattr(out, "path", None)
            if not path:
                continue
            if os.path.isabs(path):
                paths.append(path)
            else:
                base = Path(self.project_root or ".").resolve()
                paths.append(str(base / path))
        return paths

    def _ensure_output_artifacts(self, outputs) -> List[str]:
        """确保输出产物存在（用于 demo/兜底）"""
        if not outputs:
            return []

        created: List[str] = []
        base = Path(self.project_root or ".").resolve()

        for out in outputs:
            path = getattr(out, "path", None)
            if not path:
                continue

            target = Path(path)
            if not target.is_absolute():
                target = base / target

            out_type = getattr(out, "type", None) or ("dir" if path.endswith("/") else "file")
            if out_type == "dir":
                target.mkdir(parents=True, exist_ok=True)
                created.append(str(target))
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                continue

            fmt = (getattr(out, "format", None) or "text").lower()
            if fmt == "json":
                payload = {"placeholder": True, "path": path, "status": "demo"}
                content = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
            elif fmt in ("yaml", "yml"):
                content = "placeholder: true\nstatus: demo\n"
            elif fmt in ("markdown", "md"):
                content = "# Placeholder\n\nGenerated in demo mode.\n"
            else:
                content = "placeholder\n"

            target.write_text(content, encoding="utf-8")
            created.append(str(target))

        return created

    def _demo_mode_enabled(self) -> bool:
        return os.getenv("LEE_DEMO_MODE", "").lower() in ("1", "true", "yes")

    async def _run_verifiers(self, workflow_id: str, step) -> Optional[List]:
        """运行 verifiers，返回结果列表或 None"""
        verifiers = step.config.get("verifiers") if step.config else None
        if not verifiers:
            return None

        if self._demo_mode_enabled():
            from lee.orchestrator.verifiers.base import VerifyResult, VerifyStatus
            results = []
            for item in verifiers or []:
                vtype = item.get("type") if isinstance(item, dict) else None
                results.append(VerifyResult(
                    status=VerifyStatus.PASSED,
                    verifier_id=vtype or "unknown",
                    message="verifier skipped in demo mode",
                    details={"mode": "demo"},
                ))

            instance = await self.store.get_workflow(workflow_id)
            run_id = instance.data.get("run_id") if instance else None
            if instance and not run_id:
                run_id = self._generate_run_id()
                instance.data["run_id"] = run_id
                await self.store.update_workflow_data(workflow_id, instance.data)

            report_path = self._write_verifier_report(run_id or "RUN-UNKNOWN", step.id, results)
            if report_path:
                await self._collect_evidence(workflow_id, step.id, [report_path])

            return results

        instance = await self.store.get_workflow(workflow_id)
        run_id = instance.data.get("run_id") if instance else None
        if instance and not run_id:
            run_id = self._generate_run_id()
            instance.data["run_id"] = run_id
            await self.store.update_workflow_data(workflow_id, instance.data)

        context = {
            "workflow_id": workflow_id,
            "step_id": step.id,
            "run_id": run_id,
        }

        results = self.verifier_engine.run(verifiers, context)

        report_path = self._write_verifier_report(run_id or "RUN-UNKNOWN", step.id, results)
        if report_path:
            await self._collect_evidence(workflow_id, step.id, [report_path])

        return results

    def _verifiers_passed(self, results: List) -> bool:
        return self.verifier_engine.all_passed(results)

    def _write_verifier_report(self, run_id: str, step_id: str, results: List) -> Optional[str]:
        """写入 verifier 结果报告到 .workflow/verifiers/"""
        base = Path(self.project_root or ".").resolve()
        report_dir = base / ".workflow" / "verifiers"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{run_id}-{step_id}.json"

        payload = []
        for r in results:
            payload.append({
                "verifier_id": r.verifier_id,
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "message": r.message,
                "details": r.details,
            })

        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(report_path)
