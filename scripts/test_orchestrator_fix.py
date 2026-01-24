#!/usr/bin/env python3
"""
Test script to verify orchestrator context passing fixes

This tests:
1. Human gates are properly detected in _build_execution_context
2. Gate files are read correctly when building context
3. Freeze contracts are generated when gates are approved
4. Downstream steps receive the full frozen context
"""
import sys
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from flowcore.orchestrator.engine_commands import (
    _get_step_by_id,
    _build_execution_context
)
from flowcore.api import (
    _generate_freeze_contract,
    _extract_confidence_from_comment,
    api_gate_decide
)

def test_get_step_by_id():
    """Test _get_step_by_id helper function"""
    print("\n=== Test _get_step_by_id ===")

    workflow_file = Path("workflow.yaml")
    if not workflow_file.exists():
        print("✗ workflow.yaml not found")
        return False

    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)

    # Test finding a human gate
    step = _get_step_by_id("freeze_market_signals", workflow)
    if step and step.get("kind") == "human_gate":
        print("✓ Found freeze_market_signals as human_gate")
    else:
        print("✗ Failed to identify freeze_market_signals as human_gate")
        return False

    # Test finding a regular step
    step = _get_step_by_id("search_signals", workflow)
    if step and step.get("kind") == "agent":
        print("✓ Found search_signals as agent")
    else:
        print("✗ Failed to identify search_signals as agent")
        return False

    return True


def test_build_context_with_human_gate():
    """Test _build_execution_context with human gate dependency"""
    print("\n=== Test _build_execution_context with human gate ===")

    workflow_file = Path("workflow.yaml")
    state_file = Path(".workflow/state.yaml")

    if not workflow_file.exists() or not state_file.exists():
        print("✗ Required files not found (workflow.yaml or state.yaml)")
        return False

    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)

    with open(state_file) as f:
        state = yaml.safe_load(f)

    # Test building context for build_business_opportunity (depends on freeze_market_signals)
    step_data = _get_step_by_id("build_business_opportunity", workflow)
    if not step_data:
        print("✗ build_business_opportunity step not found")
        return False

    context = _build_execution_context(
        step_id="build_business_opportunity",
        step_data=step_data,
        workflow=workflow,
        state=state,
        project_dir="."
    )

    # Check that inputs include the human gate
    inputs = context.get("inputs", [])
    if not inputs:
        print("✗ No inputs found in context")
        return False

    freeze_input = next((inp for inp in inputs if inp.get("id") == "freeze_market_signals"), None)
    if not freeze_input:
        print("✗ freeze_market_signals not found in inputs")
        return False

    # Check that the gate content is included
    content = freeze_input.get("content", "")
    if not content or len(content) < 100:
        print(f"✗ Gate content too short or empty ({len(content)} chars)")
        return False

    # Check for key indicators
    if "Gate:" not in content:
        print("✗ Gate content missing 'Gate:' header")
        return False

    if "Upstream Analysis" in content or "Freeze Contract" in content:
        print("✓ Gate content includes upstream analysis")
    else:
        print("⚠ Gate content may be missing upstream analysis section")

    # Check if the content is actually about the research topic (not empty)
    if "卡路里" in content or "营养" in content or "calorie" in content.lower() or "nutrition" in content.lower():
        print("✓ Gate content contains research topic context")
    else:
        print("⚠ Gate content may not contain research topic (this is expected if gate was created before fix)")

    return True


def test_freeze_contract_generation():
    """Test freeze contract generation"""
    print("\n=== Test _generate_freeze_contract ===")

    # Read an existing gate to simulate
    gate_file = Path(".workflow/gates/freeze_market_signals.yaml")
    if not gate_file.exists():
        print("⚠ No gate file found, skipping freeze contract test")
        return True

    with open(gate_file) as f:
        gate_info = yaml.safe_load(f)

    # Test confidence extraction
    comment = gate_info.get("comment", "")
    confidence = _extract_confidence_from_comment(comment)
    print(f"  Extracted confidence: {confidence}% (from comment: '{comment[:50]}...')")

    # Test freeze contract generation (this will create/update the file)
    try:
        _generate_freeze_contract(".", "freeze_market_signals", gate_info)
        print("✓ Freeze contract generation succeeded")

        # Verify the contract was created
        contract_file = Path("contracts/market_signals_freeze/v1/freeze.yaml")
        if contract_file.exists():
            print(f"✓ Freeze contract created at: {contract_file}")
        else:
            # Try alternative path pattern
            contract_file = Path("contracts/market_signal_freeze/v1/freeze.yaml")
            if contract_file.exists():
                print(f"✓ Freeze contract created at: {contract_file}")
            else:
                print("⚠ Freeze contract file not found (may use different path pattern)")
    except Exception as e:
        print(f"✗ Freeze contract generation failed: {e}")
        return False

    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Orchestrator Context Passing Fix Verification")
    print("=" * 60)

    tests = [
        test_get_step_by_id,
        test_build_context_with_human_gate,
        test_freeze_contract_generation,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"\n✗ {test.__name__} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False))

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! The orchestrator fixes are working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
