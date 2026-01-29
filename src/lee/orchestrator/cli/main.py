"""
LEE Orchestrator CLI - 命令行工具
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional

import click

from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus, WorkflowInstance
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.core.state_machine import SimpleStateMachine
from lee.orchestrator.core.event_bus import MemoryEventBus


_db: Optional[SQLiteStore] = None
_state_machine: Optional[SimpleStateMachine] = None
_event_bus: Optional[MemoryEventBus] = None


async def init_orchestrator(db_path: str = "orchestrator.db"):
    """初始化组件"""
    global _db, _state_machine, _event_bus
    _db = SQLiteStore(db_path)
    await _db.connect()
    _state_machine = SimpleStateMachine(_db)
    await _state_machine.load_from_db()
    _event_bus = MemoryEventBus()


@click.group()
@click.version_option(version="3.0.0")
def cli():
    """LEE Orchestrator v3.0 - 三层工作流编排系统"""
    pass


@cli.command()
@click.option('--level', required=True, type=click.Choice(['project', 'department', 'task']))
@click.option('--template', required=True)
@click.option('--parent-id', help='父工作流 ID')
@click.option('--db', default='orchestrator.db')
def create(level: str, template: str, parent_id: Optional[str], db: str):
    """创建工作流实例"""
    async def _create():
        await init_orchestrator(db)

        import uuid
        workflow_id = f"wf_{level}_{uuid.uuid4().hex[:8]}"
        workflow = WorkflowInstance(
            id=workflow_id,
            level=WorkflowLevel(level),
            template_id=template,
            status=WorkflowStatus.PENDING,
            data={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            parent_id=parent_id,
        )

        await _db.create_workflow(workflow)
        await _event_bus.publish_workflow_created(workflow_id, level, template)

        click.echo(f"Created {level.upper()} workflow: {workflow_id}")
        click.echo(f"Template: {template}")
        if parent_id:
            click.echo(f"Parent: {parent_id}")

    asyncio.run(_create())


@cli.command()
@click.argument('workflow_id')
@click.option('--db', default='orchestrator.db')
def status(workflow_id: str, db: str):
    """查询工作流状态"""
    async def _status():
        await init_orchestrator(db)

        instance = await _db.get_workflow(workflow_id)
        if not instance:
            click.echo(f"Error: Workflow '{workflow_id}' not found", err=True)
            sys.exit(1)

        click.echo(f"Workflow: {workflow_id} ({instance.level.value})")
        click.echo(f"Status: {instance.status.value}")
        click.echo(f"Template: {instance.template_id}")

        children = await _db.get_children(workflow_id)
        if children:
            click.echo(f"\nChildren ({len(children)}):")
            for child in children:
                click.echo(f"  - {child.id} ({child.level.value}): {child.status.value}")

    asyncio.run(_status())


@cli.command()
@click.option('--db', default='orchestrator.db')
def list(db: str):
    """列出所有工作流"""
    async def _list():
        await init_orchestrator(db)
        instances = await _db.get_all_instances()

        if not instances:
            click.echo("No workflows found.")
            return

        click.echo(f"Total: {len(instances)}\n")
        for inst in instances:
            parent = f" (parent: {inst.parent_id})" if inst.parent_id else ""
            click.echo(f"{inst.id} - {inst.level.value} - {inst.status.value}{parent}")

    asyncio.run(_list())


def main():
    """CLI 入口"""
    cli()


if __name__ == '__main__':
    main()
