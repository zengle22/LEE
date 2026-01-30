"""
Shell 命令工具

提供安全的命令执行功能。
"""

import subprocess
import time
import os
from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class ShellResult:
    """Shell 命令执行结果"""
    exit_code: int
    stdout: str
    stderr: str
    command: str
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        """是否执行成功"""
        return self.exit_code == 0


def run_shell(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 600,
    env: Optional[Dict[str, str]] = None,
    shell: bool = True,
) -> ShellResult:
    """
    执行 Shell 命令

    Args:
        command: 命令字符串
        cwd: 工作目录
        timeout: 超时时间（秒）
        env: 环境变量（会与系统环境变量合并）
        shell: 是否使用 shell

    Returns:
        执行结果
    """
    start_time = time.time()

    # 合并环境变量
    process_env = os.environ.copy()
    if env is not None:
        process_env.update(env)

    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=process_env,
        )

        stdout, stderr = proc.communicate(timeout=timeout)
        exit_code = proc.returncode
        duration = time.time() - start_time

        return ShellResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            command=command,
            duration_seconds=duration,
        )

    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        return ShellResult(
            exit_code=124,  # 124 是 timeout 的标准 exit code
            stdout=stdout or "",
            stderr=stderr or "",
            command=command,
            duration_seconds=time.time() - start_time,
        )


def run_pytest(
    test_path: str = ".",
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    timeout: int = 600,
    verbose: bool = False,
) -> ShellResult:
    """
    执行 pytest

    Args:
        test_path: 测试目录或文件
        args: 额外的 pytest 参数
        cwd: 工作目录
        timeout: 超时
        verbose: 是否详细输出

    Returns:
        执行结果
    """
    cmd_parts = ["python", "-m", "pytest"]

    if verbose:
        cmd_parts.append("-v")
    else:
        cmd_parts.append("-q")

    if args:
        cmd_parts.extend(args)

    cmd_parts.append(test_path)

    cmd_str = " ".join(cmd_parts)
    return run_shell(cmd_str, cwd=cwd, timeout=timeout, shell=True)


def run_command_list(
    commands: List[str],
    cwd: Optional[str] = None,
    timeout: int = 600,
    stop_on_error: bool = True,
) -> List[ShellResult]:
    """
    顺序执行多个命令

    Args:
        commands: 命令列表
        cwd: 工作目录
        timeout: 每个命令的超时
        stop_on_error: 遇到错误是否停止

    Returns:
        执行结果列表
    """
    results = []
    for cmd in commands:
        result = run_shell(cmd, cwd=cwd, timeout=timeout)
        results.append(result)

        if not result.success and stop_on_error:
            break

    return results
