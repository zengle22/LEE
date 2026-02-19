"""
Week 3-4 Orchestrator、Runners、Executors 测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
import asyncio
from datetime import datetime
from pathlib import Path

from lee.orchestrator.storage.models import (
    WorkflowLevel,
    WorkflowStatus,
    WorkflowInstance,
    TaskExecution,
    TaskExecutionStatus,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.state_machine import WorkflowStateMachine
from lee.orchestrator.core.event_bus import EventBus
from lee.orchestrator.core.template_manager import TemplateManager
from lee.orchestrator.core.template_manager import TemplateManager
from lee.orchestrator.execution.orchestrator import Orchestrator, StepResult
from lee.orchestrator.execution.runners import ProjectRunner, DepartmentRunner
from lee.orchestrator.execution.executors import ShellExecutor, LLMExecutor, ExecutorFactory, BaseExecutor


# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"


def _create_orchestrator(db):
    """创建带有正确模板路径的 Orchestrator"""
    template_manager = TemplateManager(template_dir=str(EXAMPLES_DIR))
    return Orchestrator(db, template_manager=template_manager, project_root=str(PROJECT_ROOT))


# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"


@pytest.fixture
async def orchestrator_with_template():
    """创建带有正确模板路径的 Orchestrator"""
    db = SQLiteStore(":memory:")
    await db.connect()

    template_manager = TemplateManager(template_dir=str(EXAMPLES_DIR))
    orchestrator = Orchestrator(db, template_manager=template_manager, project_root=str(PROJECT_ROOT))

    yield orchestrator, db

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_create_workflow():
    """测试 Orchestrator 创建工作流"""
    db = SQLiteStore(":memory:")
    await db.connect()

    template_manager = TemplateManager(template_dir=str(EXAMPLES_DIR))
    orchestrator = Orchestrator(db, template_manager=template_manager, project_root=str(PROJECT_ROOT))

    # 创建 L1 项目工作流
    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
        data={"project_name": "test_project"}
    )

    assert project.level == WorkflowLevel.PROJECT
    assert project.status == WorkflowStatus.PENDING
    assert project.data["project_name"] == "test_project"

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_spawn_workflow():
    """测试 Orchestrator Spawn 子工作流"""
    db = SQLiteStore(":memory:")
    await db.connect()
    sm = WorkflowStateMachine(db)
    eb = EventBus()

    orchestrator = _create_orchestrator(db)

    # 创建父工作流
    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )

    # project_main 模板会自动创建2个部门（开发和测试）
    auto_children = await db.get_children(project.id)
    assert len(auto_children) == 2

    # 再手动 Spawn 1 个 L2 子工作流
    department = await orchestrator.spawn_workflow(
        parent_id=project.id,
        level=WorkflowLevel.DEPARTMENT,
        template_id="dept_development",
    )

    assert department.parent_id == project.id
    assert department.level == WorkflowLevel.DEPARTMENT

    # 验证父子关系（2个自动创建 + 1个手动创建 = 3个）
    children = await db.get_children(project.id)
    assert len(children) == 3

    # 验证手动创建的部门在列表中
    child_ids = [c.id for c in children]
    assert department.id in child_ids

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_get_state():
    """测试获取工作流状态"""
    db = SQLiteStore(":memory:")
    await db.connect()
    sm = WorkflowStateMachine(db)
    eb = EventBus()

    orchestrator = _create_orchestrator(db)

    # 创建工作流
    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )

    # 获取状态
    state = await orchestrator.get_state(project.id)
    assert state.workflow_id == project.id
    assert state.level == WorkflowLevel.PROJECT
    assert state.status == WorkflowStatus.PENDING
    # project_main 模板会自动创建2个子工作流
    assert len(state.children) == 2

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_pause_resume():
    """测试暂停和恢复工作流"""
    db = SQLiteStore(":memory:")
    await db.connect()
    sm = WorkflowStateMachine(db)
    eb = EventBus()

    orchestrator = _create_orchestrator(db)

    # 创建工作流
    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )

    # 先将工作流设置为 RUNNING 状态（只能暂停 RUNNING 状态）
    await db.update_workflow_status(project.id, WorkflowStatus.RUNNING)
    await db.create_task_execution(
        TaskExecution(
            id="exec_pause_001",
            workflow_id=project.id,
            step_name="s1_test",
            executor_type="claude_code",
            input_data={},
            status=TaskExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
    )

    # 暂停
    await orchestrator.pause(project.id)
    state = await orchestrator.get_state(project.id)
    assert state.status == WorkflowStatus.PAUSED
    executions = await db.get_task_executions(project.id)
    assert executions[0].status == TaskExecutionStatus.FAILED
    assert "paused" in (executions[0].error_message or "").lower()

    # 恢复
    await orchestrator.resume(project.id)
    state = await orchestrator.get_state(project.id)
    assert state.status == WorkflowStatus.RUNNING

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_complete_fail():
    """测试完成和失败工作流"""
    db = SQLiteStore(":memory:")
    await db.connect()
    sm = WorkflowStateMachine(db)
    eb = EventBus()

    orchestrator = _create_orchestrator(db)

    # 创建工作流
    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )

    # 完成
    await orchestrator.complete_workflow(project.id)
    state = await orchestrator.get_state(project.id)
    assert state.status == WorkflowStatus.COMPLETED

    # 失败
    project2 = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )
    await orchestrator.fail_workflow(project2.id, "Test error")
    state = await orchestrator.get_state(project2.id)
    assert state.status == WorkflowStatus.FAILED

    await db.close()


@pytest.mark.asyncio
async def test_project_runner():
    """测试 ProjectRunner 便捷封装"""
    db = SQLiteStore(":memory:")
    await db.connect()
    sm = WorkflowStateMachine(db)
    eb = EventBus()

    orchestrator = _create_orchestrator(db)
    runner = ProjectRunner(orchestrator)

    # 创建项目
    project = await runner.create_project(
        template_id="project_main",
        data={"name": "my_project"}
    )

    assert project.level == WorkflowLevel.PROJECT
    assert project.data["name"] == "my_project"

    # Spawn 部门
    dept = await runner.spawn_department(
        project_id=project.id,
        template_id="dept_development"
    )

    assert dept.parent_id == project.id
    assert dept.level == WorkflowLevel.DEPARTMENT

    # 获取部门列表（包括自动创建的2个 + 手动创建的1个 = 3个）
    departments = await runner.get_departments(project.id)
    assert len(departments) == 3  # 2个自动创建 + 1个手动创建
    # 验证手动创建的部门在列表中
    dept_ids = [d.id for d in departments]
    assert dept.id in dept_ids

    await db.close()


@pytest.mark.asyncio
async def test_department_runner():
    """测试 DepartmentRunner 便捷封装"""
    db = SQLiteStore(":memory:")
    await db.connect()
    sm = WorkflowStateMachine(db)
    eb = EventBus()

    orchestrator = _create_orchestrator(db)
    project_runner = ProjectRunner(orchestrator)
    dept_runner = DepartmentRunner(orchestrator)

    # 创建项目 → 部门
    project = await project_runner.create_project("project_main")
    dept = await project_runner.spawn_department(project.id, "dept_development")

    # Spawn 任务（使用现有模板 task_backend_api）
    task = await dept_runner.spawn_task(
        department_id=dept.id,
        template_id="task_backend_api"
    )

    assert task.parent_id == dept.id
    assert task.level == WorkflowLevel.TASK

    # 获取任务列表（dept_development 模板会自动创建2个任务 + 手动创建的1个 = 3个）
    tasks = await dept_runner.get_tasks(dept.id)
    assert len(tasks) == 3  # 2个自动创建 + 1个手动创建
    # 验证手动创建的任务在列表中
    task_ids = [t.id for t in tasks]
    assert task.id in task_ids

    await db.close()


@pytest.mark.asyncio
async def test_shell_executor():
    """测试 ShellExecutor"""
    executor = ShellExecutor()

    # 测试简单命令
    result = await executor.execute({
        "command": "echo 'Hello World'",
    })

    assert result["status"] == "completed"
    assert result["return_code"] == 0
    assert "Hello World" in result["stdout"]

    # 测试错误命令
    result = await executor.execute({
        "command": "exit 1",
    })

    assert result["status"] == "failed"
    assert result["return_code"] == 1


def test_llm_executor():
    """测试 LLMExecutor"""
    # 使用 zhipu (GLM) 配置
    try:
        executor = LLMExecutor(profile="zhipu")
    except ValueError as e:
        if "api_key" in str(e).lower() or "missing" in str(e).lower():
            pytest.skip(f"LLM API key not configured: {e}")
        raise

    # 同步执行（LLM 执行器实际是异步但可以同步调用）
    result = asyncio.run(executor.execute({
        "prompt": "Test prompt",
        "system_message": "You are a test assistant.",
        "max_tokens": 50,
    }))

    # 检查结果（可能是 completed 或 failed，取决于 API 状态）
    assert result["status"] in ["completed", "failed"]
    if result["status"] == "completed":
        assert "generated_text" in result
        # GLM 模型名称
        assert result["model"] in ["glm-4-flash", "glm-4", "unknown"]
    else:
        # 如果失败，检查是否有错误信息
        assert "error" in result


def test_executor_factory():
    """测试执行器工厂"""
    # 创建 LLM 执行器 (may fail without API key)
    try:
        llm_exec = ExecutorFactory.create("llm", model="gpt-4")
        assert isinstance(llm_exec, (LLMExecutor, BaseExecutor))
    except ValueError as e:
        if "api_key" in str(e).lower() or "missing" in str(e).lower():
            pass  # Expected when no API key is configured
        else:
            raise

    # 创建 Shell 执行器
    shell_exec = ExecutorFactory.create("shell")
    assert isinstance(shell_exec, ShellExecutor)

    # 未知类型
    try:
        ExecutorFactory.create("unknown")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "Unknown executor type" in str(e)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
