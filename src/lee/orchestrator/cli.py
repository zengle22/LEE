"""
LEE Orchestrator v3.0 - CLI 接口

提供命令行接口来操作 Orchestrator。

使用方法：
    python -m lee.orchestrator.cli create project <template_id>
    python -m lee.orchestrator.cli run <workflow_id>
    python -m lee.orchestrator.cli status <workflow_id>
    python -m lee.orchestrator.cli list
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import Optional

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager


class LEECLI:
    """LEE Orchestrator CLI"""

    def __init__(self, db_path: str = "lee_orchestrator.db"):
        self.db_path = db_path
        self.store = None
        self.orchestrator = None
        self.tm = None

    async def init(self):
        """初始化组件"""
        self.store = SQLiteStore(self.db_path)
        await self.store.connect()

        self.tm = TemplateManager()
        self.orchestrator = Orchestrator(self.store, self.tm)

    async def close(self):
        """关闭连接"""
        if self.store:
            await self.store.close()

    async def cmd_create(self, args):
        """创建工作流"""
        await self.init()

        level_map = {
            "project": WorkflowLevel.PROJECT,
            "department": WorkflowLevel.DEPARTMENT,
            "task": WorkflowLevel.TASK,
        }

        level = level_map.get(args.level)
        if not level:
            print(f"❌ 无效的层级: {args.level}")
            print(f"   有效层级: project, department, task")
            return 1

        try:
            workflow = await self.orchestrator.create_workflow(
                level=level,
                template_id=args.template_id,
                data={"name": args.name} if args.name else {},
            )

            print(f"✅ 工作流创建成功")
            print(f"   ID: {workflow.id}")
            print(f"   层级: {workflow.level.value}")
            print(f"   模板: {workflow.template_id}")
            print(f"   状态: {workflow.status.value}")

            if args.run:
                print(f"\n🚀 开始执行工作流...")
                summary = await self.orchestrator.run_until_blocked(workflow.id)
                print(f"\n✅ 执行完成:")
                print(f"   总步骤: {summary.total_steps}")
                print(f"   已完成: {summary.completed_steps}")
                print(f"   状态: {summary.status}")

            return 0

        except Exception as e:
            print(f"❌ 创建失败: {e}")
            return 1

        finally:
            await self.close()

    async def cmd_run(self, args):
        """运行工作流"""
        await self.init()

        try:
            print(f"🚀 运行工作流: {args.workflow_id}")

            if args.step:
                # 运行单个步骤
                result = await self.orchestrator.run_step(args.workflow_id, args.step)
                print(f"\n结果: {result.status}")
                print(f"步骤 ID: {result.step_id}")
                print(f"消息: {result.message}")
            else:
                # 运行直到阻塞
                summary = await self.orchestrator.run_until_blocked(
                    args.workflow_id,
                    max_steps=args.max_steps or 10
                )
                print(f"\n✅ 执行完成:")
                print(f"   总步骤: {summary.total_steps}")
                print(f"   已完成: {summary.completed_steps}")
                print(f"   状态: {summary.status}")
                print(f"   耗时: {summary.duration_seconds:.2f}s")

            # 显示最终状态
            state = await self.orchestrator.get_state(args.workflow_id)
            print(f"\n📊 最终状态: {state.status.value}")

            return 0

        except Exception as e:
            print(f"❌ 运行失败: {e}")
            import traceback
            traceback.print_exc()
            return 1

        finally:
            await self.close()

    async def cmd_status(self, args):
        """查询工作流状态"""
        await self.init()

        try:
            state = await self.orchestrator.get_state(args.workflow_id)

            print(f"📊 工作流状态")
            print(f"   ID: {state.workflow_id}")
            print(f"   层级: {state.level.value}")
            print(f"   状态: {state.status.value}")
            print(f"   当前步骤: {state.current_step or '无'}")
            print(f"   父工作流: {state.parent_id or '无'}")
            print(f"   子节点: {len(state.children)} 个")

            if state.data:
                print(f"\n📋 数据:")
                for key, value in state.data.items():
                    if key != "completed_steps" and key != "params":
                        print(f"   {key}: {value}")

            # 查询子工作流
            if state.children:
                print(f"\n📁 子工作流:")
                for child_id in state.children:
                    child_state = await self.orchestrator.get_state(child_id)
                    status_icon = {
                        WorkflowStatus.PENDING: "⏳",
                        WorkflowStatus.RUNNING: "▶️",
                        WorkflowStatus.PAUSED: "⏸️",
                        WorkflowStatus.COMPLETED: "✅",
                        WorkflowStatus.FAILED: "❌",
                    }.get(child_state.status, "")
                    print(f"   {status_icon} {child_id} ({child_state.level.value})")

            return 0

        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return 1

        finally:
            await self.close()

    async def cmd_list(self, args):
        """列出所有工作流"""
        await self.init()

        try:
            instances = await self.store.get_all_instances()

            if not instances:
                print("📭 没有工作流")
                return 0

            print(f"📋 工作流列表 (共 {len(instances)} 个)\n")

            # 按层级分组
            by_level = {
                WorkflowLevel.PROJECT: [],
                WorkflowLevel.DEPARTMENT: [],
                WorkflowLevel.TASK: [],
            }
            for inst in instances:
                by_level[inst.level].append(inst)

            level_icons = {
                WorkflowLevel.PROJECT: "🎯",
                WorkflowLevel.DEPARTMENT: "🏢",
                WorkflowLevel.TASK: "📋",
            }
            status_icons = {
                WorkflowStatus.PENDING: "⏳",
                WorkflowStatus.RUNNING: "▶️",
                WorkflowStatus.PAUSED: "⏸️",
                WorkflowStatus.COMPLETED: "✅",
                WorkflowStatus.FAILED: "❌",
            }

            for level in [WorkflowLevel.PROJECT, WorkflowLevel.DEPARTMENT, WorkflowLevel.TASK]:
                items = by_level[level]
                if items:
                    icon = level_icons[level]
                    print(f"{icon} {level.value.upper()} ({len(items)} 个):")
                    for inst in items:
                        status_icon = status_icons.get(inst.status, "")
                        print(f"  {status_icon} {inst.id}")
                        print(f"     模板: {inst.template_id}")
                        if inst.parent_id:
                            print(f"     父级: {inst.parent_id}")
                        print()

            return 0

        except Exception as e:
            print(f"❌ 列表失败: {e}")
            return 1

        finally:
            await self.close()

    async def cmd_pause(self, args):
        """暂停工作流"""
        await self.init()

        try:
            await self.orchestrator.pause(args.workflow_id)
            print(f"✅ 工作流已暂停: {args.workflow_id}")
            return 0
        except Exception as e:
            print(f"❌ 暂停失败: {e}")
            return 1
        finally:
            await self.close()

    async def cmd_resume(self, args):
        """恢复工作流"""
        await self.init()

        try:
            await self.orchestrator.resume(args.workflow_id)
            print(f"✅ 工作流已恢复: {args.workflow_id}")
            return 0
        except Exception as e:
            print(f"❌ 恢复失败: {e}")
            return 1
        finally:
            await self.close()


async def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="LEE Orchestrator v3.0 - CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--db",
        default="lee_orchestrator.db",
        help="数据库文件路径",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # create 命令
    create_parser = subparsers.add_parser("create", help="创建工作流")
    create_parser.add_argument("level", help="层级 (project/department/task)")
    create_parser.add_argument("template_id", help="模板 ID")
    create_parser.add_argument("--name", help="工作流名称")
    create_parser.add_argument("--run", action="store_true", help="创建后自动运行")

    # run 命令
    run_parser = subparsers.add_parser("run", help="运行工作流")
    run_parser.add_argument("workflow_id", help="工作流 ID")
    run_parser.add_argument("--step", help="指定步骤 ID")
    run_parser.add_argument("--max-steps", type=int, default=10, help="最大执行步数")

    # status 命令
    status_parser = subparsers.add_parser("status", help="查询工作流状态")
    status_parser.add_argument("workflow_id", help="工作流 ID")

    # list 命令
    subparsers.add_parser("list", help="列出所有工作流")

    # pause 命令
    pause_parser = subparsers.add_parser("pause", help="暂停工作流")
    pause_parser.add_argument("workflow_id", help="工作流 ID")

    # resume 命令
    resume_parser = subparsers.add_parser("resume", help="恢复工作流")
    resume_parser.add_argument("workflow_id", help="工作流 ID")

    args = parser.parse_args()
    cli = LEECLI(args.db)

    # 路由到对应的命令
    if args.command == "create":
        sys.exit(await cli.cmd_create(args))
    elif args.command == "run":
        sys.exit(await cli.cmd_run(args))
    elif args.command == "status":
        sys.exit(await cli.cmd_status(args))
    elif args.command == "list":
        sys.exit(await cli.cmd_list(args))
    elif args.command == "pause":
        sys.exit(await cli.cmd_pause(args))
    elif args.command == "resume":
        sys.exit(await cli.cmd_resume(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
