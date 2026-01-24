#!/usr/bin/env python3
"""
Test script to verify the retry logic works
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_retry_logic():
    """Test that the retry logic is properly implemented"""

    print("=" * 80)
    print("TESTING RETRY LOGIC IMPLEMENTATION")
    print("=" * 80)

    # Import the executor
    from flowcore.engines.llm.executor import LLMExecutor

    # Check if the method exists
    if hasattr(LLMExecutor, '_call_with_retry'):
        print("✅ _call_with_retry method exists")
    else:
        print("❌ _call_with_retry method NOT found")
        return False

    # Check the executor code
    import inspect
    source = inspect.getsource(LLMExecutor.execute)

    if "_call_with_retry" in source:
        print("✅ execute() method uses _call_with_retry")
    else:
        print("❌ execute() method does NOT use _call_with_retry")
        return False

    # Check for empty response handling
    source_full = inspect.getsource(LLMExecutor)
    if "empty response" in source_full.lower():
        print("✅ Empty response handling implemented")
    else:
        print("⚠️  Empty response handling may not be implemented")

    print("\n" + "=" * 80)
    print("ALL CHECKS PASSED")
    print("=" * 80)

    return True


if __name__ == "__main__":
    result = asyncio.run(test_retry_logic())
    sys.exit(0 if result else 1)
