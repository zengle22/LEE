"""
LEE Orchestrator — Shell/Skill Step Runners

包含:
  - SkillRunner: 处理技能步骤 (kind=skill)
  - OrchestratorCLIRunner: 处理 Orchestrator CLI 步骤 (kind=orchestrator_cli)

从 step_runners.py 提取，保持原有逻辑不变。
"""

from __future__ import annotations

import re
import shlex
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)
from lee.orchestrator.execution.runners.base import StepRunnerBase, RunnerContext

_PARAM_TEMPLATE_PATTERN = re.compile(r"^\$?\{\{\s*params\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}$")
_STEP_REF_PATTERN = re.compile(r"^\$s\d+_\d+(?:_[a-zA-Z0-9_.-]+)?$")


class _SafeFormatDict(dict):
    """容错 format_map：缺失键时保留原占位符"""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class SkillRunner(StepRunnerBase):
    """Skill 步骤运行器"""

    def can_handle(self, step_kind: str) -> bool:
        return step_kind == "skill"

    @staticmethod
    def _extract_params(raw_input: Any) -> Dict[str, Any]:
        """归一化 step.input -> params 字典"""
        if isinstance(raw_input, dict):
            return raw_input.get("params", raw_input)
        if isinstance(raw_input, list):
            params: Dict[str, Any] = {}
            for item in raw_input:
                if isinstance(item, dict):
                    params.update(item)
            return params
        return {}

    @staticmethod
    def _resolve_param_value(value: Any, workflow_params: Dict[str, Any]) -> Any:
        """解析 params 模板引用，兼容 `${{ params.xxx }}` / `{{ params.xxx }}`。"""
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        matched = _PARAM_TEMPLATE_PATTERN.match(stripped)
        if matched:
            return workflow_params.get(matched.group(1))

        # 兼容 parser 旧行为：把常量误改成 `$value`
        if (
            stripped.startswith("$")
            and "{{" not in stripped
            and not stripped.startswith("$inputs.")
            and not _STEP_REF_PATTERN.match(stripped)
        ):
            return stripped[1:]

        return value

    @staticmethod
    def _resolve_params(params: Dict[str, Any], workflow_params: Dict[str, Any]) -> Dict[str, Any]:
        resolved: Dict[str, Any] = {}
        for key, value in params.items():
            resolved[key] = SkillRunner._resolve_param_value(value, workflow_params)
        return resolved

    @staticmethod
    def _find_skill_spec_path(project_root: Optional[str], skill_id: str) -> Optional[Path]:
        """按 skill_id 在 spec-global 下查找 skill.yaml。"""
        root = Path(project_root or ".").resolve()
        search_roots = [root / "spec-global", root]

        for base in search_roots:
            if not base.exists():
                continue
            for candidate in base.rglob("skill.yaml"):
                try:
                    data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
                except Exception:
                    continue
                if isinstance(data, dict) and data.get("id") == skill_id:
                    return candidate
        return None

    @staticmethod
    def _apply_skill_defaults(
        input_data: Dict[str, Any], skill_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """将 skill.interface.inputs.properties.*.default 合并到输入。"""
        merged = dict(input_data)
        props = (
            skill_spec.get("interface", {})
            .get("inputs", {})
            .get("properties", {})
        )
        if not isinstance(props, dict):
            return merged

        for key, spec in props.items():
            if not isinstance(spec, dict):
                continue
            if "default" not in spec:
                continue
            if key not in merged or merged.get(key) in (None, ""):
                merged[key] = spec.get("default")
        return merged

    @staticmethod
    def _build_skill_commands(
        step,
        skill_spec: Dict[str, Any],
        input_data: Dict[str, Any],
        project_root: Optional[str],
    ) -> List[str]:
        """从 skill spec 的 execution.steps[].command 生成可执行命令列表。"""
        execution = skill_spec.get("execution", {})
        steps = execution.get("steps", []) if isinstance(execution, dict) else []
        if not isinstance(steps, list):
            return []

        format_values: Dict[str, str] = {}
        for key, value in input_data.items():
            if value is None:
                continue
            format_values[str(key)] = shlex.quote(str(value))

        # 分支未显式指定时，回退到当前分支
        if not input_data.get("branch"):
            format_values["branch"] = "$(git branch --show-current)"

        workspace = input_data.get("workspace_path") or str(Path(project_root or ".").resolve())
        workspace_quoted = shlex.quote(str(workspace))

        commands: List[str] = []
        for spec_step in steps:
            if not isinstance(spec_step, dict):
                continue
            command_tpl = spec_step.get("command")
            if not command_tpl:
                continue
            command = str(command_tpl).format_map(_SafeFormatDict(format_values)).strip()
            if not command:
                continue
            commands.append(f"cd {workspace_quoted} && {command}")

        # 允许 step.config.execution.command 覆盖 skill 规范
        execution_config = step.config.get("execution", {}) if step.config else {}
        if isinstance(execution_config, dict) and execution_config.get("command"):
            return [str(execution_config["command"])]

        return commands

    @staticmethod
    def _is_failed_shell_output(output: Dict[str, Any]) -> bool:
        status = str(output.get("status", "")).lower()
        if status in {"failed", "error", "timeout"}:
            return True
        return int(output.get("return_code", 0) or 0) != 0

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
        params = self._extract_params(raw_input)

        instance = await ctx.store.get_workflow(workflow_id)
        workflow_params = {}
        if instance and isinstance(instance.data, dict):
            candidate = instance.data.get("params")
            if isinstance(candidate, dict):
                workflow_params = candidate

        params = self._resolve_params(params, workflow_params)
        execution_config = step.config.get("execution", {}) if step.config else {}
        input_data = {**params, **execution_config}

        # 自动加载 skill 规范并注入默认值/命令
        skill_spec = None
        if getattr(step, "skill_id", None):
            skill_spec_path = self._find_skill_spec_path(ctx.project_root, step.skill_id)
            if skill_spec_path is not None:
                try:
                    skill_spec = yaml.safe_load(skill_spec_path.read_text(encoding="utf-8")) or {}
                except Exception:
                    skill_spec = None

        if isinstance(skill_spec, dict):
            input_data = self._apply_skill_defaults(input_data, skill_spec)
            if "command" not in input_data and "commands" not in input_data:
                commands = self._build_skill_commands(step, skill_spec, input_data, ctx.project_root)
                if commands:
                    input_data["commands"] = commands

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
                command_list = input_data["commands"]
                if isinstance(command_list, dict):
                    iterable = list(command_list.items())
                elif isinstance(command_list, list):
                    iterable = [(f"cmd_{idx+1}", command) for idx, command in enumerate(command_list)]
                else:
                    iterable = [("cmd_1", command_list)]

                for env, command in iterable:
                    command_input = {
                        "command": str(command),
                        "timeout": input_data.get("timeout", 600),
                    }
                    result = await ctx.executor_factory.create("shell").execute(command_input)
                    results.append(
                        {
                            "name": env,
                            "command": str(command),
                            **result,
                        }
                    )
                    if self._is_failed_shell_output(result):
                        break

                combined_output = "\n".join([
                    f"=== {env} ===\n{r.get('stdout', '')}" for r in results
                ])
                failed_result = next((r for r in results if self._is_failed_shell_output(r)), None)
                if failed_result:
                    output = {
                        "stdout": combined_output,
                        "stderr": failed_result.get("stderr", ""),
                        "status": "failed",
                        "return_code": failed_result.get("return_code", 1),
                        "commands_run": results,
                    }
                else:
                    output = {
                        "stdout": combined_output,
                        "status": "completed",
                        "return_code": 0,
                        "commands_run": results,
                    }
            else:
                # 单命令执行
                if "command" not in input_data:
                    input_data["command"] = "true"
                    used_fallback_command = True
                executor = ctx.executor_factory.create(step.executor_type or "shell")
                output = await executor.execute(input_data)

            if self._is_failed_shell_output(output):
                error_msg = output.get("stderr") or f"Skill step {step.id} command failed"
                await ctx.state_machine.fail_step(workflow_id, step.id, error_msg)
                await ctx.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    output_data=output,
                    error_message=error_msg,
                    completed_at=datetime.now(),
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Skill execution failed: {error_msg}",
                    output=output,
                )

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
