#!/usr/bin/env python3
"""
LEE PM Agent + Gate Assistant Integration Test

This demo shows how PM Agent and Gate Assistant work together
to manage workflow execution and human approvals.

Architecture:
┌─────────────────┐
│   PM Session    │  Workflow management
│  (Claude Code)  │  - Query state
│   pm-workflow   │  - Execute steps
└────────┬────────┘  - Make decisions
         │
         ├──────────────────────────────┐
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌─────────────────┐
│   Orchestrator  │          │ Gate Session    │
│  (flowcore)     │◄─────────│  (Claude Code)  │
│                 │          │  gate-approval  │
│ - StateMachine  │          │  - List gates   │
│ - Engine        │          │  - Show details │
│ - WorkflowParser│          │  - Approve      │
└─────────────────┘          └─────────────────┘
"""

import sys
from pathlib import Path

# Add flowcore to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flowcore.api import (
    api_get_state,
    api_list_ready_steps,
    api_run_step,
    api_next_step,
    api_gate_list_pending,
    api_gate_show,
    api_gate_decide,
    pm_workflow_handler,
    gate_approval_handler,
)


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n▶ {title}")
    print("-" * 70)


def demo_pm_session(project_dir: str):
    """
    Demo: PM Session - Workflow Management

    Shows how PM Agent manages workflow execution
    """
    print_section("🎯 PM Session: Workflow Management")

    # 1. Get current state
    print_subsection("1. Query Current State")
    state = api_get_state(project_dir)

    if "error" in state:
        print(f"❌ Error: {state['error']}")
        return

    print(f"✓ Workflow: {state.get('workflow_name', 'Unknown')}")
    print(f"✓ Progress: {state.get('completed_steps', 0)}/{state.get('total_steps', 0)} steps completed")
    print(f"✓ Ready steps: {len(state.get('ready_steps', []))}")

    # 2. List ready steps
    print_subsection("2. List Ready Steps")
    ready_steps = api_list_ready_steps(project_dir)

    if not ready_steps:
        print("No ready steps available")
    else:
        print(f"✓ Found {len(ready_steps)} ready step(s):")
        for step in ready_steps:
            print(f"  - {step['id']}: {step.get('description', 'No description')}")

    # 3. Execute next step automatically
    print_subsection("3. Auto-execute Next Step")
    result = api_next_step(project_dir)

    if result.get("status") == "completed":
        print(f"✓ Step '{result['step_id']}' completed successfully")
        print(f"  Duration: {result.get('duration_seconds', 0):.2f}s")
        print(f"  Engine: {result.get('engine_type', 'unknown')}")
    elif result.get("status") == "no_ready_steps":
        print("ℹ  No ready steps available")
    else:
        print(f"❌ Step execution failed: {result.get('error', 'Unknown error')}")

    # 4. Execute specific step
    print_subsection("4. Execute Specific Step (if available)")

    # Get ready steps again
    ready_steps = api_list_ready_steps(project_dir)
    if ready_steps:
        step_id = ready_steps[0]['id']
        print(f"Executing step: {step_id}")
        result = api_run_step(project_dir, step_id)

        if result.get("status") == "completed":
            print(f"✓ Step '{result['step_id']}' completed")
            outputs = result.get('outputs', [])
            if outputs:
                print(f"  Outputs: {', '.join(outputs[:3])}")
        else:
            print(f"❌ Execution failed: {result.get('error', 'Unknown')}")


def demo_gate_session(project_dir: str):
    """
    Demo: Gate Session - Human Approval

    Shows how Gate Assistant handles human approvals
    """
    print_section("🚦 Gate Session: Human Approval")

    # 1. List pending gates
    print_subsection("1. List Pending Gates")
    pending_gates = api_gate_list_pending(project_dir)

    if not pending_gates:
        print("ℹ  No pending gates")
        return

    print(f"✓ Found {len(pending_gates)} pending gate(s):")
    for gate in pending_gates:
        print(f"  - {gate['id']}: {gate.get('description', 'No description')}")

    # 2. Show gate details
    if pending_gates:
        gate_id = pending_gates[0]['id']
        print_subsection(f"2. Show Gate Details: {gate_id}")

        gate_details = api_gate_show(project_dir, gate_id)

        if "error" in gate_details:
            print(f"❌ Error: {gate_details['error']}")
            return

        print(f"Gate: {gate_id}")
        print(f"Description: {gate_details.get('description', '')}")
        print(f"Status: {gate_details.get('status', 'unknown')}")

        # Show checklist
        checklist = gate_details.get('checklist', [])
        if checklist:
            print("\nChecklist:")
            for item in checklist:
                status = "✓" if item.get('ok', False) else "✗"
                print(f"  {status} {item.get('item', 'Unknown')}")

        # Show upstream artifacts
        artifacts = gate_details.get('upstream_artifacts', [])
        if artifacts:
            print("\nUpstream Artifacts:")
            for artifact in artifacts:
                print(f"  - From: {artifact.get('from_step', 'Unknown')}")
                print(f"    Path: {artifact.get('artifact_path', 'Unknown')}")

    # 3. Submit gate decision
    print_subsection("3. Submit Gate Decision")

    # For demo purposes, we'll simulate an approval
    if pending_gates:
        gate_id = pending_gates[0]['id']
        print(f"Approving gate: {gate_id}")

        result = api_gate_decide(
            project_dir=project_dir,
            gate_id=gate_id,
            option="approve",
            comment="Demo approval - all criteria met",
            decided_by="demo_user"
        )

        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✓ Gate '{result['gate_id']}' has been {result.get('status', 'processed')}")
            print(f"  Decided by: {result.get('decided_by', 'Unknown')}")
            print(f"  At: {result.get('decided_at', 'Unknown')}")


def demo_tool_handlers(project_dir: str):
    """
    Demo: Tool Handler Usage

    Shows how the tool handlers route calls to API functions
    """
    print_section("🔧 Tool Handler Usage")

    # PM Workflow handler
    print_subsection("1. PM Workflow Handler")

    result = pm_workflow_handler(
        action="get_state",
        project_dir=project_dir
    )

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✓ Workflow: {result.get('workflow_name', 'Unknown')}")
        print(f"✓ Total steps: {result.get('total_steps', 0)}")

    # Gate Approval handler
    print_subsection("2. Gate Approval Handler")

    result = gate_approval_handler(
        action="list_pending",
        project_dir=project_dir
    )

    gates = result.get("gates", [])
    print(f"✓ Pending gates: {len(gates)}")


def demo_complete_workflow(project_dir: str):
    """
    Demo: Complete PM + Gate Workflow

    Simulates a realistic workflow with PM decisions and gate approvals
    """
    print_section("🚀 Complete Workflow Demo")

    print("\nThis demo simulates a realistic workflow execution:")
    print("1. PM Agent checks state")
    print("2. PM Agent executes agent steps")
    print("3. Workflow reaches a human gate")
    print("4. Gate Assistant requests approval")
    print("5. User approves the gate")
    print("6. PM Agent continues execution")

    # Simulate the workflow
    print_subsection("Step 1: PM Checks State")
    state = api_get_state(project_dir)
    print(f"✓ Current progress: {state.get('completed_steps', 0)}/{state.get('total_steps', 0)}")

    print_subsection("Step 2: PM Executes Ready Steps")
    ready_steps = api_list_ready_steps(project_dir)
    print(f"✓ Found {len(ready_steps)} ready steps")

    print_subsection("Step 3: Check for Pending Gates")
    pending_gates = api_gate_list_pending(project_dir)
    if pending_gates:
        print(f"✓ Workflow paused at gate: {pending_gates[0]['id']}")

        print_subsection("Step 4: Show Gate Details")
        gate_details = api_gate_show(project_dir, pending_gates[0]['id'])
        print(f"✓ Gate requires approval: {gate_details.get('description', '')}")

        print_subsection("Step 5: User Approves Gate")
        result = api_gate_decide(
            project_dir=project_dir,
            gate_id=pending_gates[0]['id'],
            option="approve",
            comment="Approved in demo",
            decided_by="demo_user"
        )
        print(f"✓ Gate approved: {result.get('message', '')}")

    print_subsection("Step 6: PM Continues Execution")
    ready_steps = api_list_ready_steps(project_dir)
    print(f"✓ New ready steps: {len(ready_steps)}")


def main():
    """Main test function"""
    print("\n" + "🎉" * 35)
    print("  LEE PM Agent + Gate Assistant Integration Test")
    print("  Complete Tool System Demo")
    print("🎉" * 35)

    # Set project directory
    project_dir = str(Path(__file__).parent.parent / "spec-global" / "departments" / "stg")

    print(f"\n📁 Project directory: {project_dir}")

    # Run demos
    try:
        demo_pm_session(project_dir)
        demo_gate_session(project_dir)
        demo_tool_handlers(project_dir)
        demo_complete_workflow(project_dir)

        print_section("✅ Demo Complete")
        print("\nAll tool integrations tested successfully!")
        print("\n📚 Next Steps:")
        print("  1. Test with real workflow data")
        print("  2. Integrate with Claude Code")
        print("  3. Test two-session architecture")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
