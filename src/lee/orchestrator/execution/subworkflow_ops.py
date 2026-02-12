"""
LEE Orchestrator v3.1 - 子工作流操作 Mixin

提取自 orchestrator.py，包含子工作流 spawn、执行、回填逻辑。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from lee.orchestrator.storage.models import (
    WorkflowLevel,
    WorkflowStatus,
    TaskExecutionStatus,
    StepResult,
)



class SubworkflowMixin:
    """子工作流操作 Mixin — spawn / 执行 / 输出回填"""

    async def _run_subworkflow_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行子工作流步骤（workflow_spawn/subworkflow）。

        语义：
        1. 首次执行时创建子工作流实例
        2. 驱动子工作流执行到阻塞点
        3. 子工作流完成后，结构化回填输出到父工作流 data
        """
        parent = await self.store.get_workflow(workflow_id)
        if not parent:
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Parent workflow not found: {workflow_id}",
            )

        subworkflow_ref, requested_level = self._resolve_subworkflow_ref(step)
        if not subworkflow_ref:
            await self.state_machine.fail_step(workflow_id, step.id, "Missing subworkflow ref")
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Step {step.id} missing subworkflow ref",
            )

        parent_data = dict(parent.data or {})
        subworkflow_children = dict(parent_data.get("subworkflow_children", {}))

        child_workflow_id = subworkflow_children.get(step.id)
        child = await self.store.get_workflow(child_workflow_id) if child_workflow_id else None

        # 子流程不存在时创建
        if not child:
            child_level = self._resolve_subworkflow_level(requested_level, parent.level)
            child_data = self._build_subworkflow_input_data(parent, step)

            child = await self.spawn_workflow(
                parent_id=workflow_id,
                level=child_level,
                template_id=subworkflow_ref,
                data=child_data,
            )

            subworkflow_children[step.id] = child.id
            parent_data["subworkflow_children"] = subworkflow_children
            await self.store.update_workflow_data(workflow_id, parent_data)

        # 驱动子流程执行（直到阻塞）
        if child.status in (WorkflowStatus.PENDING, WorkflowStatus.RUNNING):
            max_steps = 20
            if step.config and isinstance(step.config.get("subworkflow_max_steps"), int):
                max_steps = step.config.get("subworkflow_max_steps")
            await self.run_until_blocked(child.id, max_steps=max_steps)
            child = await self.store.get_workflow(child.id)

        if not child:
            await self.state_machine.fail_step(workflow_id, step.id, "Child workflow disappeared")
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Child workflow disappeared for step {step.id}",
            )

        if child.status == WorkflowStatus.COMPLETED:
            backfill_output = await self._backfill_subworkflow_output(workflow_id, step, child)
            await self.state_machine.complete_step(workflow_id, step.id, backfill_output)
            await self._check_workflow_completion(workflow_id)
            return StepResult(
                status="success",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Subworkflow {child.id} completed",
                output=backfill_output,
            )

        if child.status == WorkflowStatus.FAILED:
            error_message = child.data.get("error", "Child workflow failed")
            await self.state_machine.fail_step(workflow_id, step.id, str(error_message))
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Subworkflow {child.id} failed: {error_message}",
            )

        # 子流程仍阻塞/暂停，父步骤保持阻塞状态（不完成）
        return StepResult(
            status="blocked",
            blocked_reason="subworkflow_blocked",
            step_id=step.id,
            workflow_id=workflow_id,
            message=f"Subworkflow {child.id} waiting (status={child.status.value})",
            output={
                "child_workflow_id": child.id,
                "child_status": child.status.value,
            },
        )

    # ============ 辅助方法 ============

    def _resolve_subworkflow_ref(self, step) -> Tuple[Optional[str], Optional[str]]:
        """从步骤配置中解析子工作流引用与层级。"""
        config = step.config or {}

        subworkflow_ref = config.get("subworkflow_ref")
        subworkflow_level = config.get("subworkflow_level")

        subworkflow_cfg = config.get("subworkflow")
        if isinstance(subworkflow_cfg, dict):
            if not subworkflow_ref:
                subworkflow_ref = subworkflow_cfg.get("ref") or subworkflow_cfg.get("id")
            if not subworkflow_level:
                subworkflow_level = subworkflow_cfg.get("level")
        elif isinstance(subworkflow_cfg, str) and not subworkflow_ref:
            subworkflow_ref = subworkflow_cfg

        if not subworkflow_ref and isinstance(config.get("workflow"), str):
            subworkflow_ref = config.get("workflow")

        run_ref = config.get("run")
        if not subworkflow_ref and isinstance(run_ref, str) and run_ref.startswith("workflow."):
            subworkflow_ref = run_ref

        return subworkflow_ref, subworkflow_level

    def _resolve_subworkflow_level(
        self,
        requested_level: Optional[str],
        parent_level: WorkflowLevel,
    ) -> WorkflowLevel:
        """将配置层级字符串映射到 WorkflowLevel。"""
        if requested_level:
            normalized = str(requested_level).strip().lower()
            level_map = {
                "project": WorkflowLevel.PROJECT,
                "department": WorkflowLevel.DEPARTMENT,
                "task": WorkflowLevel.TASK,
                "l1": WorkflowLevel.PROJECT,
                "l2": WorkflowLevel.DEPARTMENT,
                "l3": WorkflowLevel.TASK,
            }
            if normalized in level_map:
                return level_map[normalized]

        if parent_level == WorkflowLevel.PROJECT:
            return WorkflowLevel.DEPARTMENT
        if parent_level == WorkflowLevel.DEPARTMENT:
            return WorkflowLevel.TASK
        return WorkflowLevel.TASK

    def _build_subworkflow_input_data(self, parent, step) -> Dict[str, Any]:
        """构造子工作流初始化数据。"""
        input_map = (step.config or {}).get("input_map")

        normalized_input: Dict[str, Any]
        if isinstance(input_map, dict):
            normalized_input = {
                str(key): self._resolve_input_reference(value, parent.data)
                for key, value in input_map.items()
            }
        else:
            raw_input = step.input or {}
            if isinstance(raw_input, dict):
                normalized_input = {
                    key: self._resolve_input_reference(value, parent.data)
                    for key, value in raw_input.items()
                }
            elif isinstance(raw_input, list):
                normalized_input = {}
                for item in raw_input:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            normalized_input[key] = self._resolve_input_reference(value, parent.data)
            else:
                normalized_input = {"input": self._resolve_input_reference(raw_input, parent.data)}

        return {
            "params": normalized_input,
            "parent_workflow_id": parent.id,
            "parent_step_id": step.id,
            "parent_template_id": parent.template_id,
            "parent_run_id": parent.data.get("run_id"),
        }

    def _resolve_input_reference(self, value: Any, parent_data: Dict[str, Any]) -> Any:
        """解析步骤输入中的简单变量引用。"""
        if isinstance(value, dict):
            return {k: self._resolve_input_reference(v, parent_data) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_input_reference(v, parent_data) for v in value]
        if not isinstance(value, str):
            return value

        if value == "$inputs":
            return parent_data.get("params", {})

        if value.startswith("$inputs."):
            path = value[len("$inputs."):]
            return self._resolve_dotted_path(parent_data.get("params", {}), path)

        if value.startswith("$context."):
            path = value[len("$context."):]
            return self._resolve_dotted_path(parent_data, path)

        return value

    def _resolve_dotted_path(self, obj: Any, dotted_path: str) -> Any:
        """按 a.b.c 形式解析嵌套路径。"""
        if not dotted_path:
            return obj

        current = obj
        for part in dotted_path.split("."):
            if isinstance(current, dict):
                if part not in current:
                    return None
                current = current.get(part)
            elif isinstance(current, list):
                if not part.isdigit():
                    return None
                index = int(part)
                if index < 0 or index >= len(current):
                    return None
                current = current[index]
            else:
                return None
        return current

    async def _backfill_subworkflow_output(
        self,
        parent_workflow_id: str,
        step,
        child,
    ) -> Dict[str, Any]:
        """将子工作流核心产物结构化回填到父流程 data。"""
        parent_step_id = step.id
        parent = await self.store.get_workflow(parent_workflow_id)
        if not parent:
            return {
                "child_workflow_id": child.id,
                "child_status": child.status.value,
            }

        child_data = child.data or {}
        child_run_id = child_data.get("run_id")

        evidence_refs: List[str] = []
        if child_run_id:
            manifest_path = Path(self.project_root or ".").resolve() / "evidence" / child_run_id / "manifest.yaml"
            if manifest_path.exists():
                evidence_refs.append(str(manifest_path))

        child_executions = await self.store.get_task_executions(child.id)
        completed_jobs = [
            execution.step_name
            for execution in child_executions
            if execution.status == TaskExecutionStatus.COMPLETED
        ]

        backfill_output = {
            "child_workflow_id": child.id,
            "child_template_id": child.template_id,
            "child_level": child.level.value,
            "child_status": child.status.value,
            "child_run_id": child_run_id,
            "completed_steps": child_data.get("completed_steps", []),
            "completed_jobs": completed_jobs,
            "child_error": child_data.get("error"),
            "evidence_refs": evidence_refs,
        }

        parent_data = dict(parent.data or {})
        subworkflow_outputs = dict(parent_data.get("subworkflow_outputs", {}))
        subworkflow_outputs[parent_step_id] = backfill_output
        parent_data["subworkflow_outputs"] = subworkflow_outputs

        output_map = (step.config or {}).get("output_map")
        if isinstance(output_map, dict):
            artifacts = dict(parent_data.get("artifacts", {}))
            for target_key, source in output_map.items():
                if not isinstance(target_key, str):
                    continue
                artifacts[target_key] = self._resolve_output_map_value(source, backfill_output, child_data)
            parent_data["artifacts"] = artifacts

        parent_data["last_output"] = {parent_step_id: backfill_output}
        await self.store.update_workflow_data(parent_workflow_id, parent_data)

        return backfill_output

    def _resolve_output_map_value(
        self,
        source: Any,
        backfill_output: Dict[str, Any],
        child_data: Dict[str, Any],
    ) -> Any:
        """解析 output_map 映射值。"""
        if not isinstance(source, str):
            return source

        if source == "$child":
            return backfill_output
        if source.startswith("$child."):
            return self._resolve_dotted_path(backfill_output, source[len("$child."):])
        if source == "$child_data":
            return child_data
        if source.startswith("$child_data."):
            return self._resolve_dotted_path(child_data, source[len("$child_data."):])
        return source
