"""
QA L2/L3 Workflow Integration Test Demo

This script demonstrates QA department's L2/L3 workflow system:
1. L2 template (test-plan-l2-template) with 8 phases
2. L3 template (test-set-l3-template) with 7 steps
3. Test Set dependency resolution (serial execution)
4. L3 spawning per Test Set
5. Bug aggregation and report generation

Usage:
    python qa_l2_l3_demo.py
"""

import asyncio
from pathlib import Path
from datetime import datetime

# Mock implementations for demo purposes
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List, Optional


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_success(msg: str):
    """Print success message."""
    print(f"  ✓ {msg}")


def print_info(msg: str):
    """Print info message."""
    print(f"  ℹ {msg}")


def print_error(msg: str):
    """Print error message."""
    print(f"  ✗ {msg}")


# ============================================
# Mock Models
# ============================================

class WorkflowStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Complexity:
    S = "S"
    M = "M"
    L = "L"


# ============================================
# Demo: L2 Template Loading
# ============================================

def demo_l2_template_loading():
    """Demo: Load QA L2 template."""
    print_section("1. QA L2 Template Loading")

    project_root = Path("/private/var/folders/mc/9mqwl12d4h133r98k7prgr140000gn/T/vibe-kanban/worktrees/26d3-qa-l2/lee")
    template_path = project_root / "spec-global/departments/qa/workflows/templates/test-plan-l2-template.yaml"

    if not template_path.exists():
        print_error(f"Template not found: {template_path}")
        return None

    content = template_path.read_text()

    # Parse key sections
    print("\n🔹 Template ID:")
    if "id:" in content:
        for line in content.split("\n")[:20]:
            if "id:" in line:
                print(f"  {line.strip()}")
                break

    print("\n🔹 Name:")
    if "name:" in content:
        for line in content.split("\n")[:20]:
            if "name:" in line and "description:" not in line:
                print(f"  {line.strip()}")
                break

    # Count phases
    phases = content.count("id: \"")
    print(f"\n🔹 Phases: 8")
    phase_names = [
        "test_run_init",
        "env_provision",
        "env_check",
        "test_set_execution",
        "bug_summary",
        "test_report",
        "exit_evaluation",
        "retrospective",
    ]
    for i, phase in enumerate(phase_names, 1):
        print(f"  {i}. {phase}")

    print("\n🔹 L3 Spawning Phase:")
    print("  - Phase 4 (test_set_execution) spawns L3 instances")
    print("  - Each Test Set → one L3 instance")
    print("  - Execution order based on Test Set dependencies")

    return template_path


# ============================================
# Demo: L3 Template Loading
# ============================================

def demo_l3_template_loading():
    """Demo: Load QA L3 template."""
    print_section("2. QA L3 Template Loading")

    project_root = Path("/private/var/folders/mc/9mqwl12d4h133r98k7prgr140000gn/T/vibe-kanban/worktrees/26d3-qa-l2/lee")
    template_path = project_root / "spec-global/departments/qa/workflows/templates/test-set-l3-template.yaml"

    if not template_path.exists():
        print_error(f"Template not found: {template_path}")
        return None

    content = template_path.read_text()

    print("\n🔹 Template ID:")
    if "id:" in content:
        for line in content.split("\n")[:20]:
            if "id:" in line:
                print(f"  {line.strip()}")
                break

    print("\n🔹 Steps: 7")
    step_names = [
        "case_generation",
        "script_translation",
        "script_execution",
        "behavior_compliance",
        "result_judgment",
        "tse_assembly",
        "bug_drafting",
    ]
    for i, step in enumerate(step_names, 1):
        print(f"  {i}. {step}")

    print("\n🔹 Role Separation:")
    print("  - Step 3 (script_execution): EXECUTOR role")
    print("    - Can: call test_runner, collect evidence")
    print("    - Cannot: judge pass/fail, fabricate errors")
    print("  - Step 5 (result_judgment): JUDGE role")
    print("    - Can: read evidence, judge results")
    print("    - Cannot: call test_runner, modify evidence")

    return template_path


# ============================================
# Demo: Test Set Dependency Resolution
# ============================================

def demo_dependency_resolution():
    """Demo: Test Set dependency resolution (topological sort)."""
    print_section("3. Test Set Dependency Resolution")

    # Example Test Sets with dependencies
    test_sets = [
        {"id": "ts_smoke", "name": "冒烟测试", "depends_on": []},
        {"id": "ts_auth", "name": "用户认证", "depends_on": []},
        {"id": "ts_payment", "name": "支付功能", "depends_on": ["ts_auth"]},
        {"id": "ts_checkout", "name": "结算功能", "depends_on": ["ts_payment"]},
        {"id": "ts_order", "name": "订单管理", "depends_on": ["ts_auth"]},
        {"id": "ts_notification", "name": "消息通知", "depends_on": ["ts_order"]},
    ]

    print("\n🔹 Test Sets and Dependencies:")
    for ts in test_sets:
        deps = ts["depends_on"] or ["无"]
        print(f"  - {ts['id']}: {ts['name']}")
        print(f"    depends_on: {', '.join(deps) if deps and deps[0] != '无' else 'none'}")

    # Topological sort
    def topological_sort(test_sets: List[Dict]) -> List[str]:
        """Sort Test Sets by dependency using Kahn's algorithm."""
        # Build dependency graph
        graph = {ts["id"]: ts["depends_on"] for ts in test_sets}
        in_degree = {ts["id"]: len(ts["depends_on"]) for ts in test_sets}

        # Queue of nodes with no incoming edges
        from collections import deque
        queue = deque([ts_id for ts_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            # Reduce in-degree for dependent nodes
            for ts in test_sets:
                if node in ts["depends_on"]:
                    in_degree[ts["id"]] -= 1
                    if in_degree[ts["id"]] == 0:
                        queue.append(ts["id"])

        if len(result) != len(test_sets):
            raise ValueError("Circular dependency detected!")

        return result

    execution_order = topological_sort(test_sets)

    print("\n🔹 Execution Order (Topological Sort):")
    for i, ts_id in enumerate(execution_order, 1):
        ts = next(t for t in test_sets if t["id"] == ts_id)
        print(f"  {i}. {ts['id']}: {ts['name']}")

    return execution_order


# ============================================
# Demo: L3 Instance Creation
# ============================================

def demo_l3_instance_creation(execution_order: List[str]):
    """Demo: L3 instance creation for each Test Set."""
    print_section("4. L3 Instance Creation")

    print("\n🔹 L3 Instances Created:")
    for i, ts_id in enumerate(execution_order, 1):
        l3_id = f"l3.qa.test_set_{ts_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"  {i}. L3 Instance: {l3_id}")
        print(f"     Template: template.qa.test_set_l3")
        print(f"     Parent: L2 (test_plan_execution_v2)")
        print(f"     Input: test_set_id={ts_id}, test_run_id=TR-XXX")

    return [f"l3_qa_test_set_{ts_id}" for ts_id in execution_order]


# ============================================
# Demo: L3 Execution Flow (Simulated)
# ============================================

def demo_l3_execution_flow():
    """Demo: Simulated L3 execution flow for one Test Set."""
    print_section("5. L3 Execution Flow (Simulated: ts_auth)")

    print("\n🔹 L3 Instance: l3_qa_test_set_ts_auth")
    print("\n  Step 1: case_generation")
    print("    → Agent: agent.qa.case_generator")
    print("    → Output: cases.yaml (15 cases)")

    print("\n  Step 2: script_translation")
    print("    → Agent: agent.qa.script_translator")
    print("    → Output: scripts/ (15 scripts)")

    print("\n  Step 3: script_execution (EXECUTOR role)")
    print("    → Skill: skill.runner.test_e2e")
    print("    → Command: test_runner run --case TC_AUTH_001 --env test")
    print("    → Output: runner-output.json, evidence/")

    print("\n  Step 4: behavior_compliance")
    print("    → Skill: skill.qa.behavior_compliance_checker")
    print("    → Check: no mock, evidence exists")
    print("    → Output: compliance.yaml (pass)")

    print("\n  Step 5: result_judgment (JUDGE role)")
    print("    → Agent: agent.qa.result_judge")
    print("    → Input: runner-output.json, evidence/")
    print("    → Output: results.yaml (13 pass, 2 fail)")

    print("\n  Step 6: tse_assembly")
    print("    → Agent: agent.qa.tse_assembler")
    print("    → Output: tse.yaml")

    print("\n  Step 7: bug_drafting")
    print("    → Agent: agent.qa.bug_drafter")
    print("    → Input: 2 failures")
    print("    → Output: bug_drafts/ (2 bug drafts)")

    print("\n🔹 L3 Output:")
    print("    status: completed")
    print("    tse_path: qa/test-runs/TR-XXX/tse-ts_auth/tse.yaml")
    print("    results_summary: {total: 15, passed: 13, failed: 2, pass_rate: 86.7}")
    print("    bug_drafts: [bug_ts_auth_TC_AUTH_002.yaml, bug_ts_auth_TC_AUTH_005.yaml]")

    return {
        "status": "completed",
        "pass_rate": 86.7,
        "bug_count": 2
    }


# ============================================
# Demo: L2 Aggregation (Bug Summary, Report, Exit)
# ============================================

def demo_l2_aggregation():
    """Demo: L2 aggregation after all L3s complete."""
    print_section("6. L2 Aggregation")

    # Simulated L3 outputs
    l3_results = {
        "ts_smoke": {"status": "completed", "pass_rate": 100.0, "bug_count": 0},
        "ts_auth": {"status": "completed", "pass_rate": 86.7, "bug_count": 2},
        "ts_payment": {"status": "completed", "pass_rate": 92.0, "bug_count": 1},
        "ts_checkout": {"status": "completed", "pass_rate": 88.0, "bug_count": 2},
        "ts_order": {"status": "completed", "pass_rate": 95.0, "bug_count": 1},
        "ts_notification": {"status": "completed", "pass_rate": 100.0, "bug_count": 0},
    }

    total_cases = 90  # Mock
    total_passed = 78
    total_failed = 12

    print("\n🔹 All L3 Results:")
    for ts_id, result in l3_results.items():
        status_icon = "✓" if result["status"] == "completed" else "✗"
        print(f"  {status_icon} {ts_id}: {result['pass_rate']}% pass_rate, {result['bug_count']} bugs")

    print(f"\n🔹 Overall Statistics:")
    print(f"  Total Test Sets: 6")
    print(f"  Total Cases: {total_cases}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print(f"  Pass Rate: {total_passed / total_cases * 100:.1f}%")
    print(f"  Total Bugs: {sum(r['bug_count'] for r in l3_results.values())}")

    print("\n🔹 Phase 5: Bug Summary")
    print("    → Agent: agent.qa.bug_summarizer")
    print("    → Collect: 6 bug drafts from L3s")
    print("    → Deduplicate: 8 → 5 unique bugs")
    print("    → Output: bug-summary.yaml")

    print("\n🔹 Phase 6: Test Report")
    print("    → Agent: agent.qa.report_generator")
    print("    → Sections:")
    print("      - Execution Summary")
    print("      - Test Case Statistics")
    print("      - Feature Coverage")
    print("      - Bug Summary")
    print("      - Risk Assessment")
    print("    → Output: test-report.yaml, test-report.md")

    print("\n🔹 Phase 7: Exit Evaluation")
    print("    → Agent: agent.qa.exit_evaluator")
    print("    → Decision: conditional_pass")
    print("    → Conditions:")
    print("      - Fix P0 bug before release")
    print("      - Monitor production metrics")

    print("\n🔹 Phase 8: Retrospective")
    print("    → Agent: agent.qa.retrospective_generator")
    print("    → Sections:")
    print("      - Issues (network jitter)")
    print("      - Successes (automation stable)")
    print("      - Action Items (optimize script, fix network)")
    print("    → Output: retrospective.md")


# ============================================
# Demo: Full L2/L3 Workflow
# ============================================

def demo_full_workflow():
    """Demo: Complete L2/L3 workflow end-to-end."""
    print_section("7. Complete L2/L3 Workflow")

    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║     QA Test Plan Execution - L2/L3 Workflow                     ║")
    print("╚════════════════════════════════════════════════════════════╝")

    print("\n📋 Input:")
    print("  test_plan_id: TP-2026-Q1")
    print("  build_version: v1.2.3")
    print("  test_sets: 6 (smoke, auth, payment, checkout, order, notification)")

    print("\n🚀 Execution Flow:")

    print("\n  [L2] Phase 1: Test Run Init")
    print("    → Create Test Run: TR-2026-0224-XXX")

    print("\n  [L2] Phase 2: Environment Provision")
    print("    → Deploy v1.2.3 to test environment")

    print("\n  [L2] Phase 3: Environment Check")
    print("    → Orchestrator checks: playwright, npx, node")
    print("    → Result: All checks passed ✓")

    print("\n  [L2] Phase 4: Test Set Execution (L3 Spawning)")
    execution_order = demo_dependency_resolution()
    l3_ids = demo_l3_instance_creation(execution_order)

    print("\n  [L3] Executing L3 instances (serial)...")
    for i, l3_id in enumerate(l3_ids, 1):
        print(f"    [{i}/{len(l3_ids)}] Executing {l3_id}...")
        # Skip full flow for demo, just show summary
        result = demo_l3_execution_flow() if i == 1 else {"status": "completed", "pass_rate": 90.0, "bug_count": 1}

    print("\n  [L2] Phase 5: Bug Summary")
    print("    → Deduplicate: 8 drafts → 5 unique bugs")
    print("    → Gate: Human review required")

    print("\n  [L2] Phase 6: Test Report")
    print("    → Generate: test-report.yaml, test-report.md")

    print("\n  [L2] Phase 7: Exit Evaluation")
    print("    → Decision: conditional_pass")
    print("    → Gate: Human decision required")

    print("\n  [L2] Phase 8: Retrospective")
    print("    → Generate: retrospective.md")

    print("\n📊 Final Output:")
    print("  Test Run ID: TR-2026-0224-XXX")
    print("  Status: completed")
    print("  Pass Rate: 86.7%")
    print("  Bugs: 5 unique (1 P0, 2 P1, 2 P2)")
    print("  Exit Decision: conditional_pass")
    print("  ")
    print("  Artifacts:")
    print("    qa/test-runs/TR-2026-0224-XXX/")
    print("    ├── test-run.yaml")
    print("    ├── tse-*/tse.yaml (6 TSE files)")
    print("    ├── bug-summary.yaml")
    print("    ├── test-report.yaml, test-report.md")
    print("    ├── exit-evaluation.yaml")
    print("    └── retrospective.md")


# ============================================
# Demo: Anti-Mock Constitution
# ============================================

def demo_anti_mock_constitution():
    """Demo: Anti-Mock enforcement in L3."""
    print_section("8. Anti-Mock Constitution Enforcement")

    print("\n🔹 Executor Role Constraints (Step 3):")
    print("  FORBIDDEN:")
    print("    ✗ Mocking execution ('假设通过')")
    print("    ✗ Simulating network response ('假定返回')")
    print("    ✗ Judging pass/fail (only executor role)")

    print("\n🔹 Judge Role Constraints (Step 5):")
    print("  FORBIDDEN:")
    print("    ✗ Calling test_runner")
    print("    ✗ Modifying evidence")
    print("    ✗ Fabricating evidence")

    print("\n🔹 Evidence Requirements:")
    print("  MANDATORY for P0/P1:")
    print("    ✓ logs/ (execution log)")
    print("    ✓ *.png (screenshots)")
    print("    ✓ runner_result_ref")

    print("\n🔹 Violation Consequences:")
    print("  → No evidence_bundle → status: invalid_run")
    print("  → Mock detected → status: invalid_run")
    print("  → L2 marks entire test run as INVALID")


# ============================================
# Demo: Command Line Interface
# ============================================

def demo_cli_usage():
    """Demo: How to run QA L2/L3 workflow."""
    print_section("9. Command Line Usage")

    print("\n🔹 Option 1: Using lee-qa-test-run skill")
    print("  $ lee qa test-run \\")
    print("      --test-plan TP-2026-Q1 \\")
    print("      --build-version v1.2.3 \\")
    print("      --build-commit a1b2c3d4 \\")
    print("      --environment test")

    print("\n🔹 Option 2: Using lee run")
    print("  $ lee run workflow.qa.test_plan_execution_v2 \\")
    print("      --test-plan-id TP-2026-Q1 \\")
    print("      --build-version v1.2.3")

    print("\n🔹 Option 3: With specific Test Sets")
    print("  $ lee qa test-run \\")
    print("      --test-plan TP-2026-Q1 \\")
    print("      --target-test-sets ts_auth,ts_payment")

    print("\n🔹 Human Gates:")
    print("  1. Bug Review (after Phase 5)")
    print("     $ lee gate review")
    print("  2. Exit Decision (after Phase 7)")
    print("     $ lee gate approve  # or reject")


# ============================================
# Main
# ============================================

def main():
    """Run all QA L2/L3 demos."""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║     QA L2/L3 Workflow - Integration Test Demo                   ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n📅 Demo Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Project: /vibe-kanban/lee")
    print(f"🏷️  Branch: vk/26d3-qa-l2")

    # Check if files exist
    project_root = Path("/private/var/folders/mc/9mqwl12d4h133r98k7prgr140000gn/T/vibe-kanban/worktrees/26d3-qa-l2/lee")
    l2_template = project_root / "spec-global/departments/qa/workflows/templates/test-plan-l2-template.yaml"
    l3_template = project_root / "spec-global/departments/qa/workflows/templates/test-set-l3-template.yaml"

    if not l2_template.exists():
        print_error(f"L2 template not found: {l2_template}")
        return

    if not l3_template.exists():
        print_error(f"L3 template not found: {l3_template}")
        return

    # Run demos
    demo_l2_template_loading()
    demo_l3_template_loading()
    execution_order = demo_dependency_resolution()
    demo_l3_instance_creation(execution_order)
    demo_l2_aggregation()
    demo_full_workflow()
    demo_anti_mock_constitution()
    demo_cli_usage()

    print_section("Demo Complete")
    print("\n✅ QA L2/L3 Workflow Integration Test Demo Completed!")
    print("\n📝 Key Takeaways:")
    print("  1. L2 template defines 8 phases (3 direct, 1 L3 spawning, 4 aggregation)")
    print("  2. L3 template defines 7 steps with role separation (executor/judge)")
    print("  3. Test Sets execute in dependency order (topological sort)")
    print("  4. Anti-Mock constitution enforced via role constraints")
    print("  5. Orchestrator's SubworkflowMixin handles L3 spawning")
    print("  6. Use 'lee qa test-run' to execute the workflow")
    print()


if __name__ == "__main__":
    main()
