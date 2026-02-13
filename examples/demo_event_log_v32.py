#!/usr/bin/env python3
"""
v3.2 EventLog 端到端演示

模拟一次完整的工作流执行，产生所有 v3.2 新增事件类型，
然后打印 events.jsonl 日志内容 + 统计报告。

运行方式:
    python examples/demo_event_log_v32.py
"""

import asyncio
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# ── 颜色辅助（ANSI，macOS/Linux 原生支持）────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

EVENT_COLORS = {
    "run_created":  GREEN,
    "run_started":  GREEN,
    "run_completed": GREEN,
    "run_failed":   RED,
    "run_paused":   YELLOW,
    "step_started": CYAN,
    "step_completed": GREEN,
    "step_failed":  RED,
    "gate_triggered": YELLOW,
    "gate_approved":  GREEN,
    "gate_rejected":  RED,
}


def banner(text):
    width = 60
    print(f"\n{BOLD}{'═' * width}")
    print(f"  {text}")
    print(f"{'═' * width}{RESET}\n")


async def main():
    banner("v3.2 EventLog 端到端演示")

    # 创建临时项目目录
    tmp_dir = tempfile.mkdtemp(prefix="lee_demo_eventlog_")
    print(f"📂 临时项目目录: {tmp_dir}\n")

    try:
        await run_demo(tmp_dir)
    finally:
        # 清理
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def run_demo(project_dir: str):
    from lee.orchestrator.storage.event_log import EventLog, EventType
    import time

    el = EventLog(project_dir, run_id="RUN-DEMO-20260213")

    # ─── Phase 1: 模拟 create_workflow ───
    print(f"{BOLD}▶ Phase 1: 创建工作流{RESET}")
    el.log_run_created(
        workflow_id="wf_task_abc12345",
        workflow_name="feature-login-impl"
    )
    print("  ✅ run_created 事件已记录\n")

    # ─── Phase 2: 模拟 run_until_blocked → run_started ───
    print(f"{BOLD}▶ Phase 2: 开始执行{RESET}")
    el.log(EventType.RUN_STARTED, data={
        "workflow_id": "wf_task_abc12345",
        "max_steps": 10
    })
    print("  ✅ run_started 事件已记录\n")

    # ─── Phase 3: Agent 步骤 (模拟 _run_agent_step) ───
    print(f"{BOLD}▶ Phase 3: 执行 Agent 步骤{RESET}")

    # step_started
    el.log_step_started(
        step_id="implement_backend",
        agent_id="agent.dev.go-backend-engineer",
    )
    print("  📝 step_started: implement_backend")

    time.sleep(0.1)  # 模拟 LLM 执行耗时

    # step_completed (含 outputs_hash)
    output_data = {
        "generated_text": "package main\n\nfunc Login(user, pass string) bool { ... }",
        "written_files": ["src/api/login.go", "src/api/login_test.go"],
        "agent_id": "agent.dev.go-backend-engineer",
        "llm_meta": {
            "model": "glm-4-flash",
            "provider": "zhipu",
            "tokens_used": 1560,
            "input_tokens": 1200,
            "output_tokens": 360,
            "duration_seconds": 3.142,
            "stop_reason": "stop",
        }
    }
    el.log_step_completed(
        step_id="implement_backend",
        agent_id="agent.dev.go-backend-engineer",
        outputs=["src/api/login.go", "src/api/login_test.go"],
        outputs_hash=el._compute_hash(output_data),
    )
    print("  ✅ step_completed: implement_backend (2 files)\n")

    # ─── Phase 4: 第二个步骤失败 ───
    print(f"{BOLD}▶ Phase 4: 步骤失败场景{RESET}")
    el.log_step_started(
        step_id="run_unit_tests",
        agent_id="agent.dev.test-runner",
    )
    print("  📝 step_started: run_unit_tests")

    el.log_step_failed(
        step_id="run_unit_tests",
        agent_id="agent.dev.test-runner",
        error="exit code 1: TestLogin_InvalidPassword FAILED",
    )
    print("  ❌ step_failed: run_unit_tests\n")

    # ─── Phase 5: Human Gate ───
    print(f"{BOLD}▶ Phase 5: 门禁审批流程{RESET}")
    el.log_gate_triggered(
        gate_id="code_review_gate",
        step_id="code_review",
        gate_type="human",
        blocking=True,
    )
    print("  🚧 gate_triggered: code_review_gate (等待人工)")

    time.sleep(0.05)

    el.log_gate_approved(
        gate_id="code_review_gate",
        step_id="code_review",
        approver="zengle",
        approval_id="wf_task_abc12345_code_review_gate",
    )
    print("  ✅ gate_approved: code_review_gate (by zengle)\n")

    # ─── Phase 6: 另一个 Gate 被拒绝 ───
    print(f"{BOLD}▶ Phase 6: 门禁拒绝场景{RESET}")
    el.log_gate_triggered(
        gate_id="deploy_gate",
        step_id="deploy_staging",
        gate_type="human",
        blocking=True,
    )
    print("  🚧 gate_triggered: deploy_gate")

    el.log_gate_rejected(
        gate_id="deploy_gate",
        step_id="deploy_staging",
        approver="zengle",
        reason="测试覆盖率不足 (68% < 80%)",
    )
    print("  ❌ gate_rejected: deploy_gate\n")

    # ─── Phase 7: run_completed ───
    print(f"{BOLD}▶ Phase 7: 执行完成{RESET}")
    el.log(EventType.RUN_COMPLETED, data={
        "workflow_id": "wf_task_abc12345",
        "total_steps": 4,
        "completed_steps": 1,
        "blocked_at": "deploy_staging",
        "duration_seconds": 12.5,
    })
    print("  ✅ run_completed 事件已记录\n")

    # ═══════════════════════════════════════════════════════
    # 打印结果
    # ═══════════════════════════════════════════════════════

    log_path = Path(project_dir) / ".workflow" / "events.jsonl"

    # ── 原始事件时间线 ────────────
    banner("📋 事件时间线 (events.jsonl)")
    with open(log_path, 'r') as f:
        for i, line in enumerate(f, 1):
            event = json.loads(line)
            etype = event["event_type"]
            color = EVENT_COLORS.get(etype, "")
            ts = event["timestamp"][11:23]  # HH:MM:SS.mmm
            step = event.get("step_id") or "-"
            agent = event.get("agent_id") or ""
            error = event.get("error") or ""

            line_str = f"  {i:2d}. {color}{etype:20s}{RESET}  {ts}  step={step:22s}"
            if agent:
                line_str += f"  agent={agent}"
            if error:
                line_str += f"  {RED}error={error[:50]}{RESET}"
            print(line_str)

    # ── 统计信息 ────────────
    banner("📊 统计信息")
    stats = el.get_statistics()
    print(f"  总事件数:       {stats['total_events']}")
    print(f"  错误事件数:     {stats['error_count']}")
    print(f"  重试次数:       {stats['retry_count']}")

    print(f"\n  {BOLD}事件类型分布:{RESET}")
    for etype, count in sorted(stats["event_counts"].items(), key=lambda x: -x[1]):
        color = EVENT_COLORS.get(etype, "")
        print(f"    {color}{etype:25s}{RESET}  ×{count}")

    if stats["step_durations"]:
        print(f"\n  {BOLD}步骤耗时:{RESET}")
        for step_id, duration in stats["step_durations"].items():
            print(f"    {step_id:25s}  {duration:.3f}s")

    if stats["gate_wait_times"]:
        print(f"\n  {BOLD}门禁等待时间:{RESET}")
        for gate_id, wait in stats["gate_wait_times"].items():
            print(f"    {gate_id:25s}  {wait:.3f}s")

    # ── 审计报告 ────────────
    banner("📄 审计报告导出")
    report_path = el.export_audit_report()
    print(f"  导出路径: {report_path}")
    report_size = Path(report_path).stat().st_size
    print(f"  文件大小: {report_size:,} bytes")

    # 打印报告摘要
    with open(report_path) as f:
        report = json.load(f)
    print(f"  生成时间: {report['generated_at'][:19]}")
    print(f"  Run ID:   {report['run_id']}")
    print(f"  事件总数: {len(report['events'])}")

    print(f"\n{GREEN}{BOLD}✅ Demo 完成 — 所有 v3.2 事件类型正常工作！{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
