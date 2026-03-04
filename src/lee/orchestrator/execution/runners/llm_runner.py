"""
LEE Orchestrator — LLM Step Runners

包含:
  - LLMRunner: 处理 agent 步骤 (kind=agent)
  - ClaudeCodeRunner: 处理 claude_code 步骤 (kind=claude_code)

从 step_runners.py 提取，保持原有逻辑不变。
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)
from lee.orchestrator.execution.retry import AsyncRetryExecutor, DEFAULT_RETRY_POLICY
from lee.orchestrator.execution.runners.base import StepRunnerBase, RunnerContext
from lee.orchestrator.execution.llm_executor import LLMExecutor as RealLLMExecutor


class LLMRunner(StepRunnerBase):
    """Agent (LLM) 步骤运行器 - 使用智谱 GLM 模型"""

    def can_handle(self, step_kind: str) -> bool:
        return step_kind in ("agent", "llm")

    def __init__(self, profile: str = "qwen", config_path: str = None,
                 fallback_providers: list = None,
                 **kwargs):
        self.profile = profile
        self.config_path = config_path
        self.fallback_providers = fallback_providers

        self._executor = RealLLMExecutor(
            profile=profile,
            config_path=config_path,
            fallback_providers=fallback_providers
        )

    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """
        运行 Agent 步骤

        v1.5: 添加 task_execution 记录
        v1.4: 从 agent spec 加载 prompt，执行后处理输出文件
        """
        # 获取工作流上下文
        instance = await ctx.store.get_workflow(workflow_id)
        workflow_context = {
            "workflow_id": workflow_id,
            "project_name": instance.data.get("project_name", "ai-marathon-coach"),
            "data": instance.data,
        }

        # v3.1: 注入已发现的契约路径到工作流上下文
        try:
            contract_inputs = ctx.contract_discovery.get_workflow_inputs(
                instance.template_id
            )
            if contract_inputs:
                workflow_context["contract_inputs"] = contract_inputs
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(
                f"Contract discovery failed for template {instance.template_id}: {e}"
            )
            pass  # 契约发现失败不阻塞执行

        # 1. 构建 Agent 执行上下文（包含 prompt）
        agent_ctx = await ctx.agent_context_builder.build(step, workflow_context)

        # v3.1: ToolGuard - 签发步骤令牌
        step_token = None
        try:
            default_perms = ["read", "write"]
            if step.executor_type == "shell":
                default_perms = ["read", "write", "execute"]
            step_token = ctx.token_manager.issue_token(
                run_id=instance.data.get("run_id", workflow_id),
                step_id=step.id,
                agent_id=step.agent_id or "",
                permissions=default_perms,
            )
        except Exception:
            pass  # token 签发失败不阻塞执行

        # 2. 解析 executor_type：CLI 参数优先级最高
        executor_type = instance.data.get("executor_override") or step.executor_type or "llm"

        # 3. 调用 LLM Executor
        # 优先使用环境变量，否则从配置文件读取 default_profile，最后兜底为 huawei_deepseek
        default_profile = ctx.llm_config_loader.get_default_profile() if hasattr(ctx, 'llm_config_loader') else "huawei_deepseek"
        executor = ctx.executor_factory.create(
            executor_type,
            profile=os.getenv("LLM_PROFILE", default_profile),
            agent_id=step.agent_id or ""
        )

        input_data = {
            "system_message": agent_ctx.system_prompt,
            "prompt": agent_ctx.user_prompt,
            "temperature": agent_ctx.temperature,
            "max_tokens": agent_ctx.max_tokens,
        }
        if step_token:
            input_data["token_context"] = ctx.token_manager.encode_token_for_context(step_token)

        # 创建 task_execution 记录
        execution_id = uuid.uuid4().hex
        execution = TaskExecution(
            id=execution_id,
            workflow_id=workflow_id,
            step_name=step.id,
            executor_type=executor_type,
            input_data=input_data,
            status=TaskExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
        await ctx.store.create_task_execution(execution)

        # P0-5: 记录步骤执行开始日志
        import logging
        logging.info(f"[LLMRunner] Starting execution for step {step.id} (workflow={workflow_id}, execution={execution_id})")

        try:
            # v3.5: 步骤级超时保护
            import asyncio
            STEP_TIMEOUT = int(os.getenv("LEE_STEP_TIMEOUT_SECONDS", "300"))  # 5分钟

            # v3.4: AsyncRetryExecutor 包裹 LLM 调用
            retry_executor = AsyncRetryExecutor(policy=DEFAULT_RETRY_POLICY)

            try:
                retry_result = await asyncio.wait_for(
                    retry_executor.execute(executor.execute, input_data),
                    timeout=STEP_TIMEOUT
                )
            except asyncio.TimeoutError:
                error_msg = f"Step execution timeout after {STEP_TIMEOUT}s"
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message=error_msg,
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=error_msg,
                )

            if not retry_result.success:
                error_msg = retry_result.final_error or "LLM call failed after retries"
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message=f"Retry exhausted ({retry_result.total_attempts} attempts): {error_msg}",
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"LLM execution failed after {retry_result.total_attempts} attempts: {error_msg}",
                )

            llm_output = retry_result.result

            # 检查 LLM 调用是否成功
            if llm_output.get("status") == "failed":
                error_msg = llm_output.get("error", "Unknown error")
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
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
                await ctx.state_machine.fail_step(workflow_id, step.id, "LLM returned empty response")
                await ctx.store.update_task_execution(
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
                    written_files = await ctx.file_output_handler.handle(
                        generated_text,
                        step.outputs,
                        workflow_context
                    )
                except Exception as e:
                    print(f"[FileOutputHandler] Warning: {e}")

            # v1.0: SSOT 集成 - 注册写入的文件为产出物
            if written_files:
                await self._collect_evidence(ctx, workflow_id, step.id, written_files)
                await self._register_artifacts(ctx, workflow_id, step.id, written_files, generated_text)

            # 4. Verifiers (if configured)
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

            # v3.4: 输出 Contract Schema 校验
            validation_result = self._validate_step_output(step, generated_text)
            if validation_result and not validation_result.passed:
                strict = (step.config or {}).get("strict_output_validation", False)
                if strict:
                    error_msg = f"Output schema validation failed: {validation_result.errors[0].message if validation_result.errors else 'unknown'}"
                    await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                    return StepResult(
                        status="failed",
                        step_id=step.id,
                        workflow_id=workflow_id,
                        message=error_msg,
                    )
                else:
                    print(f"[OutputValidation] Warning: Step {step.id} output schema validation failed (soft mode)")

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

            result = await ctx.state_machine.complete_step(
                workflow_id, step.id, output_data,
                step_outputs=step.outputs if hasattr(step, 'outputs') else None
            )

            # P0-1: 确保 task_execution 状态更新（BUG-2026-0038）
            # 使用 try-except 确保即使 update 失败也不会丢失步骤完成状态
            try:
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.COMPLETED,
                    output_data=output_data,
                    completed_at=datetime.now()
                )
                # P0-5: 记录 task_execution 更新日志
                import logging
                logging.info(f"[LLMRunner] Updated task_execution {execution_id} to COMPLETED for step {step.id}")
            except Exception as update_error:
                # 记录错误但不抛出，因为步骤已经完成
                logging.error(f"[LLMRunner] Failed to update task_execution {execution_id}: {update_error}")

            ctx.event_log.log_step_completed(
                step_id=step.id,
                agent_id=step.agent_id or "",
                outputs=written_files,
                outputs_hash=ctx.event_log._compute_hash(output_data),
            )

            if written_files:
                result.message = f"Step {step.id} completed. Files written: {', '.join(written_files)}"
            else:
                result.message = f"Step {step.id} completed. No files written (outputs may be empty)"

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
        finally:
            if step_token:
                try:
                    ctx.token_manager.revoke_token(step_token.token_id, reason="step_completed")
                except Exception:
                    pass

    async def _register_artifacts(
        self,
        ctx: RunnerContext,
        workflow_id: str,
        step_id: str,
        written_files: List[str],
        llm_output: str,
    ) -> None:
        """
        v1.0: 注册写入的文件为产出物 (SSOT 集成)

        Args:
            ctx: RunnerContext
            workflow_id: Workflow ID
            step_id: Step ID
            written_files: 已写入的文件路径列表
            llm_output: LLM 原始输出 (用于记录 Context Bundle)
        """
        try:
            from lee.orchestrator.execution.artifacts import (
                create_artifact_handler,
                ContextBuilder,
                ArtifactManager,
            )

            # 获取 run_id 和部门信息
            instance = await ctx.store.get_workflow(workflow_id)
            if not instance:
                return

            run_id = instance.data.get("run_id")
            if not run_id:
                return

            department = instance.data.get("department")
            template_id = instance.template_id or ""

            # 创建产出物处理器
            handler = create_artifact_handler(
                run_id=run_id,
                workflow_id=workflow_id,
                department=department,
                project_root=Path(ctx.file_output_handler.project_root),
            )

            # 注册写入的文件
            handler.register_files_from_output(written_files)

            # v1.0: 记录 Context Bundle (简化版 v0.9)
            # 仅在配置启用时记录
            if getattr(ctx, "enable_context_bundle", True):
                try:
                    manager = ArtifactManager()
                    context_builder = ContextBuilder(manager)

                    # 构建 prompt 快照 (system + user)
                    # 注意：这里只能使用 llm_output，因为 system/user prompt 在 agent_ctx 中
                    # 简化版只记录最终输出
                    context_builder.record_llm_call(
                        run_id=run_id,
                        step_id=step_id,
                        prompt_text=f"[Step Output] {step_id}\n\n{llm_output[:10000]}",  # 限制大小
                        department=department,
                        workflow_id=workflow_id,
                    )
                except Exception as bundle_error:
                    # Context Bundle 记录失败不阻塞主流程
                    import logging
                    logging.getLogger(__name__).debug(
                        f"Failed to record Context Bundle for step {step_id}: {bundle_error}"
                    )

        except Exception as e:
            # 产出物注册失败不阻塞主流程 (warning 模式)
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to register artifacts for step {step_id}: {e}"
            )


class ClaudeCodeRunner(StepRunnerBase):
    """Claude Code 步骤运行器"""

    @staticmethod
    def _get_success_criteria(step) -> Dict[str, Any]:
        config = step.config or {}
        criteria = config.get("success_criteria")
        return criteria if isinstance(criteria, dict) else {}

    @staticmethod
    def _extract_commands_run(output: Dict[str, Any]) -> List[str]:
        commands = output.get("commands_run", [])
        if not isinstance(commands, list):
            return []
        result: List[str] = []
        for item in commands:
            if isinstance(item, dict):
                cmd = item.get("cmd") or item.get("command")
                if cmd:
                    result.append(str(cmd))
            elif isinstance(item, str):
                result.append(item)
        return result

    @staticmethod
    def _git_head(workspace: str) -> Optional[str]:
        try:
            proc = subprocess.run(
                ["git", "-C", workspace, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                return None
            value = (proc.stdout or "").strip()
            return value or None
        except Exception:
            return None

    @staticmethod
    def _check_outputs_completed(step, workspace: str, project_root: Optional[str] = None) -> bool:
        """
        智能完成检测 (BUG-2026-0061)

        检测 step.outputs 中定义的文件是否已生成。
        如果所有必需文件都已存在，认为任务已完成，即使达到迭代上限也返回成功。

        Args:
            step: 步骤对象
            workspace: 工作目录
            project_root: 项目根目录

        Returns:
            bool: 所有必需输出文件是否都已存在
        """
        outputs = getattr(step, 'outputs', None)
        if not outputs:
            return False

        base_path = Path(workspace) if workspace else Path(project_root or ".")

        for out in outputs:
            # 只检查文件类型输出，忽略目录
            path = getattr(out, 'path', None)
            if not path:
                continue
            out_type = getattr(out, 'type', None) or ("dir" if path.endswith("/") else "file")
            if out_type == "dir":
                continue

            target = Path(path)
            if not target.is_absolute():
                target = base_path / target

            if not target.exists():
                return False

        return True

    @classmethod
    def _validate_success_criteria(
        cls,
        output: Dict[str, Any],
        criteria: Dict[str, Any],
        workspace: str,
        head_before: Optional[str],
    ) -> Optional[str]:
        required_commands = criteria.get("require_commands") or criteria.get("required_commands") or []
        if isinstance(required_commands, str):
            required_commands = [required_commands]
        if not isinstance(required_commands, list):
            required_commands = []

        commands_run = cls._extract_commands_run(output)
        lowered = [cmd.lower() for cmd in commands_run]

        missing: List[str] = []
        for expected in required_commands:
            expected_text = str(expected).strip().lower()
            if not expected_text:
                continue
            if not any(expected_text in cmd for cmd in lowered):
                missing.append(str(expected))
        if missing:
            return f"Missing required command(s): {', '.join(missing)}"

        if bool(criteria.get("require_new_commit", False)):
            head_after = cls._git_head(workspace)
            if not head_before or not head_after:
                return "Unable to verify git commit creation (HEAD unavailable)"
            if head_before == head_after:
                return f"No new commit detected (HEAD unchanged: {head_after[:8]})"

        return None

    def can_handle(self, step_kind: str) -> bool:
        return step_kind == "claude_code"

    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """
        运行 Claude Code 步骤

        多轮 LLM + 工具调用的闭环执行器，适用于 L3 实现/修复类 step。
        """
        # 获取工作流上下文
        instance = await ctx.store.get_workflow(workflow_id)
        workflow_context = {
            "workflow_id": workflow_id,
            "project_name": instance.data.get("project_name", ""),
            "data": instance.data,
        }

        # 1. 构建 Agent 执行上下文
        agent_ctx = await ctx.agent_context_builder.build(step, workflow_context)

        # 2. ToolGuard - 签发步骤令牌
        step_token = None
        try:
            step_token = ctx.token_manager.issue_token(
                run_id=instance.data.get("run_id", workflow_id),
                step_id=step.id,
                agent_id=step.agent_id or "",
                permissions=["read", "write", "execute"],
            )
        except Exception:
            pass

        # 3. 解析 executor_type：CLI 参数优先级最高
        # 对于 claude_code 步骤，executor_override 可能指定为 "codex"
        executor_type = instance.data.get("executor_override") or "claude_code"

        # 4. 构建 claude_code 输入
        claude_config = step.config.get("claude_code", {}) if step.config else {}
        workspace = ctx.resolve_workdir(step, instance.data.get("run_id", workflow_id))
        success_criteria = self._get_success_criteria(step)
        head_before = None
        if success_criteria.get("require_new_commit"):
            head_before = self._git_head(workspace)

        input_data = {
            "goal": agent_ctx.user_prompt or claude_config.get("goal", ""),
            "workspace": workspace,
            "context_files": claude_config.get("context_files", []),
            "write_scope": claude_config.get("write_scope", []),
            "max_iterations": claude_config.get("max_iterations", 5),
            "timeout_seconds": claude_config.get("timeout_seconds", 3600),
            "timeout_retries": claude_config.get("timeout_retries", 1),
            "retry_backoff_seconds": claude_config.get("retry_backoff_seconds", 5),
            "stop_conditions": claude_config.get("stop_conditions", {}),
            "system_prompt_extra": agent_ctx.system_prompt or "",
        }

        # 仅在显式配置时传 allowed_commands，避免把空列表传给执行器导致 Bash 被禁用。
        configured_allowed_commands = claude_config.get("allowed_commands")
        if isinstance(configured_allowed_commands, list) and configured_allowed_commands:
            input_data["allowed_commands"] = configured_allowed_commands
        if "setting_sources" in claude_config:
            input_data["setting_sources"] = claude_config.get("setting_sources", "")
        if "strict_mcp_config" in claude_config:
            input_data["strict_mcp_config"] = bool(claude_config.get("strict_mcp_config"))
        if claude_config.get("mcp_config_path"):
            input_data["mcp_config_path"] = claude_config.get("mcp_config_path")
        if claude_config.get("model"):
            input_data["model"] = claude_config.get("model")
        if "silence_timeout_seconds" in claude_config:
            input_data["silence_timeout_seconds"] = claude_config.get(
                "silence_timeout_seconds"
            )
        if "silence_grace_seconds" in claude_config:
            input_data["silence_grace_seconds"] = claude_config.get(
                "silence_grace_seconds"
            )
        if "max_bash_calls" in claude_config:
            input_data["max_bash_calls"] = claude_config.get("max_bash_calls")
        if "resume_on_retry" in claude_config:
            input_data["resume_on_retry"] = bool(claude_config.get("resume_on_retry"))

        if step_token:
            input_data["token_context"] = ctx.token_manager.encode_token_for_context(step_token)

        # Evidence 目录
        run_id = instance.data.get("run_id", workflow_id)
        evidence_base = str(
            Path(workspace) / ".workflow" / "claude-code" / f"{run_id}-{step.id}"
        )
        input_data["evidence_base"] = evidence_base

        # 5. 创建 task_execution 记录
        execution_id = uuid.uuid4().hex
        execution = TaskExecution(
            id=execution_id,
            workflow_id=workflow_id,
            step_name=step.id,
            executor_type=executor_type,
            input_data={k: v for k, v in input_data.items() if k != "token_context"},
            status=TaskExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
        await ctx.store.create_task_execution(execution)

        # P0-5: 记录步骤执行开始日志
        import logging
        logging.info(f"[ClaudeCodeRunner] Starting execution for step {step.id} (workflow={workflow_id}, execution={execution_id})")

        try:
            # 6. v3.4: AsyncRetryExecutor 包裹 Claude Code/Codex 调用
            executor = ctx.executor_factory.create(executor_type)
            retry_executor = AsyncRetryExecutor(policy=DEFAULT_RETRY_POLICY)
            retry_result = await retry_executor.execute(executor.execute, input_data)

            if not retry_result.success:
                error_msg = retry_result.final_error or "Claude Code call failed after retries"
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message=f"Retry exhausted ({retry_result.total_attempts} attempts): {error_msg}",
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Claude Code failed after {retry_result.total_attempts} attempts: {error_msg}",
                )

            output = retry_result.result
            status = output.get("status", "fail")

            # 6. 治理 Gate：diff 过大检查
            diff_summary = output.get("diff_summary", {})
            max_diff_files = claude_config.get("max_diff_files", 1000)
            if diff_summary.get("files_changed", 0) > max_diff_files:
                status = "needs_human"
                output["error"] = (
                    f"Diff too large: {diff_summary['files_changed']} files changed "
                    f"(limit: {max_diff_files})"
                )

            # 7. 处理 needs_human → 暂停工作流
            if status == "needs_human":
                from lee.orchestrator.storage.models import WorkflowStatus

                await ctx.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)
                await ctx.store.update_task_execution(
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
                debug_hint = output.get("debug_log_path") or output.get("conversation_log_path")
                if debug_hint:
                    error_msg = f"{error_msg} (debug: {debug_hint})"
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data=output,
                    error_message=error_msg,
                    completed_at=datetime.now(),
                )
                ctx.event_log.log_step_failed(
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

            criteria_error = self._validate_success_criteria(
                output=output,
                criteria=success_criteria,
                workspace=workspace,
                head_before=head_before,
            )
            if criteria_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, criteria_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data=output,
                    error_message=criteria_error,
                    completed_at=datetime.now(),
                )
                ctx.event_log.log_step_failed(
                    step_id=step.id,
                    agent_id=step.agent_id or "claude_code",
                    error=criteria_error,
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Claude Code success criteria not met: {criteria_error}",
                    output=output,
                )

            # 9. 收集证据
            evidence_path = output.get("evidence_bundle_path", "")
            if evidence_path:
                await self._collect_evidence(ctx, workflow_id, step.id, [evidence_path])
            changed = output.get("changed_files", [])
            if changed:
                abs_changed = [
                    str(Path(workspace) / f) if not os.path.isabs(f) else f
                    for f in changed
                ]
                await self._collect_evidence(ctx, workflow_id, step.id, abs_changed)

            # 10. Verifiers
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

            # v3.4: 输出 Contract Schema 校验
            cc_output_text = output.get("raw_output", "") or json.dumps(output)
            cc_validation = self._validate_step_output(step, cc_output_text)
            if cc_validation and not cc_validation.passed:
                strict = (step.config or {}).get("strict_output_validation", False)
                if strict:
                    error_msg = f"Output schema validation failed: {cc_validation.errors[0].message if cc_validation.errors else 'unknown'}"
                    await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                    return StepResult(
                        status="failed",
                        step_id=step.id,
                        workflow_id=workflow_id,
                        message=error_msg,
                    )
                else:
                    print(f"[OutputValidation] Warning: Step {step.id} output schema validation failed (soft mode)")

            # BUG-2026-0061: 智能完成检测
            # 即使状态是 fail，如果是因达到迭代上限但输出文件已完成，仍视为成功
            iterations_used = output.get("iterations_used", 0)
            max_iterations = input_data.get("max_iterations", 5)
            if status == "fail" and iterations_used >= max_iterations:
                # 检测输出文件是否已完成
                if self._check_outputs_completed(step, workspace, ctx.project_root):
                    logging.info(
                        f"[ClaudeCodeRunner] Smart completion: step {step.id} reached max iterations "
                        f"({iterations_used}/{max_iterations}) but outputs are complete, treating as success"
                    )
                    status = "success"
                    output["status"] = "success"
                    output["smart_completion"] = True

            # 11. 完成步骤
            result = await ctx.state_machine.complete_step(
                workflow_id, step.id, output,
                step_outputs=step.outputs if hasattr(step, 'outputs') else None
            )

            # P0-1: 确保 task_execution 状态更新（BUG-2026-0038）
            # 使用重试机制确保状态更新成功
            updated = await self._update_task_execution_with_retry(
                ctx,
                execution_id,
                TaskExecutionStatus.COMPLETED,
                max_retries=3,
                output_data=output,
                completed_at=datetime.now(),
            )
            if updated:
                logging.info(f"[ClaudeCodeRunner] Updated task_execution {execution_id} to COMPLETED for step {step.id}")
            else:
                logging.error(f"[ClaudeCodeRunner] Failed to update task_execution {execution_id} after retries")

            changed = output.get("changed_files", [])
            ctx.event_log.log_step_completed(
                step_id=step.id,
                agent_id=step.agent_id or "claude_code",
                outputs=changed,
                outputs_hash=ctx.event_log._compute_hash(output),
            )

            result.message = (
                f"Step {step.id} completed via Claude Code. "
                f"Files changed: {diff_summary.get('files_changed', 0)}, "
                f"Iterations: {output.get('iterations_used', '?')}"
            )
            return result

        except Exception as e:
            await ctx.state_machine.fail_step(workflow_id, step.id, str(e))
            # 使用重试机制更新失败状态 (BUG-2026-0038)
            await self._update_task_execution_with_retry(
                ctx,
                execution_id,
                TaskExecutionStatus.FAILED,
                max_retries=3,
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
                    ctx.token_manager.revoke_token(step_token.token_id, reason="step_completed")
                except Exception:
                    pass
