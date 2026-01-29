"""
Week 1 核心功能测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
import asyncio
from datetime import datetime

pytest_plugins = ('pytest_asyncio',)

from lee.orchestrator.storage.models import (
    WorkflowLevel,
    WorkflowStatus,
    WorkflowInstance,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.core.state_machine import SimpleStateMachine
from lee.orchestrator.core.event_bus import MemoryEventBus
from lee.orchestrator.core.template_engine import TemplateEngine


@pytest.mark.asyncio
async def test_sqlite_workflow_crud():
    """测试 SQLite 工作流 CRUD"""
    store = SQLiteStore(":memory:")
    await store.connect()

    # 创建
    workflow = WorkflowInstance(
        id="wf_test_001",
        level=WorkflowLevel.PROJECT,
        template_id="test_template",
        status=WorkflowStatus.PENDING,
        data={"test": "data"},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    await store.create_workflow(workflow)

    # 读取
    retrieved = await store.get_workflow("wf_test_001")
    assert retrieved is not None
    assert retrieved.id == "wf_test_001"
    assert retrieved.status == WorkflowStatus.PENDING

    # 更新状态
    await store.update_workflow_status("wf_test_001", WorkflowStatus.RUNNING)
    updated = await store.get_workflow("wf_test_001")
    assert updated.status == WorkflowStatus.RUNNING

    # 子工作流
    child = WorkflowInstance(
        id="wf_test_002",
        level=WorkflowLevel.DEPARTMENT,
        template_id="dept_template",
        status=WorkflowStatus.PENDING,
        data={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
        parent_id="wf_test_001",
        parent_level=WorkflowLevel.PROJECT,
    )
    await store.create_workflow(child)

    children = await store.get_children("wf_test_001")
    assert len(children) == 1
    assert children[0].id == "wf_test_002"

    await store.close()


@pytest.mark.asyncio
async def test_state_machine():
    """测试状态机"""
    store = SQLiteStore(":memory:")
    await store.connect()

    sm = SimpleStateMachine(store)

    workflow = WorkflowInstance(
        id="wf_sm_test",
        level=WorkflowLevel.PROJECT,
        template_id="test",
        status=WorkflowStatus.PENDING,
        data={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    await store.create_workflow(workflow)

    # 状态转换
    await sm.transition("wf_sm_test", WorkflowStatus.RUNNING)

    # 验证
    state = await sm.get_state("wf_sm_test")
    assert state == WorkflowStatus.RUNNING

    # 缓存重建
    await sm.load_from_db()
    rebuilt = await sm.get_state("wf_sm_test")
    assert rebuilt == WorkflowStatus.RUNNING

    await store.close()


@pytest.mark.asyncio
async def test_event_bus():
    """测试事件总线"""
    bus = MemoryEventBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe("workflow.created", handler)
    await bus.publish_workflow_created("wf_001", "project", "tpl")

    assert len(received) == 1
    assert received[0].type == "workflow.created"
    assert received[0].workflow_id == "wf_001"


def test_template_engine():
    """测试模板引擎"""
    engine = TemplateEngine()

    # 字符串渲染
    result = engine.render_string("Hello {{ name }}!", {"name": "World"})
    assert result == "Hello World!"

    # YAML 渲染
    yaml_str = "name: {{ name }}\nvalue: {{ value }}"
    rendered = engine.render_yaml(yaml_str, {"name": "test", "value": 123})
    assert rendered["name"] == "test"
    assert rendered["value"] == 123

    # 验证模板
    valid = {"name": "test", "steps": [{"name": "s1"}]}
    errors = engine.validate_workflow_template(valid)
    assert len(errors) == 0

    # 可执行步骤
    steps = engine.get_ready_steps(valid, set())
    assert steps == ["s1"]


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
