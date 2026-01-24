#!/usr/bin/env python3
"""
Test script to verify LLM executor works correctly
"""
import sys
import asyncio
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flowcore.engines.protocol import StepExecutionRequest
from flowcore.engines.llm.executor import LLMExecutor


async def test_llm_executor():
    """Test LLM executor directly"""

    # Load agent spec
    agent_file = project_root / "spec-global" / "departments" / "stg" / "agents" / "search_agent" / "v1" / "agent.yaml"
    with open(agent_file) as f:
        agent_spec = yaml.safe_load(f)

    print("=" * 80)
    print("TESTING LLM EXECUTOR")
    print("=" * 80)

    print("\n📋 Agent Spec:")
    print(f"  ID: {agent_spec.get('id')}")
    print(f"  Engine Type: {agent_spec.get('engine', {}).get('type')}")
    print(f"  Provider: {agent_spec.get('engine', {}).get('provider')}")
    print(f"  Base URL: {agent_spec.get('engine', {}).get('base_url')}")
    print(f"  Model: {agent_spec.get('engine', {}).get('model')}")

    # Create executor
    executor = LLMExecutor(str(project_root), agent_spec)

    # Create test request
    request = StepExecutionRequest(
        project_dir=str(project_root),
        step_id="test_search_signals",
        run_id="test-run-001",
        agent_spec=agent_spec,
        context={
            "step_description": "Test: Search for market signals about AI SaaS industry in US region",
            "inputs": [],
            "contracts": {},
            "project_meta": {
                "name": "Test Project",
                "id": "test-project"
            }
        },
        timeout_seconds=60
    )

    print("\n🚀 Executing LLM request...")
    print(f"  Step ID: {request.step_id}")
    print(f"  Working Dir: {request.get_working_dir()}")

    # Execute
    result = await executor.execute(request)

    print("\n📊 Execution Result:")
    print(f"  Status: {result.status}")
    print(f"  Engine Type: {result.engine_type}")
    if result.duration_seconds:
        print(f"  Duration: {result.duration_seconds:.2f}s")

    if result.error:
        print(f"  ❌ Error: {result.error}")
        if result.error_details:
            print(f"  Error Details: {result.error_details}")

    if result.outputs:
        print(f"\n📤 Outputs: {len(result.outputs)}")
        for out in result.outputs:
            print(f"  - ID: {out.id}")
            print(f"    Path: {out.path}")
            print(f"    Summary: {out.summary}")

    # Check output file
    output_file = request.get_working_dir() / "response.txt"
    if output_file.exists():
        size = output_file.stat().st_size
        print(f"\n📄 Output File: {output_file}")
        print(f"  Size: {size} bytes")

        if size > 0:
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"  Content Length: {len(content)} chars")
            print(f"  Preview:\n{content[:500]}...")
        else:
            print("  ⚠️  File is EMPTY!")
    else:
        print(f"\n❌ Output file not created: {output_file}")

    # Check messages
    if result.messages:
        print(f"\n💬 Messages: {len(result.messages)}")
        for i, msg in enumerate(result.messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            print(f"\n  [{i+1}] {role.upper()}:")
            if len(content) > 200:
                print(f"      {content[:200]}...")
            else:
                print(f"      {content}")


if __name__ == "__main__":
    asyncio.run(test_llm_executor())
