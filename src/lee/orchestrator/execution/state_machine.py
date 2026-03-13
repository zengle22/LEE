"""
LEE Orchestrator v3.0 - 工作流状态机

本模块定义了工作流状态机，负责状态转换和生命周期管理。

核心职责：
1. 计算状态转换
2. 验证状态转换合法性
3. 管理工作流生命周期
4. 处理步骤完成/失败
5. 支持暂停/恢复
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

import yaml

from lee.orchestrator.storage.models import (
    WorkflowStatus,
    TaskExecutionStatus,
    Step,
    StepResult,
    TaskExecution,
)


# ========================================================================
# 状态转换规则
# ========================================================================

class StateTransition:
    """
    状态转换规则

    定义合法的状态转换路径
    """

    # 工作流状态转换图
    WORKFLOW_TRANSITIONS = {
        WorkflowStatus.PENDING: [
            WorkflowStatus.RUNNING,
            WorkflowStatus.FAILED,
        ],
        WorkflowStatus.RUNNING: [
            WorkflowStatus.PAUSED,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
        ],
        WorkflowStatus.PAUSED: [
            WorkflowStatus.RUNNING,
            WorkflowStatus.FAILED,
        ],
        WorkflowStatus.COMPLETED: [],  # 终态
        WorkflowStatus.FAILED: [],     # 终态
    }

    # 步骤状态转换图
    STEP_TRANSITIONS = {
        TaskExecutionStatus.PENDING: [
            TaskExecutionStatus.RUNNING,
            TaskExecutionStatus.FAILED,
        ],
        TaskExecutionStatus.RUNNING: [
            TaskExecutionStatus.COMPLETED,
            TaskExecutionStatus.FAILED,
        ],
        TaskExecutionStatus.COMPLETED: [],  # 终态
        TaskExecutionStatus.FAILED: [],     # 终态
    }

    @classmethod
    def can_transition(
        cls,
        from_status: WorkflowStatus,
        to_status: WorkflowStatus
    ) -> bool:
        """
        检查状态转换是否合法

        Args:
            from_status: 当前状态
            to_status: 目标状态

        Returns:
            是否可以转换
        """
        return to_status in cls.WORKFLOW_TRANSITIONS.get(from_status, [])


# ========================================================================
# 状态机接口
# ========================================================================

class IStateMachine:
    """
    状态机接口

    定义状态机的核心抽象方法
    """

    async def get_current_state(self, workflow_id: str) -> WorkflowStatus:
        """获取当前状态"""
        pass

    async def can_start_step(
        self,
        workflow_id: str,
        step_id: str
    ) -> bool:
        """检查是否可以开始步骤"""
        pass

    async def start_step(
        self,
        workflow_id: str,
        step_id: str
    ) -> None:
        """开始步骤"""
        pass

    async def complete_step(
        self,
        workflow_id: str,
        step_id: str,
        output: Dict[str, Any]
    ) -> StepResult:
        """完成步骤"""
        pass

    async def fail_step(
        self,
        workflow_id: str,
        step_id: str,
        error: str
    ) -> None:
        """步骤失败"""
        pass

    async def pause_workflow(
        self,
        workflow_id: str
    ) -> None:
        """暂停工作流"""
        pass

    async def resume_workflow(
        self,
        workflow_id: str
    ) -> None:
        """恢复工作流"""
        pass

    async def get_ready_steps(
        self,
        workflow_id: str,
        all_steps: List[Step]
    ) -> List[Step]:
        """获取可执行步骤"""
        pass


# ========================================================================
# 状态机实现
# ========================================================================

class WorkflowStateMachine(IStateMachine):
    """
    工作流状态机实现

    核心逻辑：
    1. 维护工作流状态
    2. 追踪步骤完成情况
    3. 计算可执行步骤
    4. 验证状态转换合法性
    """

    def __init__(self, store, template_manager=None, event_log=None):
        """
        初始化状态机

        Args:
            store: SQLite 存储层
        """
        self.store = store
        self.template_manager = template_manager
        self.event_log = event_log

    async def get_current_state(self, workflow_id: str) -> WorkflowStatus:
        """获取当前状态"""
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")
        return instance.status

    async def can_start_step(
        self,
        workflow_id: str,
        step_id: str
    ) -> bool:
        """
        检查是否可以开始步骤

        检查条件：
        1. 工作流状态为 RUNNING
        2. 步骤未被完成
        3. 所有依赖步骤已完成
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return False

        # 检查工作流状态
        if instance.status != WorkflowStatus.RUNNING:
            return False

        # 检查步骤是否已完成
        completed_steps = instance.data.get("completed_steps", [])
        if step_id in completed_steps:
            return False

        # 检查步骤是否正在执行
        if instance.current_step == step_id:
            return False

        return True

    async def start_step(
        self,
        workflow_id: str,
        step_id: str
    ) -> None:
        """
        开始步骤

        操作：
        1. 验证状态转换合法性
        2. 创建 TaskExecution 记录
        3. 更新 workflow.current_step
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # 更新当前步骤
        await self.store.update_workflow_status(
            workflow_id,
            instance.status,
            current_step=step_id
        )

    async def complete_step(
        self,
        workflow_id: str,
        step_id: str,
        output: Dict[str, Any],
        step_outputs: Optional[List[Any]] = None
    ) -> StepResult:
        """
        完成步骤

        操作：
        1. 将 step_id 添加到 completed_steps
        2. 存储 step_outputs 用于后续 $outputs 引用解析
        3. 原子性更新 data 和清除 current_step（BUG-2026-0040）
        4. 构建 StepResult
        """
        import logging

        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # P0-5: 记录步骤完成日志
        logging.info(f"[StateMachine] Completing step {step_id} for workflow {workflow_id}")

        # 更新 completed_steps
        completed_steps = instance.data.get("completed_steps", [])
        if step_id not in completed_steps:
            completed_steps.append(step_id)
            # P0-5: 记录步骤添加到已完成列表日志
            logging.info(f"[StateMachine] Step {step_id} added to completed_steps")

        if step_outputs is None and self.template_manager and instance.template_id:
            try:
                template = self.template_manager.get_template(instance.template_id)
                step_info = template.get_step_info(step_id) if template else None
                if step_info and getattr(step_info, "outputs", None):
                    step_outputs = step_info.outputs
            except Exception:
                step_outputs = step_outputs

        materialized_paths = self._materialize_declared_outputs(
            instance=instance,
            step_id=step_id,
            output=output,
            step_outputs=step_outputs or [],
        )

        # 更新 step_outputs 映射
        step_outputs_map = dict(instance.data.get("step_outputs", {}))
        step_output_entry = dict(step_outputs_map.get(step_id, {}))
        if isinstance(output, dict):
            step_output_entry.update(output)
        if step_outputs:
            # 提取输出路径（支持 OutputSpec dataclass, dict, str）
            output_paths = []
            for out in step_outputs:
                output_type = getattr(out, "type", None)
                if output_type == "symbol":
                    continue
                if hasattr(out, 'path'):
                    # OutputSpec dataclass
                    output_paths.append(out.path)
                elif isinstance(out, dict) and out.get("path"):
                    if out.get("type") == "symbol":
                        continue
                    output_paths.append(out["path"])
                elif isinstance(out, str):
                    output_paths.append(out)

            if output_paths:
                # Merge with existing paths (handle retry scenario)
                existing = step_output_entry.get("paths", [])
                merged_paths = list(dict.fromkeys(existing + output_paths))  # Preserve order, remove dupes
                step_output_entry["paths"] = merged_paths
        if materialized_paths:
            existing = step_output_entry.get("paths", [])
            step_output_entry["paths"] = list(dict.fromkeys(existing + materialized_paths))

        if step_output_entry:
            step_outputs_map[step_id] = step_output_entry
        self._register_symbol_output_aliases(
            step_outputs_map=step_outputs_map,
            output=output,
            step_outputs=step_outputs or [],
        )

        # P0-3: 优先使用原子性更新；旧 store 接口回退为两步更新。
        updated_data = {
            **instance.data,
            "completed_steps": completed_steps,
            "step_outputs": step_outputs_map,
        }
        if hasattr(self.store, "update_workflow_data_and_clear_current_step"):
            await self.store.update_workflow_data_and_clear_current_step(
                workflow_id,
                updated_data,
                instance.status,
            )
        else:
            await self.store.update_workflow_data(workflow_id, updated_data)
            await self.store.update_workflow_status(
                workflow_id,
                instance.status,
                clear_current_step=True,
            )

        # P0-5: 记录原子性更新完成日志
        logging.info(f"[StateMachine] Atomically updated data and cleared current_step for workflow {workflow_id}")

        # 构建 StepResult
        result = StepResult(
            status="success",
            step_id=step_id,
            workflow_id=workflow_id,
            message=f"Step {step_id} completed successfully",
            next_steps=[],
            output=output,
        )

        return result

    @staticmethod
    def _register_symbol_output_aliases(
        *,
        step_outputs_map: Dict[str, Any],
        output: Dict[str, Any],
        step_outputs: List[Any],
    ) -> None:
        if not isinstance(step_outputs_map, dict) or not step_outputs:
            return

        alias_payload = output if isinstance(output, dict) else {"value": output}
        aliases: List[str] = []
        for output_spec in step_outputs:
            output_type = getattr(output_spec, "type", None)
            output_symbol = getattr(output_spec, "symbol", None)
            output_path = getattr(output_spec, "path", None)
            if isinstance(output_symbol, str) and output_symbol.strip():
                aliases.append(output_symbol.strip())
            elif output_type == "symbol" and isinstance(output_path, str) and output_path.strip():
                aliases.append(output_path.strip())

        for alias in aliases:
            step_outputs_map[alias] = alias_payload

    def _materialize_declared_outputs(
        self,
        *,
        instance,
        step_id: str,
        output: Dict[str, Any],
        step_outputs: List[Any],
    ) -> List[str]:
        materialized: List[str] = []
        if not step_outputs:
            return materialized

        project_root = self._infer_project_root(instance)
        step_output_map = instance.data.get("step_outputs", {}) if isinstance(instance.data, dict) else {}

        for output_spec in step_outputs:
            raw_path = getattr(output_spec, "path", None)
            output_type = getattr(output_spec, "type", None)
            if output_type == "symbol" or not raw_path:
                continue
            rendered_path = self._render_output_path(raw_path, instance)
            target_path = Path(rendered_path)
            if not target_path.is_absolute():
                target_path = project_root / target_path

            payload = self._build_declared_output_payload(
                step_id=step_id,
                output=output,
                instance=instance,
                step_output_map=step_output_map,
            )
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(
                self._serialize_declared_output_payload(target_path, payload),
                encoding="utf-8",
            )
            materialized.append(str(target_path))

        return materialized

    def _infer_project_root(self, instance) -> Path:
        template_id = getattr(instance, "template_id", "") or ""
        template_path = Path(template_id)
        if template_path.is_absolute():
            parents = template_path.parts
            if ".workflow" in parents:
                idx = parents.index(".workflow")
                return Path(*parents[:idx]).resolve()
            return template_path.parent.resolve()
        return Path.cwd().resolve()

    def _render_output_path(self, raw_path: str, instance) -> str:
        rendered = str(raw_path)
        params = instance.data.get("params", {}) if isinstance(instance.data, dict) else {}
        project_value = (
            params.get("project")
            or instance.data.get("project_name")
            or self._infer_project_root(instance).name
        )
        rendered = rendered.replace("{project}", str(project_value))
        return rendered

    def _build_declared_output_payload(
        self,
        *,
        step_id: str,
        output: Dict[str, Any],
        instance,
        step_output_map: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        instance_data = instance.data if isinstance(instance.data, dict) else {}
        if isinstance(output, dict):
            if isinstance(output.get("business_output"), (dict, list)):
                payload["business_output"] = output["business_output"]
            elif isinstance(output.get("structured_payload"), dict):
                payload["business_output"] = output["structured_payload"]
            else:
                gate_business_payload = self._extract_gate_business_payload(output)
                if gate_business_payload is not None:
                    payload["business_output"] = gate_business_payload
            payload["gate_output"] = output

        step_inputs = self._resolve_step_inputs_for_freeze(step_id, instance)
        if step_inputs:
            frozen_inputs: Dict[str, Any] = {}
            for source in step_inputs:
                if source in step_output_map:
                    frozen_inputs[source] = step_output_map[source]
                elif source in instance_data.get("params", {}):
                    frozen_inputs[source] = instance_data["params"][source]
            if frozen_inputs:
                payload["frozen_inputs"] = frozen_inputs

        payload.setdefault("frozen_at", datetime.now().isoformat())
        payload.setdefault("step_id", step_id)
        return payload

    @staticmethod
    def _extract_gate_business_payload(output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(output, dict) or "gate_approved" not in output:
            return None

        noise_keys = {
            "gate_approved",
            "approver",
            "comments",
            "frozen_at",
            "step_id",
            "frozen_inputs",
            "freeze_meta",
            "gate_evaluation",
            "rules_overridden",
        }
        business_payload = {
            key: value
            for key, value in output.items()
            if key not in noise_keys
        }
        return business_payload or None

    def _resolve_step_inputs_for_freeze(self, step_id: str, instance) -> List[str]:
        if not self.template_manager:
            return []
        try:
            template = self.template_manager.get_template(getattr(instance, "template_id", "") or "")
        except Exception:
            template = None
        if template is None:
            return []
        step_info = template.get_step_info(step_id)
        if not step_info:
            return []
        raw_inputs = getattr(step_info, "input", None) or getattr(step_info, "inputs", None) or []
        sources: List[str] = []
        if isinstance(raw_inputs, list):
            for item in raw_inputs:
                if isinstance(item, dict):
                    source = item.get("source")
                    if isinstance(source, str):
                        sources.append(source)
                        sources.extend(self._freeze_source_aliases(source))
        elif isinstance(raw_inputs, dict):
            for _, value in raw_inputs.items():
                if isinstance(value, dict):
                    source = value.get("source")
                    if isinstance(source, str):
                        sources.append(source)
                        sources.extend(self._freeze_source_aliases(source))
        deduped: List[str] = []
        for source in sources:
            if source not in deduped:
                deduped.append(source)
        return deduped

    @staticmethod
    def _freeze_source_aliases(source: str) -> List[str]:
        if not isinstance(source, str):
            return []
        if source.endswith("_freeze_ref"):
            return [source[:-4]]
        if source.endswith("_freeze"):
            return [f"{source}_ref"]
        return []

    @staticmethod
    def _serialize_declared_output_payload(target_path: Path, payload: Dict[str, Any]) -> str:
        suffix = target_path.suffix.lower()
        if suffix == ".json":
            return json.dumps(payload, ensure_ascii=False, indent=2)
        if suffix in {".yaml", ".yml"}:
            return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        if suffix == ".md":
            body = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
            return f"```yaml\n{body}```\n"
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

    async def fail_step(
        self,
        workflow_id: str,
        step_id: str,
        error: str
    ) -> None:
        """
        步骤失败

        操作：
        1. 更新 TaskExecution 状态
        2. 记录错误信息
        3. 更新工作流状态为 FAILED，并清除 current_step
        """
        await self.store.update_workflow_status(
            workflow_id,
            WorkflowStatus.FAILED,
            clear_current_step=True,
        )

    async def pause_workflow(
        self,
        workflow_id: str
    ) -> None:
        """
        暂停工作流

        操作：
        1. 验证状态转换合法性
        2. 更新工作流状态为 PAUSED
        """
        current_status = await self.get_current_state(workflow_id)
        if not StateTransition.can_transition(current_status, WorkflowStatus.PAUSED):
            raise ValueError(f"Cannot pause workflow in state: {current_status}")

        await self.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)

    # ========================================================================
    # v1.1: Rewind 原语（核心回退/重试功能）
    # ========================================================================

    async def rewind_to(
        self,
        workflow_id: str,
        target_step_id: str,
        mode: str,  # "rollback" | "retry"
        reason: str,
    ) -> StepResult:
        """
        回退/重试到指定步骤（v1.1 新增）

        这是 rollback 和 retry 的统一原语，保证：
        1. 基于 template order 计算受影响步骤
        2. 事务化清理所有关联数据
        3. 明确 enqueue 行为

        Args:
            workflow_id: 工作流 ID
            target_step_id: 目标步骤 ID
            mode: "rollback" | "retry"
            reason: 原因

        Returns:
            StepResult

        Raises:
            ValueError: 如果 workflow/step 不存在
        """
        from lee.orchestrator.storage.models import WorkflowInstance

        # 1. 获取 template
        instance = await self.store.get_workflow(workflow_id)
        if instance is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        template = self.template_manager.get_template(instance.template_id)
        if template is None:
            raise ValueError(f"Template not found: {instance.template_id}")

        # 2. 基于 template order 计算受影响的步骤
        affected_steps = template.get_steps_after(target_step_id)

        # 3. 顺序清理所有关联数据
        #
        # 注意：当前 SQLiteStore 的 update_* 方法会自行提交事务，因此这里不能再依赖
        # 外层 transaction 做统一回滚，否则容易出现 “no transaction is active”。
        await self._clear_step_outputs(workflow_id, affected_steps)
        await self._invalidate_task_executions(workflow_id, affected_steps)
        await self._invalidate_gate_approvals(workflow_id, affected_steps)
        await self._clear_step_attempts(workflow_id, affected_steps)
        await self._update_completed_steps(workflow_id, target_step_id, template)

        if mode == "retry":
            # 重试模式: 增加 attempt 次数
            await self._increment_step_attempt(workflow_id, target_step_id)
            # 重置步骤状态
            await self._reset_step_status(workflow_id, target_step_id)

        # 3.6 设置当前步骤指针
        await self.store.update_workflow_current_step(workflow_id, target_step_id)

        # 3.7 恢复工作流运行状态
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

        # 4. 明确 enqueue（由 scheduler 负责）
        # 这里只更新状态，实际 enqueue 由外部 scheduler 处理

        # 记录事件
        if getattr(self, "event_log", None) and hasattr(self.event_log, "log_workflow_rewind"):
            self.event_log.log_workflow_rewind(
                workflow_id=workflow_id,
                target_step=target_step_id,
                mode=mode,
                reason=reason,
            )

        return StepResult(
            status=mode,
            step_id=target_step_id,
            workflow_id=workflow_id,
            message=f"Rewind to {target_step_id} ({mode}): {reason}",
        )

    async def invalidate_steps_after(
        self,
        workflow_id: str,
        step_id: str,
    ) -> List[str]:
        """
        作废指定步骤之后的所有步骤（v1.1 新增）

        基于 template step order 计算，而非依赖 completed_steps

        Args:
            workflow_id: 工作流 ID
            step_id: 基准步骤 ID

        Returns:
            被作废的步骤 ID 列表
        """
        instance = await self.store.get_workflow(workflow_id)
        if instance is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        template = self.template_manager.get_template(instance.template_id)
        if template is None:
            raise ValueError(f"Template not found: {instance.template_id}")

        # 获取目标步骤之后的所有步骤
        return template.get_steps_after(step_id)

    async def _invalidate_step(
        self,
        workflow_id: str,
        step_id: str,
    ) -> None:
        """
        作废单个步骤的所有关联数据（v1.1 新增）

        Args:
            workflow_id: 工作流 ID
            step_id: 步骤 ID
        """
        # 清理 task_executions
        await self._invalidate_task_executions(workflow_id, [step_id])

        # 清理 gate_approvals
        await self._invalidate_gate_approvals(workflow_id, [step_id])

    # ========================================================================
    # v1.1: 清理辅助方法
    # ========================================================================

    async def _clear_step_outputs(
        self,
        workflow_id: str,
        step_ids: list,
    ) -> None:
        """清理步骤输出"""
        instance = await self.store.get_workflow(workflow_id)
        if not instance or not instance.data:
            return

        step_outputs = instance.data.get("step_outputs", {})
        for step_id in step_ids:
            step_outputs.pop(step_id, None)

        await self.store.update_workflow_data(workflow_id, instance.data)

    async def _invalidate_task_executions(
        self,
        workflow_id: str,
        step_ids: list,
    ) -> None:
        """作废任务执行记录"""
        from datetime import datetime
        # 批量更新 task_executions.status = 'invalidated'
        for step_id in step_ids:
            await self.store.execute("""
                UPDATE task_executions
                SET status = 'invalidated',
                    invalidated_at = ?
                WHERE workflow_id = ? AND step_name = ?
            """, (datetime.utcnow(), workflow_id, step_id))
        if step_ids:
            await self.store._conn.commit()

    async def _invalidate_gate_approvals(
        self,
        workflow_id: str,
        step_ids: list,
    ) -> None:
        """作废门禁审批记录"""
        from datetime import datetime
        # 批量更新 gate_approvals.status = 'invalidated'
        for step_id in step_ids:
            await self.store.execute("""
                UPDATE gate_approvals
                SET status = 'invalidated',
                    invalidated_at = ?
                WHERE workflow_id = ? AND step_id = ?
            """, (datetime.utcnow(), workflow_id, step_id))
        if step_ids:
            await self.store._conn.commit()

    async def _clear_step_attempts(
        self,
        workflow_id: str,
        step_ids: list,
    ) -> None:
        """清理步骤尝试次数"""
        instance = await self.store.get_workflow(workflow_id)
        if not instance or not instance.data:
            return

        step_attempts = instance.data.get("step_attempts", {})
        for step_id in step_ids:
            step_attempts.pop(step_id, None)

        await self.store.update_workflow_data(workflow_id, {
            **instance.data,
            "step_attempts": step_attempts,
        })

    async def _update_completed_steps(
        self,
        workflow_id: str,
        target_step_id: str,
        template,
    ) -> None:
        """更新 completed_steps"""
        instance = await self.store.get_workflow(workflow_id)
        if not instance or not instance.data:
            return

        # 获取完整步骤顺序
        step_order = template.get_step_order()

        try:
            target_index = step_order.index(target_step_id)
        except ValueError:
            raise ValueError(f"Step {target_step_id} not in template")

        # 只保留到目标步骤（包含）
        completed_steps = step_order[:target_index + 1]

        await self.store.update_workflow_data(workflow_id, {
            **instance.data,
            "completed_steps": completed_steps,
        })

    async def _increment_step_attempt(
        self,
        workflow_id: str,
        step_id: str,
    ) -> int:
        """增加步骤尝试次数"""
        instance = await self.store.get_workflow(workflow_id)
        if not instance or not instance.data:
            return 1

        step_attempts = instance.data.get("step_attempts", {})
        current_attempt = step_attempts.get(step_id, 0)
        step_attempts[step_id] = current_attempt + 1

        await self.store.update_workflow_data(workflow_id, {
            **instance.data,
            "step_attempts": step_attempts,
        })

        return step_attempts[step_id]

    async def _reset_step_status(
        self,
        workflow_id: str,
        step_id: str,
    ) -> None:
        """重置步骤状态为 pending"""
        instance = await self.store.get_workflow(workflow_id)
        if not instance or not instance.data:
            return

        completed_steps = instance.data.get("completed_steps", [])
        if step_id in completed_steps:
            completed_steps.remove(step_id)
            await self.store.update_workflow_data(workflow_id, {
                **instance.data,
                "completed_steps": completed_steps,
            })

    async def resume_workflow(
        self,
        workflow_id: str
    ) -> None:
        """
        恢复工作流

        操作：
        1. 验证状态转换合法性
        2. 更新工作流状态为 RUNNING
        """
        current_status = await self.get_current_state(workflow_id)
        if not StateTransition.can_transition(current_status, WorkflowStatus.RUNNING):
            raise ValueError(f"Cannot resume workflow in state: {current_status}")

        await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

    async def get_ready_steps(
        self,
        workflow_id: str,
        all_steps: List[Step]
    ) -> List[Step]:
        """
        获取可执行步骤

        算法：
        1. 获取已完成的步骤列表
        2. 获取正在执行的任务记录
        3. 遍历所有步骤
        4. 检查步骤是否已完成
        5. 检查步骤是否正在执行（避免重复执行）
        6. 检查所有依赖是否已完成
        7. 返回满足条件的步骤
        """
        from lee.orchestrator.storage.models import TaskExecutionStatus

        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return []

        # 只处理 RUNNING 状态
        if instance.status != WorkflowStatus.RUNNING:
            return []

        completed_steps = instance.data.get("completed_steps", [])

        # P0-2: 获取正在执行的任务记录（BUG-2026-0039）
        executions = await self.store.get_task_executions(workflow_id)
        running_step_ids = {
            e.step_name for e in executions
            if e.status == TaskExecutionStatus.RUNNING
        }

        ready_steps = []
        for step in all_steps:
            # 跳过已完成的步骤
            if step.id in completed_steps:
                continue

            # P0-2: 跳过正在执行的步骤（避免重复执行）
            if step.id in running_step_ids:
                continue

            # 检查所有依赖是否已完成
            dependencies_met = all(
                dep in completed_steps
                for dep in step.depends_on
            )

            if dependencies_met:
                ready_steps.append(step)

        return ready_steps


# ========================================================================
# Gate 状态机（扩展）
# ========================================================================

@dataclass
class GateState:
    """
    Gate 状态

    Gate 是一种特殊的状态，需要人工介入
    """
    gate_id: str
    workflow_id: str
    step_id: str
    status: str  # pending | approved | rejected | skipped
    request_data: Dict[str, Any]
    response_data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None


class GateStateMachine:
    """
    Gate 状态机

    管理 human_gate 的生命周期
    """

    def __init__(self, store):
        self.store = store
        # 临时存储 gate 状态（实际应该存储在数据库）
        self._gates: Dict[str, GateState] = {}

    async def create_gate(
        self,
        workflow_id: str,
        step_id: str,
        request_data: Dict[str, Any]
    ) -> GateState:
        """
        创建 Gate

        当工作流遇到 human_gate 时调用
        """
        gate_id = f"gate_{step_id}_{uuid.uuid4().hex[:8]}"
        gate = GateState(
            gate_id=gate_id,
            workflow_id=workflow_id,
            step_id=step_id,
            status="pending",
            request_data=request_data,
            created_at=datetime.now().isoformat(),
        )
        self._gates[gate_id] = gate
        return gate

    async def approve_gate(
        self,
        gate_id: str,
        response_data: Dict[str, Any]
    ) -> None:
        """
        批准 Gate

        人工批准后继续执行
        """
        if gate_id not in self._gates:
            raise ValueError(f"Gate not found: {gate_id}")

        gate = self._gates[gate_id]
        gate.status = "approved"
        gate.response_data = response_data
        gate.resolved_at = datetime.now().isoformat()

    async def reject_gate(
        self,
        gate_id: str,
        reason: str
    ) -> None:
        """
        拒绝 Gate

        人工拒绝后终止工作流
        """
        if gate_id not in self._gates:
            raise ValueError(f"Gate not found: {gate_id}")

        gate = self._gates[gate_id]
        gate.status = "rejected"
        gate.response_data = {"reason": reason}
        gate.resolved_at = datetime.now().isoformat()

        # 更新工作流状态为 FAILED
        await self.store.update_workflow_status(
            gate.workflow_id,
            WorkflowStatus.FAILED
        )

    async def skip_gate(
        self,
        gate_id: str
    ) -> None:
        """
        跳过 Gate

        跳过当前 Gate，继续执行
        """
        if gate_id not in self._gates:
            raise ValueError(f"Gate not found: {gate_id}")

        gate = self._gates[gate_id]
        gate.status = "skipped"
        gate.resolved_at = datetime.now().isoformat()
