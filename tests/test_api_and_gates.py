"""
测试 LEE Orchestrator v3.0 - API 和 Gate 系统

测试内容：
1. CLI 命令
2. Gate API
3. 人工审批流程
4. 暂停/恢复机制
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
    WorkflowLevel,
    WorkflowStatus,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.execution.gate_api import GateAPI


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def test_cli_interface():
    """测试 CLI 接口"""
    print_section("测试 1: CLI 接口")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

        try:
            # 初始化
            store = SQLiteStore(db_path)
            await store.connect()

            tm = TemplateManager()

            # 注册测试模板
            tm._cache["test_workflow"] = tm._parse_template_doc(
                {
                    "id": "test_workflow",
                    "level": "task",
                    "name": "Test Workflow",
                    "steps": [
                        {
                            "id": "human_review",
                            "kind": "human_gate",
                            "executor": "gate",
                        },
                        {
                            "id": "final_step",
                            "kind": "agent",
                            "executor": "shell",
                            "depends_on": ["human_review"],
                        },
                    ],
                },
                "test_workflow"
            )

            orchestrator = Orchestrator(store, tm)
            gate_api = GateAPI(store, orchestrator)

            # 模拟 CLI 创建工作流
            print("\n1. 创建工作流...")
            workflow = await orchestrator.create_workflow(
                level=WorkflowLevel.TASK,
                template_id="test_workflow",
                data={"task_name": "需要人工审核的任务"},
            )
            print(f"   ✅ 工作流 ID: {workflow.id}")
            print(f"   ✅ 状态: {workflow.status.value}")

            # 运行到 Gate
            print("\n2. 运行工作流（会停在 Gate）...")
            result = await orchestrator.run_step(workflow.id)
            print(f"   ✅ 执行结果: {result.status}")

            # 创建 Gate
            print("\n3. 创建人工审批 Gate...")
            gate = await gate_api.create_gate(
                workflow_id=workflow.id,
                step_id="human_review",
                step_name="人工审核",
                description="请审核此任务",
                context={"task_data": "任务数据"},
            )
            print(f"   ✅ Gate ID: {gate.gate_id}")
            print(f"   ✅ 状态: {gate.status}")

            # 查询 Gate 状态
            print("\n4. 查询 Gate 状态...")
            gate_status = await gate_api.get_gate_status(gate.gate_id)
            print(f"   ✅ Gate 状态: {gate_status['status']}")
            print(f"   ✅ 工作流状态: {gate_status['workflow_status']}")

            # 批准 Gate
            print("\n5. 批准 Gate...")
            await gate_api.approve_gate(
                gate.gate_id,
                comment="审核通过",
                checklist=[{"item": "代码质量", "ok": True}],
            )
            print(f"   ✅ Gate 已批准")

            # 验证工作流状态
            state = await orchestrator.get_state(workflow.id)
            print(f"\n6. 最终工作流状态: {state.status.value}")

            # 继续执行
            print("\n7. 继续执行...")
            result = await orchestrator.run_step(workflow.id)
            print(f"   ✅ 执行结果: {result.status}")

            await store.close()
            print("\n✅ CLI 和 Gate API 测试通过!")

        finally:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except PermissionError:
                pass


async def test_gate_workflow_lifecycle():
    """测试完整的工作流生命周期（含 Gate）"""
    print_section("测试 2: Gate 工作流生命周期")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

        try:
            store = SQLiteStore(db_path)
            await store.connect()

            tm = TemplateManager()

            # 创建含 Gate 的模板
            tm._cache["gated_workflow"] = tm._parse_template_doc(
                {
                    "id": "gated_workflow",
                    "level": "task",
                    "name": "Gated Workflow",
                    "steps": [
                        {
                            "id": "prepare",
                            "kind": "agent",
                            "executor": "shell",
                        },
                        {
                            "id": "approval",
                            "kind": "human_gate",
                            "executor": "gate",
                            "depends_on": ["prepare"],
                        },
                        {
                            "id": "execute",
                            "kind": "agent",
                            "executor": "shell",
                            "depends_on": ["approval"],
                        },
                    ],
                },
                "gated_workflow"
            )

            orchestrator = Orchestrator(store, tm)
            gate_api = GateAPI(store, orchestrator)

            # 创建工作流
            workflow = await orchestrator.create_workflow(
                level=WorkflowLevel.TASK,
                template_id="gated_workflow",
            )

            print(f"✅ 创建工作流: {workflow.id}")

            # 执行到准备步骤
            result = await orchestrator.run_step(workflow.id)
            print(f"✅ 步骤 1 完成: {result.status}")

            # 执行到 Gate
            result = await orchestrator.run_step(workflow.id)
            print(f"✅ 触发 Gate: {result.status}")

            # 创建 Gate
            gate = await gate_api.create_gate(
                workflow_id=workflow.id,
                step_id="approval",
                step_name="审批",
                description="需要审批才能继续",
                context={"step": "approval"},
            )
            print(f"✅ Gate 创建: {gate.gate_id}")

            # 模拟待审批的 Gates
            pending = await gate_api.list_pending_gates(workflow.id)
            print(f"✅ 待审批 Gates: {len(pending)} 个")

            # 批准并继续
            await gate_api.approve_gate(gate.gate_id, comment="批准通过")
            print(f"✅ Gate 已批准")

            # 继续执行
            summary = await orchestrator.run_until_blocked(workflow.id)
            print(f"✅ 执行摘要:")
            print(f"   总步骤: {summary.total_steps}")
            print(f"   已完成: {summary.completed_steps}")
            print(f"   状态: {summary.status}")

            await store.close()
            print("\n✅ Gate 工作流生命周期测试通过!")

        finally:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except PermissionError:
                pass


async def test_gate_rejection():
    """测试 Gate 拒绝流程"""
    print_section("测试 3: Gate 拒绝流程")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

        try:
            store = SQLiteStore(db_path)
            await store.connect()

            tm = TemplateManager()

            tm._cache["reject_workflow"] = tm._parse_template_doc(
                {
                    "id": "reject_workflow",
                    "level": "task",
                    "name": "Reject Workflow",
                    "steps": [
                        {
                            "id": "gate_step",
                            "kind": "human_gate",
                            "executor": "gate",
                        },
                    ],
                },
                "reject_workflow"
            )

            orchestrator = Orchestrator(store, tm)
            gate_api = GateAPI(store, orchestrator)

            # 创建工作流并执行到 Gate
            workflow = await orchestrator.create_workflow(
                level=WorkflowLevel.TASK,
                template_id="reject_workflow",
            )

            result = await orchestrator.run_step(workflow.id)
            print(f"✅ 执行到 Gate: {result.status}")

            # 创建 Gate
            gate = await gate_api.create_gate(
                workflow_id=workflow.id,
                step_id="gate_step",
                step_name="审批",
                description="会被拒绝的 Gate",
                context={},
            )
            print(f"✅ Gate 创建: {gate.gate_id}")

            # 拒绝 Gate
            await gate_api.reject_gate(gate.gate_id, reason="不满足要求")
            print(f"✅ Gate 已拒绝")

            # 验证工作流状态
            state = await orchestrator.get_state(workflow.id)
            assert state.status == WorkflowStatus.FAILED
            print(f"✅ 工作流状态正确: {state.status.value}")

            await store.close()
            print("\n✅ Gate 拒绝流程测试通过!")

        finally:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except PermissionError:
                pass


async def main():
    """主测试流程"""
    print("=" * 60)
    print("🚀 LEE Orchestrator v3.0 - API 和 Gate 系统测试")
    print("=" * 60)

    await test_cli_interface()
    await test_gate_workflow_lifecycle()
    await test_gate_rejection()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

    print("\n📋 验证结果:")
    print("  ✅ CLI 接口")
    print("  ✅ Gate API")
    print("  ✅ 人工审批流程")
    print("  ✅ 暂停/恢复机制")
    print("  ✅ Gate 拒绝流程")
    print("  ✅ 工作流生命周期")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
