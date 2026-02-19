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

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

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
from lee.cli.commands.repo import repo
from lee.cli.commands.verify import verify
from lee.cli.commands.chat import chat
from lee.cli.commands.watch import watch
from lee.cli.commands import gates_cmd as gates

try:
    import fcntl
except ImportError:  # pragma: no cover - non-posix fallback
    fcntl = None

LOCK_ENV_DISABLE = "LEE_DISABLE_CLI_LOCK"
READ_ONLY_COMMANDS = {"status", "watch"}


def _should_lock(argv: list[str]) -> bool:
    """
    判断当前命令是否需要持有 CLI 互斥锁。

    约定：
    - `lee status/watch ...` 是只读查询，允许并发执行
    - 其他命令默认需要加锁，避免并发写 workflow/db
    """
    if not argv:
        return False
    first = argv[0]
    if first in ("-h", "--help", "-v", "--version"):
        return False
    if first in READ_ONLY_COMMANDS:
        return False
    return True


def _resolve_project_dir(argv: list[str]) -> Path:
    """
    从 CLI 参数中解析 project-dir（若未指定则使用当前目录）
    """
    for idx, arg in enumerate(argv):
        if arg == "--project-dir" and idx + 1 < len(argv):
            return Path(argv[idx + 1]).resolve()
        if arg.startswith("--project-dir="):
            return Path(arg.split("=", 1)[1]).resolve()
    return Path.cwd().resolve()


def _acquire_cli_lock(argv: list[str]) -> Optional[int]:
    """
    申请 CLI 入口锁，防止同一项目目录并发执行多个 lee 进程。
    """
    if fcntl is None:
        return None

    project_root = _resolve_project_dir(argv)
    lock_dir = project_root / ".lee"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "cli.lock"

    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        owner = {}
        try:
            owner = json.loads(lock_path.read_text(encoding="utf-8") or "{}")
        except Exception:
            owner = {}
        os.close(fd)

        owner_pid = owner.get("pid")
        owner_cmd = owner.get("cmd")
        detail = f"pid={owner_pid}" if owner_pid else "unknown owner"
        if owner_cmd:
            detail += f", cmd={owner_cmd}"
        raise click.ClickException(
            f"Another lee process is running for project '{project_root}' ({detail})."
        )

    metadata = {
        "pid": os.getpid(),
        "started_at": datetime.now().isoformat(),
        "cmd": " ".join(sys.argv),
    }
    os.ftruncate(fd, 0)
    os.write(fd, json.dumps(metadata, ensure_ascii=False).encode("utf-8"))
    os.fsync(fd)
    return fd


def _release_cli_lock(fd: Optional[int]) -> None:
    """释放 CLI 锁"""
    if fd is None:
        return
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


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
cli.add_command(repo)
cli.add_command(verify)
cli.add_command(chat)
cli.add_command(watch)
cli.add_command(gates.gates)
cli.add_command(qa)
cli.add_command(test_runner, "test-runner")
cli.add_command(check_env, "check-env")
cli.add_command(behavior_compliance_checker, "behavior-check")
cli.add_command(diagram_gen, "diagram-gen")
cli.add_command(diagram_insert, "diagram-insert")
cli.add_command(md_to_wechat, "md-to-wechat")
cli.add_command(wf, "workflow")
cli.add_command(repo)
cli.add_command(verify)
cli.add_command(chat)
cli.add_command(watch)


def main():
    lock_fd: Optional[int] = None
    try:
        if (
            os.getenv(LOCK_ENV_DISABLE, "0") not in ("1", "true", "TRUE")
            and _should_lock(sys.argv[1:])
        ):
            try:
                lock_fd = _acquire_cli_lock(sys.argv[1:])
            except click.ClickException as e:
                e.show()
                raise SystemExit(e.exit_code)
        cli()
    finally:
        _release_cli_lock(lock_fd)


if __name__ == "__main__":
    main()
