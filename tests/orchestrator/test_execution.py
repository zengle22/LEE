"""
Week 3-4 Orchestrator、Runners、Executors 测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
import asyncio
from datetime import datetime

from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus, WorkflowInstance
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.core.state_machine import SimpleStateMachine
from lee.orchestrator.core.event_bus import MemoryEventBus
from lee.orchestrator.core.template_engine import TemplateEngine
from lee.orchestrator.execution.orchestrator import Orchestrator, StepResult
from lee.orchestrator.execution.runners import ProjectRunner, DepartmentRunner
from lee.orchestrator.execution.executors import ShellExecutor, LLMExecutor, ExecutorFactory


@pytest.mark.asyncio
async def test_orchestrator_create_workflow():
    """测试 Orchestrator 创建工作流"""
    db = SQLiteStore(":memory:")
    await db.connect()
    sm = SimpleStateMachine(db)
    eb = MemoryEventBus()
    te = TemplateEngine()

    orchestrator = Orchestrator(db, sm, eb, te)

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
    sm = SimpleStateMachine(db)
    eb = MemoryEventBus()
    te = TemplateEngine()

    orchestrator = Orchestrator(db, sm, eb, te)

    # 创建父工作流
    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )

    # Spawn L2 子工作流
    department = await orchestrator.spawn_workflow(
        parent_id=project.id,
        level=WorkflowLevel.DEPARTMENT,
        template_id="dept_dev",
    )

    assert department.parent_id == project.id
    assert department.level == WorkflowLevel.DEPARTMENT

    # 验证父子关系
    children = await db.get_children(project.id)
    assert len(children) == 1
    assert children[0].id == department.id

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_get_state():
    """测试获取工作流状态"""
    db = SQLiteStore(":memory:")
    await db.connect()
    sm = SimpleStateMachine(db)
    eb = MemoryEventBus()
    te = TemplateEngine()

    orchestrator = Orchestrator(db, sm, eb, te)

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
    assert len(state.children) == 0

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_pause_resume():
    """测试暂停和恢复工作流"""
    db = SQLiteStore(":memory:")
    await db.connect()
    sm = SimpleStateMachine(db)
    eb = MemoryEventBus()
    te = TemplateEngine()

    orchestrator = Orchestrator(db, sm, eb, te)

    # 创建工作流
    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )

    # 暂停
    await orchestrator.pause(project.id)
    state = await orchestrator.get_state(project.id)
    assert state.status == WorkflowStatus.PAUSED

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
    sm = SimpleStateMachine(db)
    eb = MemoryEventBus()
    te = TemplateEngine()

    orchestrator = Orchestrator(db, sm, eb, te)

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
    sm = SimpleStateMachine(db)
    eb = MemoryEventBus()
    te = TemplateEngine()

    orchestrator = Orchestrator(db, sm, eb, te)
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
        template_id="dept_dev"
    )

    assert dept.parent_id == project.id
    assert dept.level == WorkflowLevel.DEPARTMENT

    # 获取部门列表
    departments = await runner.get_departments(project.id)
    assert len(departments) == 1
    assert departments[0].id == dept.id

    await db.close()


@pytest.mark.asyncio
async def test_department_runner():
    """测试 DepartmentRunner 便捷封装"""
    db = SQLiteStore(":memory:")
    await db.connect()
    sm = SimpleStateMachine(db)
    eb = MemoryEventBus()
    te = TemplateEngine()

    orchestrator = Orchestrator(db, sm, eb, te)
    project_runner = ProjectRunner(orchestrator)
    dept_runner = DepartmentRunner(orchestrator)

    # 创建项目 → 部门
    project = await project_runner.create_project("project_main")
    dept = await project_runner.spawn_department(project.id, "dept_dev")

    # Spawn 任务
    task = await dept_runner.spawn_task(
        department_id=dept.id,
        template_id="task_bug_fix"
    )

    assert task.parent_id == dept.id
    assert task.level == WorkflowLevel.TASK

    # 获取任务列表
    tasks = await dept_runner.get_tasks(dept.id)
    assert len(tasks) == 1
    assert tasks[0].id == task.id

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
    executor = LLMExecutor(model="gpt-4")

    # 同步执行（LLM 执行器实际是异步但可以同步调用）
    result = asyncio.run(executor.execute({
        "prompt": "Test prompt",
        "system_message": "You are a test assistant.",
        "max_tokens": 50,
    }))

    assert result["status"] == "completed"
    assert "generated_text" in result
    assert result["model"] == "gpt-4"


def test_executor_factory():
    """测试执行器工厂"""
    # 创建 LLM 执行器
    llm_exec = ExecutorFactory.create("llm", model="gpt-4")
    assert isinstance(llm_exec, LLMExecutor)

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
