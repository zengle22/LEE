"""
Run complete DevOps workflow
"""
import asyncio
import sys
from pathlib import Path

# Add LEE src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager


async def run_full_workflow():
    project_root = Path("e:/projects/ai-marathon-coach").resolve()
    lee_root = Path("E:/ai/LEE").resolve()
    db_path = project_root / "devops" / "orchestrator_full.db"
    template_dir = lee_root / "spec-global" / "departments" / "devops" / "workflows"

    # 删除旧数据库
    if db_path.exists():
        db_path.unlink()

    print(f"📂 项目根目录: {project_root}")

    # 初始化
    store = SQLiteStore(str(db_path))
    await store.connect()

    tm = TemplateManager(template_dir=str(template_dir))
    orchestrator = Orchestrator(store, tm, project_root=str(project_root))

    # 创建工作流
    workflow = await orchestrator.create_workflow(
        level=WorkflowLevel.DEPARTMENT,
        template_id="workflow.devops.deployment",
        data={"name": "Full DevOps Workflow"}
    )

    print(f"\n✅ 工作流创建成功: {workflow.id}")

    # 更新状态为 RUNNING
    await store.update_workflow_status(workflow.id, WorkflowStatus.RUNNING)

    # 获取所有步骤
    all_steps = tm.get_steps("workflow.devops.deployment")
    print(f"\n📋 工作流步骤 ({len(all_steps)} 个):")
    for step in all_steps:
        print(f"   {step.id} ({step.kind}): {step.agent_id or step.skill_id or ''}")

    # 运行所有步骤（自动通过人工门禁）
    print(f"\n🚀 开始执行工作流...")
    completed = 0
    max_iterations = 20

    for iteration in range(max_iterations):
        print(f"\n--- 迭代 {iteration + 1} ---")

        # 运行直到阻塞或完成
        summary = await orchestrator.run_until_blocked(workflow.id, max_steps=1)
        print(f"   完成: {summary.completed_steps}/{summary.total_steps}")
        print(f"   状态: {summary.status}")

        # 获取当前工作流状态
        instance = await store.get_workflow(workflow.id)
        print(f"   工作流状态: {instance.status.value}")

        # 检查是否完成或失败
        if instance.status == WorkflowStatus.COMPLETED:
            print(f"\n🎉 工作流完成！")
            break
        elif instance.status == WorkflowStatus.FAILED:
            print(f"\n❌ 工作流失败")
            # 查看失败原因
            executions = await store.get_task_executions(workflow.id)
            for exe in executions:
                if exe.status.value == "failed":
                    print(f"   失败步骤: {exe.step_name}")
                    print(f"   错误: {exe.error_message}")
            break
        elif instance.status == WorkflowStatus.PAUSED:
            # 人工门禁，自动通过
            print(f"   🚦 遇到人工门禁，自动通过...")
            pending_gates = await store.get_pending_gates(workflow.id)
            for gate in pending_gates:
                print(f"      通过门禁: {gate.gate_id}")
                await store.update_gate_approval(
                    gate.id,
                    "approved",
                    "Auto-approved by script"
                )
            # 恢复工作流
            await store.update_workflow_status(workflow.id, WorkflowStatus.RUNNING)

    # 检查生成的文件
    print(f"\n📁 生成的文件:")
    devops_dir = project_root / "devops"

    # 列出关键文件
    key_files = [
        "infra-architecture.yaml",
        "env-matrix.yaml",
        "release-strategy.md",
        "infra/docker-compose.yml",
        "infra/ansible/inventory/dev.yml",
        "scripts/deploy-dev.sh",
        "scripts/deploy-testing.sh",
        "env/env-config.dev.yaml",
    ]

    for f in key_files:
        full_path = devops_dir / f
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"   ✅ {f} ({size} bytes)")
        else:
            print(f"   ❌ {f} (缺失)")

    # 列出所有目录
    print(f"\n📂 目录结构:")
    for item in sorted(devops_dir.rglob("*")):
        if item.is_dir():
            files_count = len(list(item.iterdir()))
            print(f"   {item.relative_to(devops_dir)}/ ({files_count} 项)")

    await store.close()


if __name__ == "__main__":
    asyncio.run(run_full_workflow())
