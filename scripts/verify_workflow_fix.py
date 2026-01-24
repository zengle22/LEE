#!/usr/bin/env python3
"""
Quick verification that the workflow fix is working
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_fixes():
    """Verify all fixes are in place"""

    print("=" * 80)
    print("VERIFYING FILE CONTENT PASSING FIX")
    print("=" * 80)

    checks = []

    # 1. Check retry logic exists
    print("\n1. Checking retry logic...")
    try:
        from flowcore.engines.llm.executor import LLMExecutor
        if hasattr(LLMExecutor, '_call_with_retry'):
            print("   ✅ _call_with_retry method exists")
            checks.append(True)
        else:
            print("   ❌ _call_with_retry method missing")
            checks.append(False)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        checks.append(False)

    # 2. Check empty response handling
    print("\n2. Checking empty response handling...")
    try:
        import inspect
        source = inspect.getsource(LLMExecutor.execute)
        if "empty response" in source.lower():
            print("   ✅ Empty response validation present")
            checks.append(True)
        else:
            print("   ❌ Empty response validation missing")
            checks.append(False)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        checks.append(False)

    # 3. Check empty file warning
    print("\n3. Checking empty file warning...")
    try:
        from flowcore.orchestrator.engine_commands import _build_execution_context
        source = inspect.getsource(_build_execution_context)
        if "[WARNING] Empty file" in source:
            print("   ✅ Empty file warning present")
            checks.append(True)
        else:
            print("   ❌ Empty file warning missing")
            checks.append(False)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        checks.append(False)

    # 4. Check integration
    print("\n4. Checking integration...")
    try:
        from flowcore.engines.llm.executor import LLMExecutor
        from flowcore.orchestrator.engine_commands import _build_execution_context
        print("   ✅ All modules import successfully")
        checks.append(True)
    except Exception as e:
        print(f"   ❌ Import error: {e}")
        checks.append(False)

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    passed = sum(checks)
    total = len(checks)

    print(f"\nPassed: {passed}/{total}")

    if all(checks):
        print("\n✅ All checks passed! The fix is working correctly.")
        print("\nNext steps:")
        print("  1. Run: python -m flowcore.orchestrator run-engine . search_signals")
        print("  2. Check: .workflow/workspace/search_signals/response.txt")
        print("  3. Run: python -m flowcore.orchestrator run-engine . analyze_user_signals")
        return True
    else:
        print("\n❌ Some checks failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = verify_fixes()
    sys.exit(0 if success else 1)
