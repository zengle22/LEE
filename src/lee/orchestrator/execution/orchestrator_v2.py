"""
完整工作流执行器 - 支持模板解析和步骤执行

这是 run_step 的完整实现版本
"""

import asyncio
import yaml
from typing import Optional, List, Dict, Any
from datetime import datetime

from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus, WorkflowInstance, TaskExecution, TaskExecutionStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.core.state_machine import SimpleStateMachine
from lee.orchestrator.core.event_bus import MemoryEventBus
from lee.orchestrator.core.template_engine import TemplateEngine
from lee.orchestrator.core.template_manager import TemplateManager
from lee.orchestrator.execution.executors import ExecutorFactory, BaseExecutor


class WorkflowExecutor:
    """
    工作流执行器 - 负责执行具体的工作流步骤

    职责：
    - 解析模板
    - 管理步骤依赖
    - 调用 Executor 执行步骤
    - 更新工作流状态
    """

    def __init__(
        self,
        db: SQLiteStore,
        template_manager: TemplateManager,
        template_engine: TemplateEngine,
        event_bus: MemoryEventBus,
    ):
        self.db = db
        self.template_manager = template_manager
        self.template_engine = template_engine
        self.event_bus = event_bus

        # 执行器缓存
        self._executors: Dict[str, BaseExecutor] = {}

    def _get_executor(self, executor_type: str, config: Dict[str, Any] = None) -> BaseExecutor:
        """获取或创建执行器实例"""
        if executor_type not in self._executors:
            self._executors[executor_type] = ExecutorFactory.create(executor_type, **(config or {}))
        return self._executors[executor_type]

    async def execute_step(
        self,
        workflow_id: str,
        step: Dict[str, Any],
        workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单个步骤

        Args:
            workflow_id: 工作流 ID
            step: 步骤定义
            workflow_data: 工作流数据

        Returns:
            步骤执行结果
        """
        executor_type = step.get("executor", "llm")
        step_input = step.get("input", {})
        step_name = step.get("name", f"step_{datetime.now().timestamp()}")

        # 合并工作流数据和步骤输入
        input_data = {**workflow_data, **step_input}

        # 获取执行器并执行
        executor = self._get_executor(executor_type)
        output = await executor.execute(input_data)

        return {
            "step_name": step_name,
            "executor_type": executor_type,
            "input": input_data,
            "output": output,
            "status": output.get("status", "completed"),
        }

    async def get_ready_steps(
        self,
        workflow_id: str,
        template_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取当前可执行的步骤

        Args:
            workflow_id: 工作流 ID
            template_id: 模板 ID

        Returns:
            可执行步骤列表（已满足依赖）
        """
        template = self.template_manager.get_template_content(template_id)
        if not template:
            return []

        steps = template.get("steps", [])
        completed_steps = set()

        # TODO: 从 TaskExecution 记录获取已完成的步骤
        # 当前简化版本：从工作流 data 中获取
        workflow = await self.db.get_workflow(workflow_id)
        if workflow and "completed_steps" in workflow.data:
            completed_steps = set(workflow.data["completed_steps"])

        ready_steps = []
        for step in steps:
            step_name = step.get("name")
            if step_name in completed_steps:
                continue

            dependencies = step.get("depends_on", [])
            if all(dep in completed_steps for dep in dependencies):
                ready_steps.append(step)

        return ready_steps

    async def mark_step_completed(
        self,
        workflow_id: str,
        step_name: str,
        output: Dict[str, Any]
    ):
        """标记步骤完成"""
        workflow = await self.db.get_workflow(workflow_id)
        if workflow:
            data = workflow.data.copy()
            if "completed_steps" not in data:
                data["completed_steps"] = []
            data["completed_steps"].append(step_name)
            data["last_output"] = output
            await self.db.update_workflow_data(workflow_id, data)


class Orchestrator:
    """完整版 Orchestrator - 支持模板解析和执行"""

    def __init__(
        self,
        db: SQLiteStore,
        state_machine: SimpleStateMachine,
        event_bus: MemoryEventBus,
        template_engine: TemplateEngine,
    ):
        self.db = db
        self.state_machine = state_machine
        self.event_bus = event_bus
        self.template_engine = template_engine

        # 新增组件
        self.template_manager = TemplateManager("examples")
        self.executor = WorkflowExecutor(db, self.template_manager, template_engine, event_bus)

    async def create_workflow(
        self,
        level: WorkflowLevel,
        template_id: str,
        parent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """创建工作流实例"""
        workflow_id = f"wf_{level.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        workflow = WorkflowInstance(
            id=workflow_id,
            level=level,
            template_id=template_id,
            status=WorkflowStatus.PENDING,
            data=data or {},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            parent_id=parent_id,
        )

        await self.db.create_workflow(workflow)

        # 如果是 L1 项目模板，自动创建 L2 部门
        if level == WorkflowLevel.PROJECT:
            template = self.template_manager.get_template_content(template_id)
            if template and "departments" in template:
                for dept_config in template["departments"]:
                    await self.spawn_workflow(
                        parent_id=workflow_id,
                        level=WorkflowLevel.DEPARTMENT,
                        template_id=dept_config["template"],
                        data=dept_config.get("data", {}),
                    )

        # 如果是 L2 部门模板，自动创建 L3 任务
        if level == WorkflowLevel.DEPARTMENT:
            template = self.template_manager.get_template_content(template_id)
            if template and "tasks" in template:
                for task_config in template["tasks"]:
                    await self.spawn_workflow(
                        parent_id=workflow_id,
                        level=WorkflowLevel.TASK,
                        template_id=task_config["template"],
                        data=task_config.get("data", {}),
                    )

        await self.event_bus.publish_workflow_created(workflow_id, level.value, template_id)
        return workflow

    async def get_state(self, workflow_id: str):
        """获取工作流状态"""
        instance = await self.db.get_workflow(workflow_id)
        if instance is None:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        children = await self.db.get_children(workflow_id)
        child_ids = [c.id for c in children]

        from lee.orchestrator.execution.orchestrator import WorkflowState

        return WorkflowState(
            workflow_id=instance.id,
            level=instance.level,
            status=instance.status,
            current_step=instance.data.get("current_step"),
            parent_id=instance.parent_id,
            children=child_ids,
            data=instance.data,
        )

    async def spawn_workflow(
        self,
        parent_id: str,
        level: WorkflowLevel,
        template_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """Spawn 子工作流"""
        parent = await self.db.get_workflow(parent_id)
        if parent is None:
            raise ValueError(f"Parent workflow '{parent_id}' not found")

        child = await self.create_workflow(
            level=level,
            template_id=template_id,
            parent_id=parent_id,
            data=data,
        )

        # 更新子工作流的 parent_level
        child.parent_level = parent.level
        await self.db.update_workflow_data(child.id, child.data)

        return child

    async def run_step(
        self,
        workflow_id: str,
        step_id: Optional[str] = None
    ):
        """
        执行工作流的一个步骤（完整版）

        行为：
        1. 加载模板
        2. 查找可执行步骤
        3. 执行步骤
        4. 更新状态
        5. 检查完成条件
        """
        instance = await self.db.get_workflow(workflow_id)
        if instance is None:
            from lee.orchestrator.execution.orchestrator import StepResult
            return StepResult(
                status="failed",
                step_id=None,
                workflow_id=workflow_id,
                message="Workflow not found",
            )

        # 如果是 PENDING 状态，转换为 RUNNING
        if instance.status == WorkflowStatus.PENDING:
            await self.state_machine.transition(workflow_id, WorkflowStatus.RUNNING)

        # 获取模板步骤
        ready_steps = await self.executor.get_ready_steps(workflow_id, instance.template_id)

        if not ready_steps:
            # 没有可执行步骤，检查是否完成
            template = self.template_manager.get_template_content(instance.template_id)
            if template:
                completion = template.get("completion_criteria", {})
                if self._check_completion(instance, completion):
                    await self.state_machine.transition(workflow_id, WorkflowStatus.COMPLETED)
                    await self.event_bus.publish_workflow_completed(workflow_id)

            from lee.orchestrator.execution.orchestrator import StepResult
            return StepResult(
                status="no_ready_step",
                step_id=None,
                workflow_id=workflow_id,
                message="No ready steps available",
                next_steps=[],
            )

        # 执行第一个可执行步骤
        step = ready_steps[0]
        step_name = step.get("name")

        try:
            # 执行步骤
            result = await self.executor.execute_step(workflow_id, step, instance.data)

            # 标记步骤完成
            await self.executor.mark_step_completed(workflow_id, step_name, result)

            # 更新当前步骤
            instance.data["current_step"] = step_name
            await self.db.update_workflow_data(workflow_id, instance.data)

            await self.event_bus.publish_workflow_completed(workflow_id)

            # 返回下一步
            next_steps = [s.get("name") for s in ready_steps[1:]]
            from lee.orchestrator.execution.orchestrator import StepResult
            return StepResult(
                status="success",
                step_id=step_name,
                workflow_id=workflow_id,
                message=f"Step '{step_name}' completed",
                next_steps=next_steps,
            )

        except Exception as e:
            await self.state_machine.transition(workflow_id, WorkflowStatus.FAILED)
            from lee.orchestrator.execution.orchestrator import StepResult
            return StepResult(
                status="failed",
                step_id=step_name,
                workflow_id=workflow_id,
                message=f"Step failed: {str(e)}",
                next_steps=[],
            )

    def _check_completion(self, instance: WorkflowInstance, criteria: Dict[str, Any]) -> bool:
        """检查完成条件"""
        if not criteria:
            return True

        # 简化版：检查 all_tasks_completed
        if criteria.get("all_tasks_completed"):
            steps = self.template_manager.get_template_content(instance.template_id)
            if steps:
                total_steps = len(steps.get("steps", []))
                completed = instance.data.get("completed_steps", [])
                return len(completed) >= total_steps

        return True

    async def pause(self, workflow_id: str):
        """暂停工作流"""
        await self.state_machine.transition(workflow_id, WorkflowStatus.PAUSED)

    async def resume(self, workflow_id: str):
        """恢复工作流"""
        instance = await self.db.get_workflow(workflow_id)
        if instance.status != WorkflowStatus.PAUSED:
            raise ValueError(f"Cannot resume workflow in {instance.status.value} status")

        await self.state_machine.transition(workflow_id, WorkflowStatus.RUNNING)

    async def complete_workflow(self, workflow_id: str):
        """标记工作流完成"""
        await self.state_machine.transition(workflow_id, WorkflowStatus.COMPLETED)
        await self.event_bus.publish_workflow_completed(workflow_id)

    async def fail_workflow(self, workflow_id: str, error_message: str):
        """标记工作流失败"""
        await self.state_machine.transition(workflow_id, WorkflowStatus.FAILED)
        await self.event_bus.publish_workflow_failed(workflow_id, error_message)
