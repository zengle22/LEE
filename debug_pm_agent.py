#!/usr/bin/env python3
"""Debug PM Agent intent classification"""
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lee.orchestrator.execution.pm_agent.config import IntentClassifierConfig
from lee.orchestrator.execution.pm_agent.intent_classifier import IntentClassifier
from lee.orchestrator.execution.pm_agent.models import ConversationContext
from lee.orchestrator.execution.llm_executor import LLMExecutor

async def debug_intent_classification():
    print("=" * 70)
    print("Debug: Intent Classification")
    print("=" * 70)
    print()

    # Initialize
    config = IntentClassifierConfig(project_root=str(PROJECT_ROOT))
    llm_executor = LLMExecutor(profile="deepseek")
    classifier = IntentClassifier(config=config, llm_executor=llm_executor)

    # Test inputs
    test_inputs = [
        "当前状态如何？",
        "列出所有工作流",
        "帮助"
    ]

    context = ConversationContext(
        session_id="debug_session",
        user_permissions=[],
        history=[]
    )

    for user_input in test_inputs:
        print(f"\n输入: {user_input}")
        print("-" * 70)

        try:
            intent = await classifier.classify(user_input, context)
            print(f"✓ 意图类型: {intent.type.value}")
            print(f"  置信度: {intent.confidence}")
            print(f"  推理: {intent.reasoning}")
            print(f"  匹配模式: {intent.matched_pattern}")
        except Exception as e:
            print(f"✗ 错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_intent_classification())
