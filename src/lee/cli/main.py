"""
LEE CLI

提供统一命令入口：
- lee run <dept>.<workflow>
- lee status [workflow_id]
- lee approve <workflow_id> <gate_id>
- lee test-runner run-e2e ...
- lee check-env qa-e2e ...
- lee behavior-check verify ...
"""

import click

from lee.cli.commands.run import run
from lee.cli.commands.status import status
from lee.cli.commands.approve import approve
from lee.cli.commands.init import init
from lee.cli.commands.demo import demo
from lee.cli.commands.qa import qa
from lee.cli.commands.test_runner import test_runner
from lee.cli.commands.check_env import check_env
from lee.cli.commands.behavior_compliance_checker import behavior_compliance_checker


@click.group()
def cli():
    """LEE 命令行工具"""
    pass


cli.add_command(run)
cli.add_command(status)
cli.add_command(approve)
cli.add_command(init)
cli.add_command(demo)
cli.add_command(qa)
cli.add_command(test_runner, "test-runner")
cli.add_command(check_env, "check-env")
cli.add_command(behavior_compliance_checker, "behavior-check")


def main():
    cli()


if __name__ == "__main__":
    main()

