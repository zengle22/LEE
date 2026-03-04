"""QA CLI commands"""

from __future__ import annotations

import click

from .test_set import test_set
from .test_plan import test_plan
from .test_run import test_run
from .sut import sut


@click.group()
def qa():
    """QA 工作流命令"""
    pass


qa.add_command(test_set)
qa.add_command(test_plan)
qa.add_command(test_run)
qa.add_command(sut)


# 快捷命令
@qa.command("run")
@click.argument("test_plan_id")
@click.option("--build", required=True, help="构建版本")
@click.option("--commit", required=True, help="构建 commit")
@click.option("--env", default="test", help="测试环境")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--max-steps", default=50, show_default=True, help="最大执行步数")
def run_test_plan(test_plan_id: str, build: str, commit: str, env: str,
                  project_dir: str, max_steps: int) -> None:
    """快捷执行 Test Plan (= test-run start)"""
    from .test_run import _start_test_run
    _start_test_run(test_plan_id, build, commit, env, project_dir, max_steps)
