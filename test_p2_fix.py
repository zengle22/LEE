"""
Test p2_infra_code fix
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


async def test_p2():
    project_root = Path("e:/projects/ai-marathon-coach").resolve()
    lee_root = Path("E:/ai/LEE").resolve()
    db_path = project_root / "devops" / "orchestrator_p2_test.db"
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
        data={"name": "P2 Test"}
    )

    print(f"\n✅ 工作流创建成功: {workflow.id}")

    # 更新状态为 RUNNING
    await store.update_workflow_status(workflow.id, WorkflowStatus.RUNNING)

    # 运行 p1 和 p2
    print(f"\n🚀 运行 p1_architecture...")
    summary = await orchestrator.run_until_blocked(workflow.id, max_steps=1)
    print(f"   状态: {summary.status}, 完成: {summary.completed_steps}")

    print(f"\n🚀 运行 p2_infra_code...")
    summary = await orchestrator.run_until_blocked(workflow.id, max_steps=1)
    print(f"   状态: {summary.status}, 完成: {summary.completed_steps}")

    # 检查生成的文件
    print(f"\n📁 检查生成的文件:")
    devops_dir = project_root / "devops"

    expected_files = [
        "infra/docker-compose.yml",
        "infra/ansible/inventory/dev.yml",
        "infra/ansible/playbooks/deploy-services.yml",
        "scripts/deploy-dev.sh",
        "scripts/deploy-testing.sh",
    ]

    for f in expected_files:
        full_path = devops_dir / f
        if full_path.exists():
            print(f"   ✅ {f}")
            # 显示文件大小
            size = full_path.stat().st_size
            print(f"      ({size} bytes)")
        else:
            print(f"   ❌ {f} (缺失)")

    # 列出所有 devops 目录下的文件
    print(f"\n📂 所有 devops 文件:")
    for item in sorted(devops_dir.rglob("*")):
        if item.is_file():
            rel_path = item.relative_to(devops_dir)
            print(f"   {rel_path}")

    await store.close()


if __name__ == "__main__":
    asyncio.run(test_p2())
