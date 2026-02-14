"""
LEE CLI

提供统一命令入口：
- lee run <dept>.<workflow>
- lee status [workflow_id]
- lee approve <workflow_id> <gate_id>
- lee workflow create/list/pause/resume/run-step/reject
- lee test-runner run-e2e ...
- lee check-env qa-e2e ...
- lee behavior-check verify ...
- lee diagram-gen render ...
- lee diagram-insert insert ...
- lee md-to-wechat convert ...
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
from lee.cli.commands.diagram_gen import diagram_gen
from lee.cli.commands.diagram_insert import diagram_insert
from lee.cli.commands.md_to_wechat import md_to_wechat
from lee.cli.commands.orchestrator_cmds import wf


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
cli.add_command(diagram_gen, "diagram-gen")
cli.add_command(diagram_insert, "diagram-insert")
cli.add_command(md_to_wechat, "md-to-wechat")
cli.add_command(wf, "workflow")


def main():
    cli()


if __name__ == "__main__":
    main()

