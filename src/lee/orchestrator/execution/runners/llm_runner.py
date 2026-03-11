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
import re
import subprocess
import uuid
import difflib
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)
from lee.orchestrator.execution.retry import AsyncRetryExecutor, DEFAULT_RETRY_POLICY, RetryPolicy
from lee.orchestrator.execution.runners.base import StepRunnerBase, RunnerContext
from lee.orchestrator.execution.llm_executor import LLMExecutor as RealLLMExecutor


class LLMRunner(StepRunnerBase):
    """Agent (LLM) 步骤运行器 - 使用智谱 GLM 模型"""

    DEFAULT_CLAUDE_CODE_FORBIDDEN_READ_PATHS = [
        "output/",
        "evidence/",
        ".workflow/claude-code/",
    ]
    FEAT_TOPIC_FAMILIES = {
        "governance": [
            "cli",
            "workflow",
            "ssot",
            "gate",
            "freeze",
            "governance",
            "command",
            "approval",
            "review",
            "治理",
            "命令",
            "工作流",
            "物化",
            "放行",
            "审阅",
            "冻结",
            "约束",
        ],
        "auth_sms": [
            "sms",
            "otp",
            "mobile",
            "phone",
            "login",
            "session",
            "验证码",
            "短信",
            "手机号",
            "手机",
            "登录",
            "会话",
            "账户",
            "手机号绑定",
            "手机号解绑",
            "验证码登录",
        ],
    }

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

    def _build_executor_input(
        self,
        *,
        executor_type: str,
        step,
        ctx: RunnerContext,
        instance,
        workflow_id: str,
        agent_ctx,
        step_token: Optional[str],
    ) -> Dict[str, Any]:
        if executor_type in ("codex", "claude_code"):
            code_config = step.config.get("claude_code", {}) if step.config else {}
            workspace = ctx.resolve_workdir(step, instance.data.get("run_id", workflow_id))
            context_files = self._merge_context_files(
                self._collect_authoritative_context_files(step, instance.data),
                code_config.get("context_files", []),
            )
            input_data: Dict[str, Any] = {
                "goal": agent_ctx.user_prompt or code_config.get("goal", ""),
                "workspace": workspace,
                "context_files": context_files,
                "write_scope": code_config.get("write_scope", []),
                "forbidden_read_paths": self._merge_forbidden_read_paths(
                    code_config.get("forbidden_read_paths")
                ),
                "max_iterations": code_config.get("max_iterations", 5),
                "timeout_seconds": code_config.get("timeout_seconds", 3600),
                "timeout_retries": code_config.get("timeout_retries", 1),
                "retry_backoff_seconds": code_config.get("retry_backoff_seconds", 5),
                "stop_conditions": code_config.get("stop_conditions", {}),
                "system_prompt_extra": agent_ctx.system_prompt or "",
            }
            if code_config.get("allowed_commands"):
                input_data["allowed_commands"] = code_config.get("allowed_commands")
            if code_config.get("model"):
                input_data["model"] = code_config.get("model")
            if "silence_timeout_seconds" in code_config:
                input_data["silence_timeout_seconds"] = code_config.get("silence_timeout_seconds")
            if "silence_grace_seconds" in code_config:
                input_data["silence_grace_seconds"] = code_config.get("silence_grace_seconds")
            if "max_bash_calls" in code_config:
                input_data["max_bash_calls"] = code_config.get("max_bash_calls")
            if "resume_on_retry" in code_config:
                input_data["resume_on_retry"] = bool(code_config.get("resume_on_retry"))
        else:
            input_data = {
                "system_message": agent_ctx.system_prompt,
                "prompt": agent_ctx.user_prompt,
                "temperature": agent_ctx.temperature,
                "max_tokens": agent_ctx.max_tokens,
            }

        if step_token:
            input_data["token_context"] = ctx.token_manager.encode_token_for_context(step_token)
        return input_data

    @classmethod
    def _merge_forbidden_read_paths(cls, configured_paths: Any) -> List[str]:
        merged: List[str] = []
        for raw_path in cls.DEFAULT_CLAUDE_CODE_FORBIDDEN_READ_PATHS:
            normalized = str(raw_path).strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
        if isinstance(configured_paths, list):
            for raw_path in configured_paths:
                normalized = str(raw_path).strip()
                if normalized and normalized not in merged:
                    merged.append(normalized)
        return merged

    @staticmethod
    def _merge_context_files(*groups: Any) -> List[str]:
        merged: List[str] = []
        for group in groups:
            if not isinstance(group, list):
                continue
            for raw_path in group:
                normalized = str(raw_path).strip()
                if normalized and normalized not in merged:
                    merged.append(normalized)
        return merged

    @classmethod
    def _collect_authoritative_context_files(cls, step, instance_data: Optional[Dict[str, Any]]) -> List[str]:
        if not step or not isinstance(instance_data, dict):
            return []

        raw_inputs = getattr(step, "inputs", None)
        if not isinstance(raw_inputs, list):
            return []

        params = instance_data.get("params", {}) if isinstance(instance_data.get("params", {}), dict) else {}
        step_outputs = instance_data.get("step_outputs", {}) if isinstance(instance_data.get("step_outputs", {}), dict) else {}
        data = instance_data if isinstance(instance_data, dict) else {}

        collected: List[str] = []
        for item in raw_inputs:
            if not isinstance(item, dict):
                continue
            source = item.get("source")
            if not isinstance(source, str) or not source.strip():
                continue
            value = cls._resolve_authoritative_input_value(
                source=source,
                data=data,
                params=params,
                step_outputs=step_outputs,
            )
            cls._extract_context_file_paths(value, collected)
        return collected

    @classmethod
    def _resolve_authoritative_input_value(
        cls,
        *,
        source: str,
        data: Dict[str, Any],
        params: Dict[str, Any],
        step_outputs: Dict[str, Any],
    ) -> Any:
        candidate_keys = [source]
        if source.endswith("_freeze"):
            candidate_keys.append(f"{source}_ref")
        elif source.endswith("_freeze_ref"):
            candidate_keys.append(source[:-4])

        for key in candidate_keys:
            if key in data:
                return data[key]
            if key in params:
                return params[key]
            if key in step_outputs:
                return step_outputs[key]
        return None

    @classmethod
    def _extract_context_file_paths(cls, value: Any, collected: List[str]) -> None:
        if isinstance(value, dict):
            for key in ("resolved_path", "path"):
                raw_path = value.get(key)
                if isinstance(raw_path, str):
                    normalized = raw_path.strip()
                    if normalized and normalized not in collected:
                        collected.append(normalized)
            for nested in value.values():
                cls._extract_context_file_paths(nested, collected)
            return

        if isinstance(value, list):
            for item in value:
                cls._extract_context_file_paths(item, collected)

    @staticmethod
    def _coerce_output_file_value(raw_text: str) -> Any:
        text = (raw_text or "").strip()
        stripped = StepRunnerBase._strip_code_fence(text)
        if not stripped:
            return ""
        lowered = stripped.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if re.fullmatch(r"-?\d+", stripped):
            try:
                return int(stripped)
            except ValueError:
                pass
        if re.fullmatch(r"-?\d+\.\d+", stripped):
            try:
                return float(stripped)
            except ValueError:
                pass
        return stripped

    @staticmethod
    def _extract_named_output_segment(raw_text: str, output_name: str) -> str:
        text = (raw_text or "").strip()
        if not text or not output_name:
            return text

        lines = text.splitlines()
        start_index: Optional[int] = None
        token = f"`{output_name}`"
        for index, line in enumerate(lines):
            stripped = line.strip()
            is_output_heading = stripped.startswith("#") or bool(re.match(r"^\d+\.\s+", stripped))
            if is_output_heading and token in stripped:
                start_index = index + 1
                break

        if start_index is None:
            return text

        body_lines: List[str] = []
        for line in lines[start_index:]:
            stripped = line.strip()
            if stripped == "---":
                break
            is_output_heading = stripped.startswith("#") or bool(re.match(r"^\d+\.\s+", stripped))
            if is_output_heading and "`" in stripped:
                break
            body_lines.append(line)

        body = "\n".join(body_lines).strip()
        if body:
            return body
        return text

    def _extract_declared_output_values(
        self,
        step,
        written_files: List[str],
        project_root: Optional[str],
        generated_text: str = "",
    ) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}
        if not step.outputs:
            return extracted

        written_index = {Path(path).name: Path(path) for path in written_files}
        for output_spec in step.outputs:
            raw_path = getattr(output_spec, "path", None)
            if not raw_path:
                continue
            normalized_path = self._normalize_project_relative_path(str(raw_path))
            path_obj = Path(normalized_path)
            file_name = path_obj.name
            key_name = path_obj.stem if path_obj.suffix else file_name
            if "/" in normalized_path or "\\" in normalized_path:
                continue
            try:
                matched_path = written_index.get(file_name)
                raw_text = ""
                if matched_path and matched_path.exists() and not matched_path.is_dir():
                    raw_text = matched_path.read_text(encoding="utf-8")
                elif generated_text:
                    raw_text = generated_text
                else:
                    continue
                if key_name:
                    raw_text = self._extract_named_output_segment(raw_text, key_name)
                extracted[key_name] = self._coerce_output_file_value(raw_text)
            except Exception:
                continue
        return extracted

    def _resolve_spec_writeback_payload(
        self,
        *,
        step,
        structured_payload: Optional[Any],
        generated_text: str,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if isinstance(structured_payload, dict):
            payload.update(structured_payload)
            business_output = structured_payload.get("business_output")
            if isinstance(business_output, dict):
                payload.update({k: v for k, v in business_output.items() if k not in payload})

        for key in ("maintained_spec_path", "target_spec_path", "spec_path"):
            if key in payload and payload[key]:
                payload["maintained_spec_path"] = payload[key]
                break

        for key in ("maintained_spec_content", "target_spec_content", "spec_content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                payload["maintained_spec_content"] = self._strip_code_fence(value).strip()
                break
        else:
            for key in ("maintained_spec_content", "target_spec_content", "spec_content"):
                segment = self._extract_named_output_segment(generated_text, key)
                if segment and segment.strip() and segment.strip() != generated_text.strip():
                    payload["maintained_spec_content"] = self._strip_code_fence(segment).strip()
                    break

        if not payload.get("maintained_spec_content"):
            target_ref = ((step.config or {}).get("spec_writeback") or {}).get("target_path")
            if target_ref:
                segment = self._extract_named_output_segment(generated_text, str(target_ref))
                if segment and segment.strip() and segment.strip() != generated_text.strip():
                    payload["maintained_spec_content"] = self._strip_code_fence(segment).strip()

        if not payload.get("maintained_spec_path"):
            for key in ("maintained_spec_path", "target_spec_path", "spec_path"):
                segment = self._extract_named_output_segment(generated_text, key)
                if segment and segment.strip() and segment.strip() != generated_text.strip():
                    payload["maintained_spec_path"] = self._strip_code_fence(segment).strip()
                    break

        return payload

    def _apply_spec_writeback(
        self,
        *,
        step,
        project_root: Optional[str],
        structured_payload: Optional[Any],
        generated_text: str,
    ) -> Optional[Dict[str, Any]]:
        writeback_config = ((step.config or {}).get("spec_writeback") or {})
        if not writeback_config.get("enabled"):
            return None

        payload = self._resolve_spec_writeback_payload(
            step=step,
            structured_payload=structured_payload,
            generated_text=generated_text,
        )

        target_ref = (
            writeback_config.get("target_path")
            or payload.get("maintained_spec_path")
            or payload.get("target_spec_path")
        )
        content = payload.get("maintained_spec_content")
        if not target_ref or not isinstance(content, str) or not content.strip():
            return {
                "enabled": True,
                "applied": False,
                "reason": "missing_target_path_or_spec_content",
            }

        normalized_target = self._normalize_project_relative_path(str(target_ref))
        target_path = Path(normalized_target)
        if not target_path.is_absolute():
            target_path = (Path(project_root or ".").resolve() / target_path).resolve()

        existing_content = ""
        if target_path.exists():
            existing_content = target_path.read_text(encoding="utf-8")

        new_content = content.strip()
        changed = existing_content != new_content
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(new_content, encoding="utf-8")

        diff_report_path = writeback_config.get("diff_report_path")
        diff_report: Optional[Path] = None
        diff_text = ""
        if diff_report_path:
            normalized_diff = self._normalize_project_relative_path(str(diff_report_path))
            diff_report = Path(normalized_diff)
            if not diff_report.is_absolute():
                diff_report = (Path(project_root or ".").resolve() / diff_report).resolve()
            diff_report.parent.mkdir(parents=True, exist_ok=True)
            diff_lines = list(
                difflib.unified_diff(
                    existing_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=str(target_path),
                    tofile=str(target_path),
                    lineterm="",
                )
            )
            diff_text = "\n".join(diff_lines).strip()
            if not diff_text:
                diff_text = f"No content changes for {target_path}\n"
            diff_report.write_text(diff_text, encoding="utf-8")

        written_files = [str(target_path)]
        if diff_report:
            written_files.append(str(diff_report))

        return {
            "enabled": True,
            "applied": True,
            "changed": changed,
            "target_path": str(target_path),
            "diff_report_path": str(diff_report) if diff_report else None,
            "diff_preview": diff_text[:2000] if diff_text else "",
            "written_files": written_files,
        }

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
        executor_type = instance.data.get("executor_override") or step.executor_type or "claude_code"

        input_data = self._build_executor_input(
            executor_type=executor_type,
            step=step,
            ctx=ctx,
            instance=instance,
            workflow_id=workflow_id,
            agent_ctx=agent_ctx,
            step_token=step_token,
        )

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
            # 3. 调用 LLM Executor
            # 优先使用环境变量，否则从配置文件读取 default_profile，最后兜底为 huawei_deepseek
            default_profile = ctx.llm_config_loader.get_default_profile() if hasattr(ctx, 'llm_config_loader') else "huawei_deepseek"
            executor = ctx.executor_factory.create(
                executor_type,
                profile=os.getenv("LLM_PROFILE", default_profile),
                agent_id=step.agent_id or ""
            )

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

            structured_payload = self._parse_structured_output_if_possible(generated_text)
            agent_spec = self._load_agent_spec_for_step(ctx, step)
            governance_preflight = self._evaluate_governance_preflight(
                step=step,
                agent_spec=agent_spec,
                project_root=ctx.project_root,
                structured_payload=structured_payload,
            )
            spec_writeback = self._apply_spec_writeback(
                step=step,
                project_root=ctx.project_root,
                structured_payload=structured_payload,
                generated_text=generated_text,
            )
            # 3. 处理输出文件
            written_files = []
            file_outputs = [
                output
                for output in (step.outputs or [])
                if getattr(output, "type", None) in {"file", "dir"} and getattr(output, "path", None)
            ]
            if file_outputs:
                try:
                    written_files = await ctx.file_output_handler.handle(
                        generated_text,
                        file_outputs,
                        workflow_context
                    )
                except Exception as e:
                    print(f"[FileOutputHandler] Warning: {e}")

            if spec_writeback and spec_writeback.get("applied"):
                writeback_files = spec_writeback.get("written_files", [])
                written_files = list(
                    dict.fromkeys(written_files + writeback_files)
                )

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
            business_output = self._extract_business_output_payload(
                structured_payload,
                generated_text,
                step=step,
                written_files=written_files,
            )
            business_output, structured_payload = self._normalize_business_payload(
                step=step,
                workflow_id=workflow_id,
                business_output=business_output,
                structured_payload=structured_payload,
                instance_data=instance.data,
            )
            validation_result = self._validate_step_output(step, business_output)
            if validation_result and not validation_result.passed:
                strict = (step.config or {}).get("strict_output_validation", False)
                if strict:
                    error_msg = f"Output schema validation failed: {validation_result.errors[0].message if validation_result.errors else 'unknown'}"
                    repaired = await self._attempt_schema_repair(
                        executor=executor,
                        executor_type=executor_type,
                        input_data=input_data,
                        step=step,
                        workflow_id=workflow_id,
                        validation_error=error_msg,
                        business_output=business_output,
                        structured_payload=structured_payload,
                    )
                    if repaired:
                        repaired_validation = self._validate_step_output(step, repaired["business_output"])
                        if not repaired_validation or repaired_validation.passed:
                            business_output = repaired["business_output"]
                            structured_payload = repaired["structured_payload"]
                            generated_text = repaired["output"].get("generated_text", generated_text)
                            validation_result = repaired_validation
                            repaired_workspace_files = self._materialize_symbolic_workspace_outputs(
                                step=step,
                                workflow_id=workflow_id,
                                project_root=ctx.project_root,
                                business_output=business_output,
                                structured_payload=structured_payload,
                            )
                            if repaired_workspace_files:
                                written_files = list(dict.fromkeys(written_files + repaired_workspace_files))
                        else:
                            error_msg = (
                                "Output schema validation failed after repair retry: "
                                f"{repaired_validation.errors[0].message if repaired_validation.errors else 'unknown'}"
                            )
                            validation_result = repaired_validation
                    if validation_result and not validation_result.passed:
                        await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                        await ctx.store.update_task_execution(
                            execution_id,
                            TaskExecutionStatus.FAILED,
                            output_data={
                                "generated_text": generated_text,
                                "business_output": business_output,
                                "validation_result": validation_result.to_dict(),
                            },
                            error_message=error_msg,
                            completed_at=datetime.now(),
                        )
                        return StepResult(
                            status="failed",
                            step_id=step.id,
                            workflow_id=workflow_id,
                            message=error_msg,
                        )
                else:
                    print(f"[OutputValidation] Warning: Step {step.id} output schema validation failed (soft mode)")

            feat_review_subject_error = None
            expected_subject_refs: List[str] = []
            if getattr(step, "agent_id", "") == "agent.product.feat_reviewer":
                expected_subject_refs = self._expected_feat_review_subject_refs(instance.data)
                feat_review_subject_error = self._validate_feat_review_subject_refs(
                    business_output,
                    expected_subject_refs,
                )
                if not feat_review_subject_error:
                    feat_review_subject_error = self._validate_feat_review_semantics(
                        business_output,
                        expected_subject_refs,
                    )
            if feat_review_subject_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, feat_review_subject_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data={
                        "generated_text": generated_text,
                        "business_output": business_output,
                        "expected_subject_refs": expected_subject_refs,
                    },
                    error_message=feat_review_subject_error,
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=feat_review_subject_error,
                )

            feat_bundle_semantic_error = None
            if getattr(step, "agent_id", "") == "agent.product.prd_writer":
                feat_bundle_semantic_error = self._validate_feat_bundle_epic_semantics(
                    project_root=ctx.project_root,
                    business_output=business_output,
                )
            if feat_bundle_semantic_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, feat_bundle_semantic_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data={
                        "generated_text": generated_text,
                        "business_output": business_output,
                    },
                    error_message=feat_bundle_semantic_error,
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=feat_bundle_semantic_error,
                )

            if governance_preflight["warnings"]:
                for warning in governance_preflight["warnings"]:
                    print(f"[Governance] Warning: Step {step.id}: {warning}")

            governance_strict = bool((step.config or {}).get("strict_governance"))
            if governance_preflight["implementation_facing"] and not governance_preflight["allow_full_completion"]:
                if governance_strict:
                    error_msg = (
                        "Governance preflight failed: no formal SSOT truth source and no Acceptance Brief or Module Contract found"
                    )
                    await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                    return StepResult(
                        status="failed",
                        step_id=step.id,
                        workflow_id=workflow_id,
                        message=error_msg,
                    )

            # SSOT agent output contract 校验与物化
            ssot_materialized = await self._materialize_ssot_outputs(
                ctx=ctx,
                step=step,
                workflow_id=workflow_id,
                generated_text=generated_text,
                structured_payload=structured_payload,
            )
            if ssot_materialized:
                materialized_files = ssot_materialized.get("materialized_files", [])
                if materialized_files:
                    await self._collect_evidence(ctx, workflow_id, step.id, materialized_files)
                written_files = list(dict.fromkeys(written_files + materialized_files))

            workspace_files = self._materialize_symbolic_workspace_outputs(
                step=step,
                workflow_id=workflow_id,
                project_root=ctx.project_root,
                business_output=business_output,
                structured_payload=structured_payload,
            )
            if workspace_files:
                written_files = list(dict.fromkeys(written_files + workspace_files))

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
            output_data.update(
                self._extract_declared_output_values(
                    step=step,
                    written_files=written_files,
                    project_root=ctx.project_root,
                    generated_text=generated_text,
                )
            )
            if ssot_materialized:
                output_data["ssot_materialized"] = ssot_materialized["outputs"]
            if spec_writeback:
                output_data["spec_writeback"] = spec_writeback
                if spec_writeback.get("target_path"):
                    output_data["maintained_spec_path"] = spec_writeback["target_path"]
            output_data["governance_preflight"] = governance_preflight
            output_data["completion_summary"] = self._build_completion_summary(
                step=step,
                written_files=written_files,
                structured_payload=structured_payload,
                governance_preflight=governance_preflight,
            )

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

    async def _materialize_ssot_outputs(
        self,
        ctx: RunnerContext,
        step,
        workflow_id: str,
        generated_text: str,
        structured_payload: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        If the agent spec declares ssot_output_schema, validate and materialize it.
        """
        agent_spec = self._load_agent_spec_for_step(ctx, step)
        contracts = getattr(agent_spec, "contracts", {}) or {} if agent_spec else {}
        schema_ref = contracts.get("ssot_output_schema")

        if structured_payload is None:
            structured_payload = self._parse_structured_output_if_possible(generated_text)

        contract_data = self._extract_ssot_contract_payload(
            structured_payload,
            generated_text=generated_text,
        )
        if not schema_ref and contract_data is None:
            return None
        if contract_data is None:
            try:
                contract_data = self._parse_structured_output(generated_text)
            except ValueError as exc:
                strict = (step.config or {}).get("strict_output_validation", False)
                if strict:
                    raise
                print(f"[SSOTContract] Warning: Step {step.id} structured output parse failed: {exc}")
                return None

        if contract_data is None:
            strict = (step.config or {}).get("strict_output_validation", False)
            if strict:
                raise ValueError("SSOT output schema declared but no ssot_output_contract found")
            print(f"[SSOTContract] Warning: Step {step.id} missing ssot_output_contract payload")
            return None

        if schema_ref:
            schema_path = self._resolve_contract_path(
                schema_ref=schema_ref,
                spec_path=getattr(agent_spec, "spec_path", None),
                project_root=ctx.project_root,
            )
        else:
            from lee.orchestrator.execution.artifacts.ssot_contract import DEFAULT_SSOT_CONTRACT_SCHEMA

            schema_path = str(Path(DEFAULT_SSOT_CONTRACT_SCHEMA).resolve())
        contract_data = self._normalize_ssot_contract_payload(contract_data)

        try:
            from lee.orchestrator.execution.artifacts import ArtifactManager, SSOTContractMaterializer

            manager = ArtifactManager(
                project_root=Path(ctx.project_root or ".").resolve(),
            )
            materializer = SSOTContractMaterializer(manager, schema_path=Path(schema_path))
            outputs = materializer.materialize(contract_data)
        except Exception as exc:
            strict = (step.config or {}).get("strict_output_validation", False)
            if strict:
                raise
            print(f"[SSOTContract] Warning: Step {step.id} SSOT materialization failed: {exc}")
            return None

        materialized_summary = {}
        materialized_files: List[str] = []
        for key, item in outputs.items():
            artifact = item.artifact
            materialized_summary[key] = {
                "id": artifact.id,
                "identity_kind": item.identity_kind,
                "path": artifact.path,
                "path_root": artifact.path_root,
                "parent_id": artifact.properties.get("parent_id"),
            }
            materialized_files.append(str(artifact.absolute_path))

        return {
            "schema_path": schema_path,
            "outputs": materialized_summary,
            "materialized_files": materialized_files,
        }

    @staticmethod
    def _normalize_ssot_contract_payload(contract_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(contract_data)
        if "contract_version" in normalized:
            normalized["contract_version"] = "1.0"
        if "run_id" in normalized and normalized["run_id"] is not None:
            normalized["run_id"] = str(normalized["run_id"])
        allowed_output_keys = {
            "key",
            "identity_kind",
            "ssot_type",
            "title",
            "description",
            "content",
            "owner",
            "version",
            "parent",
            "derived_from",
            "derived_from_ids",
            "source_refs",
            "primary_refs",
            "verifies",
            "implements",
            "depends_on",
            "derived_from_one",
            "placement_key",
            "tags",
            "artifact_type",
            "category",
            "governance_kind",
            "properties",
            "evidence_layers",
        }
        outputs = []
        for raw_output in normalized.get("outputs", []) or []:
            if not isinstance(raw_output, dict):
                outputs.append(raw_output)
                continue
            output = {
                key: value for key, value in dict(raw_output).items() if key in allowed_output_keys
            }
            parent = output.get("parent")
            if isinstance(parent, str) and parent.lower() == "feat":
                candidates: List[str] = []
                for value in output.get("verifies", []) or []:
                    if isinstance(value, str) and value.upper().startswith("FEAT-"):
                        candidates.append(value)
                properties = output.get("properties") or {}
                for key in ("feature_id", "feat_id", "parent_feat_id"):
                    value = properties.get(key)
                    if isinstance(value, str) and value.upper().startswith("FEAT-"):
                        candidates.append(value)
                if candidates:
                    output["parent"] = candidates[0]
            if isinstance(output.get("parent"), str) and output["parent"].upper().startswith("FEAT-"):
                verifies = []
                for value in output.get("verifies", []) or []:
                    if isinstance(value, str) and value.lower() == "feat":
                        verifies.append(output["parent"])
                    else:
                        verifies.append(value)
                if verifies:
                    output["verifies"] = verifies
            outputs.append(output)
        normalized["outputs"] = outputs
        return normalized

    @staticmethod
    def _parse_structured_output_if_possible(generated_text: str) -> Optional[Any]:
        try:
            return StepRunnerBase._parse_structured_output(generated_text)
        except ValueError:
            return None

    def _extract_business_output_payload(
        self,
        structured_payload: Optional[Any],
        fallback_text: str,
        *,
        step=None,
        written_files: Optional[List[str]] = None,
    ) -> Any:
        if isinstance(structured_payload, dict) and "business_output" in structured_payload:
            wrapped_business_output = structured_payload["business_output"]
            if (
                step
                and written_files
                and self._should_prefer_written_file_payload(step, wrapped_business_output)
            ):
                best_file_payload = self._extract_best_written_file_payload(step, written_files)
                if best_file_payload is not None:
                    return self._unwrap_business_output_candidate(best_file_payload)
            return wrapped_business_output
        if isinstance(structured_payload, dict):
            return structured_payload
        segment_payload = self._extract_structured_segment_payload(fallback_text, "business_output")
        if segment_payload is not None:
            return segment_payload
        if step and written_files:
            file_output = self._extract_primary_file_output(step, written_files)
            if file_output is not None:
                return file_output
            best_file_payload = self._extract_best_written_file_payload(step, written_files)
            if best_file_payload is not None:
                return self._unwrap_business_output_candidate(best_file_payload)
        return fallback_text

    @classmethod
    def _should_prefer_written_file_payload(cls, step, payload: Any) -> bool:
        candidate = cls._unwrap_business_output_candidate(payload)
        if not isinstance(candidate, dict):
            return True
        agent_id = getattr(step, "agent_id", "")
        if agent_id == "agent.product.pm_planner":
            task_specs = candidate.get("task_specs")
            if isinstance(task_specs, list) and task_specs:
                return False
            return True
        return False

    def _expected_feat_review_subject_refs(
        self,
        instance_data: Dict[str, Any],
    ) -> List[str]:
        step_outputs = instance_data.get("step_outputs", {}) if isinstance(instance_data, dict) else {}
        feat_spec_output = step_outputs.get("feat_spec_generation")
        if not isinstance(feat_spec_output, dict):
            return []

        ssot_materialized = feat_spec_output.get("ssot_materialized")
        if isinstance(ssot_materialized, dict):
            feat_entry = ssot_materialized.get("feat")
            if isinstance(feat_entry, dict):
                feat_id = feat_entry.get("id")
                if isinstance(feat_id, str) and feat_id.strip():
                    return [feat_id]
            elif isinstance(feat_entry, list):
                materialized_ids = [
                    item.get("id")
                    for item in feat_entry
                    if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("id").strip()
                ]
                if materialized_ids:
                    return materialized_ids

        generated_text = feat_spec_output.get("generated_text", "")
        feat_payload: Any = None
        try:
            parsed_output = StepRunnerBase._parse_structured_output(generated_text)
        except Exception:
            parsed_output = None

        if isinstance(parsed_output, dict):
            if isinstance(parsed_output.get("business_output"), dict):
                feat_payload = parsed_output.get("business_output")
            else:
                feat_payload = parsed_output

        if feat_payload is None:
            feat_payload = self._extract_business_output_payload(None, generated_text)
        if not isinstance(feat_payload, dict):
            return []

        bundle_specs = feat_payload.get("feat_specs")
        if isinstance(bundle_specs, list):
            feat_ids = [
                item.get("feat_id")
                for item in bundle_specs
                if isinstance(item, dict) and isinstance(item.get("feat_id"), str) and item.get("feat_id").strip()
            ]
            if feat_ids:
                return feat_ids

        feat_id = feat_payload.get("feat_id")
        return [feat_id] if isinstance(feat_id, str) and feat_id.strip() else []

    @staticmethod
    def _resolve_epic_ref_from_instance_data(instance_data: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(instance_data, dict):
            return None

        candidates: List[Any] = [
            instance_data.get("epic_freeze"),
            instance_data.get("epic_freeze_ref"),
        ]

        params = instance_data.get("params")
        if isinstance(params, dict):
            candidates.extend(
                [
                    params.get("epic_freeze"),
                    params.get("epic_freeze_ref"),
                ]
            )

        for candidate in candidates:
            if isinstance(candidate, dict):
                artifact_id = candidate.get("artifact_id") or candidate.get("id")
                if isinstance(artifact_id, str) and artifact_id.strip():
                    return artifact_id.strip()
                path_value = candidate.get("path")
            elif isinstance(candidate, str):
                path_value = candidate
            else:
                continue

            if not isinstance(path_value, str) or not path_value.strip():
                continue
            path = Path(path_value)
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8")
                parsed = StepRunnerBase._parse_structured_output(text)
            except Exception:
                try:
                    text = path.read_text(encoding="utf-8")
                except Exception:
                    continue
                parsed = None
            if isinstance(parsed, dict):
                artifact_id = parsed.get("artifact_id") or parsed.get("id")
                if isinstance(artifact_id, str) and artifact_id.strip():
                    return artifact_id.strip()
            match = re.search(r"(?m)^(?:artifact_id|id):\s*([A-Za-z0-9_.-]+)\s*$", text)
            if match:
                return match.group(1).strip()

        return None

    @staticmethod
    def _normalize_requirement_decomposer_payload(
        step,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if getattr(step, "agent_id", "") != "agent.product.requirement_decomposer":
            return business_output, structured_payload
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        actual_epic_ref = LLMRunner._resolve_epic_ref_from_instance_data(instance_data)
        if not actual_epic_ref:
            return business_output, structured_payload

        normalized_business = dict(business_output)
        normalized_business["epic_ref"] = actual_epic_ref

        if isinstance(structured_payload, dict):
            normalized_structured = dict(structured_payload)
            normalized_structured["business_output"] = normalized_business
            return normalized_business, normalized_structured

        return normalized_business, structured_payload

    @staticmethod
    def _normalize_prd_writer_feat_payload(
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if getattr(step, "agent_id", "") != "agent.product.prd_writer":
            return business_output, structured_payload
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        actual_epic_ref = LLMRunner._resolve_epic_ref_from_instance_data(instance_data)
        step_config = getattr(step, "config", {}) or {}
        output_contract = str(step_config.get("output_contract") or "").replace("\\", "/")
        expects_bundle = output_contract.endswith("feat-bundle-contract/v1/schema.json") or (
            not output_contract and getattr(step, "id", "") == "feat_spec_generation"
        )

        def _clean_text(value: Any) -> str:
            return str(value or "").strip()

        def _normalize_priority(value: Any) -> str:
            normalized = _clean_text(value).upper()
            if normalized in {"P0", "P1", "P2"}:
                return normalized
            if normalized in {"HIGH", "CRITICAL"}:
                return "P0"
            if normalized in {"MEDIUM", "NORMAL"}:
                return "P1"
            if normalized in {"LOW"}:
                return "P2"
            if normalized in {"0", "1", "2"}:
                return f"P{normalized}"
            if normalized.startswith("P") and len(normalized) > 1 and normalized[1:].isdigit():
                return normalized if normalized in {"P0", "P1", "P2"} else "P1"
            return "P1"

        def _normalize_lifecycle_status(value: Any) -> str:
            normalized = _clean_text(value).lower()
            mapping = {
                "draft": "draft",
                "active": "active",
                "frozen": "frozen",
                "archived": "archived",
                "completed": "active",
                "complete": "active",
                "success": "active",
                "done": "active",
                "specified": "draft",
            }
            return mapping.get(normalized, "draft")

        def _normalize_string_list(values: Any, *, fallback: Optional[List[str]] = None) -> List[str]:
            items = values if isinstance(values, list) else [values] if values is not None else []
            normalized_items: List[str] = []
            for item in items:
                if isinstance(item, dict):
                    candidate = (
                        item.get("description")
                        or item.get("criterion")
                        or item.get("title")
                        or item.get("id")
                    )
                else:
                    candidate = item
                text = _clean_text(candidate)
                if text:
                    normalized_items.append(text)
            if normalized_items:
                return normalized_items
            return [text for text in (fallback or []) if _clean_text(text)]

        def _normalize_dependency_ids(values: Any) -> List[str]:
            items = values if isinstance(values, list) else [values] if values is not None else []
            normalized_dependencies: List[str] = []
            for item in items:
                if isinstance(item, dict):
                    candidate = item.get("id") or item.get("feat_id") or item.get("epic_id") or item.get("title")
                else:
                    candidate = item
                text = _clean_text(candidate)
                if text:
                    normalized_dependencies.append(text)
            return normalized_dependencies

        def _normalize_acceptance_criteria(values: Any, *, title: str, goal: str) -> List[str]:
            items = values if isinstance(values, list) else [values] if values is not None else []
            normalized_criteria: List[str] = []
            for item in items:
                if isinstance(item, dict):
                    candidate = item.get("description") or item.get("criterion") or item.get("validation")
                else:
                    candidate = item
                text = _clean_text(candidate)
                if text:
                    normalized_criteria.append(text)
            if normalized_criteria:
                return normalized_criteria
            fallback_text = goal or title or "Feature is independently acceptable"
            return [fallback_text]

        def _build_acceptance_checks(
            feat_item: Dict[str, Any],
            acceptance_criteria: List[str],
        ) -> List[Dict[str, Any]]:
            raw_checks = feat_item.get("acceptance_checks")
            normalized_checks: List[Dict[str, Any]] = []
            if isinstance(raw_checks, list):
                for index, item in enumerate(raw_checks[:5], start=1):
                    if not isinstance(item, dict):
                        normalized_checks.append(
                            {
                                "id": f"AC-{index:03d}",
                                "scenario": _clean_text(item),
                                "given": "",
                                "when": "",
                                "then": "",
                                "trace_hints": ["TECH"],
                            }
                        )
                        continue
                    normalized_item = dict(item)
                    normalized_item.setdefault("id", f"AC-{index:03d}")
                    normalized_item.setdefault("scenario", "")
                    normalized_item.setdefault("given", "")
                    normalized_item.setdefault("when", "")
                    normalized_item.setdefault("then", "")
                    trace_hints = normalized_item.get("trace_hints")
                    if not isinstance(trace_hints, list) or not trace_hints:
                        normalized_item["trace_hints"] = ["TECH"]
                    normalized_checks.append(normalized_item)
            if normalized_checks:
                return normalized_checks

            scenario_seed = acceptance_criteria[:5]
            if len(scenario_seed) == 1:
                scenario_seed.append(f"{feat_item.get('title') or 'Feature'} remains traceable")
            if not scenario_seed:
                scenario_seed = [
                    feat_item.get("goal") or feat_item.get("title") or "Feature behavior is verifiable",
                    f"{feat_item.get('title') or 'Feature'} outputs remain stable",
                ]

            synthesized_checks: List[Dict[str, Any]] = []
            for index, criterion in enumerate(scenario_seed[:5], start=1):
                synthesized_checks.append(
                    {
                        "id": f"AC-{index:03d}",
                        "scenario": criterion,
                        "given": feat_item.get("title") or "",
                        "when": "the feature workflow runs",
                        "then": criterion,
                        "trace_hints": ["TECH"],
                    }
                )
            return synthesized_checks

        def _extract_breakdown_feature_candidates(
            payload: Dict[str, Any],
            fallback_epic_ref: Optional[str],
        ) -> tuple[Optional[List[Any]], Optional[str]]:
            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            resolved_epic_ref = (
                _clean_text(payload.get("epic_ref"))
                or _clean_text(metadata.get("epic_id"))
                or fallback_epic_ref
            )
            if isinstance(payload.get("features"), list):
                return payload.get("features"), resolved_epic_ref
            if isinstance(payload.get("feats"), list):
                return payload.get("feats"), resolved_epic_ref
            if isinstance(payload.get("feat_candidates"), list):
                return payload.get("feat_candidates"), resolved_epic_ref
            if isinstance(payload.get("feat_specifications"), list):
                return payload.get("feat_specifications"), resolved_epic_ref

            epic_breakdowns = payload.get("epic_breakdowns")
            if not isinstance(epic_breakdowns, list):
                return None, resolved_epic_ref

            selected_breakdown: Optional[Dict[str, Any]] = None
            if resolved_epic_ref:
                for item in epic_breakdowns:
                    if not isinstance(item, dict):
                        continue
                    if _clean_text(item.get("epic_id")).lower() == resolved_epic_ref.lower():
                        selected_breakdown = item
                        break
            if selected_breakdown is None:
                for item in epic_breakdowns:
                    if isinstance(item, dict) and isinstance(item.get("features"), list):
                        selected_breakdown = item
                        break
            if not isinstance(selected_breakdown, dict):
                return None, resolved_epic_ref

            resolved_epic_ref = _clean_text(selected_breakdown.get("epic_id")) or resolved_epic_ref
            if isinstance(selected_breakdown.get("features"), list):
                return selected_breakdown.get("features"), resolved_epic_ref
            return None, resolved_epic_ref

        def _synthesize_feat_spec(candidate: Dict[str, Any], epic_ref: Optional[str]) -> Dict[str, Any]:
            title = _clean_text(candidate.get("title")) or "Untitled FEAT"
            feat_id = _clean_text(candidate.get("feat_id") or candidate.get("id"))
            if not feat_id:
                slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").upper()
                feat_id = f"FEAT-{slug}" if slug else "FEAT-AUTO"

            business_context = candidate.get("business_context") if isinstance(candidate.get("business_context"), dict) else {}
            scope_boundary = candidate.get("scope_boundary") if isinstance(candidate.get("scope_boundary"), dict) else {}
            requirement = candidate.get("requirement") if isinstance(candidate.get("requirement"), dict) else {}
            interface_spec = candidate.get("interface_spec") if isinstance(candidate.get("interface_spec"), dict) else {}
            input_schema = interface_spec.get("input_schema") if isinstance(interface_spec.get("input_schema"), dict) else {}
            output_schema = interface_spec.get("output_schema") if isinstance(interface_spec.get("output_schema"), dict) else {}
            state_machine = candidate.get("state_machine") if isinstance(candidate.get("state_machine"), dict) else {}
            dependency_block = candidate.get("dependencies") if isinstance(candidate.get("dependencies"), dict) else {}
            description = _clean_text(candidate.get("description"))
            rich_description = _clean_text(requirement.get("description"))
            goal = _clean_text(candidate.get("goal")) or rich_description or description or title
            user_value = (
                _clean_text(candidate.get("user_value"))
                or _clean_text(business_context.get("problem"))
                or rich_description
                or description
                or title
            )
            inputs = _normalize_string_list(
                candidate.get("inputs")
                or candidate.get("input")
                or [
                    field.get("name")
                    for field in (input_schema.get("fields") if isinstance(input_schema.get("fields"), list) else [])
                    if isinstance(field, dict) and _clean_text(field.get("name"))
                ]
                or scope_boundary.get("in_scope"),
                fallback=["Inputs defined by EPIC scope"],
            )
            processing = _normalize_string_list(
                candidate.get("processing")
                or [
                    transition.get("trigger")
                    for transition in (state_machine.get("transitions") if isinstance(state_machine.get("transitions"), list) else [])
                    if isinstance(transition, dict) and _clean_text(transition.get("trigger"))
                ],
                fallback=[rich_description or description or f"Deliver {title} capability"],
            )
            outputs = _normalize_string_list(
                candidate.get("outputs")
                or candidate.get("output")
                or [
                    field.get("name")
                    for field in (output_schema.get("fields") if isinstance(output_schema.get("fields"), list) else [])
                    if isinstance(field, dict) and _clean_text(field.get("name"))
                ]
                or candidate.get("acceptance_boundary"),
                fallback=[f"{title} FEAT specification"],
            )
            acceptance_criteria = _normalize_acceptance_criteria(
                candidate.get("acceptance_criteria")
                or requirement.get("acceptance_criteria")
                or candidate.get("acceptance_boundaries"),
                title=title,
                goal=goal,
            )
            non_goals = _normalize_string_list(
                candidate.get("non_goals") or scope_boundary.get("out_of_scope"),
            )
            priority = _normalize_priority(candidate.get("priority"))
            parent_workflow = _clean_text(candidate.get("parent_workflow"))
            category = _clean_text(candidate.get("category"))
            delivery_slice = _clean_text(candidate.get("delivery_slice")) or parent_workflow or category or "core"
            normalized_epic_ref = epic_ref or _clean_text(candidate.get("parent_epic"))
            source_refs = _normalize_string_list(
                candidate.get("source_refs"),
                fallback=[f"{normalized_epic_ref}#scope"] if normalized_epic_ref else [],
            )
            dependencies = _normalize_dependency_ids(
                candidate.get("dependencies")
                if not isinstance(candidate.get("dependencies"), dict)
                else dependency_block.get("upstream")
            )

            synthesized = {
                "feat_id": feat_id,
                "title": title,
                "goal": goal,
                "user_value": user_value,
                "inputs": inputs,
                "processing": processing,
                "outputs": outputs,
                "acceptance_criteria": acceptance_criteria,
                "dependencies": dependencies,
                "non_goals": non_goals,
                "priority": priority,
                "delivery_slice": delivery_slice,
                "lifecycle_status": _normalize_lifecycle_status(
                    candidate.get("lifecycle_status") or candidate.get("status")
                ),
                "source_refs": source_refs,
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "FEAT",
                    "parent": normalized_epic_ref,
                    "derived_from": normalized_epic_ref,
                },
                "testability_seed": {
                    "risk_notes": non_goals,
                    "integration_points": [value for value in [parent_workflow, category] if value],
                    "priority_hint": priority,
                },
            }
            synthesized["acceptance_checks"] = _build_acceptance_checks(synthesized, acceptance_criteria)
            return synthesized

        def normalize_feat_item(feat_item: Any) -> Any:
            if not isinstance(feat_item, dict):
                return feat_item

            normalized_feat = dict(feat_item)

            def _truncate_list(values: Any, max_items: int) -> Any:
                if not isinstance(values, list):
                    return values
                return values[:max_items]

            ssot = normalized_feat.get("ssot")
            if isinstance(ssot, dict):
                normalized_ssot = dict(ssot)
            else:
                normalized_ssot = {}
            feat_id = _clean_text(normalized_feat.get("feat_id") or normalized_feat.get("id"))
            if not feat_id:
                seed_text = (
                    _clean_text(normalized_feat.get("title"))
                    or _clean_text(normalized_feat.get("goal"))
                    or _clean_text(normalized_feat.get("name"))
                )
                seed_slug = re.sub(r"[^A-Za-z0-9]+", "-", seed_text).strip("-").lower()
                feat_id = (
                    f"feat-{seed_slug}"
                    if seed_slug
                    else (
                        f"{actual_epic_ref}-feat"
                        if actual_epic_ref
                        else "FEAT-AUTO"
                    )
                )
            if feat_id:
                normalized_feat["feat_id"] = feat_id
            title = _clean_text(normalized_feat.get("title")) or feat_id or "Untitled FEAT"
            normalized_feat["title"] = title
            goal = _clean_text(normalized_feat.get("goal") or normalized_feat.get("description")) or title
            normalized_feat["goal"] = goal
            normalized_feat["user_value"] = (
                _clean_text(normalized_feat.get("user_value"))
                or _clean_text(
                    normalized_feat.get("business_context", {}).get("problem")
                    if isinstance(normalized_feat.get("business_context"), dict)
                    else ""
                )
                or _clean_text(normalized_feat.get("description"))
                or title
            )
            scope_boundary = normalized_feat.get("scope_boundary")
            if not isinstance(scope_boundary, dict):
                scope_boundary = {}
            normalized_feat["inputs"] = _truncate_list(
                _normalize_string_list(
                    normalized_feat.get("inputs") or normalized_feat.get("input") or scope_boundary.get("in_scope"),
                    fallback=["Inputs defined by EPIC scope"],
                ),
                5,
            )
            normalized_feat["processing"] = _truncate_list(
                _normalize_string_list(
                    normalized_feat.get("processing"),
                    fallback=[_clean_text(normalized_feat.get("description")) or f"Deliver {title} capability"],
                ),
                5,
            )
            normalized_feat["outputs"] = _truncate_list(
                _normalize_string_list(
                    normalized_feat.get("outputs")
                    or normalized_feat.get("output")
                    or normalized_feat.get("acceptance_boundary"),
                    fallback=[f"{title} FEAT specification"],
                ),
                5,
            )
            normalized_feat["acceptance_criteria"] = _truncate_list(
                _normalize_acceptance_criteria(
                    normalized_feat.get("acceptance_criteria") or normalized_feat.get("acceptance_boundaries"),
                    title=title,
                    goal=goal,
                ),
                5,
            )
            normalized_feat["dependencies"] = _truncate_list(
                _normalize_dependency_ids(normalized_feat.get("dependencies")),
                10,
            )
            normalized_feat["non_goals"] = _truncate_list(
                _normalize_string_list(
                    normalized_feat.get("non_goals") or scope_boundary.get("out_of_scope"),
                ),
                10,
            )
            normalized_feat["priority"] = _normalize_priority(normalized_feat.get("priority"))
            normalized_feat["delivery_slice"] = (
                _clean_text(normalized_feat.get("delivery_slice"))
                or _clean_text(normalized_feat.get("parent_workflow"))
                or _clean_text(normalized_feat.get("category"))
                or "core"
            )
            normalized_feat["lifecycle_status"] = _normalize_lifecycle_status(
                normalized_feat.get("lifecycle_status") or normalized_feat.get("status")
            )
            source_refs = normalized_feat.get("source_refs")
            if isinstance(source_refs, list):
                normalized_feat["source_refs"] = _truncate_list(
                    _normalize_string_list(source_refs),
                    5,
                )
            if normalized_feat.get("feat_id"):
                normalized_ssot.setdefault("identity_kind", "ssot")
                normalized_ssot.setdefault("ssot_type", "FEAT")
                normalized_ssot.setdefault(
                    "parent",
                    actual_epic_ref
                    or _clean_text(normalized_feat.get("epic_ref"))
                    or _clean_text(normalized_ssot.get("parent")),
                )
                normalized_ssot.setdefault(
                    "derived_from",
                    actual_epic_ref
                    or _clean_text(normalized_feat.get("epic_ref"))
                    or _clean_text(normalized_ssot.get("derived_from"))
                    or _clean_text(normalized_ssot.get("parent")),
                )
            if normalized_ssot:
                normalized_feat["ssot"] = normalized_ssot

            derived = normalized_feat.get("derived_object_expectations")
            if isinstance(derived, dict):
                normalized_derived = dict(derived)
            else:
                normalized_derived = {}
            normalized_derived.setdefault("task_required", True)
            normalized_derived.setdefault("testset_required", True)
            normalized_derived.setdefault("testset_owner", "qa")
            normalized_derived.setdefault("qa_seed_required", True)
            normalized_feat["derived_object_expectations"] = normalized_derived
            testability_seed = normalized_feat.get("testability_seed")
            if isinstance(testability_seed, dict):
                normalized_testability = dict(testability_seed)
            else:
                normalized_testability = {}
            normalized_testability.setdefault("risk_notes", normalized_feat.get("non_goals") or [])
            normalized_testability.setdefault("integration_points", normalized_feat.get("dependencies") or [])
            normalized_testability.setdefault("priority_hint", normalized_feat.get("priority"))
            normalized_feat["testability_seed"] = normalized_testability
            normalized_user_stories = _truncate_list(normalized_feat.get("user_stories"), 3)
            normalized_feat["user_stories"] = normalized_user_stories if isinstance(normalized_user_stories, list) else []
            normalized_feat["acceptance_checks"] = _build_acceptance_checks(
                normalized_feat,
                normalized_feat.get("acceptance_criteria") or [],
            )
            return normalized_feat

        def _format_list_section(title: str, values: Any) -> str:
            normalized_values = [str(item).strip() for item in (values or []) if str(item).strip()]
            if not normalized_values:
                return f"# {title}\n\n- None\n"
            lines = "\n".join(f"- {item}" for item in normalized_values)
            return f"# {title}\n\n{lines}\n"

        def _format_acceptance_checks_section(checks: Any) -> str:
            if not isinstance(checks, list) or not checks:
                return "# Acceptance Checks\n\n- None\n"

            blocks: List[str] = []
            for index, item in enumerate(checks, start=1):
                if not isinstance(item, dict):
                    blocks.append(f"## AC-{index:03d}\n\n{item}\n")
                    continue
                trace_hints = item.get("trace_hints") or []
                trace_text = ", ".join(str(hint).strip() for hint in trace_hints if str(hint).strip()) or "None"
                block = (
                    f"## {item.get('id') or f'AC-{index:03d}'}\n\n"
                    f"- Scenario: {item.get('scenario', '')}\n"
                    f"- Given: {item.get('given', '')}\n"
                    f"- When: {item.get('when', '')}\n"
                    f"- Then: {item.get('then', '')}\n"
                    f"- Trace Hints: {trace_text}\n"
                )
                blocks.append(block)
            return "# Acceptance Checks\n\n" + "\n".join(blocks).rstrip() + "\n"

        def _build_feat_markdown(feat_item: Dict[str, Any]) -> str:
            sections = [
                f"# Goal\n\n{feat_item.get('goal', '').strip()}\n",
                f"# User Value\n\n{feat_item.get('user_value', '').strip()}\n",
                _format_list_section("Inputs", feat_item.get("inputs")),
                _format_list_section("Processing", feat_item.get("processing")),
                _format_list_section("Outputs", feat_item.get("outputs")),
                _format_list_section("Acceptance", feat_item.get("acceptance_criteria")),
                _format_acceptance_checks_section(feat_item.get("acceptance_checks")),
                _format_list_section("Dependencies", feat_item.get("dependencies")),
                _format_list_section("Non Goals", feat_item.get("non_goals")),
            ]
            return "\n".join(section.rstrip() for section in sections).strip() + "\n"

        def _build_contract_outputs(feat_specs: List[Dict[str, Any]], epic_ref: Optional[str]) -> List[Dict[str, Any]]:
            outputs: List[Dict[str, Any]] = []
            use_single_key = len(feat_specs) == 1
            for index, feat_item in enumerate(feat_specs, start=1):
                if not isinstance(feat_item, dict):
                    continue
                feat_id = str(feat_item.get("feat_id") or "").strip()
                feat_title = str(feat_item.get("title") or feat_id or f"FEAT {index}").strip()
                feat_ssot = feat_item.get("ssot") if isinstance(feat_item.get("ssot"), dict) else {}
                source_refs = LLMRunner._filter_materializable_refs(feat_item.get("source_refs"))
                parent_ref = feat_ssot.get("parent") or epic_ref
                if not LLMRunner._is_literal_ssot_ref(parent_ref):
                    parent_ref = None
                output_key = "feat" if use_single_key else f"feat_{index:03d}"
                output_item = {
                    "key": output_key,
                    "identity_kind": "ssot",
                    "ssot_type": "feat",
                    "title": feat_title,
                    "content": _build_feat_markdown(feat_item),
                    "properties": {
                        "feat_id": feat_id,
                        "epic_ref": epic_ref,
                    },
                }
                if parent_ref:
                    output_item["parent"] = parent_ref
                if source_refs:
                    output_item["source_refs"] = source_refs
                outputs.append(output_item)
            return outputs

        normalized_business = dict(business_output)
        bundle_specs = normalized_business.get("feat_specs")
        if isinstance(bundle_specs, list):
            structured_business = (
                structured_payload.get("business_output")
                if isinstance(structured_payload, dict)
                and isinstance(structured_payload.get("business_output"), dict)
                else {}
            )
            normalized_business = {
                "epic_ref": normalized_business.get("epic_ref"),
                "feat_specs": [normalize_feat_item(item) for item in bundle_specs],
            }
            if normalized_business["epic_ref"] is None and structured_business.get("epic_ref"):
                normalized_business["epic_ref"] = structured_business["epic_ref"]
        else:
            candidate_specs, candidate_epic_ref = _extract_breakdown_feature_candidates(
                normalized_business,
                actual_epic_ref or _clean_text(normalized_business.get("epic_ref")) or None,
            )
            if isinstance(candidate_specs, list) and candidate_specs:
                normalized_business = {
                    "epic_ref": candidate_epic_ref,
                    "feat_specs": [
                        normalize_feat_item(_synthesize_feat_spec(item, candidate_epic_ref))
                        for item in candidate_specs
                        if isinstance(item, dict)
                    ],
                }
                if not normalized_business["feat_specs"]:
                    normalized_business = normalize_feat_item(normalized_business)
            else:
                normalized_business = normalize_feat_item(normalized_business)
                if expects_bundle:
                    normalized_business = {
                        "epic_ref": actual_epic_ref or _clean_text(normalized_business.get("epic_ref")) or None,
                        "feat_specs": [normalized_business],
                    }

        if actual_epic_ref:
            normalized_business["epic_ref"] = actual_epic_ref
            if isinstance(normalized_business.get("feat_specs"), list):
                rewritten_specs = []
                for item in normalized_business["feat_specs"]:
                    if not isinstance(item, dict):
                        rewritten_specs.append(item)
                        continue
                    normalized_item = dict(item)
                    normalized_item["source_refs"] = [f"{actual_epic_ref}#scope"]
                    ssot = normalized_item.get("ssot") if isinstance(normalized_item.get("ssot"), dict) else {}
                    normalized_item["ssot"] = {
                        **dict(ssot),
                        "identity_kind": "ssot",
                        "ssot_type": "FEAT",
                        "parent": actual_epic_ref,
                        "derived_from": actual_epic_ref,
                    }
                    rewritten_specs.append(normalized_item)
                normalized_business["feat_specs"] = rewritten_specs

        normalized_structured = LLMRunner._ensure_structured_envelope(
            business_output=normalized_business,
            structured_payload=structured_payload,
        )

        ssot_contract = normalized_structured.get("ssot_output_contract")
        if isinstance(ssot_contract, dict):
            normalized_contract = dict(ssot_contract)
        else:
            normalized_contract = {}
        normalized_contract.setdefault("contract_version", "1.0")
        normalized_contract.setdefault("run_id", workflow_id)

        outputs = normalized_contract.get("outputs")
        if isinstance(normalized_business.get("feat_specs"), list):
            normalized_contract["outputs"] = _build_contract_outputs(
                normalized_business.get("feat_specs") or [],
                normalized_business.get("epic_ref"),
            )
        elif not isinstance(outputs, list) or not outputs:
            normalized_contract["outputs"] = _build_contract_outputs(
                normalized_business.get("feat_specs") or [],
                normalized_business.get("epic_ref"),
            )
        elif isinstance(outputs, list):
            normalized_outputs = []
            for item in outputs:
                if not isinstance(item, dict):
                    normalized_outputs.append(item)
                    continue
                normalized_item = dict(item)
                normalized_item.setdefault("identity_kind", "ssot")
                if normalized_item.get("key") == "feat":
                    normalized_item.setdefault("ssot_type", "feat")
                    if normalized_business.get("title"):
                        normalized_item.setdefault("title", normalized_business["title"])
                    parent = normalized_business.get("ssot", {}).get("parent")
                    if LLMRunner._is_literal_ssot_ref(parent):
                        normalized_item.setdefault("parent", parent)
                    source_refs = LLMRunner._filter_materializable_refs(normalized_business.get("source_refs"))
                    if source_refs:
                        normalized_item.setdefault("source_refs", source_refs)
                if actual_epic_ref and LLMRunner._is_literal_ssot_ref(actual_epic_ref):
                    normalized_item["parent"] = actual_epic_ref
                    normalized_item["source_refs"] = [f"{actual_epic_ref}#scope"]
                else:
                    normalized_item.pop("parent", None)
                    filtered_refs = LLMRunner._filter_materializable_refs(normalized_item.get("source_refs"))
                    if filtered_refs:
                        normalized_item["source_refs"] = filtered_refs
                    else:
                        normalized_item.pop("source_refs", None)
                properties = normalized_item.get("properties") if isinstance(normalized_item.get("properties"), dict) else {}
                normalized_item["properties"] = {
                    **properties,
                    "epic_ref": actual_epic_ref or normalized_business.get("epic_ref"),
                }
                normalized_outputs.append(normalized_item)
            normalized_contract["outputs"] = normalized_outputs
        normalized_structured["ssot_output_contract"] = normalized_contract

        return normalized_business, normalized_structured

    @staticmethod
    def _ensure_structured_envelope(
        *,
        business_output: Any,
        structured_payload: Any,
    ) -> Dict[str, Any]:
        if isinstance(structured_payload, dict):
            normalized = dict(structured_payload)
        else:
            normalized = {}
        normalized["business_output"] = business_output
        return normalized

    @staticmethod
    def _is_literal_ssot_ref(value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(
            re.match(
                r"^(?:SRC|EPIC|FEAT|REL|UI|TECH|DEVPLAN|TESTPLAN|TASK|TESTSET|TC|BUG|REPORT|ADR|EVI|ART)-",
                value.strip(),
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _filter_materializable_refs(values: Any) -> List[str]:
        refs = values if isinstance(values, list) else [values] if values is not None else []
        filtered: List[str] = []
        for item in refs:
            if not isinstance(item, str):
                continue
            ref = item.strip()
            if not ref:
                continue
            ref_root = ref.split("#", 1)[0]
            if LLMRunner._is_literal_ssot_ref(ref_root):
                filtered.append(ref)
        return filtered

    @staticmethod
    def _resolve_changed_file_paths(
        *,
        workspace: str,
        project_root: Optional[str],
        changed_files: List[str],
    ) -> List[str]:
        resolved_paths: List[str] = []
        project_root_path = Path(project_root or workspace).resolve()
        workspace_path = Path(workspace).resolve()
        project_relative_roots = {
            ".workflow",
            ".artifacts",
            "spec",
            "output",
            "docs",
            "tests",
            ".tmp",
        }

        for item in changed_files or []:
            if not isinstance(item, str) or not item.strip():
                continue
            candidate = Path(item)
            if candidate.is_absolute():
                resolved_paths.append(str(candidate))
                continue

            normalized = candidate.as_posix()
            project_candidate = (project_root_path / candidate).resolve()
            workspace_candidate = (workspace_path / candidate).resolve()
            root_part = normalized.split("/", 1)[0]
            if root_part in project_relative_roots:
                resolved_paths.append(str(project_candidate))
            elif project_candidate.exists() and not workspace_candidate.exists():
                resolved_paths.append(str(project_candidate))
            else:
                resolved_paths.append(str(workspace_candidate))
        return resolved_paths

    @staticmethod
    def _normalize_pm_planner_task_payload(
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if getattr(step, "agent_id", "") != "agent.product.pm_planner":
            return business_output, structured_payload
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        def _clean_text(value: Any) -> str:
            return str(value or "").strip()

        def _normalize_list(values: Any) -> List[str]:
            items = values if isinstance(values, list) else [values] if values is not None else []
            return [_clean_text(item) for item in items if _clean_text(item)]

        def _normalize_priority(value: Any) -> str:
            normalized = _clean_text(value).upper()
            if normalized in {"P0", "P1", "P2"}:
                return normalized
            lowered = _clean_text(value).lower()
            if lowered in {"critical", "high"}:
                return "P0"
            if lowered in {"medium", "normal"}:
                return "P1"
            if lowered in {"low", "minor"}:
                return "P2"
            return "P1"

        def _normalize_role(value: Any) -> str:
            normalized = _clean_text(value).lower().replace("_", "-").replace(" ", "-")
            return normalized or "workflow-runtime-owner"

        def _normalize_workstream(task: Dict[str, Any], role: str) -> str:
            explicit = _clean_text(task.get("workstream"))
            if explicit:
                return explicit
            combined = " ".join(
                [
                    _clean_text(task.get("task_id")).lower(),
                    _clean_text(task.get("title")).lower(),
                    _clean_text(task.get("description")).lower(),
                ]
            )
            if any(token in combined for token in ("migration", "registry", "compatibility", "文档", "迁移")):
                return "governance-spec"
            if role.startswith("qa"):
                return "qa-seed"
            if role.startswith("technical-writer"):
                return "governance-docs"
            return "workflow-runtime"

        def _infer_task_kind(task: Dict[str, Any], role: str, workstream: str) -> str:
            combined = " ".join(
                [
                    _clean_text(task.get("title")).lower(),
                    _clean_text(task.get("description")).lower(),
                    role.lower(),
                    workstream.lower(),
                ]
            )
            if any(token in combined for token in ("migration", "迁移")):
                return "migration"
            if any(token in combined for token in ("governance", "registry", "compatibility", "文档")):
                return "governance"
            if role.startswith("qa") or "test" in combined or "验证" in combined:
                return "validation"
            if any(token in combined for token in ("ux", "design", "ui")):
                return "ux"
            if "refactor" in combined:
                return "refactor"
            return "implementation"

        def _title_key(value: Any) -> str:
            lowered = _clean_text(value).lower()
            return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", lowered)

        def _derive_project_root_from_feat_freeze(feat_freeze_path: str) -> Optional[Path]:
            candidate = Path(feat_freeze_path)
            for parent in [candidate, *candidate.parents]:
                if parent.name == ".workflow":
                    return parent.parent
            return None

        def _extract_canonical_title_map(project_root: Optional[Path]) -> Dict[str, str]:
            if project_root is None:
                return {}
            features_dir = project_root / "spec" / "requirements" / "features"
            if not features_dir.exists():
                return {}
            title_map: Dict[str, str] = {}
            for path in sorted(features_dir.glob("*.md")):
                try:
                    text = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                if not text.startswith("---"):
                    continue
                try:
                    _, frontmatter, _ = text.split("---", 2)
                    metadata = yaml.safe_load(frontmatter) or {}
                except Exception:
                    continue
                if not isinstance(metadata, dict):
                    continue
                title = _clean_text(metadata.get("title"))
                canonical_id = _clean_text(metadata.get("id"))
                if title and canonical_id:
                    title_map[_title_key(title)] = canonical_id
            return title_map

        def _extract_source_feat_title_map(feat_freeze_path: str) -> Dict[str, str]:
            freeze_path = Path(feat_freeze_path)
            if not freeze_path.exists():
                return {}
            try:
                payload = yaml.safe_load(freeze_path.read_text(encoding="utf-8")) or {}
            except Exception:
                return {}
            title_map: Dict[str, str] = {}
            candidates = payload.get("feat_specifications")
            if not isinstance(candidates, list):
                candidates = payload.get("feat_specs")
            if not isinstance(candidates, list):
                return {}
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                feat_id = _clean_text(item.get("feat_id"))
                title = _clean_text(item.get("title"))
                if feat_id and title:
                    title_map[feat_id] = title
            return title_map

        def _build_feat_alias_map(instance_payload: Optional[Dict[str, Any]]) -> Dict[str, str]:
            if not isinstance(instance_payload, dict):
                return {}
            params = instance_payload.get("params") if isinstance(instance_payload.get("params"), dict) else {}
            feat_freeze_path = params.get("feat_freeze")
            if not isinstance(feat_freeze_path, str) or not feat_freeze_path.strip():
                return {}
            source_title_map = _extract_source_feat_title_map(feat_freeze_path)
            if not source_title_map:
                return {}
            canonical_title_map = _extract_canonical_title_map(
                _derive_project_root_from_feat_freeze(feat_freeze_path)
            )
            if not canonical_title_map:
                return {}
            alias_map: Dict[str, str] = {}
            for source_feat_id, title in source_title_map.items():
                canonical_id = canonical_title_map.get(_title_key(title))
                if canonical_id:
                    alias_map[source_feat_id] = canonical_id
            return alias_map

        feat_alias_map = _build_feat_alias_map(instance_data)

        def _build_task_markdown(task_spec: Dict[str, Any]) -> str:
            lines = [
                f"# Objective\n\n{_clean_text(task_spec.get('objective'))}\n",
                f"# Description\n\n{_clean_text(task_spec.get('description'))}\n",
            ]
            mapping = task_spec.get("acceptance_criteria_mapping")
            if isinstance(mapping, list) and mapping:
                lines.append("## Acceptance Mapping")
                for item in mapping:
                    if not isinstance(item, dict):
                        continue
                    lines.append(
                        f"- {item.get('feat', '')} / {item.get('ac', '')}: {item.get('description', '')}"
                    )
                lines.append("")
            for heading, key in (("Dependencies", "dependencies"), ("Definition Of Done", "definition_of_done")):
                values = task_spec.get(key)
                if not isinstance(values, list) or not values:
                    continue
                lines.append(f"## {heading}")
                for item in values:
                    lines.append(f"- {item}")
                lines.append("")
            return "\n".join(lines).strip() + "\n"

        payload = business_output.get("task_planning") if isinstance(business_output.get("task_planning"), dict) else business_output
        if not isinstance(payload, dict):
            return business_output, structured_payload

        if isinstance(payload.get("task_specs"), list) and payload.get("task_specs"):
            normalized_business = dict(payload)
            normalized_business["source_feats"] = [
                feat_alias_map.get(_clean_text(item), _clean_text(item))
                for item in (payload.get("source_feats") or [])
                if _clean_text(item)
            ]
            remapped_task_specs: List[Dict[str, Any]] = []
            for task_spec in payload.get("task_specs") or []:
                if not isinstance(task_spec, dict):
                    continue
                remapped_task = dict(task_spec)
                raw_source_feat = _clean_text(task_spec.get("source_feat"))
                canonical_source_feat = feat_alias_map.get(raw_source_feat, raw_source_feat) or "FEAT-001"
                remapped_task["source_feat"] = canonical_source_feat
                if isinstance(task_spec.get("source_refs"), list):
                    remapped_task["source_refs"] = [
                        f"{canonical_source_feat}#delivery"
                        if isinstance(ref, str) and ref == f"{raw_source_feat}#delivery" and canonical_source_feat
                        else ref
                        for ref in task_spec.get("source_refs") or []
                    ]
                if isinstance(task_spec.get("ssot"), dict):
                    remapped_ssot = dict(task_spec.get("ssot") or {})
                    remapped_ssot["parent"] = canonical_source_feat
                    derived_from = _clean_text(remapped_ssot.get("derived_from"))
                    if raw_source_feat and derived_from == f"{raw_source_feat}#delivery":
                        remapped_ssot["derived_from"] = f"{canonical_source_feat}#delivery"
                    remapped_task["ssot"] = remapped_ssot
                if isinstance(task_spec.get("acceptance_criteria_mapping"), list):
                    remapped_task["acceptance_criteria_mapping"] = [
                        {
                            **item,
                            "feat": canonical_source_feat if isinstance(item, dict) and _clean_text(item.get("feat")) == raw_source_feat else item.get("feat"),
                            "ac": (
                                str(item.get("ac")).replace(raw_source_feat, canonical_source_feat, 1)
                                if isinstance(item, dict) and raw_source_feat and canonical_source_feat and isinstance(item.get("ac"), str)
                                else item.get("ac")
                            ),
                        }
                        for item in task_spec.get("acceptance_criteria_mapping") or []
                        if isinstance(item, dict)
                    ]
                remapped_task_specs.append(remapped_task)
            normalized_business["task_specs"] = remapped_task_specs
        else:
            epic_ref = _clean_text(payload.get("parent_epic") or payload.get("epic_ref"))
            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            if not epic_ref:
                epic_ref = _clean_text(metadata.get("epic_id"))
            feat_tasks = payload.get("feat_tasks") if isinstance(payload.get("feat_tasks"), list) else []
            source_feats = [
                feat_alias_map.get(_clean_text(item.get("feat_id")), _clean_text(item.get("feat_id")))
                for item in feat_tasks
                if isinstance(item, dict) and _clean_text(item.get("feat_id"))
            ]

            task_specs: List[Dict[str, Any]] = []
            milestones_map: Dict[str, Dict[str, Any]] = {}
            resource_allocation: Dict[str, Dict[str, Any]] = {}
            critical_path: List[str] = []
            risk_mitigation: List[Dict[str, Any]] = []

            for feat_entry in feat_tasks:
                if not isinstance(feat_entry, dict):
                    continue
                feat_id = feat_alias_map.get(
                    _clean_text(feat_entry.get("feat_id")),
                    _clean_text(feat_entry.get("feat_id")),
                )
                phases = (
                    feat_entry.get("implementation_plan", {}).get("phases")
                    if isinstance(feat_entry.get("implementation_plan"), dict)
                    else []
                )
                for phase in phases if isinstance(phases, list) else []:
                    if not isinstance(phase, dict):
                        continue
                    milestone_id = _clean_text(phase.get("phase_id")) or f"M{len(milestones_map) + 1}"
                    milestone_name = _clean_text(phase.get("name")) or milestone_id
                    milestone = milestones_map.setdefault(
                        milestone_id,
                        {
                            "id": milestone_id,
                            "name": milestone_name,
                            "task_ids": [],
                            "acceptance_criteria": f"{feat_id} {milestone_name}".strip(),
                        },
                    )
                    tasks = phase.get("tasks") if isinstance(phase.get("tasks"), list) else []
                    for task in tasks:
                        if not isinstance(task, dict):
                            continue
                        task_id = _clean_text(task.get("task_id")) or f"{feat_id}-TASK-{len(task_specs) + 1:03d}"
                        title = _clean_text(task.get("title")) or task_id
                        description = _clean_text(task.get("description")) or title
                        role = _normalize_role(task.get("assignee_role") or task.get("responsible_role"))
                        workstream = _normalize_workstream(task, role)
                        acceptance_items = _normalize_list(task.get("acceptance_criteria"))
                        if not acceptance_items:
                            acceptance_items = [description]
                        task_specs.append(
                            {
                                "task_id": task_id,
                                "title": title,
                                "objective": acceptance_items[0],
                                "description": description,
                                "source_feat": feat_id or "FEAT-001",
                                "workstream": workstream,
                                "task_kind": _infer_task_kind(task, role, workstream),
                                "responsible_role": role,
                                "acceptance_criteria_mapping": [
                                    {
                                        "feat": feat_id or "FEAT-001",
                                        "ac": f"{feat_id or 'FEAT-001'}-AC-{index:03d}",
                                        "description": item,
                                    }
                                    for index, item in enumerate(acceptance_items, start=1)
                                ],
                                "prerequisites": _normalize_list(task.get("prerequisites")),
                                "dependencies": _normalize_list(task.get("dependencies")),
                                "definition_of_done": acceptance_items[:3] or [f"{title} completed"],
                                "priority": _normalize_priority(feat_entry.get("priority") or task.get("priority")),
                                "milestone": milestone_id,
                                "estimated_effort": _clean_text(task.get("effort") or task.get("estimated_effort") or "1 day"),
                                "lifecycle_status": "draft",
                                "observability": {
                                    "execution_unit": "task",
                                    "log_scope": "task-execution",
                                    "audit_fields": ["run_id", "task_id", "changed_files", "evidence_refs"],
                                },
                                "evidence_requirements": {
                                    "required_refs": [feat_id] if feat_id else ["delivery-plan"],
                                    "review_required": True,
                                },
                                "rollback_strategy": {
                                    "mode": "revert",
                                    "restore_targets": [workstream],
                                },
                                "source_refs": [f"{feat_id}#delivery"] if feat_id and LLMRunner._is_literal_ssot_ref(feat_id) else [],
                                "ssot": {
                                    "identity_kind": "ssot",
                                    "ssot_type": "TASK",
                                    "parent": feat_id or "FEAT-001",
                                    "derived_from": f"{feat_id}#delivery" if feat_id else "delivery-plan",
                                },
                            }
                        )
                        milestone["task_ids"].append(task_id)
                        critical_path.append(task_id)
                        resource_allocation.setdefault(role, {"tasks": []})
                        resource_allocation[role]["tasks"].append(task_id)

            if not task_specs:
                task_hierarchy = payload.get("task_hierarchy") if isinstance(payload.get("task_hierarchy"), list) else []
                seen_source_feats: set[str] = set(source_feats)
                for phase in task_hierarchy:
                    if not isinstance(phase, dict):
                        continue
                    milestone_id = _clean_text(phase.get("phase_id")) or f"M{len(milestones_map) + 1}"
                    milestone_name = _clean_text(phase.get("phase")) or _clean_text(phase.get("name")) or milestone_id
                    milestone = milestones_map.setdefault(
                        milestone_id,
                        {
                            "id": milestone_id,
                            "name": milestone_name,
                            "task_ids": [],
                            "acceptance_criteria": f"{milestone_name} completed",
                        },
                    )
                    tasks = phase.get("tasks") if isinstance(phase.get("tasks"), list) else []
                    for task in tasks:
                        if not isinstance(task, dict):
                            continue
                        raw_feat_id = _clean_text(
                            task.get("related_feat") or task.get("source_feat") or task.get("feat_id")
                        )
                        feat_id = feat_alias_map.get(raw_feat_id, raw_feat_id)
                        if feat_id and feat_id not in seen_source_feats:
                            source_feats.append(feat_id)
                            seen_source_feats.add(feat_id)
                        task_id = _clean_text(task.get("task_id")) or f"{feat_id or 'FEAT-001'}-TASK-{len(task_specs) + 1:03d}"
                        title = _clean_text(task.get("title")) or task_id
                        description = _clean_text(task.get("description")) or title
                        role = _normalize_role(task.get("assignee_role") or task.get("responsible_role"))
                        workstream = _normalize_workstream(task, role)
                        acceptance_items = _normalize_list(task.get("acceptance_criteria"))
                        if not acceptance_items:
                            acceptance_items = [description]
                        estimated_effort = _clean_text(task.get("estimated_effort") or task.get("effort"))
                        if not estimated_effort and task.get("story_points") is not None:
                            estimated_effort = f"{_clean_text(task.get('story_points'))} points"
                        task_specs.append(
                            {
                                "task_id": task_id,
                                "title": title,
                                "objective": acceptance_items[0],
                                "description": description,
                                "source_feat": feat_id or "FEAT-001",
                                "workstream": workstream,
                                "task_kind": _infer_task_kind(task, role, workstream),
                                "responsible_role": role,
                                "acceptance_criteria_mapping": [
                                    {
                                        "feat": feat_id or "FEAT-001",
                                        "ac": f"{feat_id or 'FEAT-001'}-AC-{index:03d}",
                                        "description": item,
                                    }
                                    for index, item in enumerate(acceptance_items, start=1)
                                ],
                                "prerequisites": _normalize_list(task.get("prerequisites")),
                                "dependencies": _normalize_list(task.get("dependencies")),
                                "definition_of_done": acceptance_items[:3] or [f"{title} completed"],
                                "priority": _normalize_priority(task.get("priority")),
                                "milestone": milestone_id,
                                "estimated_effort": estimated_effort or "1 day",
                                "lifecycle_status": "draft",
                                "observability": {
                                    "execution_unit": "task",
                                    "log_scope": "task-execution",
                                    "audit_fields": ["run_id", "task_id", "changed_files", "evidence_refs"],
                                },
                                "evidence_requirements": {
                                    "required_refs": [feat_id] if feat_id else ["delivery-plan"],
                                    "review_required": True,
                                },
                                "rollback_strategy": {
                                    "mode": "revert",
                                    "restore_targets": [workstream],
                                },
                                "source_refs": [f"{feat_id}#delivery"] if feat_id and LLMRunner._is_literal_ssot_ref(feat_id) else [],
                                "ssot": {
                                    "identity_kind": "ssot",
                                    "ssot_type": "TASK",
                                    "parent": feat_id or "FEAT-001",
                                    "derived_from": f"{feat_id}#delivery" if feat_id else "delivery-plan",
                                },
                            }
                        )
                        milestone["task_ids"].append(task_id)
                        critical_path.append(task_id)
                        resource_allocation.setdefault(role, {"tasks": []})
                        resource_allocation[role]["tasks"].append(task_id)

            raw_risks = payload.get("risks") if isinstance(payload.get("risks"), list) else []
            for risk in raw_risks:
                if not isinstance(risk, dict):
                    continue
                affected_tasks = _normalize_list(risk.get("affected_tasks")) or critical_path[:2]
                if not affected_tasks and task_specs:
                    affected_tasks = [str(task_specs[0].get("task_id"))]
                risk_mitigation.append(
                    {
                        "risk": _clean_text(risk.get("description") or risk.get("title") or risk.get("risk_id") or "planning-risk"),
                        "mitigation": _clean_text(risk.get("mitigation") or risk.get("fallback") or "Track in delivery review"),
                        "affected_tasks": affected_tasks,
                    }
                )

            normalized_business = {
                "parent_epic": epic_ref or "EPIC-001",
                "source_feats": source_feats or ["FEAT-001"],
                "planning_metadata": {
                    "planning_timestamp": _clean_text(payload.get("created_at")) or datetime.now().strftime("%Y-%m-%d"),
                    "project_profile": "legacy_task_planning_view",
                    "task_directory": f"spec/tasks/{(source_feats or ['FEAT-001'])[0]}",
                },
                "task_specs": task_specs,
                "milestones": list(milestones_map.values()) or [
                    {
                        "id": "M1",
                        "name": "Initial Delivery Plan",
                        "task_ids": [item.get("task_id") for item in task_specs[:1] if isinstance(item, dict)],
                        "acceptance_criteria": "Delivery plan created",
                    }
                ],
                "dependency_graph": {
                    "critical_path": critical_path or [item.get("task_id") for item in task_specs[:1] if isinstance(item, dict)],
                },
                "resource_allocation": resource_allocation or {"workflow-runtime-owner": {"tasks": []}},
                "risk_mitigation": risk_mitigation,
            }

        normalized_structured = LLMRunner._ensure_structured_envelope(
            business_output=normalized_business,
            structured_payload=structured_payload,
        )
        task_specs = normalized_business.get("task_specs") if isinstance(normalized_business.get("task_specs"), list) else []
        outputs: List[Dict[str, Any]] = []
        for index, task_spec in enumerate(task_specs, start=1):
            if not isinstance(task_spec, dict):
                continue
            task_id = _clean_text(task_spec.get("task_id")) or f"TASK-{index:03d}"
            title = _clean_text(task_spec.get("title")) or task_id
            source_feat = _clean_text(task_spec.get("source_feat")) or "FEAT-001"
            output_key = re.sub(r"[^a-z0-9_]+", "_", task_id.lower()).strip("_") or f"task_{index:03d}"
            output_item = {
                "key": output_key,
                "identity_kind": "ssot",
                "ssot_type": "task",
                "title": title,
                "parent": source_feat,
                "content": _build_task_markdown(task_spec),
                "properties": {
                    "feat_id": source_feat,
                    "task_id": task_id,
                    "slice_key": _clean_text(task_spec.get("task_kind")) or "implementation",
                    "workstream": _clean_text(task_spec.get("workstream")) or "workflow-runtime",
                },
            }
            if LLMRunner._is_literal_ssot_ref(source_feat):
                output_item["source_refs"] = [f"{source_feat}#delivery"]
                output_item["verifies"] = [source_feat]
            outputs.append(output_item)
        normalized_structured["ssot_output_contract"] = {
            "contract_version": "1.0",
            "run_id": workflow_id,
            "outputs": outputs,
        }
        return normalized_business, normalized_structured

    @staticmethod
    def _synthesize_single_ssot_payload(
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
    ) -> tuple[Any, Any]:
        if not isinstance(business_output, dict):
            return business_output, structured_payload
        if isinstance(structured_payload, dict) and isinstance(structured_payload.get("ssot_output_contract"), dict):
            return business_output, structured_payload

        agent_id = getattr(step, "agent_id", "") or ""
        step_id = getattr(step, "id", "") or ""
        if agent_id == "agent.product.epic_designer":
            payload = LLMRunner._ensure_structured_envelope(
                business_output=business_output,
                structured_payload=structured_payload,
            )
            payload["ssot_output_contract"] = {
                "contract_version": "1.0",
                "run_id": workflow_id,
                "outputs": [
                    {
                        "key": "epic",
                        "identity_kind": "ssot",
                        "ssot_type": "epic",
                        "title": str(business_output.get("title") or "EPIC").strip() or "EPIC",
                        "content": yaml.safe_dump(business_output, allow_unicode=True, sort_keys=False),
                    }
                ],
            }
            return business_output, payload

        if step_id == "source_normalization":
            normalized_content = (
                business_output.get("normalized_content")
                if isinstance(business_output.get("normalized_content"), dict)
                else {}
            )
            payload = LLMRunner._ensure_structured_envelope(
                business_output=business_output,
                structured_payload=structured_payload,
            )
            payload["ssot_output_contract"] = {
                "contract_version": "1.0",
                "run_id": workflow_id,
                "outputs": [
                    {
                        "key": "src",
                        "identity_kind": "ssot",
                        "ssot_type": "src",
                        "title": (
                            str(
                                business_output.get("title")
                                or normalized_content.get("title")
                                or business_output.get("src_id")
                                or "SRC"
                            ).strip()
                            or "SRC"
                        ),
                        "content": yaml.safe_dump(business_output, allow_unicode=True, sort_keys=False),
                    }
                ],
            }
            return business_output, payload

        return business_output, structured_payload

    @staticmethod
    def _normalize_business_payload(
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        business_output, structured_payload = LLMRunner._normalize_requirement_decomposer_payload(
            step=step,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )
        business_output, structured_payload = LLMRunner._normalize_prd_writer_feat_payload(
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )
        business_output, structured_payload = LLMRunner._normalize_pm_planner_task_payload(
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=instance_data,
        )
        business_output, structured_payload = LLMRunner._normalize_product_review_payload(
            step=step,
            business_output=business_output,
            structured_payload=structured_payload,
        )
        return LLMRunner._synthesize_single_ssot_payload(
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
        )

    @staticmethod
    def _normalize_product_review_payload(
        step,
        business_output: Any,
        structured_payload: Any,
    ) -> tuple[Any, Any]:
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        normalized_business = dict(business_output)
        if (
            getattr(step, "agent_id", "") == "agent.product.feat_reviewer"
            and normalized_business.get("review_type") is None
        ):
            normalized_business["review_type"] = "feat_review"
            normalized_business.setdefault("summary", normalized_business.get("review_summary") or "")
            feat_reviews = normalized_business.get("feat_reviews")
            if isinstance(feat_reviews, list):
                normalized_business.setdefault(
                    "subject_refs",
                    [
                        str(item.get("feat_id")).strip()
                        for item in feat_reviews
                        if isinstance(item, dict) and str(item.get("feat_id") or "").strip()
                    ],
                )
                if "findings" not in normalized_business:
                    findings = [
                        str(item.get("notes")).strip()
                        for item in feat_reviews
                        if isinstance(item, dict)
                        and str(item.get("status") or "").strip().lower()
                        not in {"approved", "pass", "passed", "approved_with_notes", "approved_with_recommendations"}
                        and str(item.get("notes") or "").strip()
                    ]
                    normalized_business["findings"] = findings
                if not isinstance(normalized_business.get("recommendations"), list):
                    normalized_business["recommendations"] = []
                for item in feat_reviews:
                    if not isinstance(item, dict):
                        continue
                    item_status = str(item.get("status") or "").strip().lower()
                    note = str(item.get("notes") or "").strip()
                    if item_status in {"approved_with_notes", "approved_with_recommendations"} and note:
                        normalized_business["recommendations"].append(note)
            recommendations = normalized_business.get("recommendations")
            if not isinstance(recommendations, list):
                normalized_business["recommendations"] = []
            normalized_business.setdefault("risks", [])
            status_text = str(normalized_business.get("status") or "").strip().lower()
            if normalized_business.get("decision") not in {"pass", "revise", "reject"}:
                if status_text in {"approved", "approved_with_recommendations", "approved_with_notes"}:
                    normalized_business["decision"] = "pass"
                elif status_text in {"revise", "needs_revision", "changes_requested"}:
                    normalized_business["decision"] = "revise"
                elif status_text in {"rejected", "reject", "failed"}:
                    normalized_business["decision"] = "reject"
            if "findings" not in normalized_business:
                normalized_business["findings"] = []

        review_type = normalized_business.get("review_type")
        if review_type not in {"source_review", "epic_review", "feat_review", "delivery_plan_review"}:
            return business_output, structured_payload

        if normalized_business.get("decision") not in {"pass", "revise", "reject"}:
            candidate = (
                normalized_business.get("status")
                or normalized_business.get("review_status")
                or normalized_business.get("approval_decision")
            )
            decision_map = {
                "pass": "pass",
                "passed": "pass",
                "approved": "pass",
                "approve": "pass",
                "success": "pass",
                "ok": "pass",
                "revise": "revise",
                "revision_required": "revise",
                "needs_revision": "revise",
                "needs_revise": "revise",
                "changes_requested": "revise",
                "approved_with_recommendations": "pass",
                "approved_with_notes": "pass",
                "reject": "reject",
                "rejected": "reject",
                "fail": "reject",
                "failed": "reject",
            }
            normalized_candidate = str(candidate or "").strip().lower()
            normalized_decision = decision_map.get(normalized_candidate)
            if normalized_decision:
                normalized_business["decision"] = normalized_decision
        if not isinstance(normalized_business.get("summary"), str):
            normalized_business["summary"] = str(
                normalized_business.get("review_summary")
                or normalized_business.get("summary")
                or ""
            ).strip()
        for field_name in ("subject_refs", "findings", "risks", "recommendations"):
            value = normalized_business.get(field_name)
            if isinstance(value, list):
                normalized_business[field_name] = [str(item).strip() for item in value if str(item).strip()]
            elif field_name == "subject_refs":
                normalized_business[field_name] = []
            else:
                normalized_business[field_name] = []

        normalized_structured = structured_payload
        if (
            isinstance(structured_payload, dict)
            and isinstance(structured_payload.get("business_output"), dict)
        ):
            normalized_structured = dict(structured_payload)
            normalized_structured["business_output"] = normalized_business

        return normalized_business, normalized_structured

    @staticmethod
    def _build_schema_repair_prompt(
        *,
        step,
        validation_error: str,
        business_output: Any,
        structured_payload: Any,
    ) -> str:
        payload = business_output
        if not isinstance(payload, dict) and isinstance(structured_payload, dict):
            payload = structured_payload

        payload_text = json.dumps(
            payload if payload is not None else {},
            ensure_ascii=False,
            indent=2,
        )
        return (
            "修复下面这个结构化输出，使其满足当前 step 的 output contract。\n"
            "只允许返回最终 JSON 对象，不要输出解释、标题、代码块或额外包裹层。\n"
            f"step_id: {getattr(step, 'id', '')}\n"
            f"validation_error: {validation_error}\n"
            "要求：\n"
            "- 保留原始语义，不要重新发明业务内容\n"
            "- 仅补足缺失字段、修正字段名或枚举值、规范结构\n"
            "- 如果原输出里缺少必要结论字段，请基于已有 summary/findings/risks/recommendations 做最小修复\n"
            "- 返回内容必须是可直接通过 schema 校验的单个 JSON 对象\n"
            "原始 payload:\n"
            f"{payload_text}"
        )

    @classmethod
    def _build_schema_repair_input(
        cls,
        *,
        executor_type: str,
        input_data: Dict[str, Any],
        step,
        validation_error: str,
        business_output: Any,
        structured_payload: Any,
    ) -> Dict[str, Any]:
        repair_prompt = cls._build_schema_repair_prompt(
            step=step,
            validation_error=validation_error,
            business_output=business_output,
            structured_payload=structured_payload,
        )
        repaired_input = dict(input_data)
        if executor_type in ("codex", "claude_code"):
            repaired_input["goal"] = repair_prompt
            repaired_input["context_files"] = []
            repaired_input["write_scope"] = []
            repaired_input["max_iterations"] = 1
            repaired_input["allowed_commands"] = []
            repaired_input["system_prompt_extra"] = (
                "你正在执行 schema repair retry。"
                "不要修改文件，不要调用命令，只输出最终 JSON 对象。"
            )
        else:
            repaired_input["prompt"] = repair_prompt
            repaired_input["system_message"] = (
                "You are repairing structured output to satisfy a JSON schema. "
                "Return only a single JSON object."
            )
            repaired_input["temperature"] = 0
        return repaired_input

    async def _attempt_schema_repair(
        self,
        *,
        executor,
        executor_type: str,
        input_data: Dict[str, Any],
        step,
        workflow_id: str,
        validation_error: str,
        business_output: Any,
        structured_payload: Any,
    ) -> Optional[Dict[str, Any]]:
        repair_input = self._build_schema_repair_input(
            executor_type=executor_type,
            input_data=input_data,
            step=step,
            validation_error=validation_error,
            business_output=business_output,
            structured_payload=structured_payload,
        )

        retry_executor = AsyncRetryExecutor(
            policy=RetryPolicy(max_retries=0, base_delay=0, jitter=False)
        )
        repair_result = await retry_executor.execute(executor.execute, repair_input)
        if not repair_result.success:
            return None

        repaired_output = repair_result.result
        if not isinstance(repaired_output, dict):
            return None

        if executor_type in ("codex", "claude_code"):
            repaired_business_output, repaired_structured_payload = ClaudeCodeRunner._extract_business_output_for_validation(
                step=step,
                workflow_id=workflow_id,
                output=repaired_output,
                written_files=[],
            )
        else:
            repaired_generated_text = repaired_output.get("generated_text", "") or ""
            repaired_structured_payload = self._parse_structured_output_if_possible(repaired_generated_text)
            repaired_business_output = self._extract_business_output_payload(
                repaired_structured_payload,
                repaired_generated_text,
                step=step,
                written_files=[],
            )
            repaired_business_output, repaired_structured_payload = self._normalize_business_payload(
                step=step,
                workflow_id=workflow_id,
                business_output=repaired_business_output,
                structured_payload=repaired_structured_payload,
            )

        if not isinstance(repaired_business_output, dict):
            return None

        return {
            "output": repaired_output,
            "business_output": repaired_business_output,
            "structured_payload": repaired_structured_payload,
        }

    @staticmethod
    def _validate_feat_review_subject_refs(
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        if not expected_subject_refs:
            return None
        if not isinstance(review_payload, dict):
            return "FEAT review output is not a structured object"

        subject_refs = review_payload.get("subject_refs")
        if not isinstance(subject_refs, list):
            return "FEAT review output missing subject_refs list"

        expected = {ref for ref in expected_subject_refs if isinstance(ref, str) and ref.strip()}
        actual = {ref for ref in subject_refs if isinstance(ref, str) and ref.strip()}
        if not expected.issubset(actual):
            return (
                "FEAT review subject_refs must include the reviewed FEAT ID(s): "
                + ", ".join(sorted(expected))
            )
        return None

    @staticmethod
    def _validate_feat_review_semantics(
        review_payload: Any,
        expected_subject_refs: List[str],
    ) -> Optional[str]:
        if not isinstance(review_payload, dict):
            return "FEAT review output is not a structured object"

        review_type = review_payload.get("review_type")
        if review_type != "feat_review":
            return "FEAT review output must set review_type=feat_review"

        summary = review_payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            return "FEAT review output must include a non-empty summary"

        decision = review_payload.get("decision")
        if decision not in {"pass", "revise", "reject"}:
            return "FEAT review output decision must be one of: pass, revise, reject"

        for field_name in ("findings", "risks", "recommendations"):
            value = review_payload.get(field_name)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                return f"FEAT review output field '{field_name}' must be a string array"

        subject_refs = review_payload.get("subject_refs")
        if not isinstance(subject_refs, list):
            return "FEAT review output missing subject_refs list"

        expected = [ref for ref in expected_subject_refs if isinstance(ref, str) and ref.strip()]
        actual = [ref for ref in subject_refs if isinstance(ref, str) and ref.strip()]
        if expected and sorted(actual) != sorted(expected):
            return (
                "FEAT review subject_refs must exactly match the reviewed FEAT ID(s): "
                + ", ".join(sorted(expected))
            )

        findings = review_payload.get("findings") or []
        if decision == "pass":
            if findings:
                return "FEAT review output with decision=pass must not include findings"
            if LLMRunner._contains_feat_review_negative_signal(summary):
                return "FEAT review summary conflicts with decision=pass"

        if decision in {"revise", "reject"} and not findings:
            return f"FEAT review output with decision={decision} must include at least one finding"

        return None

    @staticmethod
    def _contains_feat_review_negative_signal(text: Any) -> bool:
        if not isinstance(text, str):
            return False
        normalized = text.strip().lower()
        if not normalized:
            return False

        patterns = [
            r"\bblocker\b",
            r"\bmajor\b",
            r"\breject\b",
            r"\brevise\b",
            r"\bmust fix\b",
            r"\bcritical issue\b",
            r"阻塞",
            r"不通过",
            r"拒绝",
            r"驳回",
            r"需修订",
            r"需要修订",
            r"必须修复",
            r"关键问题",
            r"严重问题",
            r"不可通过",
        ]
        return any(re.search(pattern, normalized) for pattern in patterns)

    @classmethod
    def _extract_topic_families(cls, text: Any) -> set[str]:
        if not isinstance(text, str):
            return set()
        normalized = text.lower()
        families: set[str] = set()
        for family, keywords in cls.FEAT_TOPIC_FAMILIES.items():
            for keyword in keywords:
                if not keyword:
                    continue
                lowered = keyword.lower()
                if re.search(r"[a-z]", lowered):
                    if re.search(rf"\b{re.escape(lowered)}\b", normalized):
                        families.add(family)
                        break
                elif lowered in normalized:
                    families.add(family)
                    break
        return families

    @staticmethod
    def _load_ssot_markdown(project_root: str, artifact_id: str) -> Optional[str]:
        if not artifact_id:
            return None
        try:
            from lee.orchestrator.execution.artifacts.manager import ArtifactManager

            manager = ArtifactManager(project_root=Path(project_root))
            content = manager.get_content(artifact_id)
            if isinstance(content, bytes):
                try:
                    return content.decode("utf-8")
                except UnicodeDecodeError:
                    return None
            if isinstance(content, str):
                return content
        except Exception:
            pass

        project_root_path = Path(project_root)
        candidates = list(project_root_path.glob(f"spec/**/*{artifact_id}__*.md"))
        if not candidates:
            return None
        try:
            return candidates[0].read_text(encoding="utf-8")
        except OSError:
            return None

    @classmethod
    def _validate_feat_bundle_epic_semantics(
        cls,
        *,
        project_root: str,
        business_output: Any,
    ) -> Optional[str]:
        if not isinstance(business_output, dict):
            return None
        epic_ref = business_output.get("epic_ref")
        feat_specs = business_output.get("feat_specs")
        if not isinstance(epic_ref, str) or not epic_ref.strip():
            return None
        if not isinstance(feat_specs, list) or not feat_specs:
            return None

        epic_markdown = cls._load_ssot_markdown(project_root, epic_ref.strip())
        if not isinstance(epic_markdown, str) or not epic_markdown.strip():
            return None

        epic_families = cls._extract_topic_families(epic_markdown)
        if not epic_families:
            return None

        feat_fragments: List[str] = []
        for feat_spec in feat_specs:
            if not isinstance(feat_spec, dict):
                continue
            for key in ("title", "goal", "user_value"):
                value = feat_spec.get(key)
                if isinstance(value, str) and value.strip():
                    feat_fragments.append(value.strip())
            for key in ("inputs", "processing", "outputs", "acceptance_criteria", "dependencies", "non_goals"):
                value = feat_spec.get(key)
                if isinstance(value, list):
                    feat_fragments.extend(str(item).strip() for item in value if str(item).strip())

        feat_text = "\n".join(feat_fragments)
        feat_families = cls._extract_topic_families(feat_text)
        if feat_families and epic_families.isdisjoint(feat_families):
            return (
                f"FEAT bundle semantics drift from {epic_ref}: "
                f"epic topic families={sorted(epic_families)}, "
                f"feat topic families={sorted(feat_families)}"
            )
        return None

    @staticmethod
    def _extract_primary_file_output(step, written_files: List[str]) -> Optional[Any]:
        file_specs = [
            output
            for output in (getattr(step, "outputs", None) or [])
            if getattr(output, "type", None) == "file"
        ]
        if len(file_specs) != 1 or not written_files:
            return None
        spec_filename = Path(getattr(file_specs[0], "path", "")).name
        for file_path in written_files:
            if Path(file_path).name != spec_filename:
                continue
            try:
                return StepRunnerBase._parse_structured_output(
                    Path(file_path).read_text(encoding="utf-8")
                )
            except Exception:
                return None
        return None

    @staticmethod
    def _unwrap_business_output_candidate(payload: Any) -> Any:
        if isinstance(payload, dict) and "business_output" in payload:
            return payload["business_output"]
        return payload

    @staticmethod
    def _coerce_single_prd_writer_feat_candidate(payload: Any) -> Optional[Dict[str, Any]]:
        candidate = LLMRunner._unwrap_business_output_candidate(payload)
        if not isinstance(candidate, dict):
            return None

        feat_id = str(
            candidate.get("feat_id")
            or candidate.get("id")
            or candidate.get("parent_feat")
            or candidate.get("symbol_id")
            or ""
        ).strip()
        title = str(candidate.get("title") or candidate.get("name") or "").strip()
        if not feat_id or not title:
            return None

        kind = str(candidate.get("kind") or "").strip().lower()
        specification = candidate.get("specification") if isinstance(candidate.get("specification"), dict) else {}
        overview = specification.get("overview") if isinstance(specification.get("overview"), dict) else {}
        objective = str(
            candidate.get("goal")
            or candidate.get("objective")
            or overview.get("summary")
            or ""
        ).strip()
        if kind not in {"feat_specification", "feat_spec", "feat"} and not objective:
            return None

        dependencies = candidate.get("dependencies") or candidate.get("depends_on") or []
        if isinstance(dependencies, str):
            dependencies = [dependencies]

        interface_spec = specification.get("technical_specifications", {}).get("interfaces", {}) if isinstance(
            specification.get("technical_specifications"), dict
        ) else {}
        input_fields = (
            interface_spec.get("input", {}).get("fields")
            if isinstance(interface_spec.get("input"), dict)
            else []
        ) or []
        output_fields = (
            interface_spec.get("output", {}).get("fields")
            if isinstance(interface_spec.get("output"), dict)
            else []
        ) or []
        functional_requirements = specification.get("functional_requirements") if isinstance(
            specification.get("functional_requirements"), list
        ) else []
        aggregated_acceptance: List[str] = []
        for requirement in functional_requirements[:5]:
            if not isinstance(requirement, dict):
                continue
            for item in requirement.get("acceptance_criteria") or []:
                if isinstance(item, str) and item.strip():
                    aggregated_acceptance.append(item.strip())
        if not aggregated_acceptance and objective:
            aggregated_acceptance = [objective]

        return {
            "feat_id": feat_id,
            "title": title,
            "goal": objective,
            "user_value": candidate.get("user_value") or objective or title,
            "inputs": candidate.get("inputs")
            or candidate.get("input")
            or [field.get("name") for field in input_fields if isinstance(field, dict) and field.get("name")],
            "processing": candidate.get("processing")
            or [req.get("requirement") for req in functional_requirements if isinstance(req, dict) and req.get("requirement")],
            "outputs": candidate.get("outputs")
            or candidate.get("output")
            or [field.get("name") for field in output_fields if isinstance(field, dict) and field.get("name")],
            "acceptance_criteria": candidate.get("acceptance_criteria")
            or candidate.get("acceptance_boundaries")
            or aggregated_acceptance,
            "dependencies": dependencies,
            "non_goals": candidate.get("non_goals"),
            "priority": candidate.get("priority"),
            "delivery_slice": candidate.get("delivery_slice") or candidate.get("category"),
            "lifecycle_status": candidate.get("lifecycle_status") or candidate.get("status"),
            "epic_ref": candidate.get("epic_ref") or candidate.get("parent_epic"),
            "source_refs": candidate.get("source_refs"),
        }

    @classmethod
    def _referenced_written_files(cls, file_path: str, payload: Any) -> List[str]:
        candidate = cls._unwrap_business_output_candidate(payload)
        if not isinstance(candidate, dict):
            return []

        references: List[str] = []
        deliverables = candidate.get("deliverables")
        if not isinstance(deliverables, list):
            return references

        base_path = Path(file_path).parent
        for item in deliverables:
            if not isinstance(item, dict):
                continue
            referenced_path = item.get("file_path")
            if not isinstance(referenced_path, str) or not referenced_path.strip():
                continue
            resolved_path = Path(referenced_path)
            if not resolved_path.is_absolute():
                resolved_path = (base_path / resolved_path).resolve()
            if resolved_path.exists():
                references.append(str(resolved_path))
        return references

    @classmethod
    def _score_written_output_candidate(cls, step, payload: Any) -> int:
        candidate = cls._unwrap_business_output_candidate(payload)
        if not isinstance(candidate, dict):
            return -1

        score = 1
        agent_id = getattr(step, "agent_id", "")
        if agent_id == "agent.product.prd_writer":
            if isinstance(candidate.get("feat_specs"), list):
                score += 100
            if isinstance(candidate.get("features"), list):
                score += 90
            if isinstance(candidate.get("feat_candidates"), list):
                score += 80
            if isinstance(candidate.get("epic_breakdowns"), list):
                score += 70
            if isinstance(candidate.get("feats"), list):
                score += 65
            if cls._coerce_single_prd_writer_feat_candidate(payload):
                score += 60
            if isinstance(candidate.get("epic_ref"), str) and candidate.get("epic_ref").strip():
                score += 10
        elif agent_id == "agent.product.requirement_decomposer":
            if isinstance(candidate.get("feat_candidates"), list):
                score += 100
            if isinstance(candidate.get("features"), list):
                score += 90
            if isinstance(candidate.get("epic_breakdowns"), list):
                score += 80
            if isinstance(candidate.get("breakdown_id"), str) and candidate.get("breakdown_id").strip():
                score += 10
        elif agent_id == "agent.product.pm_planner":
            if isinstance(candidate.get("task_specs"), list) and candidate.get("task_specs"):
                score += 100
            if isinstance(candidate.get("task_hierarchy"), list) and candidate.get("task_hierarchy"):
                score += 95
            if isinstance(candidate.get("task_planning"), dict):
                score += 80
            metadata = candidate.get("metadata")
            if isinstance(metadata, dict) and isinstance(metadata.get("epic_id"), str) and metadata.get("epic_id").strip():
                score += 10
        elif isinstance(candidate.get("business_output"), dict):
                score += 10
        return score

    @classmethod
    def _build_prd_writer_bundle_from_written_files(cls, written_files: List[str]) -> Optional[Dict[str, Any]]:
        feat_specs: List[Dict[str, Any]] = []
        epic_ref: Optional[str] = None
        pending_files = list(written_files)
        seen_files: set[str] = set()
        direct_bundle_candidates: List[Dict[str, Any]] = []

        if written_files:
            workspace_dir = Path(written_files[0]).parent
            upstream_boundary_dir = workspace_dir.parent / "feat_boundary_design"
            if upstream_boundary_dir.exists():
                for candidate_name in (
                    "feat_breakdown.yaml",
                    "feat-breakdown.yaml",
                    "business_output.yaml",
                    "structured_payload.yaml",
                ):
                    candidate_path = upstream_boundary_dir / candidate_name
                    if candidate_path.exists():
                        pending_files.append(str(candidate_path))

        while pending_files:
            file_path = pending_files.pop(0)
            if file_path in seen_files:
                continue
            seen_files.add(file_path)
            try:
                parsed_file = StepRunnerBase._parse_structured_output(
                    Path(file_path).read_text(encoding="utf-8")
                )
            except Exception:
                continue

            for referenced_file in cls._referenced_written_files(file_path, parsed_file):
                if referenced_file not in seen_files:
                    pending_files.append(referenced_file)

            unwrapped = cls._unwrap_business_output_candidate(parsed_file)
            if isinstance(unwrapped, dict) and any(
                isinstance(unwrapped.get(key), list)
                for key in ("feat_specs", "features", "feats", "feat_candidates", "epic_breakdowns")
            ):
                direct_bundle_candidates.append(unwrapped)
                continue

            coerced_feat = cls._coerce_single_prd_writer_feat_candidate(parsed_file)
            if not isinstance(coerced_feat, dict):
                continue
            feat_specs.append(coerced_feat)
            if epic_ref is None:
                candidate_epic_ref = str(coerced_feat.get("epic_ref") or "").strip()
                if candidate_epic_ref:
                    epic_ref = candidate_epic_ref

        if not feat_specs:
            for candidate in direct_bundle_candidates:
                if isinstance(candidate.get("epic_ref"), str) and candidate.get("epic_ref").strip():
                    return candidate
            return direct_bundle_candidates[0] if direct_bundle_candidates else None
        return {
            "epic_ref": epic_ref,
            "feat_specs": feat_specs,
        }

    @classmethod
    def _extract_best_written_file_payload(cls, step, written_files: List[str]) -> Optional[Any]:
        if getattr(step, "agent_id", "") == "agent.product.prd_writer":
            aggregated_bundle = cls._build_prd_writer_bundle_from_written_files(written_files)
            if aggregated_bundle is not None:
                return aggregated_bundle

        best_payload: Optional[Any] = None
        best_score = -1
        for file_path in written_files:
            try:
                parsed_file = StepRunnerBase._parse_structured_output(
                    Path(file_path).read_text(encoding="utf-8")
                )
            except Exception:
                continue
            score = cls._score_written_output_candidate(step, parsed_file)
            if score > best_score:
                best_score = score
                best_payload = parsed_file
        return best_payload

    def _extract_structured_segment_payload(
        self,
        generated_text: str,
        segment_name: str,
    ) -> Optional[Any]:
        segment = self._extract_named_output_segment(generated_text, segment_name)
        if not segment or segment.strip() == (generated_text or "").strip():
            heading_pattern = (
                rf"(?ms)^(?:#+|\d+\.)\s*`?{re.escape(segment_name)}`?\s*\n"
                rf"(?:```[a-zA-Z0-9_-]*\n)?(.*?)(?:```|\n(?:#+|\d+\.)\s+|\Z)"
            )
            match = re.search(heading_pattern, generated_text or "")
            if match:
                segment = match.group(1).strip()
        if not segment or segment.strip() == (generated_text or "").strip():
            plain_label_pattern = (
                rf"(?ms)^\s*{re.escape(segment_name)}\s*\n"
                rf"```[a-zA-Z0-9_-]*\n(.*?)```"
            )
            match = re.search(plain_label_pattern, generated_text or "")
            if match:
                segment = match.group(1).strip()
        if not segment or segment.strip() == (generated_text or "").strip():
            return None
        try:
            return self._parse_structured_output(segment)
        except ValueError:
            return None

    def _extract_structured_payload_from_code_blocks(
        self,
        generated_text: str,
        segment_name: str,
    ) -> Optional[Any]:
        pattern = r"```(?:yaml|yml|json)?\n(.*?)```"
        for match in re.finditer(pattern, generated_text or "", re.DOTALL):
            candidate = match.group(1).strip()
            if segment_name not in candidate:
                continue
            parsed = self._parse_structured_output_if_possible(candidate)
            if not isinstance(parsed, dict):
                continue
            if segment_name in parsed:
                return parsed[segment_name]
            if "contract_version" in parsed and "outputs" in parsed:
                return parsed
        return None

    def _extract_ssot_contract_payload(
        self,
        structured_payload: Optional[Any],
        generated_text: str = "",
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(structured_payload, dict):
            payload = self._extract_structured_segment_payload(generated_text, "ssot_output_contract")
            payload = self._coerce_ssot_contract_dict(payload)
            if isinstance(payload, dict):
                return payload
            block_payload = self._extract_structured_payload_from_code_blocks(
                generated_text,
                "ssot_output_contract",
            )
            block_payload = self._coerce_ssot_contract_dict(block_payload)
            return block_payload if isinstance(block_payload, dict) else None
        if "contract_version" in structured_payload and "outputs" in structured_payload:
            return structured_payload
        payload = self._coerce_ssot_contract_dict(structured_payload.get("ssot_output_contract"))
        if isinstance(payload, dict):
            return payload
        segment_payload = self._coerce_ssot_contract_dict(
            self._extract_structured_segment_payload(generated_text, "ssot_output_contract")
        )
        if isinstance(segment_payload, dict):
            return segment_payload
        block_payload = self._coerce_ssot_contract_dict(
            self._extract_structured_payload_from_code_blocks(
                generated_text,
                "ssot_output_contract",
            )
        )
        if isinstance(block_payload, dict):
            return block_payload
        return None

    @staticmethod
    def _coerce_ssot_contract_dict(payload: Optional[Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        if "contract_version" in payload and "outputs" in payload:
            return payload
        nested = payload.get("ssot_output_contract")
        if isinstance(nested, dict):
            return nested
        return None

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

    DEFAULT_CLAUDE_CODE_FORBIDDEN_READ_PATHS = LLMRunner.DEFAULT_CLAUDE_CODE_FORBIDDEN_READ_PATHS
    FEAT_TOPIC_FAMILIES = LLMRunner.FEAT_TOPIC_FAMILIES
    _attempt_schema_repair = LLMRunner._attempt_schema_repair
    _build_schema_repair_input = staticmethod(LLMRunner._build_schema_repair_input)
    _build_schema_repair_prompt = staticmethod(LLMRunner._build_schema_repair_prompt)
    _normalize_requirement_decomposer_payload = staticmethod(LLMRunner._normalize_requirement_decomposer_payload)
    _normalize_prd_writer_feat_payload = staticmethod(LLMRunner._normalize_prd_writer_feat_payload)
    _normalize_pm_planner_task_payload = staticmethod(LLMRunner._normalize_pm_planner_task_payload)
    _normalize_business_payload = staticmethod(LLMRunner._normalize_business_payload)
    _ensure_structured_envelope = staticmethod(LLMRunner._ensure_structured_envelope)
    _filter_materializable_refs = staticmethod(LLMRunner._filter_materializable_refs)
    _is_literal_ssot_ref = staticmethod(LLMRunner._is_literal_ssot_ref)
    _resolve_changed_file_paths = staticmethod(LLMRunner._resolve_changed_file_paths)
    _synthesize_single_ssot_payload = staticmethod(LLMRunner._synthesize_single_ssot_payload)
    _extract_topic_families = classmethod(LLMRunner._extract_topic_families.__func__)
    _load_ssot_markdown = staticmethod(LLMRunner._load_ssot_markdown)
    _validate_feat_bundle_epic_semantics = classmethod(LLMRunner._validate_feat_bundle_epic_semantics.__func__)
    _materialize_ssot_outputs = LLMRunner._materialize_ssot_outputs
    _extract_ssot_contract_payload = LLMRunner._extract_ssot_contract_payload
    _extract_structured_segment_payload = LLMRunner._extract_structured_segment_payload
    _extract_structured_payload_from_code_blocks = LLMRunner._extract_structured_payload_from_code_blocks
    _extract_named_output_segment = staticmethod(LLMRunner._extract_named_output_segment)
    _coerce_ssot_contract_dict = staticmethod(LLMRunner._coerce_ssot_contract_dict)
    _normalize_ssot_contract_payload = staticmethod(LLMRunner._normalize_ssot_contract_payload)
    _parse_structured_output_if_possible = staticmethod(LLMRunner._parse_structured_output_if_possible)
    _merge_context_files = staticmethod(LLMRunner._merge_context_files)
    _collect_authoritative_context_files = classmethod(LLMRunner._collect_authoritative_context_files.__func__)
    _resolve_authoritative_input_value = classmethod(LLMRunner._resolve_authoritative_input_value.__func__)
    _extract_context_file_paths = classmethod(LLMRunner._extract_context_file_paths.__func__)
    _merge_forbidden_read_paths = classmethod(LLMRunner._merge_forbidden_read_paths.__func__)

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

    @staticmethod
    def _parse_structured_output_if_possible(output_text: str) -> Optional[Any]:
        try:
            return StepRunnerBase._parse_structured_output(output_text)
        except ValueError:
            return None

    @classmethod
    def _extract_business_output_for_validation(
        cls,
        *,
        step,
        workflow_id: str,
        output: Dict[str, Any],
        written_files: List[str],
    ) -> tuple[Any, Any]:
        raw_output = output.get("raw_output", "") or ""
        generated_text = output.get("generated_text", "") or ""

        def looks_like_executor_wrapper(payload: Any) -> bool:
            if not isinstance(payload, dict):
                return False
            wrapper_keys = {
                "status",
                "changed_files",
                "commands_run",
                "test_results",
                "diff_summary",
                "evidence_bundle_path",
                "conversation_log_path",
                "debug_log_path",
                "prompt_system_path",
                "prompt_user_path",
                "generated_text",
                "error",
                "iterations_used",
            }
            return bool(wrapper_keys & set(payload.keys()))

        raw_structured_payload = cls._parse_structured_output_if_possible(raw_output)
        generated_structured_payload = cls._parse_structured_output_if_possible(generated_text)

        structured_payload = raw_structured_payload
        if structured_payload is None or looks_like_executor_wrapper(structured_payload):
            if generated_structured_payload is not None:
                structured_payload = generated_structured_payload

        if isinstance(structured_payload, dict) and "business_output" in structured_payload:
            business_output = structured_payload["business_output"]
        elif isinstance(structured_payload, dict) and not looks_like_executor_wrapper(structured_payload):
            business_output = structured_payload
        else:
            business_output = LLMRunner._extract_primary_file_output(step, written_files)
            if business_output is None:
                business_output = LLMRunner._extract_best_written_file_payload(step, written_files)
            if isinstance(business_output, dict) and "business_output" in business_output:
                business_output = business_output["business_output"]
            if business_output is None:
                business_output = raw_output or generated_text or json.dumps(output)

        if isinstance(business_output, list):
            business_output = business_output[0] if business_output else {}

        return LLMRunner._normalize_business_payload(
            step=step,
            workflow_id=workflow_id,
            business_output=business_output,
            structured_payload=structured_payload,
            instance_data=None,
        )

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
        context_files = self._merge_context_files(
            self._collect_authoritative_context_files(step, instance.data),
            claude_config.get("context_files", []),
        )
        success_criteria = self._get_success_criteria(step)
        head_before = None
        if success_criteria.get("require_new_commit"):
            head_before = self._git_head(workspace)

        input_data = {
            "goal": agent_ctx.user_prompt or claude_config.get("goal", ""),
            "workspace": workspace,
            "step_workspace": str(
                Path(workspace) / ".workflow" / "workspace" / workflow_id / step.id
            ),
            "context_files": context_files,
            "write_scope": claude_config.get("write_scope", []),
            "forbidden_read_paths": self._merge_forbidden_read_paths(
                claude_config.get("forbidden_read_paths")
            ),
            "max_iterations": claude_config.get("max_iterations", 5),
            "timeout_seconds": claude_config.get("timeout_seconds", 3600),
            "timeout_retries": claude_config.get("timeout_retries", 1),
            "retry_backoff_seconds": claude_config.get("retry_backoff_seconds", 5),
            "silence_timeout_seconds": claude_config.get("silence_timeout_seconds", 90),
            "silence_grace_seconds": claude_config.get("silence_grace_seconds", 20),
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
                abs_changed = self._resolve_changed_file_paths(
                    workspace=workspace,
                    project_root=ctx.project_root,
                    changed_files=changed,
                )
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
            business_output, structured_payload = self._extract_business_output_for_validation(
                step=step,
                workflow_id=workflow_id,
                output=output,
                written_files=abs_changed if changed else [],
            )
            business_output, structured_payload = self._normalize_business_payload(
                step=step,
                workflow_id=workflow_id,
                business_output=business_output,
                structured_payload=structured_payload,
                instance_data=instance.data,
            )
            if isinstance(business_output, dict):
                output["business_output"] = business_output
            if isinstance(structured_payload, dict):
                output["structured_payload"] = structured_payload
            cc_validation = self._validate_step_output(step, business_output)
            if cc_validation and not cc_validation.passed:
                strict = (step.config or {}).get("strict_output_validation", False)
                if strict:
                    error_msg = f"Output schema validation failed: {cc_validation.errors[0].message if cc_validation.errors else 'unknown'}"
                    repaired = await self._attempt_schema_repair(
                        executor=executor,
                        executor_type=executor_type,
                        input_data=input_data,
                        step=step,
                        workflow_id=workflow_id,
                        validation_error=error_msg,
                        business_output=business_output,
                        structured_payload=structured_payload,
                    )
                    if repaired:
                        repaired_validation = self._validate_step_output(step, repaired["business_output"])
                        if not repaired_validation or repaired_validation.passed:
                            business_output = repaired["business_output"]
                            structured_payload = repaired["structured_payload"]
                            output["schema_repair_retry"] = True
                            output["business_output"] = business_output
                            if isinstance(structured_payload, dict):
                                output["structured_payload"] = structured_payload
                            cc_validation = repaired_validation
                        else:
                            error_msg = (
                                "Output schema validation failed after repair retry: "
                                f"{repaired_validation.errors[0].message if repaired_validation.errors else 'unknown'}"
                            )
                            cc_validation = repaired_validation
                    if cc_validation and not cc_validation.passed:
                        await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                        await ctx.store.update_task_execution(
                            execution_id,
                            TaskExecutionStatus.FAILED,
                            output_data={
                                "raw_output": output.get("raw_output", "") or json.dumps(output),
                                "business_output": business_output,
                                "structured_payload": structured_payload,
                                "validation_result": cc_validation.to_dict(),
                            },
                            error_message=error_msg,
                            completed_at=datetime.now(),
                        )
                        return StepResult(
                            status="failed",
                            step_id=step.id,
                            workflow_id=workflow_id,
                            message=error_msg,
                        )
                else:
                    print(f"[OutputValidation] Warning: Step {step.id} output schema validation failed (soft mode)")

            feat_bundle_semantic_error = None
            if getattr(step, "agent_id", "") == "agent.product.prd_writer":
                feat_bundle_semantic_error = self._validate_feat_bundle_epic_semantics(
                    project_root=ctx.project_root,
                    business_output=business_output,
                )
            if feat_bundle_semantic_error:
                await ctx.state_machine.fail_step(workflow_id, step.id, feat_bundle_semantic_error)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data={
                        "raw_output": output.get("raw_output", "") or json.dumps(output),
                        "business_output": business_output,
                        "structured_payload": structured_payload,
                    },
                    error_message=feat_bundle_semantic_error,
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=feat_bundle_semantic_error,
                )

            ssot_materialized = await self._materialize_ssot_outputs(
                ctx=ctx,
                step=step,
                workflow_id=workflow_id,
                generated_text=output.get("generated_text", "") or output.get("raw_output", ""),
                structured_payload=structured_payload,
            )
            if ssot_materialized:
                materialized_files = ssot_materialized.get("materialized_files", [])
                if materialized_files:
                    await self._collect_evidence(ctx, workflow_id, step.id, materialized_files)
                    changed = list(dict.fromkeys(changed + materialized_files))
                output["ssot_materialized"] = ssot_materialized["outputs"]

            workspace_files = self._materialize_symbolic_workspace_outputs(
                step=step,
                workflow_id=workflow_id,
                project_root=ctx.project_root,
                business_output=business_output,
                structured_payload=structured_payload,
            )
            if workspace_files:
                output["workspace_artifacts"] = list(
                    dict.fromkeys((output.get("workspace_artifacts") or []) + workspace_files)
                )
                changed = list(dict.fromkeys(changed + workspace_files))

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
