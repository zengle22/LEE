#!/usr/bin/env python3
"""
Claude Code Executor 端到端演示

展示 ClaudeCodeExecutor 的完整执行过程：

  Phase 1: 输入验证         — 确认 goal/workspace 存在
  Phase 2: 治理约束注入     — system prompt 包含白名单/边界
  Phase 3: Claude CLI 调用  — subprocess 调用 claude --print
  Phase 4: 输出解析         — 提取 JSON 结构化结果
  Phase 5: Diff 摘要        — git diff --numstat
  Phase 6: Evidence Bundle  — 写入 conversation.log + result.json + input_snapshot.json
  Phase 7: 状态判定         — success / fail / needs_human / timeout

运行方式：
    cd /Users/zengle/git/ai/lee
    python demos/demo_claude_code_executor.py

前置条件：
    - claude CLI 已安装 (npm install -g @anthropic-ai/claude-code)
    - 当前目录为项目根目录
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

# 确保能 import 项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lee.orchestrator.execution.claude_code_executor import ClaudeCodeExecutor


# ========================================================================
# 输出样式
# ========================================================================

CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def banner(text: str):
    width = 60
    print(f"\n{CYAN}{'═' * width}{RESET}")
    print(f"{CYAN}║{RESET} {BOLD}{text}{RESET}")
    print(f"{CYAN}{'═' * width}{RESET}\n")


def phase(num: int, title: str):
    print(f"\n{YELLOW}▶ Phase {num}: {title}{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")


def kv(key: str, value, indent: int = 2):
    prefix = " " * indent
    if isinstance(value, (dict, list)):
        vstr = json.dumps(value, ensure_ascii=False, indent=2)
        # 缩进多行
        vstr = vstr.replace("\n", f"\n{prefix}  ")
        print(f"{prefix}{DIM}{key}:{RESET} {vstr}")
    else:
        print(f"{prefix}{DIM}{key}:{RESET} {value}")


def success(msg: str):
    print(f"\n  {GREEN}✅ {msg}{RESET}")


def fail(msg: str):
    print(f"\n  {RED}❌ {msg}{RESET}")


def info(msg: str):
    print(f"  {DIM}{msg}{RESET}")


# ========================================================================
# 准备演示工作空间
# ========================================================================

def prepare_workspace() -> Path:
    """创建一个小型演示项目作为 workspace"""
    ws = Path(tempfile.mkdtemp(prefix="lee-demo-"))

    # 初始化 git
    os.system(f"cd {ws} && git init -q && git config user.email demo@lee && git config user.name demo")

    # 创建一个简单的 Python 文件（有 bug）
    (ws / "calculator.py").write_text("""\
\"\"\"Simple calculator module.\"\"\"


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    return a / b  # BUG: no zero-division check
""")

    # 创建一个简单测试
    (ws / "test_calculator.py").write_text("""\
from calculator import add, subtract, multiply, divide
import pytest


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(5, 3) == 2


def test_multiply():
    assert multiply(3, 4) == 12


def test_divide():
    assert divide(10, 2) == 5.0


def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(10, 0)  # This test will FAIL because divide raises ZeroDivisionError, not ValueError
""")

    # 初始提交
    os.system(f"cd {ws} && git add -A && git commit -q -m 'initial'")

    return ws


# ========================================================================
# 主演示流程
# ========================================================================

async def run_demo():
    banner("Claude Code Executor — 端到端演示")

    # ============ 准备 ============
    print(f"{DIM}准备演示工作空间...{RESET}")
    workspace = prepare_workspace()
    evidence_dir = workspace / ".workflow" / "claude-code" / "demo-run"
    print(f"  workspace: {workspace}")
    print(f"  evidence:  {evidence_dir}")

    # 展示初始文件
    print(f"\n{DIM}📂 工作空间文件:{RESET}")
    for f in sorted(workspace.glob("*.py")):
        lines = f.read_text().count("\n")
        print(f"  {f.name} ({lines} lines)")

    # ============ Phase 1: 输入验证 ============
    phase(1, "输入验证")

    executor = ClaudeCodeExecutor()
    info("创建 ClaudeCodeExecutor 实例")

    # 演示验证失败
    err = executor._validate_input({"workspace": str(workspace)})
    info(f"缺少 goal → {RED}{err}{RESET}")

    err = executor._validate_input({"goal": "test", "workspace": "/nonexistent"})
    info(f"workspace 不存在 → {RED}{err}{RESET}")

    err = executor._validate_input({"goal": "test", "workspace": str(workspace)})
    info(f"合法输入 → {GREEN}通过{RESET}")

    # ============ Phase 2: 治理约束注入 ============
    phase(2, "治理约束注入 (System Prompt)")

    goal = "修复 calculator.py 中的 divide 函数：当除数为 0 时应抛出 ValueError 而不是 ZeroDivisionError。然后运行测试确保通过。"

    system_prompt = executor._build_system_prompt(
        goal=goal,
        workspace=str(workspace),
        allowed_commands=["python", "pytest"],
        write_scope=["calculator.py"],
        max_iterations=3,
        stop_conditions={"on_test_pass": "stop", "on_test_fail": "fix_and_retry"},
        system_prompt_extra="仅修改 divide 函数，不要修改其他函数。",
    )
    print(f"\n{DIM}生成的 System Prompt ({len(system_prompt)} chars):{RESET}")
    for line in system_prompt.split("\n")[:15]:
        print(f"  {DIM}│{RESET} {line}")
    print(f"  {DIM}│ ...({system_prompt.count(chr(10)) - 15} more lines){RESET}")

    # ============ Phase 3: Claude CLI 调用 ============
    phase(3, "Claude CLI 调用")

    input_data = {
        "goal": goal,
        "workspace": str(workspace),
        "allowed_commands": ["python", "pytest"],
        "write_scope": ["calculator.py"],
        "max_iterations": 3,
        "timeout_seconds": 120,
        "stop_conditions": {
            "on_test_pass": "stop",
            "on_test_fail": "fix_and_retry",
        },
        "system_prompt_extra": "仅修改 divide 函数，不要修改其他函数。",
        "evidence_base": str(evidence_dir),
    }

    info("输入契约:")
    for k, v in input_data.items():
        if k == "evidence_base":
            continue
        kv(k, v, indent=4)

    print(f"\n  {BOLD}⏳ 正在调用 claude CLI...{RESET}")
    print(f"  {DIM}(这可能需要 30-60 秒，Claude 会阅读代码、修复 bug、运行测试){RESET}\n")

    start = datetime.now()
    result = await executor.execute(input_data)
    elapsed = (datetime.now() - start).total_seconds()

    # ============ Phase 4: 输出解析 ============
    phase(4, "输出解析")

    kv("status", result["status"])
    kv("iterations_used", result["iterations_used"])
    kv("changed_files", result["changed_files"])
    kv("commands_run", result["commands_run"])
    kv("test_results", result["test_results"])
    if result.get("error"):
        kv("error", result["error"])
    kv("elapsed", f"{elapsed:.1f}s")

    # ============ Phase 5: Diff 摘要 ============
    phase(5, "Diff 摘要")

    diff_summary = result.get("diff_summary", {})
    kv("files_changed", diff_summary.get("files_changed", 0))
    kv("lines_added", diff_summary.get("lines_added", 0))
    kv("lines_deleted", diff_summary.get("lines_deleted", 0))

    # 展示实际 diff
    import subprocess
    diff_result = subprocess.run(
        ["git", "diff"], capture_output=True, text=True, cwd=str(workspace)
    )
    if diff_result.stdout:
        print(f"\n  {DIM}git diff 输出:{RESET}")
        for line in diff_result.stdout.split("\n")[:25]:
            color = GREEN if line.startswith("+") else (RED if line.startswith("-") else DIM)
            print(f"  {color}{line}{RESET}")
        total_lines = diff_result.stdout.count("\n")
        if total_lines > 25:
            print(f"  {DIM}...({total_lines - 25} more lines){RESET}")

    # ============ Phase 6: Evidence Bundle ============
    phase(6, "Evidence Bundle")

    evidence_path = result.get("evidence_bundle_path", "")
    if evidence_path and Path(evidence_path).exists():
        info(f"bundle 目录: {evidence_path}")
        for f in sorted(Path(evidence_path).iterdir()):
            size = f.stat().st_size
            print(f"    📄 {f.name} ({size:,} bytes)")

        # 展示 result.json
        result_json = Path(evidence_path) / "result.json"
        if result_json.exists():
            data = json.loads(result_json.read_text())
            print(f"\n  {DIM}result.json 内容:{RESET}")
            formatted = json.dumps(data, ensure_ascii=False, indent=2)
            for line in formatted.split("\n")[:20]:
                print(f"    {line}")

        # 展示 input_snapshot 验证脱敏
        snapshot = Path(evidence_path) / "input_snapshot.json"
        if snapshot.exists():
            snap_data = json.loads(snapshot.read_text())
            has_token = "token_context" in snap_data
            info(f"input_snapshot.json 包含 token_context: {RED if has_token else GREEN}{'是' if has_token else '否 (已脱敏)'}{RESET}")
    else:
        info(f"evidence 目录不存在: {evidence_path}")

    # ============ Phase 7: 状态判定 ============
    phase(7, "最终状态判定")

    status = result["status"]
    if status == "success":
        success(f"执行成功！Claude Code 修复了 bug 并通过了测试 ({elapsed:.1f}s)")
    elif status == "timeout":
        fail(f"执行超时 ({elapsed:.1f}s)")
    elif status == "needs_human":
        print(f"  {YELLOW}⚠️  需要人工审查: {result.get('error', '')}{RESET}")
    else:
        fail(f"执行失败: {result.get('error', 'unknown')}")

    # 验证修复结果
    print(f"\n{DIM}🔍 验证修复结果:{RESET}")
    calc_content = (workspace / "calculator.py").read_text()
    if "ValueError" in calc_content:
        success("calculator.py 已包含 ValueError 处理")
    else:
        info("calculator.py 未被修改或未包含 ValueError")

    # 运行测试验证
    test_result = subprocess.run(
        ["python", "-m", "pytest", "test_calculator.py", "-v"],
        capture_output=True, text=True, cwd=str(workspace)
    )
    print(f"\n  {DIM}pytest 验证输出:{RESET}")
    for line in test_result.stdout.split("\n"):
        if "PASSED" in line:
            print(f"    {GREEN}{line.strip()}{RESET}")
        elif "FAILED" in line:
            print(f"    {RED}{line.strip()}{RESET}")
        elif "passed" in line or "failed" in line:
            print(f"    {BOLD}{line.strip()}{RESET}")

    # ============ 总结 ============
    banner("演示完成")
    print(f"  工作空间: {workspace}")
    print(f"  Evidence:  {evidence_path}")
    print(f"  总耗时:    {elapsed:.1f}s")
    print(f"  最终状态:  {GREEN if status == 'success' else RED}{status}{RESET}")
    print()

    # 询问是否清理
    print(f"{DIM}临时工作空间保留在: {workspace}{RESET}")
    print(f"{DIM}如需清理: rm -rf {workspace}{RESET}\n")


# ========================================================================
# 入口
# ========================================================================

if __name__ == "__main__":
    asyncio.run(run_demo())
