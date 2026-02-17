#!/usr/bin/env python3
"""
双执行器策略验证 Demo

验证 feature-be-l3 workflow 的 claude_code 执行路径是否正确集成。

测试流程：
  1. 路由验证 — template parser + orchestrator dispatch 正确路由 claude_code kind
  2. Claude CLI 调用 — 在临时 workspace 执行一个简单的 bugfix 任务
  3. Fallback 验证 — PatchApplyRunner 的补丁应用功能

运行方式：
    cd /Users/zengle/git/ai/lee
    python demos/demo_dual_executor.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 确保能 import 项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


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


def section(num: int, title: str):
    print(f"\n{YELLOW}▶ Test {num}: {title}{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")


def ok(msg: str):
    print(f"  {GREEN}✅ {msg}{RESET}")


def fail(msg: str):
    print(f"  {RED}❌ {msg}{RESET}")


def info(msg: str):
    print(f"  {DIM}{msg}{RESET}")


# ========================================================================
# Test 1: 路由验证
# ========================================================================

def test_routing():
    """验证 template parser + registry 正确路由"""
    section(1, "路由验证 (Template Parser + Registry)")

    errors = []

    # 1a. Template parser: type: claude_code
    from lee.orchestrator.execution.template_manager import TemplateManager
    manager = TemplateManager("specs/workflows")

    step_cc = manager._parse_step({
        "id": "test_cc",
        "type": "claude_code",
        "inputs": {"goal": "test"},
    })
    if step_cc.kind == "claude_code" and step_cc.executor_type == "claude_code":
        ok(f"type: claude_code → kind={step_cc.kind}, executor_type={step_cc.executor_type}")
    else:
        fail(f"type: claude_code → kind={step_cc.kind}, executor_type={step_cc.executor_type} (期望 claude_code/claude_code)")
        errors.append("claude_code routing")

    # 1b. Template parser: type: patch_apply
    step_pa = manager._parse_step({
        "id": "test_pa",
        "type": "patch_apply",
        "config": {"patch_source": "test.patch"},
    })
    if step_pa.kind == "patch_apply" and step_pa.executor_type == "patch_apply":
        ok(f"type: patch_apply → kind={step_pa.kind}, executor_type={step_pa.executor_type}")
    else:
        fail(f"type: patch_apply → kind={step_pa.kind}, executor_type={step_pa.executor_type}")
        errors.append("patch_apply routing")

    # 1c. Registry 包含所有 runner
    from lee.orchestrator.execution.runners.registry import StepRunnerRegistry
    registry = StepRunnerRegistry()
    registry.register_defaults()

    for kind_name in ["agent", "claude_code", "patch_apply", "skill"]:
        runner = registry.get_runner(kind_name)
        if runner:
            ok(f"Registry['{kind_name}'] → {runner.__class__.__name__}")
        else:
            fail(f"Registry['{kind_name}'] → NOT FOUND")
            errors.append(f"registry {kind_name}")

    # 1d. ExecutorConfig
    from lee.orchestrator.config_loader import ExecutorConfig
    config = ExecutorConfig()
    ok(f"ExecutorConfig: coding_executor={config.coding_executor}, coding_fallback={config.coding_fallback}")

    return len(errors) == 0


# ========================================================================
# Test 2: Claude CLI 实际调用
# ========================================================================

async def test_claude_code_execution():
    """验证 ClaudeCodeExecutor 能正确调用 claude CLI"""
    section(2, "Claude Code 执行 (ClaudeCodeExecutor)")

    # 检测 claude CLI
    try:
        version_result = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=10
        )
        version = version_result.stdout.strip()
        info(f"Claude CLI: {version}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        fail("Claude CLI 未安装或不可用")
        return False

    # 准备临时 workspace
    ws = Path(tempfile.mkdtemp(prefix="lee-dual-demo-"))
    os.system(f"cd {ws} && git init -q && git config user.email demo@lee && git config user.name demo")

    # 写一个简单的有 bug 的文件
    (ws / "greet.py").write_text('''\
def greet(name):
    """Return a greeting message."""
    return "Hello, " + nam  # BUG: typo - should be 'name'
''')
    os.system(f"cd {ws} && git add -A && git commit -q -m 'initial'")

    info(f"工作空间: {ws}")
    info(f"目标: 修复 greet.py 中的 typo bug (nam → name)")

    # 调用 executor
    from lee.orchestrator.execution.claude_code_executor import ClaudeCodeExecutor
    executor = ClaudeCodeExecutor()

    input_data = {
        "goal": "Fix the typo in greet.py: 'nam' should be 'name'. Just fix it, don't add anything else.",
        "workspace": str(ws),
        "allowed_commands": ["python"],
        "write_scope": ["greet.py"],
        "max_iterations": 2,
        "timeout_seconds": 180,        # 3 分钟超时
        "evidence_base": str(ws / ".evidence"),
    }

    print(f"\n  {BOLD}⏳ 正在调用 claude CLI...{RESET}")
    print(f"  {DIM}(预计 15-60 秒){RESET}\n")

    start = datetime.now()
    result = await executor.execute(input_data)
    elapsed = (datetime.now() - start).total_seconds()

    status = result["status"]

    info(f"状态: {GREEN if status == 'success' else YELLOW if status == 'timeout' else RED}{status}{RESET}")
    info(f"耗时: {elapsed:.1f}s")
    info(f"迭代: {result.get('iterations_used', 0)}")
    info(f"修改文件: {result.get('changed_files', [])}")

    if result.get("error"):
        info(f"错误: {result['error']}")

    # 检验修复结果
    content = (ws / "greet.py").read_text()
    if "nam " not in content and "name" in content:
        ok(f"Bug 已修复! ({elapsed:.1f}s)")
        # 展示 diff
        diff = subprocess.run(
            ["git", "diff"], capture_output=True, text=True, cwd=str(ws)
        )
        if diff.stdout:
            print(f"\n  {DIM}git diff:{RESET}")
            for line in diff.stdout.strip().split("\n"):
                color = GREEN if line.startswith("+") else (RED if line.startswith("-") else DIM)
                print(f"    {color}{line}{RESET}")
        return True
    elif status == "timeout":
        fail(f"执行超时 ({elapsed:.1f}s)")
        return False
    else:
        fail(f"Bug 未修复 (status={status})")
        return False


# ========================================================================
# Test 3: PatchApply Fallback
# ========================================================================

async def test_patch_apply_fallback():
    """验证 PatchApplyRunner 能正确应用补丁"""
    section(3, "Patch Apply Fallback (PatchApplyRunner)")

    ws = Path(tempfile.mkdtemp(prefix="lee-patch-demo-"))
    os.system(f"cd {ws} && git init -q && git config user.email demo@lee && git config user.name demo")

    # 创建源文件
    (ws / "app.py").write_text("def hello():\n    return 'hello'\n")
    os.system(f"cd {ws} && git add -A && git commit -q -m 'initial'")

    # 创建一个 patch 文件
    patch_content = """\
--- a/app.py
+++ b/app.py
@@ -1,2 +1,5 @@
 def hello():
     return 'hello'
+
+def goodbye():
+    return 'goodbye'
"""
    patch_file = ws / "output" / "code.patch"
    patch_file.parent.mkdir(parents=True, exist_ok=True)
    patch_file.write_text(patch_content)

    info(f"工作空间: {ws}")
    info(f"补丁文件: {patch_file}")

    # 直接测试 _apply_patch 方法
    from lee.orchestrator.execution.runners.patch_apply_runner import PatchApplyRunner
    runner = PatchApplyRunner()

    result = await runner._apply_patch(
        patch_content=patch_content,
        patch_format="unified_diff",
        workspace=ws,
    )

    if result["status"] == "success":
        ok(f"补丁应用成功: {result.get('message', '')}")

        content = (ws / "app.py").read_text()
        if "goodbye" in content:
            ok("文件内容验证通过 — goodbye 函数已添加")
            print(f"\n  {DIM}app.py 内容:{RESET}")
            for line in content.strip().split("\n"):
                print(f"    {DIM}{line}{RESET}")
            return True
        else:
            fail("文件内容验证失败 — goodbye 函数未找到")
            return False
    else:
        fail(f"补丁应用失败: {result.get('message', '')}")
        return False


# ========================================================================
# 主流程
# ========================================================================

async def main():
    banner("双执行器策略 — 验证 Demo")

    results = {}

    # Test 1: 路由
    results["routing"] = test_routing()

    # Test 2: Claude CLI 调用
    results["claude_code"] = await test_claude_code_execution()

    # Test 3: Patch Apply
    results["patch_apply"] = await test_patch_apply_fallback()

    # 总结
    banner("验证结果汇总")
    total_pass = 0
    total = len(results)
    for name, passed in results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {name:20s} {status}")
        if passed:
            total_pass += 1

    print(f"\n  {BOLD}总计: {total_pass}/{total} 通过{RESET}")

    if total_pass == total:
        print(f"\n  {GREEN}🎉 双执行器策略验证全部通过！{RESET}\n")
    elif results.get("routing") and results.get("patch_apply"):
        print(f"\n  {YELLOW}⚠️  路由和降级方案正常，仅 Claude CLI 调用需排查{RESET}\n")
    else:
        print(f"\n  {RED}❗ 存在失败项，需要排查{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
