"""
LEE Orchestrator v3.0 - 核心调度器

本模块定义了 Orchestrator 的核心实现，是整个系统的调度中心。

核心职责（8条）：
1. 管理 Workflow 模板
2. 创建/恢复 Workflow 实例
3. 计算 ready step
4. 执行一个 step
5. 根据执行结果更新状态机
6. spawn 子 workflow
7. 暂停/恢复
8. 提供外部 API

设计原则：
- 不思考，只裁决「现在该干什么」
- 不直接调用 LLM，只通过 Executor
- 不直接读写业务文件
- SQLite 是唯一状态权威
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from lee.orchestrator.storage.models import (
    WorkflowLevel,
    WorkflowStatus,
    WorkflowInstance,
    TaskExecution,
    TaskExecutionStatus,
    Step,
    WorkflowState,
    StepResult,
    ExecutionSummary,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.state_machine import WorkflowStateMachine, StateTransition
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.execution.executors import ExecutorFactory


# ========================================================================
# 核心调度器（Orchestrator）
# ========================================================================

class Orchestrator:
    """
    LEE Orchestrator v3.0 - 核心调度器

    这是整个系统的"脊柱"，唯一的调度中心，唯一的状态权威。

    核心职责（8条）：
    1. 管理 Workflow 模板
    2. 创建/恢复 Workflow 实例
    3. 计算 ready step
    4. 执行一个 step
    5. 根据执行结果更新状态机
    6. spawn 子 workflow
    7. 暂停/恢复
    8. 提供外部 API

    设计原则：
    - 不思考，只裁决「现在该干什么」
    - 不直接调用 LLM，只通过 Executor
    - 不直接读写业务文件
    - SQLite 是唯一状态权威
    """

    def __init__(
        self,
        store: SQLiteStore,
        template_manager: Optional[TemplateManager] = None,
    ):
        """
        初始化 Orchestrator

        Args:
            store: SQLite 存储层
            template_manager: 模板管理器（可选）
        """
        self.store = store
        self.state_machine = WorkflowStateMachine(store)
        self.template_manager = template_manager or TemplateManager()
        self.executor_factory = ExecutorFactory

    # ============ 工作流管理 ============

    async def create_workflow(
        self,
        level: WorkflowLevel,
        template_id: str,
        parent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """
        创建工作流实例

        Args:
            level: 工作流层级（project/department/task）
            template_id: 模板 ID
            parent_id: 父工作流 ID（L1 为 null）
            data: 工作流数据

        Returns:
            创建的 WorkflowInstance
        """
        # 生成唯一 ID
        workflow_id = f"wf_{level.value}_{uuid.uuid4().hex[:8]}"

        # 验证模板存在
        template = self.template_manager.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # 创建 WorkflowInstance
        instance = WorkflowInstance(
            id=workflow_id,
            level=level,
            parent_id=parent_id,
            template_id=template_id,
            status=WorkflowStatus.PENDING,
            data=data or {},
        )

        # 写入数据库
        await self.store.create_workflow(instance)

        # 如果是 L1/L2，自动创建子工作流
        if level == WorkflowLevel.PROJECT and template.departments:
            for dept_config in template.departments:
                await self.spawn_workflow(
                    parent_id=workflow_id,
                    level=WorkflowLevel.DEPARTMENT,
                    template_id=dept_config["template_id"],
                    data=dept_config.get("data", {}),
                )
        elif level == WorkflowLevel.DEPARTMENT and template.tasks:
            for task_config in template.tasks:
                await self.spawn_workflow(
                    parent_id=workflow_id,
                    level=WorkflowLevel.TASK,
                    template_id=task_config["template_id"],
                    data=task_config.get("data", {}),
                )

        return instance

    async def spawn_workflow(
        self,
        parent_id: str,
        level: WorkflowLevel,
        template_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """
        创建子工作流

        Args:
            parent_id: 父工作流 ID
            level: 工作流层级
            template_id: 模板 ID
            data: 工作流数据

        Returns:
            创建的子工作流
        """
        # 验证 parent_id 存在
        parent = await self.store.get_workflow(parent_id)
        if not parent:
            raise ValueError(f"Parent workflow not found: {parent_id}")

        # 调用 create_workflow，指定 parent_id
        return await self.create_workflow(level, template_id, parent_id, data)

    # ============ 状态查询 ============

    async def get_state(
        self,
        workflow_id: str
    ) -> WorkflowState:
        """
        获取工作流状态

        Args:
            workflow_id: 工作流 ID

        Returns:
            工作流当前状态
        """
        # 从数据库加载实例
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # 获取子工作流列表
        children = await self.store.get_children(workflow_id)
        children_ids = [c.id for c in children]

        # 构造 WorkflowState
        return WorkflowState(
            workflow_id=instance.id,
            level=instance.level,
            status=instance.status,
            current_step=instance.current_step,
            parent_id=instance.parent_id,
            children=children_ids,
            data=instance.data,
            template_id=instance.template_id,
        )

    async def get_ready_steps(
        self,
        workflow_id: str
    ) -> List[Step]:
        """
        获取可执行步骤列表

        Args:
            workflow_id: 工作流 ID

        Returns:
            可执行的步骤列表
        """
        # 加载模板
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return []

        # 获取模板步骤
        all_steps = self.template_manager.get_steps(instance.template_id)

        # 调用 WorkflowStateMachine.get_ready_steps
        return await self.state_machine.get_ready_steps(workflow_id, all_steps)

    # ============ 执行控制 ============

    async def run_step(
        self,
        workflow_id: str,
        step_id: Optional[str] = None
    ) -> StepResult:
        """
        执行单个步骤

        Args:
            workflow_id: 工作流 ID
            step_id: 步骤 ID（可选，不指定则执行第一个就绪步骤）

        Returns:
            步骤执行结果
        """
        # 获取 WorkflowInstance
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return StepResult(
                status="failed",
                step_id=None,
                workflow_id=workflow_id,
                message=f"Workflow not found: {workflow_id}",
            )

        # 获取可执行步骤
        ready_steps = await self.get_ready_steps(workflow_id)

        if not ready_steps:
            return StepResult(
                status="no_ready_step",
                step_id=None,
                workflow_id=workflow_id,
                message="No ready steps available",
            )

        # 选择要执行的步骤
        step_to_execute = None
        if step_id:
            # 查找指定的步骤
            for step in ready_steps:
                if step.id == step_id:
                    step_to_execute = step
                    break
            if not step_to_execute:
                return StepResult(
                    status="failed",
                    step_id=step_id,
                    workflow_id=workflow_id,
                    message=f"Step {step_id} is not ready",
                )
        else:
            # 执行第一个就绪步骤
            step_to_execute = ready_steps[0]

        # 更新工作流状态为 RUNNING（如果尚未运行）
        if instance.status != WorkflowStatus.RUNNING:
            await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

        # 开始步骤
        await self.state_machine.start_step(workflow_id, step_to_execute.id)

        # 执行步骤
        try:
            executor = self.executor_factory.create(step_to_execute.executor_type)
            input_data = step_to_execute.input or {}
            output = await executor.execute(input_data)

            # 完成步骤
            result = await self.state_machine.complete_step(
                workflow_id,
                step_to_execute.id,
                output
            )

            # 检查工作流是否完成
            await self._check_workflow_completion(workflow_id)

            return result

        except Exception as e:
            # 步骤失败
            await self.state_machine.fail_step(workflow_id, step_to_execute.id, str(e))
            return StepResult(
                status="failed",
                step_id=step_to_execute.id,
                workflow_id=workflow_id,
                message=f"Step execution failed: {e}",
            )

    async def run_until_blocked(
        self,
        workflow_id: str,
        max_steps: int = 10
    ) -> ExecutionSummary:
        """
        执行直到阻塞

        Args:
            workflow_id: 工作流 ID
            max_steps: 最大执行步数

        Returns:
            执行摘要
        """
        start_time = datetime.now()
        total_steps = 0
        completed_steps = 0
        blocked_at = None
        final_status = "completed"

        for _ in range(max_steps):
            # 执行一个步骤
            result = await self.run_step(workflow_id)

            total_steps += 1

            if result.status == "success":
                completed_steps += 1
            elif result.status == "no_ready_step":
                # 没有可执行的步骤，可能是完成或阻塞
                instance = await self.store.get_workflow(workflow_id)
                if instance.status == WorkflowStatus.COMPLETED:
                    break
                blocked_at = None  # 没有步骤可执行
                final_status = "blocked"
                break
            elif result.status == "failed":
                final_status = "failed"
                break

        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()

        # 获取最终状态
        instance = await self.store.get_workflow(workflow_id)
        if instance.status == WorkflowStatus.COMPLETED:
            final_status = "completed"
        elif instance.status == WorkflowStatus.FAILED:
            final_status = "failed"

        return ExecutionSummary(
            workflow_id=workflow_id,
            total_steps=total_steps,
            completed_steps=completed_steps,
            blocked_at=blocked_at,
            status=final_status,
            duration_seconds=duration,
        )

    # ============ 暂停/恢复 ============

    async def pause(
        self,
        workflow_id: str
    ) -> None:
        """
        暂停工作流

        Args:
            workflow_id: 工作流 ID
        """
        await self.state_machine.pause_workflow(workflow_id)

    async def resume(
        self,
        workflow_id: str
    ) -> None:
        """
        恢复工作流

        Args:
            workflow_id: 工作流 ID
        """
        await self.state_machine.resume_workflow(workflow_id)

    # ============ 辅助方法 ============

    async def _check_workflow_completion(self, workflow_id: str) -> None:
        """
        检查工作流是否完成

        Args:
            workflow_id: 工作流 ID
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return

        # 获取模板的所有步骤
        all_steps = self.template_manager.get_steps(instance.template_id)
        completed_steps = instance.data.get("completed_steps", [])

        # 检查是否所有步骤都已完成
        if len(all_steps) > 0 and len(completed_steps) >= len(all_steps):
            await self.store.update_workflow_status(
                workflow_id,
                WorkflowStatus.COMPLETED,
                completed_at=datetime.now()
            )
