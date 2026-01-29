"""
测试 LEE Orchestrator v3.0 - State Machine 和 Template Manager

测试内容：
1. WorkflowStateMachine 状态转换
2. 步骤执行（start, complete, fail）
3. 暂停/恢复工作流
4. 计算可执行步骤
5. TemplateManager 加载和查询
"""

import asyncio
import sys
import os
import tempfile

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.storage.models import (
    WorkflowInstance,
    WorkflowLevel,
    WorkflowStatus,
    Step,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.state_machine import (
    WorkflowStateMachine,
    StateTransition,
)
from lee.orchestrator.execution.template_manager import (
    TemplateManager,
    TemplateBuilder,
    BuiltinTemplates,
)


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def test_state_transitions():
    """测试状态转换规则"""
    print_section("测试 1: 状态转换规则")

    # 测试合法的状态转换
    assert StateTransition.can_transition(
        WorkflowStatus.PENDING,
        WorkflowStatus.RUNNING
    )
    print("✅ PENDING -> RUNNING: 合法")

    assert StateTransition.can_transition(
        WorkflowStatus.RUNNING,
        WorkflowStatus.PAUSED
    )
    print("✅ RUNNING -> PAUSED: 合法")

    assert StateTransition.can_transition(
        WorkflowStatus.RUNNING,
        WorkflowStatus.COMPLETED
    )
    print("✅ RUNNING -> COMPLETED: 合法")

    # 测试非法的状态转换
    assert not StateTransition.can_transition(
        WorkflowStatus.COMPLETED,
        WorkflowStatus.RUNNING
    )
    print("✅ COMPLETED -> RUNNING: 非法（终态）")

    assert not StateTransition.can_transition(
        WorkflowStatus.PENDING,
        WorkflowStatus.COMPLETED
    )
    print("✅ PENDING -> COMPLETED: 非法")

    print("\n✅ 所有状态转换测试通过!")


async def test_workflow_state_machine():
    """测试工作流状态机"""
    print_section("测试 2: WorkflowStateMachine")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

        try:
            store = SQLiteStore(db_path)
            await store.connect()

            # 创建工作流
            workflow = WorkflowInstance(
                id="wf_test_001",
                level=WorkflowLevel.TASK,
                template_id="test_task",
                status=WorkflowStatus.PENDING,
            )
            await store.create_workflow(workflow)

            # 初始化状态机
            sm = WorkflowStateMachine(store)

            # 测试获取状态
            state = await sm.get_current_state("wf_test_001")
            assert state == WorkflowStatus.PENDING
            print("✅ 获取当前状态: PENDING")

            # 测试 can_start_step
            can_start = await sm.can_start_step("wf_test_001", "step_1")
            assert not can_start  # PENDING 状态不能开始步骤
            print("✅ PENDING 状态不能开始步骤")

            # 更新为 RUNNING
            await store.update_workflow_status("wf_test_001", WorkflowStatus.RUNNING)

            # 再次测试 can_start_step
            can_start = await sm.can_start_step("wf_test_001", "step_1")
            assert can_start  # RUNNING 状态可以开始步骤
            print("✅ RUNNING 状态可以开始步骤")

            # 测试 start_step
            await sm.start_step("wf_test_001", "step_1")
            updated = await store.get_workflow("wf_test_001")
            assert updated.current_step == "step_1"
            print("✅ 开始步骤成功")

            # 测试 complete_step
            result = await sm.complete_step("wf_test_001", "step_1", {"output": "test"})
            assert result.status == "success"
            assert result.step_id == "step_1"
            updated = await store.get_workflow("wf_test_001")
            assert "step_1" in updated.data["completed_steps"]
            assert updated.current_step is None
            print("✅ 完成步骤成功")

            # 测试暂停/恢复
            await sm.pause_workflow("wf_test_001")
            state = await sm.get_current_state("wf_test_001")
            assert state == WorkflowStatus.PAUSED
            print("✅ 暂停工作流成功")

            await sm.resume_workflow("wf_test_001")
            state = await sm.get_current_state("wf_test_001")
            assert state == WorkflowStatus.RUNNING
            print("✅ 恢复工作流成功")

            await store.close()
            print("\n✅ 所有状态机测试通过!")

        finally:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except PermissionError:
                pass


async def test_ready_steps_calculation():
    """测试计算可执行步骤"""
    print_section("测试 3: 计算可执行步骤")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

        try:
            store = SQLiteStore(db_path)
            await store.connect()

            # 创建工作流
            workflow = WorkflowInstance(
                id="wf_test_002",
                level=WorkflowLevel.TASK,
                template_id="test_task",
                status=WorkflowStatus.RUNNING,
                data={"completed_steps": []},
            )
            await store.create_workflow(workflow)

            # 定义步骤（有依赖关系）
            all_steps = [
                Step(id="step_1", kind="agent", executor_type="llm", depends_on=[]),
                Step(id="step_2", kind="agent", executor_type="llm", depends_on=["step_1"]),
                Step(id="step_3", kind="agent", executor_type="llm", depends_on=["step_1"]),
                Step(id="step_4", kind="agent", executor_type="llm", depends_on=["step_2", "step_3"]),
            ]

            sm = WorkflowStateMachine(store)

            # 初始状态：只有 step_1 可执行
            ready = await sm.get_ready_steps("wf_test_002", all_steps)
            assert len(ready) == 1
            assert ready[0].id == "step_1"
            print("✅ 初始状态: step_1 可执行")

            # 完成 step_1
            await sm.complete_step("wf_test_002", "step_1", {})

            # 现在 step_2 和 step_3 可执行
            ready = await sm.get_ready_steps("wf_test_002", all_steps)
            assert len(ready) == 2
            ready_ids = {s.id for s in ready}
            assert ready_ids == {"step_2", "step_3"}
            print("✅ 完成 step_1 后: step_2, step_3 可执行")

            # 完成 step_2
            await sm.complete_step("wf_test_002", "step_2", {})

            # 只有 step_3 可执行
            ready = await sm.get_ready_steps("wf_test_002", all_steps)
            assert len(ready) == 1
            assert ready[0].id == "step_3"
            print("✅ 完成 step_2 后: step_3 可执行")

            await store.close()
            print("\n✅ 所有可执行步骤测试通过!")

        finally:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except PermissionError:
                pass


async def test_template_manager():
    """测试模板管理器"""
    print_section("测试 4: TemplateManager")

    tm = TemplateManager()

    # 测试内置模板
    simple_project = BuiltinTemplates.simple_project()
    assert simple_project["id"] == "simple_project"
    assert simple_project["level"] == "project"
    print("✅ 内置项目模板加载成功")

    bug_fix = BuiltinTemplates.bug_fix_workflow()
    assert bug_fix["id"] == "bug_fix"
    assert len(bug_fix["steps"]) == 3
    print("✅ 内置 Bug Fix 模板加载成功")

    # 测试从内容加载模板
    yaml_content = """
id: test_template
level: task
name: Test Template
description: A test template
steps:
  - id: step1
    kind: agent
    executor: llm
  - id: step2
    kind: agent
    executor: llm
    depends_on:
      - step1
"""
    template = tm.load_template_from_content(yaml_content, "test_template")
    assert template.id == "test_template"
    assert len(template.steps) == 2
    assert template.steps[1].depends_on == ["step1"]
    print("✅ 从内容加载模板成功")

    # 测试模板验证
    assert tm.validate_template(simple_project)
    print("✅ 模板验证通过")

    # 测试无效模板
    invalid_template = {"id": "invalid"}  # 缺少必需字段
    assert not tm.validate_template(invalid_template)
    print("✅ 正确拒绝无效模板")

    print("\n✅ 所有模板管理器测试通过!")


async def test_template_builder():
    """测试模板构建器"""
    print_section("测试 5: TemplateBuilder")

    builder = TemplateBuilder("custom_workflow", WorkflowLevel.TASK)

    workflow = (
        builder
        .add_step("init", "agent", "llm")
        .add_step("process", "agent", "llm", depends_on=["init"])
        .add_step("complete", "marker", depends_on=["process"])
        .set_config(timeout=300, retry=3)
        .build()
    )

    assert workflow["id"] == "custom_workflow"
    assert workflow["level"] == "task"
    assert len(workflow["steps"]) == 3
    assert workflow["config"]["timeout"] == 300
    print("✅ TemplateBuilder 构建成功")

    # 测试 YAML 导出
    yaml_str = builder.to_yaml()
    assert "custom_workflow" in yaml_str
    assert "init" in yaml_str
    print("✅ TemplateBuilder YAML 导出成功")

    print("\n✅ 所有模板构建器测试通过!")


async def main():
    """主测试流程"""
    print("=" * 60)
    print("🚀 LEE Orchestrator v3.0 - State Machine & Template Manager")
    print("=" * 60)

    await test_state_transitions()
    await test_workflow_state_machine()
    await test_ready_steps_calculation()
    await test_template_manager()
    await test_template_builder()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

    print("\n📋 验证结果:")
    print("  ✅ 状态转换规则")
    print("  ✅ WorkflowStateMachine")
    print("  ✅ 步骤执行（start/complete）")
    print("  ✅ 暂停/恢复工作流")
    print("  ✅ 可执行步骤计算")
    print("  ✅ TemplateManager")
    print("  ✅ TemplateBuilder")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
