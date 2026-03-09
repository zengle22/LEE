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
import json

from lee.orchestrator.storage.models import (
    WorkflowLevel,
    WorkflowStatus,
    TaskExecution,
    TaskExecutionStatus,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.runners import ProjectRunner, DepartmentRunner
from lee.orchestrator.execution.executors import ShellExecutor, LLMExecutor, ExecutorFactory, BaseExecutor


PROJECT_ROOT = Path(__file__).parent.parent.parent


PROJECT_TEMPLATE = """
id: project_main
level: project
name: Project Main
description: Test project template
departments:
  - template_id: dept_development
  - template_id: dept_testing
steps:
  - id: kickoff
    kind: agent
    executor: shell
    input:
      command: echo kickoff
""".strip()

DEVELOPMENT_TEMPLATE = """
id: dept_development
level: department
name: Development Department
description: Test development department
tasks:
  - template_id: task_backend_api
  - template_id: task_frontend_ui
steps:
  - id: develop
    kind: agent
    executor: shell
    input:
      command: echo develop
""".strip()

TESTING_TEMPLATE = """
id: dept_testing
level: department
name: Testing Department
description: Test testing department
steps:
  - id: qa
    kind: agent
    executor: shell
    input:
      command: echo qa
""".strip()

TASK_TEMPLATE = """
id: task_backend_api
level: task
name: Backend API Task
description: Test backend task
steps:
  - id: implement
    kind: agent
    executor: shell
    input:
      command: echo backend
""".strip()

FRONTEND_TASK_TEMPLATE = """
id: task_frontend_ui
level: task
name: Frontend UI Task
description: Test frontend task
steps:
  - id: build
    kind: agent
    executor: shell
    input:
      command: echo frontend
""".strip()


def _write_templates(template_dir: Path) -> None:
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "project_main.yaml").write_text(PROJECT_TEMPLATE, encoding="utf-8")
    (template_dir / "dept_development.yaml").write_text(DEVELOPMENT_TEMPLATE, encoding="utf-8")
    (template_dir / "dept_testing.yaml").write_text(TESTING_TEMPLATE, encoding="utf-8")
    (template_dir / "task_backend_api.yaml").write_text(TASK_TEMPLATE, encoding="utf-8")
    (template_dir / "task_frontend_ui.yaml").write_text(FRONTEND_TASK_TEMPLATE, encoding="utf-8")


@pytest.fixture
def template_dir(tmp_path: Path) -> Path:
    template_root = tmp_path / "workflow-templates"
    _write_templates(template_root)
    return template_root


def _create_orchestrator(db: SQLiteStore, template_dir: Path) -> Orchestrator:
    template_manager = TemplateManager(template_dir=str(template_dir))
    return Orchestrator(db, template_manager=template_manager, project_root=str(PROJECT_ROOT))


@pytest.fixture
async def orchestrator_with_template(template_dir: Path):
    db = SQLiteStore(":memory:")
    await db.connect()

    orchestrator = _create_orchestrator(db, template_dir)

    yield orchestrator, db

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_create_workflow(template_dir: Path):
    db = SQLiteStore(":memory:")
    await db.connect()

    orchestrator = _create_orchestrator(db, template_dir)

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
async def test_orchestrator_spawn_workflow(template_dir: Path):
    db = SQLiteStore(":memory:")
    await db.connect()

    orchestrator = _create_orchestrator(db, template_dir)

    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )

    auto_children = await db.get_children(project.id)
    assert len(auto_children) == 2

    department = await orchestrator.spawn_workflow(
        parent_id=project.id,
        level=WorkflowLevel.DEPARTMENT,
        template_id="dept_development",
    )

    assert department.parent_id == project.id
    assert department.level == WorkflowLevel.DEPARTMENT

    children = await db.get_children(project.id)
    assert len(children) == 3

    child_ids = [c.id for c in children]
    assert department.id in child_ids

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_get_state(template_dir: Path):
    db = SQLiteStore(":memory:")
    await db.connect()

    orchestrator = _create_orchestrator(db, template_dir)

    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )

    state = await orchestrator.get_state(project.id)
    assert state.workflow_id == project.id
    assert state.level == WorkflowLevel.PROJECT
    assert state.status == WorkflowStatus.PENDING
    assert len(state.children) == 2

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_pause_resume(template_dir: Path):
    db = SQLiteStore(":memory:")
    await db.connect()

    orchestrator = _create_orchestrator(db, template_dir)

    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )

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

    await orchestrator.pause(project.id)
    state = await orchestrator.get_state(project.id)
    assert state.status == WorkflowStatus.PAUSED
    executions = await db.get_task_executions(project.id)
    assert executions[0].status == TaskExecutionStatus.FAILED
    assert "paused" in (executions[0].error_message or "").lower()

    await orchestrator.resume(project.id)
    state = await orchestrator.get_state(project.id)
    assert state.status == WorkflowStatus.RUNNING

    await db.close()


@pytest.mark.asyncio
async def test_orchestrator_complete_fail(template_dir: Path):
    db = SQLiteStore(":memory:")
    await db.connect()

    orchestrator = _create_orchestrator(db, template_dir)

    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )

    await orchestrator.complete_workflow(project.id)
    state = await orchestrator.get_state(project.id)
    assert state.status == WorkflowStatus.COMPLETED

    project2 = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
    )
    await orchestrator.fail_workflow(project2.id, "Test error")
    state = await orchestrator.get_state(project2.id)
    assert state.status == WorkflowStatus.FAILED

    await db.close()


@pytest.mark.asyncio
async def test_project_runner(template_dir: Path):
    db = SQLiteStore(":memory:")
    await db.connect()

    orchestrator = _create_orchestrator(db, template_dir)
    runner = ProjectRunner(orchestrator)

    project = await runner.create_project(
        template_id="project_main",
        data={"name": "my_project"}
    )

    assert project.level == WorkflowLevel.PROJECT
    assert project.data["name"] == "my_project"

    dept = await runner.spawn_department(
        project_id=project.id,
        template_id="dept_development"
    )

    assert dept.parent_id == project.id
    assert dept.level == WorkflowLevel.DEPARTMENT

    departments = await runner.get_departments(project.id)
    assert len(departments) == 3
    dept_ids = [d.id for d in departments]
    assert dept.id in dept_ids

    await db.close()


@pytest.mark.asyncio
async def test_department_runner(template_dir: Path):
    db = SQLiteStore(":memory:")
    await db.connect()

    orchestrator = _create_orchestrator(db, template_dir)
    project_runner = ProjectRunner(orchestrator)
    dept_runner = DepartmentRunner(orchestrator)

    project = await project_runner.create_project("project_main")
    dept = await project_runner.spawn_department(project.id, "dept_development")

    task = await dept_runner.spawn_task(
        department_id=dept.id,
        template_id="task_backend_api"
    )

    assert task.parent_id == dept.id
    assert task.level == WorkflowLevel.TASK

    tasks = await dept_runner.get_tasks(dept.id)
    assert len(tasks) == 3
    task_ids = [t.id for t in tasks]
    assert task.id in task_ids

    await db.close()


@pytest.mark.asyncio
async def test_shell_executor():
    executor = ShellExecutor()

    result = await executor.execute({
        "command": "echo 'Hello World'",
    })

    assert result["status"] == "completed"
    assert result["return_code"] == 0
    assert "Hello World" in result["stdout"]

    result = await executor.execute({
        "command": "exit 1",
    })

    assert result["status"] == "failed"
    assert result["return_code"] == 1


def test_llm_executor():
    try:
        executor = LLMExecutor(profile="zhipu")
    except ValueError as e:
        if "api_key" in str(e).lower() or "missing" in str(e).lower():
            pytest.skip(f"LLM API key not configured: {e}")
        raise

    result = asyncio.run(executor.execute({
        "prompt": "Test prompt",
        "system_message": "You are a test assistant.",
        "max_tokens": 50,
    }))

    assert result["status"] in ["completed", "failed"]
    if result["status"] == "completed":
        assert "generated_text" in result
        assert isinstance(result.get("model"), str)
        assert result["model"]
        assert isinstance(result.get("profile"), str)
        assert result["profile"]
        if result["profile"] != "zhipu":
            assert any(attempt["profile"] == "zhipu" for attempt in result.get("attempts", []))
    else:
        assert "error" in result


def test_executor_factory():
    try:
        llm_exec = ExecutorFactory.create("llm", model="gpt-4")
        assert isinstance(llm_exec, (LLMExecutor, BaseExecutor))
    except ValueError as e:
        if "api_key" not in str(e).lower() and "missing" not in str(e).lower():
            raise

    shell_exec = ExecutorFactory.create("shell")
    assert isinstance(shell_exec, ShellExecutor)

    try:
        ExecutorFactory.create("unknown")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "Unknown executor type" in str(e)


@pytest.mark.asyncio
async def test_llm_step_persists_failed_task_execution_when_executor_init_fails(
    template_dir: Path,
    monkeypatch,
):
    failing_template = """
id: task_llm_failure
level: task
name: LLM Failure Task
description: Test executor init failure persistence
steps:
  - id: feat_boundary_design
    kind: agent
    agent_id: agent.product.prd_writer
    executor_type: llm
""".strip()

    (template_dir / "task_llm_failure.yaml").write_text(failing_template, encoding="utf-8")

    db = SQLiteStore(":memory:")
    await db.connect()
    orchestrator = _create_orchestrator(db, template_dir)

    workflow = await orchestrator.create_workflow(
        level=WorkflowLevel.TASK,
        template_id="task_llm_failure",
    )

    original_create = orchestrator.executor_factory.create

    def _boom(executor_type, **kwargs):
        if executor_type == "llm":
            raise ValueError("LLM config 'qwen' missing api_key")
        return original_create(executor_type, **kwargs)

    monkeypatch.setattr(orchestrator.executor_factory, "create", _boom)

    result = await orchestrator.run_step(workflow.id)

    assert result.status == "failed"
    executions = await db.get_task_executions(workflow.id)
    assert len(executions) == 1
    assert executions[0].step_name == "feat_boundary_design"
    assert executions[0].status == TaskExecutionStatus.FAILED
    assert "missing api_key" in (executions[0].error_message or "")

    await db.close()


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
