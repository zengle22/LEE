"""
LEE Orchestrator v3.0 - 完整演示

演示三层工作流编排系统的核心功能：
1. 创建 L1 项目工作流（AI ChatBot 项目）
2. 创建 L2 部门工作流（开发部门）
3. 创建 L3 任务工作流（具体的开发任务）
4. 展示状态转换和层级关系
"""

import asyncio
import sys
import os

# 添加 src 目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.core.state_machine import SimpleStateMachine
from lee.orchestrator.core.event_bus import MemoryEventBus
from lee.orchestrator.core.template_engine import TemplateEngine
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.runners import ProjectRunner, DepartmentRunner, TaskRunner
from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus


class OrchestratorDemo:
    """LEE Orchestrator 演示类"""

    def __init__(self, db_path: str = "demo_orchestrator.db"):
        self.db_path = db_path
        self.db = None
        self.orchestrator = None
        self.project_runner = None
        self.dept_runner = None
        self.task_runner = None

    async def init(self):
        """初始化 Orchestrator 组件"""
        print("=" * 60)
        print("🚀 LEE Orchestrator v3.0 - 三层工作流编排演示")
        print("=" * 60)
        print()

        self.db = SQLiteStore(self.db_path)
        await self.db.connect()

        state_machine = SimpleStateMachine(self.db)
        event_bus = MemoryEventBus()
        template_engine = TemplateEngine()

        self.orchestrator = Orchestrator(self.db, state_machine, event_bus, template_engine)
        self.project_runner = ProjectRunner(self.orchestrator)
        self.dept_runner = DepartmentRunner(self.orchestrator)
        self.task_runner = TaskRunner(self.orchestrator)

        print("✅ Orchestrator 组件初始化完成")
        print()

    async def demo_create_three_level_workflow(self):
        """演示：创建三层嵌套工作流"""
        print("=" * 60)
        print("📝 步骤 1: 创建三层嵌套工作流")
        print("=" * 60)
        print()

        # L1: 创建项目工作流
        print("🎯 创建 L1: AI ChatBot 项目工作流")
        project = await self.project_runner.create_project(
            template_id="project_main",
            data={
                "project_name": "AI ChatBot",
                "description": "企业级 AI 聊天机器人",
                "owner": "产品团队",
            }
        )
        print(f"   ✅ 项目 ID: {project.id}")
        print(f"   ✅ 模板: {project.template_id}")
        print(f"   ✅ 状态: {project.status.value}")
        print()

        # L2: 创建部门工作流
        print("🏢 创建 L2: 开发部门工作流")
        dev_dept = await self.project_runner.spawn_department(
            project_id=project.id,
            template_id="dept_development",
            data={
                "dept_name": "开发部门",
                "lead": "张三",
            }
        )
        print(f"   ✅ 部门 ID: {dev_dept.id}")
        print(f"   ✅ 父项目: {dev_dept.parent_id}")
        print(f"   ✅ 状态: {dev_dept.status.value}")
        print()

        # L2: 创建测试部门工作流
        print("🧪 创建 L2: 测试部门工作流")
        qa_dept = await self.project_runner.spawn_department(
            project_id=project.id,
            template_id="dept_testing",
            data={
                "dept_name": "测试部门",
                "lead": "李四",
            }
        )
        print(f"   ✅ 部门 ID: {qa_dept.id}")
        print(f"   ✅ 父项目: {qa_dept.parent_id}")
        print(f"   ✅ 状态: {qa_dept.status.value}")
        print()

        # L3: 创建任务工作流（开发部门下的任务）
        print("📋 创建 L3: 开发任务（归属开发部门）")
        task1 = await self.dept_runner.spawn_task(
            department_id=dev_dept.id,
            template_id="task_backend_api",
            data={
                "task_name": "后端 API 开发",
                "assignee": "王五",
                "priority": "P0",
            }
        )
        print(f"   ✅ 任务 ID: {task1.id}")
        print(f"   ✅ 父部门: {task1.parent_id}")
        print()

        task2 = await self.dept_runner.spawn_task(
            department_id=dev_dept.id,
            template_id="task_frontend_ui",
            data={
                "task_name": "前端 UI 开发",
                "assignee": "赵六",
                "priority": "P1",
            }
        )
        print(f"   ✅ 任务 ID: {task2.id}")
        print(f"   ✅ 父部门: {task2.parent_id}")
        print()

        # L3: 创建任务工作流（测试部门下的任务）
        print("🧪 创建 L3: 测试任务（归属测试部门）")
        task3 = await self.dept_runner.spawn_task(
            department_id=qa_dept.id,
            template_id="task_integration_test",
            data={
                "task_name": "集成测试",
                "assignee": "孙七",
                "priority": "P0",
            }
        )
        print(f"   ✅ 任务 ID: {task3.id}")
        print(f"   ✅ 父部门: {task3.parent_id}")
        print()

        return project, dev_dept, qa_dept

    async def demo_query_workflow_tree(self, project_id: str):
        """演示：查询完整工作流树"""
        print()
        print("=" * 60)
        print("📊 步骤 2: 查询完整工作流树")
        print("=" * 60)
        print()

        # 递归打印工作流树
        async def print_tree(workflow_id: str, level: int = 0):
            instance = await self.db.get_workflow(workflow_id)
            if not instance:
                return

            indent = "  " * level
            icon = {
                WorkflowLevel.PROJECT: "🎯",
                WorkflowLevel.DEPARTMENT: "🏢",
                WorkflowLevel.TASK: "📋",
            }.get(instance.level, "📄")

            print(f"{indent}{icon} {instance.id}")
            print(f"{indent}   状态: {instance.status.value}")
            print(f"{indent}   模板: {instance.template_id}")

            # 显示关键数据
            if instance.data:
                key_info = []
                if "project_name" in instance.data:
                    key_info.append(f"项目: {instance.data['project_name']}")
                if "dept_name" in instance.data:
                    key_info.append(f"部门: {instance.data['dept_name']}")
                if "task_name" in instance.data:
                    key_info.append(f"任务: {instance.data['task_name']}")
                if key_info:
                    print(f"{indent}   信息: {', '.join(key_info)}")

            # 递归打印子工作流
            children = await self.db.get_children(workflow_id)
            if children:
                print(f"{indent}   子节点: {len(children)} 个")
                for child in children:
                    await print_tree(child.id, level + 1)
            print()

        await print_tree(project_id)

    async def demo_state_transitions(self, task_id: str):
        """演示：状态转换"""
        print("=" * 60)
        print("⚙️  步骤 3: 演示状态转换")
        print("=" * 60)
        print()

        # PENDING -> RUNNING
        instance = await self.db.get_workflow(task_id)
        print(f"📍 当前状态: {instance.status.value}")

        await self.orchestrator.run_step(task_id)
        instance = await self.db.get_workflow(task_id)
        print(f"➡️  运行后: {instance.status.value}")
        print()

        # RUNNING -> COMPLETED
        await self.orchestrator.complete_workflow(task_id)
        instance = await self.db.get_workflow(task_id)
        print(f"✅ 完成状态: {instance.status.value}")
        print(f"📅 完成时间: {instance.completed_at}")
        print()

    async def demo_statistics(self, project_id: str):
        """演示：统计信息"""
        print("=" * 60)
        print("📈 步骤 4: 统计信息")
        print("=" * 60)
        print()

        # 统计各级别工作流数量
        all_instances = await self.db.get_all_instances()

        stats = {
            WorkflowLevel.PROJECT: 0,
            WorkflowLevel.DEPARTMENT: 0,
            WorkflowLevel.TASK: 0,
        }

        status_stats = {
            WorkflowStatus.PENDING: 0,
            WorkflowStatus.RUNNING: 0,
            WorkflowStatus.COMPLETED: 0,
            WorkflowStatus.PAUSED: 0,
            WorkflowStatus.FAILED: 0,
        }

        for inst in all_instances:
            stats[inst.level] += 1
            status_stats[inst.status] += 1

        print("📊 工作流数量统计:")
        print(f"   L1 (项目): {stats[WorkflowLevel.PROJECT]} 个")
        print(f"   L2 (部门): {stats[WorkflowLevel.DEPARTMENT]} 个")
        print(f"   L3 (任务):  {stats[WorkflowLevel.TASK]} 个")
        print(f"   总计:     {len(all_instances)} 个")
        print()

        print("📊 状态分布:")
        for status, count in status_stats.items():
            if count > 0:
                print(f"   {status.value}: {count} 个")
        print()

    async def run(self):
        """运行完整演示"""
        try:
            await self.init()

            # 步骤 1: 创建三层工作流
            project, dev_dept, qa_dept = await self.demo_create_three_level_workflow()

            # 步骤 2: 查询工作流树
            await self.demo_query_workflow_tree(project.id)

            # 步骤 3: 状态转换演示
            # 获取一个 L3 任务进行演示
            children = await self.db.get_children(dev_dept.id)
            if children:
                task_id = children[0].id
                await self.demo_state_transitions(task_id)

            # 步骤 4: 统计信息
            await self.demo_statistics(project.id)

            print("=" * 60)
            print("🎉 演示完成！")
            print("=" * 60)
            print()
            print("💡 提示：可以使用 CLI 查看工作流状态")
            print(f"   $ orchestrator status {project.id}")
            print(f"   $ orchestrator list")
            print()

        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.db:
                await self.db.close()


async def main():
    """主函数"""
    demo = OrchestratorDemo("demo_orchestrator.db")
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())
