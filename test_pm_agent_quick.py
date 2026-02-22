#!/usr/bin/env python3
"""
Quick test for PM Agent with real LLM
"""
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime
from lee.orchestrator.execution.llm_executor import LLMExecutor
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.storage.sqlite_store import SQLiteStore as SQLiteWorkflowStore

async def test_pm_agent():
    print("=" * 70)
    print("PM Agent Quick Test with Real LLM")
    print("=" * 70)
    print()

    # Initialize components
    project_dir = str(PROJECT_ROOT)
    db_path = PROJECT_ROOT / ".lee" / "lee.db"
    store = SQLiteWorkflowStore(str(db_path))
    orchestrator = Orchestrator(store, project_root=project_dir)

    # Initialize LLM (using deepseek)
    try:
        llm_executor = LLMExecutor(profile="deepseek")
        print("✓ LLM Executor initialized (deepseek)")
    except Exception as e:
        print(f"✗ LLM Executor failed: {e}")
        print("Using basic mode...")
        llm_executor = None

    # Initialize Runtime
    runtime = PMAgentRuntime(
        orchestrator,
        llm_executor,
        store,
        project_dir=project_dir,
        enable_decision_engine=bool(llm_executor)
    )

    print(f"✓ Runtime initialized (Decision Engine: {runtime.enable_decision_engine})")
    print()

    # Test inputs
    test_inputs = [
        "当前状态如何？",
        "列出所有工作流",
        "帮助"
    ]

    session_id = "test_session"

    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {user_input}")
        print('='*70)

        try:
            result = await runtime.process_input(user_input, session_id)
            print(f"\n✓ Processed successfully")
            print(f"  Status: {result['status']}")
            print(f"  Action: {result.get('action', 'N/A')}")

            if result['status'] == 'success':
                data = result.get('data', {})
                if 'state' in data:
                    state = data['state']
                    if 'status' in state:
                        print(f"  Workflow Status: {state['status']}")
                if 'workflows' in data:
                    workflows = data['workflows']
                    print(f"  Total Workflows: {data.get('total', len(workflows))}")

            elif result['status'] == 'denied':
                print(f"  Reason: {result.get('error', 'Unknown')}")

            elif result['status'] == 'error':
                print(f"  Error: {result.get('error', 'Unknown error')}")
                print(f"  Action: {result.get('action', 'N/A')}")

        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)

    # Show metrics
    metrics = runtime.get_metrics()
    print("\n📊 Metrics:")
    if 'decision_engine' in metrics:
        de = metrics['decision_engine']
        print(f"  Total decisions: {de.get('total_decisions', 0)}")
        print(f"  Success rate: {de.get('success_rate', 0):.1%}")

if __name__ == "__main__":
    asyncio.run(test_pm_agent())
