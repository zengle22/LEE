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
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from lee import __version__
from lee.orchestrator.core.io_guard import init_path_guard

try:
    import fcntl
except ImportError:  # pragma: no cover - non-posix fallback
    fcntl = None

LOCK_ENV_DISABLE = "LEE_DISABLE_CLI_LOCK"

logger = logging.getLogger(__name__)

# 这些命令允许与 `lee run` 并发执行：
# - 只读查询：status, watch, gates list, gates show
# - 门禁决策：gates approve/reject/decide/revise/flag, approve（独立命令）
# 这些命令可以在 lee run 等待门禁时安全执行
READONLY_COMMANDS = {"status", "watch"}
GATES_READONLY_SUBCOMMANDS = {"list", "show"}
GATES_DECISION_SUBCOMMANDS = {"approve", "reject", "decide", "revise", "flag"}
LIGHTWEIGHT_ARGS = {"-v", "--version"}
WORKFLOW_COMMANDS = {"run", "adr", "epic", "feat", "approve", "status", "watch", "gates"}
SYSTEM_COMMANDS = {"ssot", "workflow", "artifacts", "repo", "verify", "doctor", "context", "governance"}


def _should_lock(argv: list[str]) -> bool:
    """
    判断当前命令是否需要持有 CLI 互斥锁。

    约定：
    - `lee status/watch ...` 是只读查询，允许并发执行
    - `lee gates list/show ...` 是只读查询，允许并发执行
    - `lee gates approve/reject/decide/revise/flag ...` 用于门禁决策，允许与 `lee run` 并发
    - `lee approve ...` (独立命令) 用于门禁决策，允许与 `lee run` 并发
    - 工作流内部调用的子命令（通过 CLAUDE_CODE_ENTRYPOINT 标记）不需要锁
    - 其他命令默认需要加锁，避免并发写 workflow/db
    """
    # 工作流内部调用豁免锁检查 (BUG-2026-0060)
    if os.getenv("CLAUDE_CODE_ENTRYPOINT"):
        return False

    if not argv:
        return False

    first = argv[0]

    # Help/version 不需要锁
    if first in ("-h", "--help", "-v", "--version"):
        return False

    # 只读命令
    if first in READONLY_COMMANDS:
        return False

    # 独立的 approve 命令（与 gates approve 功能重复）
    if first == "approve":
        return False

    # `lee run` 使用 workflow-scope 互斥，不再使用项目级 CLI 锁
    if first == "run":
        return False

    # gates 子命令需要特殊处理
    if first == "gates" and len(argv) >= 2:
        subcommand = argv[1]
        # 只读子命令或决策子命令都不需要锁
        if subcommand in GATES_READONLY_SUBCOMMANDS or subcommand in GATES_DECISION_SUBCOMMANDS:
            return False

    # 其他命令需要锁
    return True


def _is_lightweight_invocation(argv: list[str]) -> bool:
    """Whether the invocation only needs top-level CLI metadata."""
    return not argv or argv[0] in LIGHTWEIGHT_ARGS


def _resolve_project_dir(argv: list[str]) -> Path:
    """
    从 CLI 参数中解析 project-dir（若未指定则使用 discover_workspace_root 发现）

    规则：
    1. CLI 参数 --project-dir（最高优先级）
    2. discover_workspace_root 自动发现 .lee 目录
    3. 退回当前目录（此时 run 等命令应报错提示 init）
    """
    # 1. CLI 参数
    cli_project_dir = None
    for idx, arg in enumerate(argv):
        if arg == "--project-dir" and idx + 1 < len(argv):
            cli_project_dir = argv[idx + 1]
            break
        if arg.startswith("--project-dir="):
            cli_project_dir = arg.split("=", 1)[1]
            break

    if cli_project_dir:
        return Path(cli_project_dir).resolve()

    # 2. 使用 discover_workspace_root 自动发现
    from lee.data_path import discover_workspace_root

    cwd = Path.cwd()
    workspace = discover_workspace_root(cwd)

    # 如果发现 workspace 且包含 .lee 目录，直接返回
    if (workspace / ".lee").is_dir():
        return workspace

    # 3. 退回 cwd（后续命令应检测并报错）
    return cwd


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
        except Exception as e:
            logger.debug(f"Failed to read lock file: {e}")
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


class WorkflowFirstGroup(click.Group):
    """Top-level CLI group with workflow-first help sections."""

    def format_commands(self, ctx, formatter):
        commands = []
        for subcommand in self.list_commands(ctx):
            command = self.get_command(ctx, subcommand)
            if command is None or getattr(command, "hidden", False):
                continue
            commands.append((subcommand, command))

        sections = [
            ("Workflow Commands", [item for item in commands if item[0] in WORKFLOW_COMMANDS]),
            ("System Commands", [item for item in commands if item[0] in SYSTEM_COMMANDS]),
            (
                "Other Commands",
                [item for item in commands if item[0] not in WORKFLOW_COMMANDS and item[0] not in SYSTEM_COMMANDS],
            ),
        ]

        for section_name, section_commands in sections:
            if not section_commands:
                continue
            rows = []
            for subcommand, command in section_commands:
                rows.append((subcommand, command.get_short_help_str(formatter.width) or ""))
            with formatter.section(section_name):
                formatter.write_dl(rows)


@click.group(context_settings={"help_option_names": ["-h", "--help"]}, cls=WorkflowFirstGroup)
@click.version_option(__version__, "-v", "--version", message="%(prog)s %(version)s")
def cli():
    """LEE 命令行工具"""
    pass


def _register_commands() -> None:
    if getattr(cli, "_lee_commands_registered", False):
        return

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
    from lee.cli.commands.artifacts import artifacts
    from lee.cli.commands.ssot import ssot
    from lee.cli.commands.context import context
    from lee.cli.commands.task_brief import task_brief
    from lee.cli.commands.doctor import doctor
    from lee.cli.commands.governance import governance
    from lee.cli.commands.workflow_entrypoints import adr, epic, feat

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
    cli.add_command(artifacts)
    cli.add_command(ssot)
    cli.add_command(context)
    cli.add_command(task_brief)
    cli.add_command(doctor)
    cli.add_command(governance)
    cli.add_command(adr)
    cli.add_command(epic)
    cli.add_command(feat)
    cli._lee_commands_registered = True


def main():
    lock_fd: Optional[int] = None
    try:
        if not _is_lightweight_invocation(sys.argv[1:]):
            _register_commands()

        # 初始化路径守卫（只在 dev/CI 模式下启用）
        project_root = _resolve_project_dir(sys.argv[1:])
        init_path_guard(str(project_root))

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
