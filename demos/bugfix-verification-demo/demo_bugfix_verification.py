"""
Bug-Fix Verification Demo (v2.1)
=================================

演示 bug-fix workflow v2.1 的 Stage 4 验证环节新增流程：

场景 1 (Happy Path):
  s4_1_fix_code → s4_2_verify_local → s4_2b_run_bug_tests (pass)
    → s4_2c_bug_test_decision → s4_3_verify_decision → s5_code_review ✅

场景 2 (Env Failure → Human Gate):
  s4_1_fix_code → s4_2_verify_local → s4_2b_run_bug_tests (env_failure)
    → s4_2c_bug_test_decision → s4_2d_env_human_gate (blocked)
    → 人工审批 approve → s4_3_verify_decision → s5_code_review ✅

场景 3 (Test Failure → Retry Loop):
  s4_1_fix_code → s4_2_verify_local → s4_2b_run_bug_tests (fail)
    → s4_2c_bug_test_decision → 回到 s4_1_fix_code 重试 🔁

使用方式：
    cd demos/bugfix-verification-demo
    python demo_bugfix_verification.py
"""

import asyncio
import os
import sys
import tempfile

# 启用 Demo 模式（无需真实 LLM / 环境）
os.environ["LEE_DEMO_MODE"] = "1"

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, src_dir)

from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.execution.gate_api import GateAPI


# =============================================================================
# 样式工具
# =============================================================================

def print_header(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_phase(text: str):
    print(f"\n{'─' * 50}")
    print(f"  📌 {text}")
    print(f"{'─' * 50}")


def print_ok(text: str):
    print(f"  ✅ {text}")


def print_fail(text: str):
    print(f"  ❌ {text}")


def print_info(text: str):
    print(f"  ℹ️  {text}")


def print_warn(text: str):
    print(f"  ⚠️  {text}")


def print_gate(text: str):
    print(f"  🚧 {text}")


# =============================================================================
# 模板定义：模拟 bugfix workflow Stage 4
# =============================================================================

def build_bugfix_template_happy_path():
    """场景 1: 测试通过的 happy path"""
    return {
        "id": "workflow.dev.bugfix_verify_happy",
        "level": "task",
        "name": "Bug Fix Verification - Happy Path",
        "steps": [
            {
                "id": "s4_1_fix_code",
                "kind": "skill",
                "name": "修复代码",
            },
            {
                "id": "s4_2_verify_local",
                "kind": "skill",
                "name": "本地验证",
                "depends_on": ["s4_1_fix_code"],
            },
            {
                "id": "s4_2b_run_bug_tests",
                "kind": "skill",
                "name": "运行 Bug 触发测试",
                "depends_on": ["s4_2_verify_local"],
                "outputs": [{"path": "output/bug-triggered-test-result.yaml"}],
            },
            {
                # decision 步骤：测试通过 → 继续
                "id": "s4_2c_bug_test_decision",
                "kind": "skill",
                "name": "Bug 测试结果判定 (pass)",
                "depends_on": ["s4_2b_run_bug_tests"],
            },
            {
                "id": "s4_3_verify_decision",
                "kind": "skill",
                "name": "验证结果判定",
                "depends_on": ["s4_2c_bug_test_decision"],
            },
            {
                "id": "s5_code_review",
                "kind": "skill",
                "name": "代码审核",
                "depends_on": ["s4_3_verify_decision"],
            },
        ],
    }


def build_bugfix_template_env_failure():
    """场景 2: 环境问题触发 human gate"""
    return {
        "id": "workflow.dev.bugfix_verify_env_fail",
        "level": "task",
        "name": "Bug Fix Verification - Env Failure → Human Gate",
        "steps": [
            {
                "id": "s4_1_fix_code",
                "kind": "skill",
                "name": "修复代码",
            },
            {
                "id": "s4_2_verify_local",
                "kind": "skill",
                "name": "本地验证",
                "depends_on": ["s4_1_fix_code"],
            },
            {
                "id": "s4_2b_run_bug_tests",
                "kind": "skill",
                "name": "运行 Bug 触发测试 (env_failure)",
                "depends_on": ["s4_2_verify_local"],
                "outputs": [{"path": "output/bug-triggered-test-result.yaml"}],
            },
            {
                # decision: 环境失败 → human gate
                "id": "s4_2c_bug_test_decision",
                "kind": "skill",
                "name": "Bug 测试结果判定 (env_failure)",
                "depends_on": ["s4_2b_run_bug_tests"],
            },
            {
                "id": "s4_2d_env_human_gate",
                "kind": "human_gate",
                "name": "测试环境人类门禁",
                "depends_on": ["s4_2c_bug_test_decision"],
                "gate": {
                    "id": "gate.dev.bug_test_env_human_gate",
                    "reviewers": [
                        {"role": "tech_lead", "description": "技术负责人"},
                        {"role": "qa_lead",   "description": "测试负责人"},
                    ],
                    "approval_criteria": [
                        {
                            "label": "环境问题已确认",
                            "criteria": "确认环境问题真实存在且非代码缺陷",
                            "required": True,
                        },
                        {
                            "label": "替代验证方案",
                            "criteria": "已提供替代验证方式或人工验证结果",
                            "required": True,
                        },
                    ],
                },
            },
            {
                "id": "s4_3_verify_decision",
                "kind": "skill",
                "name": "验证结果判定",
                "depends_on": ["s4_2d_env_human_gate"],
            },
            {
                "id": "s5_code_review",
                "kind": "skill",
                "name": "代码审核",
                "depends_on": ["s4_3_verify_decision"],
            },
        ],
    }


def build_bugfix_template_test_failure():
    """场景 3: 测试失败 → 回到修复代码（模拟重试一次）"""
    return {
        "id": "workflow.dev.bugfix_verify_test_fail",
        "level": "task",
        "name": "Bug Fix Verification - Test Failure → Retry",
        "steps": [
            {
                "id": "s4_1_fix_code",
                "kind": "skill",
                "name": "修复代码",
            },
            {
                "id": "s4_2_verify_local",
                "kind": "skill",
                "name": "本地验证",
                "depends_on": ["s4_1_fix_code"],
            },
            {
                "id": "s4_2b_run_bug_tests",
                "kind": "skill",
                "name": "运行 Bug 触发测试 (fail → 需重试)",
                "depends_on": ["s4_2_verify_local"],
                "outputs": [{"path": "output/bug-triggered-test-result.yaml"}],
            },
        ],
    }


# =============================================================================
# 场景执行
# =============================================================================

async def run_scenario_happy_path(store, tm, gate_api):
    """
    场景 1: 测试通过 Happy Path

    s4_1_fix_code → s4_2_verify_local → s4_2b_run_bug_tests → s4_2c (pass)
    → s4_3_verify_decision → s5_code_review
    """
    print_header("场景 1: Happy Path — Bug 触发测试全部通过")
    print_info("流程: fix_code → verify → run_bug_tests(pass) → decision → code_review")

    template_doc = build_bugfix_template_happy_path()
    template_id = template_doc["id"]
    tm._cache[template_id] = tm._parse_template_doc(template_doc, template_id)

    orchestrator = Orchestrator(store, tm)

    # 创建工作流
    print_phase("创建工作流")
    wf = await orchestrator.create_workflow(
        level=WorkflowLevel.TASK,
        template_id=template_id,
        data={"bug_contract": "BUG-2026-001", "scenario": "happy_path"},
    )
    print_ok(f"工作流 ID: {wf.id}")
    print_ok(f"状态: {wf.status.value}")

    # 执行所有步骤
    step_names = [
        ("s4_1_fix_code",         "修复代码"),
        ("s4_2_verify_local",     "本地验证"),
        ("s4_2b_run_bug_tests",   "运行 Bug 触发测试"),
        ("s4_2c_bug_test_decision", "Bug 测试结果判定 (pass)"),
        ("s4_3_verify_decision",  "验证结果判定"),
        ("s5_code_review",        "代码审核"),
    ]

    for step_id, step_name in step_names:
        print_phase(f"执行: {step_name} ({step_id})")
        result = await orchestrator.run_step(wf.id)
        print_ok(f"结果: {result.status}")
        print_info(f"Step ID: {result.step_id}")

    # 验证完成状态
    state = await orchestrator.get_state(wf.id)
    assert state.status == WorkflowStatus.COMPLETED, f"Expected COMPLETED, got {state.status}"
    print_phase("场景 1 结果")
    print_ok(f"工作流最终状态: {state.status.value}")
    print_ok("✨ Happy Path 验证通过！所有步骤顺利完成。")

    return True


async def run_scenario_env_failure(store, tm, gate_api):
    """
    场景 2: 环境问题 → Human Gate

    s4_1_fix_code → s4_2_verify_local → s4_2b_run_bug_tests (env_failure)
    → s4_2c (decision) → s4_2d_env_human_gate (BLOCKED → approve) → continue
    """
    print_header("场景 2: 环境问题 → 触发 Human Gate")
    print_info("流程: fix_code → verify → run_bug_tests(env_failure) → decision → human_gate → approve → code_review")

    template_doc = build_bugfix_template_env_failure()
    template_id = template_doc["id"]
    tm._cache[template_id] = tm._parse_template_doc(template_doc, template_id)

    orchestrator = Orchestrator(store, tm)

    # 创建工作流
    print_phase("创建工作流")
    wf = await orchestrator.create_workflow(
        level=WorkflowLevel.TASK,
        template_id=template_id,
        data={"bug_contract": "BUG-2026-002", "scenario": "env_failure"},
    )
    print_ok(f"工作流 ID: {wf.id}")

    # 步骤 1-4: 正常执行到 human gate 前
    pre_gate_steps = [
        ("s4_1_fix_code",         "修复代码"),
        ("s4_2_verify_local",     "本地验证"),
        ("s4_2b_run_bug_tests",   "运行 Bug 触发测试 (结果: env_failure)"),
        ("s4_2c_bug_test_decision", "Bug 测试结果判定 → 环境问题"),
    ]

    for step_id, step_name in pre_gate_steps:
        print_phase(f"执行: {step_name} ({step_id})")
        result = await orchestrator.run_step(wf.id)
        print_ok(f"结果: {result.status}")

    # 步骤 5: 触发 Human Gate
    print_phase("执行: 测试环境人类门禁 (s4_2d_env_human_gate)")
    gate_result = await orchestrator.run_step(wf.id)
    print_gate(f"结果: {gate_result.status}")

    state = await orchestrator.get_state(wf.id)
    print_gate(f"工作流状态: {state.status.value}")

    if state.status == WorkflowStatus.PAUSED:
        print_ok("工作流正确暂停 — 等待人工审批")

        # 检查无法继续执行
        ready = await orchestrator.get_ready_steps(wf.id)
        assert ready == [], f"Expected no ready steps while paused, got {ready}"
        print_ok("暂停期间无可执行步骤 ✓")

        # 模拟创建 Gate 并审批
        print_phase("人工审批: tech_lead + qa_lead 确认环境问题")
        gate = await gate_api.create_gate(
            workflow_id=wf.id,
            step_id="s4_2d_env_human_gate",
            step_name="测试环境人类门禁",
            description="Bug 触发测试因本地环境缺少 Redis 7.x 无法执行",
            context={
                "bug_test_result_status": "env_failure",
                "env_issue": "本地 Redis 版本为 6.x，测试需 7.x 的 streams 功能",
                "alternative": "已在 CI 环境 (Redis 7.2) 运行并通过",
            },
        )
        print_ok(f"Gate 创建: {gate.gate_id}")

        # 审批
        await gate_api.approve_gate(
            gate.gate_id,
            comment="确认环境问题，CI 环境已验证通过",
            checklist=[
                {"item": "环境问题已确认", "ok": True},
                {"item": "替代验证方案", "ok": True, "detail": "CI (Redis 7.2) 通过"},
            ],
        )
        print_ok("Gate 已审批 — 工作流恢复")

    # 继续执行剩余步骤
    post_gate_steps = [
        ("s4_3_verify_decision", "验证结果判定"),
        ("s5_code_review",       "代码审核"),
    ]

    for step_id, step_name in post_gate_steps:
        print_phase(f"执行: {step_name} ({step_id})")
        result = await orchestrator.run_step(wf.id)
        print_ok(f"结果: {result.status}")

    # 验证完成
    state = await orchestrator.get_state(wf.id)
    assert state.status == WorkflowStatus.COMPLETED, f"Expected COMPLETED, got {state.status}"
    print_phase("场景 2 结果")
    print_ok(f"工作流最终状态: {state.status.value}")
    print_ok("✨ 环境问题场景验证通过！Human Gate 正确触发并审批后恢复。")

    return True


async def run_scenario_test_failure(store, tm, gate_api):
    """
    场景 3: 测试失败 → 演示重试逻辑

    s4_1_fix_code → s4_2_verify_local → s4_2b_run_bug_tests (fail)
    → 工作流完成（简化演示: 实际会循环回 s4_1_fix_code）

    说明: 实际 workflow 中 s4_2c 是 decision 类型，会根据条件路由。
    此处通过简化 template 演示"测试失败"这条路径的存在。
    """
    print_header("场景 3: 测试失败 → 重试修复 (简化演示)")
    print_info("流程: fix_code → verify → run_bug_tests(fail)")
    print_info("说明: 实际 workflow 中 decision 会将流程路由回 s4_1_fix_code 重试。")
    print_info("      此 demo 展示测试失败被检测的路径。")

    template_doc = build_bugfix_template_test_failure()
    template_id = template_doc["id"]
    tm._cache[template_id] = tm._parse_template_doc(template_doc, template_id)

    orchestrator = Orchestrator(store, tm)

    # 创建工作流
    print_phase("创建工作流")
    wf = await orchestrator.create_workflow(
        level=WorkflowLevel.TASK,
        template_id=template_id,
        data={"bug_contract": "BUG-2026-003", "scenario": "test_failure"},
    )
    print_ok(f"工作流 ID: {wf.id}")

    # 执行步骤
    steps = [
        ("s4_1_fix_code",       "修复代码"),
        ("s4_2_verify_local",   "本地验证"),
        ("s4_2b_run_bug_tests", "运行 Bug 触发测试 (结果: fail)"),
    ]

    for step_id, step_name in steps:
        print_phase(f"执行: {step_name} ({step_id})")
        result = await orchestrator.run_step(wf.id)
        print_ok(f"结果: {result.status}")

    state = await orchestrator.get_state(wf.id)
    print_phase("场景 3 结果")
    print_ok(f"工作流状态: {state.status.value}")
    print_warn("实际 workflow 中: decision 会将控制流路由回 s4_1_fix_code 进行重试")
    print_warn(f"                 最多重试 10 次，超过则触发 human gate")
    print_ok("✨ 测试失败路径演示完成。")

    return True


# =============================================================================
# 主入口
# =============================================================================

async def main():
    """主函数"""
    print("\n" + "█" * 70)
    print("█                                                                    █")
    print("█    Bug-Fix Verification Demo v2.1                                   █")
    print("█    演示 bug-fix workflow 验证环节的 3 个场景                         █")
    print("█                                                                    █")
    print("█" * 70)

    scenarios = []
    success = True

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

    try:
        store = SQLiteStore(db_path)
        await store.connect()

        tm = TemplateManager()
        orchestrator = Orchestrator(store, tm)
        gate_api = GateAPI(store, orchestrator)

        # 场景 1: Happy Path
        try:
            result = await run_scenario_happy_path(store, tm, gate_api)
            scenarios.append(("Happy Path (测试通过)", result))
        except Exception as e:
            print_fail(f"场景 1 失败: {e}")
            import traceback; traceback.print_exc()
            scenarios.append(("Happy Path (测试通过)", False))
            success = False

        # 场景 2: Env Failure → Human Gate
        try:
            result = await run_scenario_env_failure(store, tm, gate_api)
            scenarios.append(("Env Failure → Human Gate", result))
        except Exception as e:
            print_fail(f"场景 2 失败: {e}")
            import traceback; traceback.print_exc()
            scenarios.append(("Env Failure → Human Gate", False))
            success = False

        # 场景 3: Test Failure → Retry
        try:
            result = await run_scenario_test_failure(store, tm, gate_api)
            scenarios.append(("Test Failure → Retry", result))
        except Exception as e:
            print_fail(f"场景 3 失败: {e}")
            import traceback; traceback.print_exc()
            scenarios.append(("Test Failure → Retry", False))
            success = False

        await store.close()

    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except PermissionError:
            pass

    # 汇总
    print_header("演示结果汇总")
    for name, ok in scenarios:
        symbol = "✅" if ok else "❌"
        print(f"  {symbol} {name}")

    print()
    if success:
        print("  🎉 所有场景验证通过！Bug-Fix Workflow v2.1 验证环节正常工作。")
        print()
        print("  📋 v2.1 新增步骤:")
        print("     • s4_2b_run_bug_tests    — 在本地运行 bug 触发的完整测试用例")
        print("     • s4_2c_bug_test_decision — 判定测试结果 (pass/fail/env_failure)")
        print("     • s4_2d_env_human_gate   — 环境/外部因素 → 人类门禁")
    else:
        print("  ⚠️  部分场景失败，请检查日志")

    print()
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print_fail(f"Demo 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
