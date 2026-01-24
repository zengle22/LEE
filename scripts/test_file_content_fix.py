#!/usr/bin/env python3
"""
Integration test to verify file content passing works correctly
"""
import sys
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flowcore.orchestrator.engine_commands import _build_execution_context


def test_file_content_with_empty_file():
    """Test that empty files are properly handled"""

    print("=" * 80)
    print("TESTING FILE CONTENT PASSING WITH EMPTY FILE DETECTION")
    print("=" * 80)

    # Create a temporary empty file to simulate the bug
    test_file = project_root / ".workflow" / "workspace" / "test_step" / "response.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)

    # Write empty content
    test_file.write_text("", encoding="utf-8")

    print(f"\n📄 Created test file: {test_file}")
    print(f"   Size: {test_file.stat().st_size} bytes")

    # Create mock state and workflow
    state = {
        "run_id": "test-run",
        "steps": {
            "test_step": {
                "state": "completed",
                "outputs": [str(test_file.relative_to(project_root))]
            }
        }
    }

    workflow = {
        "name": "Test Workflow",
        "id": "test-workflow"
    }

    step_data = {
        "id": "next_step",
        "depends_on": ["test_step"]
    }

    # Build execution context
    print("\n🔧 Building execution context...")
    context = _build_execution_context(
        step_id="next_step",
        step_data=step_data,
        workflow=workflow,
        state=state,
        project_dir=str(project_root)
    )

    # Check inputs
    inputs = context.get("inputs", [])
    print(f"\n📥 Number of inputs: {len(inputs)}")

    if inputs:
        inp = inputs[0]
        content = inp.get('content', '')

        print(f"\n--- Input Details ---")
        print(f"  ID: {inp.get('id')}")
        print(f"  Path: {inp.get('path')}")
        print(f"  Content: {content[:100]}...")

        # Verify warning message is in content
        if "[Empty file" in content:
            print("\n✅ Empty file warning is present in content")
            print("✅ The fix is working correctly!")
            return True
        else:
            print("\n❌ Empty file warning is NOT present")
            print("⚠️  The fix may not be working")
            return False
    else:
        print("\n❌ No inputs found")
        return False


def test_file_content_with_valid_file():
    """Test that valid files are properly read"""

    print("\n" + "=" * 80)
    print("TESTING FILE CONTENT PASSING WITH VALID FILE")
    print("=" * 80)

    # Create a temporary file with content
    test_file = project_root / ".workflow" / "workspace" / "test_step_valid" / "response.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)

    test_content = '{"test": "data", "signals": [{"keyword": "AI SaaS"}]}'
    test_file.write_text(test_content, encoding="utf-8")

    print(f"\n📄 Created test file: {test_file}")
    print(f"   Size: {test_file.stat().st_size} bytes")

    # Create mock state and workflow
    state = {
        "run_id": "test-run",
        "steps": {
            "test_step_valid": {
                "state": "completed",
                "outputs": [str(test_file.relative_to(project_root))]
            }
        }
    }

    workflow = {
        "name": "Test Workflow",
        "id": "test-workflow"
    }

    step_data = {
        "id": "next_step",
        "depends_on": ["test_step_valid"]
    }

    # Build execution context
    print("\n🔧 Building execution context...")
    context = _build_execution_context(
        step_id="next_step",
        step_data=step_data,
        workflow=workflow,
        state=state,
        project_dir=str(project_root)
    )

    # Check inputs
    inputs = context.get("inputs", [])
    print(f"\n📥 Number of inputs: {len(inputs)}")

    if inputs:
        inp = inputs[0]
        content = inp.get('content', '')

        print(f"\n--- Input Details ---")
        print(f"  ID: {inp.get('id')}")
        print(f"  Path: {inp.get('path')}")
        print(f"  Content Length: {len(content)} chars")
        print(f"  Content Preview: {content[:100]}...")

        # Verify content is read correctly
        if "AI SaaS" in content:
            print("\n✅ File content is correctly read and passed")
            print("✅ The fix is working correctly!")
            return True
        else:
            print("\n❌ File content was NOT read correctly")
            print("⚠️  Expected content not found")
            return False
    else:
        print("\n❌ No inputs found")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("INTEGRATION TEST: FILE CONTENT PASSING")
    print("=" * 80)

    # Run tests
    test1_passed = test_file_content_with_empty_file()
    test2_passed = test_file_content_with_valid_file()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Empty File Detection): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Valid File Reading): {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
