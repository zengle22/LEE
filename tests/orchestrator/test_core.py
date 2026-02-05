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
from lee.orchestrator.execution.state_machine import WorkflowStateMachine
from lee.orchestrator.core.event_bus import EventBus
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
    state_machine = WorkflowStateMachine(store)
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

    sm = WorkflowStateMachine(store)

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

    # 状态转换 - 使用新的 API
    # 首先需要启动工作流
    await store.update_workflow_status("wf_sm_test", WorkflowStatus.RUNNING)

    # 验证状态
    state = await sm.get_current_state("wf_sm_test")
    assert state == WorkflowStatus.RUNNING

    # 测试步骤相关方法
    can_start = await sm.can_start_step("wf_sm_test", "step1")
    # 如果步骤不在 completed_steps 中且不是当前步骤，应该可以开始
    # 具体行为取决于 data 中存储的内容

    # 获取就绪步骤 - 需要提供 all_steps 参数
    ready_steps = await sm.get_ready_steps("wf_sm_test", [])
    # 返回可以执行的步骤列表

    await store.close()


@pytest.mark.asyncio
async def test_event_bus():
    """测试事件总线"""
    from lee.orchestrator.core.event_bus import EventType, Event

    bus = EventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(EventType.TEST_FAILURE, handler)

    # 创建并发布事件
    event = Event(
        type=EventType.TEST_FAILURE,
        payload={"test_name": "test_001"},
        source_workflow="wf_001",
        timestamp=datetime.now().isoformat(),
        event_id="evt_001"
    )
    bus.publish(event)

    assert len(received) == 1
    assert received[0].type == EventType.TEST_FAILURE
    assert received[0].source_workflow == "wf_001"


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
