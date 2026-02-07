"""
LEE CLI

提供统一命令入口：
- lee run <dept>.<workflow>
- lee status [workflow_id]
- lee approve <workflow_id> <gate_id>
"""

import click

from lee.cli.commands.run import run
from lee.cli.commands.status import status
from lee.cli.commands.approve import approve
from lee.cli.commands.init import init
from lee.cli.commands.demo import demo


@click.group()
def cli():
    """LEE 命令行工具"""
    pass


cli.add_command(run)
cli.add_command(status)
cli.add_command(approve)
cli.add_command(init)
cli.add_command(demo)


def main():
    cli()


if __name__ == "__main__":
    main()
