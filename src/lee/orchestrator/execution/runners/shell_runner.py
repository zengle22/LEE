"""
LEE Orchestrator — Shell/Skill Step Runners

包含:
  - SkillRunner: 处理技能步骤 (kind=skill)
  - OrchestratorCLIRunner: 处理 Orchestrator CLI 步骤 (kind=orchestrator_cli)

从 step_runners.py 提取，保持原有逻辑不变。
"""

from __future__ import annotations

import json
import logging
import platform
import re
import shlex
import sys
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

logger = logging.getLogger(__name__)

_PARAM_TEMPLATE_PATTERN = re.compile(r"^\$?\{\{\s*params\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}$")
_STEP_REF_PATTERN = re.compile(r"^\$s\d+_\d+(?:_[a-zA-Z0-9_.-]+)?$")
# Pattern for $outputs.step_id.field or $outputs.step_id.nested.field
# Supports field names with hyphens (e.g., gitignore-recommendations)
_OUTPUTS_REF_PATTERN = re.compile(r"^\$outputs\.([a-zA-Z_][a-zA-Z0-9_-]*(?:\.[a-zA-Z_][a-zA-Z0-9_-]*)+)$")


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
    def _resolve_outputs_ref(
        ref_string: str,
        project_root: str,
        workflow_data: Optional[Dict[str, Any]],
    ) -> Any:
        """
        解析 $outputs.step_id.field 格式的引用。

        例如: $outputs.s1_1_analyze_files.gitignore_recommendations
        会从工作流数据中查找 s1_1_analyze_files 步骤的输出文件，
        读取并解析 YAML，然后提取 gitignore_recommendations 字段。

        Args:
            ref_string: 引用字符串，格式为 $outputs.step_id.field
            project_root: 项目根目录
            workflow_data: 工作流实例数据，包含 completed_steps 等信息

        Returns:
            解析后的值，如果解析失败则返回 None
        """
        match = _OUTPUTS_REF_PATTERN.match(ref_string.strip())
        if not match:
            logger.debug(f"Output reference pattern not matched: {ref_string}")
            return None

        parts = match.group(1).split(".")
        if len(parts) < 2:
            logger.debug(f"Invalid output reference format (missing field path): {ref_string}")
            return None

        step_id = parts[0]
        field_path = parts[1:]

        # 从 workflow_data 中获取已完成步骤的输出信息
        if not workflow_data:
            logger.debug(f"No workflow_data provided for resolving: {ref_string}")
            return None

        step_outputs = workflow_data.get("step_outputs", {})

        # 获取步骤输出路径（新格式：{step_id: {"paths": [...]}})
        output_info = step_outputs.get(step_id, {})
        output_paths = output_info.get("paths", [])

        # 如果没有找到路径，尝试旧格式
        if not output_paths:
            output_path = output_info.get("path")
            if output_path:
                output_paths = [output_path]

        if not output_paths:
            logger.debug(f"No output paths found for step '{step_id}' in workflow_data. "
                        f"Available steps: {list(step_outputs.keys())}")
            return None

        # 尝试每个输出路径
        for output_path in output_paths:
            # 解析输出文件路径
            full_path = Path(project_root) / output_path
            if not full_path.exists():
                logger.debug(f"Output file not found: {full_path}")
                continue

            # 读取并解析文件
            try:
                content = full_path.read_text(encoding="utf-8")

                # 根据文件扩展名选择解析方式
                if full_path.suffix in (".yaml", ".yml"):
                    data = yaml.safe_load(content)
                elif full_path.suffix == ".json":
                    data = json.loads(content)
                else:
                    # 默认尝试 YAML
                    data = yaml.safe_load(content)

                if not isinstance(data, dict):
                    logger.debug(f"Output file {full_path} does not contain a dict")
                    continue

                # 按路径提取字段
                result = data
                for field in field_path:
                    if isinstance(result, dict):
                        result = result.get(field)
                    else:
                        result = None
                        break

                if result is not None:
                    logger.debug(f"Resolved {ref_string} from {full_path}")
                    return result
                else:
                    logger.debug(f"Field path {'.'.join(field_path)} not found in {full_path}")

            except (yaml.YAMLError, json.JSONDecodeError) as e:
                # Log YAML/JSON parse errors at warning level for visibility
                logger.warning(f"Failed to parse output file {full_path}: {e}")
                # Try to extract the field using regex as a fallback
                try:
                    # Try to find the field using a simple pattern
                    # Look for: field_name: value or field_name:\n  - item1
                    field_name = field_path[-1] if field_path else None
                    if field_name:
                        # Pattern for list values
                        list_pattern = rf"{field_name}:\s*\n((?:\s+-\s+.+\n?)+)"
                        match = re.search(list_pattern, content)
                        if match:
                            logger.info(f"Extracted {field_name} using regex fallback from {full_path}")
                            # Return raw text - let the skill handle parsing
                            return match.group(1).strip()
                except Exception as regex_e:
                    logger.debug(f"Regex fallback also failed: {regex_e}")
                continue
            except IOError as e:
                logger.debug(f"Failed to read output file {full_path}: {e}")
                continue
            except Exception as e:
                # Catch any other unexpected errors
                logger.warning(f"Unexpected error parsing output file {full_path}: {e}")
                continue

        logger.warning(f"Could not resolve output reference: {ref_string}")
        return None

    @staticmethod
    def _resolve_param_value(value: Any, workflow_params: Dict[str, Any]) -> Any:
        """解析 params 模板引用，兼容 `${{ params.xxx }}` / `{{ params.xxx }}`。"""
        # VariableIR / 变量对象统一降级为可序列化字符串引用，避免 task_execution 序列化失败。
        reference = getattr(value, "reference", None)
        if isinstance(reference, str) and reference:
            return reference

        if isinstance(value, dict):
            return {
                key: SkillRunner._resolve_param_value(val, workflow_params)
                for key, val in value.items()
            }

        if isinstance(value, list):
            return [SkillRunner._resolve_param_value(item, workflow_params) for item in value]

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
    def _resolve_params(
        params: Dict[str, Any],
        workflow_params: Dict[str, Any],
        project_root: Optional[str] = None,
        workflow_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """解析参数，支持 params 模板和 outputs 引用。

        Args:
            params: 步骤参数
            workflow_params: 工作流级别参数
            project_root: 项目根目录（LEE 项目目录，用于查找 skill spec）
            workflow_data: 工作流实例数据（包含 step_outputs）
        """
        resolved: Dict[str, Any] = {}

        # Collect potential base paths for resolving output references
        # LLM runner writes outputs to project_root (LEE directory)
        # But workspace_path is the user-specified target directory
        search_paths = []
        workspace_path = params.get("workspace_path") or workflow_params.get("workspace_path")
        if workspace_path:
            search_paths.append(workspace_path)
        if project_root and project_root not in search_paths:
            search_paths.append(project_root)

        for key, value in params.items():
            # 先处理 outputs 引用
            if isinstance(value, str):
                stripped = value.strip()
                if stripped.startswith("$outputs.") and search_paths:
                    # Try each search path until we find the output
                    for base_path in search_paths:
                        output_value = SkillRunner._resolve_outputs_ref(
                            stripped, base_path, workflow_data
                        )
                        if output_value is not None:
                            resolved[key] = output_value
                            break
                    else:
                        # If not found in any path, keep the original value
                        resolved[key] = SkillRunner._resolve_param_value(value, workflow_params)
                    continue
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
        skill_spec_path: Optional[Path] = None,
    ) -> List[str]:
        """从 skill spec 的 execution.command 或 execution.steps[].command 生成可执行命令列表。

        支持的占位符：
        - {skill_dir}: skill spec 文件所在目录
        - {workspace_path}: 工作区路径
        - {key}: input_data 中的任意键
        - {patterns_json}: 将 patterns_to_add 转换为 JSON 字符串
        """
        execution = skill_spec.get("execution", {})
        if not isinstance(execution, dict):
            return []

        # 构建 format values
        format_values: Dict[str, str] = {}

        # 添加 skill_dir 占位符
        if skill_spec_path:
            skill_dir = str(skill_spec_path.parent.resolve())
            # Windows 下使用正斜杠以兼容
            if platform.system() == "Windows":
                skill_dir = skill_dir.replace("\\", "/")
            format_values["skill_dir"] = skill_dir

        # 添加 workspace_path
        workspace = input_data.get("workspace_path") or str(Path(project_root or ".").resolve())
        if platform.system() == "Windows":
            workspace = workspace.replace("\\", "/")
        format_values["workspace_path"] = workspace

        # 添加 patterns_json 特殊处理
        patterns_to_add = input_data.get("patterns_to_add", [])
        if patterns_to_add:
            # 转义单引号以兼容 shell 命令
            patterns_json = json.dumps(patterns_to_add, ensure_ascii=False)
            format_values["patterns_json"] = patterns_json

        # 添加 input_data 中的其他值
        for key, value in input_data.items():
            if value is None or key in ("patterns_to_add", "patterns_json"):
                continue
            # 字符串值直接使用，数组转 JSON
            if isinstance(value, (list, dict)):
                format_values[str(key)] = json.dumps(value, ensure_ascii=False)
            else:
                str_value = str(value)
                if platform.system() == "Windows":
                    str_value = str_value.replace("\\", "/")
                format_values[str(key)] = str_value

        # 分支未显式指定时，回退到当前分支
        if not input_data.get("branch"):
            format_values["branch"] = "$(git branch --show-current)"

        commands: List[str] = []

        # 优先使用 execution.command (单一命令)
        main_command = execution.get("command")
        if main_command:
            try:
                command = str(main_command).format_map(_SafeFormatDict(format_values)).strip()
                if command:
                    commands.append(command)
                    return commands
            except KeyError:
                pass  # 继续尝试 steps

        # 回退到 execution.steps[].command
        steps = execution.get("steps", [])
        if isinstance(steps, list):
            for spec_step in steps:
                if not isinstance(spec_step, dict):
                    continue
                command_tpl = spec_step.get("command")
                if not command_tpl:
                    continue
                try:
                    command = str(command_tpl).format_map(_SafeFormatDict(format_values)).strip()
                    if command:
                        commands.append(command)
                except KeyError:
                    continue

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
        workflow_data = None
        if instance and isinstance(instance.data, dict):
            workflow_data = instance.data
            candidate = instance.data.get("params")
            if isinstance(candidate, dict):
                workflow_params = candidate

        params = self._resolve_params(params, workflow_params, ctx.project_root, workflow_data)
        execution_config = step.config.get("execution", {}) if step.config else {}
        input_data = {**params, **execution_config}

        # 自动加载 skill 规范并注入默认值/命令
        skill_spec = None
        skill_spec_path = None
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
                commands = self._build_skill_commands(step, skill_spec, input_data, ctx.project_root, skill_spec_path)
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
                    # Cross-platform fallback command
                    # Windows: use Python to return success
                    # Unix: use 'true' command
                    if platform.system() == "Windows":
                        input_data["command"] = f'"{sys.executable}" -c "exit(0)"'
                    else:
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
                workflow_id, step.id, output,
                step_outputs=step.outputs if hasattr(step, 'outputs') else None
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
