"""lee doctor command - 诊断 LEE 配置和环境"""

from __future__ import annotations

import click
from pathlib import Path
from typing import Optional

from lee.data_path import (
    discover_workspace_root,
    load_lee_lock,
    resolve_spec,
    SpecResolveInput,
    get_builtin_spec_traversable,
)
from lee.orchestrator.config_loader import load_config


@click.command()
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--self-check", is_flag=True, help="执行安装后自检")
@click.option("--spec-root", "cli_spec_root", default=None, help="指定 spec-root（覆盖配置）")
def doctor(project_dir: str, self_check: bool, cli_spec_root: Optional[str]) -> None:
    """
    诊断 LEE 配置和环境

    显示：
    - Workspace 发现结果
    - Config 加载结果
    - Lee lock 信息
    - Spec 解析结果

    使用 --self-check 执行安装后自检验证资源可用性。
    """
    workspace_root = Path(project_dir)

    # 1. Workspace 发现
    discovered = discover_workspace_root(workspace_root)
    click.echo(f"✓ Workspace: {discovered}")

    # 2. 检查 .lee 目录
    lee_dir = discovered / ".lee"
    if not lee_dir.is_dir():
        click.echo(f"✗ .lee directory not found")
        click.echo(f"  Run 'lee init' first or pass --project-dir")
        return

    click.echo(f"✓ .lee directory exists")

    # 3. 加载配置
    try:
        config = load_config(str(discovered))
        click.echo(f"✓ Config loaded")
        click.echo(f"  spec_root: {config.spec_root or 'builtin (default)'}")
        click.echo(f"  demo_mode: {config.demo_mode}")
    except Exception as e:
        click.echo(f"✗ Config load failed: {e}")

    # 4. 加载 lock
    lock = load_lee_lock(discovered)
    if lock:
        click.echo(f"✓ Lock file loaded")
        click.echo(f"  lee_version: {lock.lee_version}")
        click.echo(f"  mode: {lock.mode}")
        click.echo(f"  lee_install: {lock.lee_install}")
        if lock.lee_src:
            click.echo(f"  lee_src: {lock.lee_src}")
    else:
        click.echo(f"  (no lock file - may not be initialized)")

    # 5. Spec 解析
    try:
        result = resolve_spec(SpecResolveInput(
            workspace_root=discovered,
            cli_spec_root=cli_spec_root,
            config_spec_root=config.spec_root,
            lock_mode=lock.mode if lock else None,
            lock_lee_src=lock.lee_src if lock else None,
        ))
        click.echo(f"✓ Spec Resolve:")
        click.echo(f"  source: {result.source}")
        click.echo(f"  kind: {result.kind}")
        click.echo(f"  value: {result.value}")
    except Exception as e:
        click.echo(f"✗ Spec resolve failed: {e}")

    # 6. 自检
    if self_check:
        click.echo(f"\n--- Self Check ---")
        self_check_builtin_spec()


def self_check_builtin_spec():
    """自检包内 spec 是否可用"""
    try:
        # 检查 Traversable 是否可用
        t = get_builtin_spec_traversable()
        click.echo(f"✓ Builtin spec traversable accessible")

        # 尝试列举内容
        try:
            from importlib.resources import as_file
            with as_file(t) as p:
                if p.exists():
                    # 抽样检查
                    workflows = list(p.glob("**/workflows/*.yaml"))[:3]
                    skills = list(p.glob("**/skills/*/skill.yaml"))[:5]
                    agents = list(p.glob("**/agents/*/agent.yaml"))[:3]

                    click.echo(f"✓ Sample workflows: {len(workflows)} found")
                    click.echo(f"✓ Sample skills: {len(skills)} found")
                    click.echo(f"✓ Sample agents: {len(agents)} found")
                else:
                    click.echo(f"✗ Builtin spec path does not exist")
        except Exception as e:
            click.echo(f"✗ Cannot enumerate builtin spec: {e}")

    except Exception as e:
        click.echo(f"✗ Builtin spec check failed: {e}")
