"""
Runners - Orchestrator 的视图封装

⚠️ 架构原则：
- Runner 不是第二状态机，只是便捷操作的视图封装
- 所有实际逻辑都委托给 Orchestrator
- Runner 提供特定层级的便捷方法
"""

from typing import Optional, List, Dict, Any

from lee.orchestrator.storage.models import WorkflowLevel, WorkflowInstance
from lee.orchestrator.execution.orchestrator import Orchestrator, StepResult


class ProjectRunner:
    """
    L1 项目工作流的便捷封装

    提供 L1 项目级工作流的便捷操作方法
    """

    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator

    async def create_project(
        self,
        template_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """创建项目工作流（L1）"""
        return await self.orchestrator.create_workflow(
            level=WorkflowLevel.PROJECT,
            template_id=template_id,
            parent_id=None,
            data=data,
        )

    async def spawn_department(
        self,
        project_id: str,
        template_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """在项目下创建部门工作流（L2）"""
        return await self.orchestrator.spawn_workflow(
            parent_id=project_id,
            level=WorkflowLevel.DEPARTMENT,
            template_id=template_id,
            data=data,
        )

    async def get_departments(self, project_id: str) -> List[WorkflowInstance]:
        """获取项目的所有部门工作流"""
        children = await self.orchestrator.db.get_children(project_id)
        return [c for c in children if c.level == WorkflowLevel.DEPARTMENT]


class DepartmentRunner:
    """
    L2 部门工作流的便捷封装

    提供 L2 部门级工作流的便捷操作方法
    """

    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator

    async def spawn_task(
        self,
        department_id: str,
        template_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """在部门下创建任务工作流（L3）"""
        return await self.orchestrator.spawn_workflow(
            parent_id=department_id,
            level=WorkflowLevel.TASK,
            template_id=template_id,
            data=data,
        )

    async def get_tasks(self, department_id: str) -> List[WorkflowInstance]:
        """获取部门的所有任务工作流"""
        children = await self.orchestrator.db.get_children(department_id)
        return [c for c in children if c.level == WorkflowLevel.TASK]


class TaskRunner:
    """
    L3 任务工作流的便捷封装

    提供 L3 任务级工作流的便捷操作方法
    """

    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator

    async def execute(self, task_id: str) -> StepResult:
        """执行任务工作流"""
        return await self.orchestrator.run_step(task_id)
