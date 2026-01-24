#!/usr/bin/env python3
"""
Debug script to trace file content passing in STG workflow
"""
import sys
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flowcore.orchestrator.engine_commands import _build_execution_context


def debug_execution_context():
    """Debug the execution context building"""

    # Load workflow state
    state_file = project_root / ".workflow" / "state.yaml"
    if not state_file.exists():
        print(f"❌ State file not found: {state_file}")
        return

    with open(state_file) as f:
        state = yaml.safe_load(f)

    # Load workflow definition
    workflow_file = project_root / "spec-global" / "departments" / "stg" / "workflow.yaml"
    if not workflow_file.exists():
        print(f"❌ Workflow file not found: {workflow_file}")
        return

    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)

    # Find analyze_user_signals step
    step_data = None
    for step in workflow.get("steps", []):
        if step.get("id") == "analyze_user_signals":
            step_data = step
            break

    if not step_data:
        print("❌ Step 'analyze_user_signals' not found in workflow")
        return

    # Build execution context
    print("=" * 80)
    print("DEBUGGING EXECUTION CONTEXT FOR analyze_user_signals")
    print("=" * 80)

    context = _build_execution_context(
        step_id="analyze_user_signals",
        step_data=step_data,
        workflow=workflow,
        state=state,
        project_dir=str(project_root)
    )

    # Print context details
    print("\n📋 Context Keys:", list(context.keys()))

    # Check inputs
    inputs = context.get("inputs", [])
    print(f"\n📥 Number of inputs: {len(inputs)}")

    for i, inp in enumerate(inputs):
        print(f"\n--- Input {i+1} ---")
        print(f"  ID: {inp.get('id')}")
        print(f"  Path: {inp.get('path')}")
        print(f"  Summary: {inp.get('summary')}")

        content = inp.get('content', '')
        print(f"  Content Length: {len(content)} chars")

        if content:
            print(f"  Content Preview: {content[:200]}...")
        else:
            print("  ⚠️  Content is EMPTY or MISSING!")

        # Check if file exists
        file_path = project_root / inp.get('path', '')
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"  File Size: {size} bytes")
            if size == 0:
                print("  ⚠️  WARNING: File is empty (0 bytes)")
        else:
            print(f"  ⚠️  File does not exist!")

    # Check if search_signals output exists
    print("\n" + "=" * 80)
    print("CHECKING search_signals OUTPUT FILE")
    print("=" * 80)

    search_signals_output = project_root / ".workflow" / "workspace" / "search_signals" / "response.txt"
    if search_signals_output.exists():
        size = search_signals_output.stat().st_size
        print(f"✅ File exists: {search_signals_output}")
        print(f"   Size: {size} bytes")

        if size > 0:
            with open(search_signals_output, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"   Content length: {len(content)} chars")
            print(f"   Preview: {content[:500]}...")
        else:
            print("   ⚠️  File is EMPTY!")
    else:
        print(f"❌ File does not exist: {search_signals_output}")

    # Check state for search_signals
    print("\n" + "=" * 80)
    print("CHECKING STATE FOR search_signals")
    print("=" * 80)

    search_signals_state = state.get("steps", {}).get("search_signals", {})
    print(f"State: {search_signals_state.get('state')}")
    print(f"Outputs: {search_signals_state.get('outputs', [])}")
    print(f"Outputs Hash: {search_signals_state.get('outputs_hash')}")

    # e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 is empty SHA256
    if search_signals_state.get('outputs_hash') == 'e3b0c44298fc1c14':
        print("⚠️  Hash indicates EMPTY file!")


if __name__ == "__main__":
    debug_execution_context()
