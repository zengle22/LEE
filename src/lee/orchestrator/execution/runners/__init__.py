"""
LEE Orchestrator — Runners

此模块包含两层内容：

1. 原 runners.py 的便捷 Runner 封装（ProjectRunner, DepartmentRunner, TaskRunner）
2. 新 v3.5 策略模式的 Step Runner 框架（StepRunnerStrategy, StepRunnerBase, RunnerContext）

注意：ProjectRunner 等依赖 Orchestrator, 为避免循环导入使用延迟导入。
"""

# ------------------------------------------------------------------
# v3.5 策略模式 Step Runner（无循环依赖，可直接导入）
# ------------------------------------------------------------------
from lee.orchestrator.execution.runners.base import (
    StepRunnerStrategy,
    StepRunnerBase,
    RunnerContext,
)
from lee.orchestrator.execution.runners.registry import StepRunnerRegistry


# ------------------------------------------------------------------
# 原 runners.py — 工作流层级便捷 Runner
# 延迟导入以避免 orchestrator ↔ step_runners ↔ runners 循环
# ------------------------------------------------------------------
def _lazy_import():
    """延迟导入以避免循环依赖"""
    from typing import Optional, List, Dict, Any
    from lee.orchestrator.storage.models import WorkflowLevel, WorkflowInstance
    from lee.orchestrator.execution.orchestrator import Orchestrator, StepResult

    class ProjectRunner:
        """L1 项目工作流的便捷封装"""

        def __init__(self, orchestrator: Orchestrator):
            self.orchestrator = orchestrator

        async def create_project(
            self,
            template_id: str,
            data: Optional[Dict[str, Any]] = None,
        ) -> WorkflowInstance:
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
            return await self.orchestrator.spawn_workflow(
                parent_id=project_id,
                level=WorkflowLevel.DEPARTMENT,
                template_id=template_id,
                data=data,
            )

        async def get_departments(self, project_id: str) -> List[WorkflowInstance]:
            children = await self.orchestrator.db.get_children(project_id)
            return [c for c in children if c.level == WorkflowLevel.DEPARTMENT]

    class DepartmentRunner:
        """L2 部门工作流的便捷封装"""

        def __init__(self, orchestrator: Orchestrator):
            self.orchestrator = orchestrator

        async def spawn_task(
            self,
            department_id: str,
            template_id: str,
            data: Optional[Dict[str, Any]] = None,
        ) -> WorkflowInstance:
            return await self.orchestrator.spawn_workflow(
                parent_id=department_id,
                level=WorkflowLevel.TASK,
                template_id=template_id,
                data=data,
            )

        async def get_tasks(self, department_id: str) -> List[WorkflowInstance]:
            children = await self.orchestrator.db.get_children(department_id)
            return [c for c in children if c.level == WorkflowLevel.TASK]

    class TaskRunner:
        """L3 任务工作流的便捷封装"""

        def __init__(self, orchestrator: Orchestrator):
            self.orchestrator = orchestrator

        async def execute(self, task_id: str) -> StepResult:
            return await self.orchestrator.run_step(task_id)

    return ProjectRunner, DepartmentRunner, TaskRunner


def __getattr__(name):
    """模块级 __getattr__ 实现延迟导入"""
    if name in ("ProjectRunner", "DepartmentRunner", "TaskRunner"):
        ProjectRunner, DepartmentRunner, TaskRunner = _lazy_import()
        globals()["ProjectRunner"] = ProjectRunner
        globals()["DepartmentRunner"] = DepartmentRunner
        globals()["TaskRunner"] = TaskRunner
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # v3.5 策略模式
    "StepRunnerStrategy",
    "StepRunnerBase",
    "RunnerContext",
    "StepRunnerRegistry",
    # 工作流层级 Runner（延迟导入）
    "ProjectRunner",
    "DepartmentRunner",
    "TaskRunner",
]
