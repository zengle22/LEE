#!/usr/bin/env python3
"""Debug PM Agent decision making"""
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lee.orchestrator.execution.pm_agent.config import IntentClassifierConfig
from lee.orchestrator.execution.pm_agent.decision_engine import DecisionEngine
from lee.orchestrator.execution.pm_agent.intent_classifier import IntentClassifier
from lee.orchestrator.execution.pm_agent.param_mapper import ParamMapper
from lee.orchestrator.execution.pm_agent.permission_checker import PermissionChecker
from lee.orchestrator.execution.pm_agent.models import ConversationContext
from lee.orchestrator.execution.llm_executor import LLMExecutor

async def debug_decision_making():
    print("=" * 70)
    print("Debug: Decision Making")
    print("=" * 70)
    print()

    # Initialize components
    config = IntentClassifierConfig(project_root=str(PROJECT_ROOT))
    llm_executor = LLMExecutor(profile="deepseek")

    classifier = IntentClassifier(config=config, llm_executor=llm_executor)
    mapper = ParamMapper(llm_executor=llm_executor, template_manager=None)
    checker = PermissionChecker(config=config)

    engine = DecisionEngine(
        intent_classifier=classifier,
        param_mapper=mapper,
        permission_checker=checker,
        enable_fallback=True
    )

    # Test input
    user_input = "列出所有工作流"

    context = ConversationContext(
        session_id="debug_session",
        user_permissions=[],
        history=[]
    )

    print(f"输入: {user_input}")
    print("-" * 70)

    try:
        decision = await engine.decide(user_input, context)

        print(f"\n✓ 决策成功:")
        print(f"  意图: {decision.intent.type.value}")
        print(f"  意图置信度: {decision.intent.confidence}")
        print(f"  动作: {decision.action}")
        print(f"  允许: {decision.allowed}")
        print(f"  工作流: {decision.params.workflow_ref}")
        print(f"  步骤 ID: {decision.params.step_id}")
        print(f"  网关 ID: {decision.params.gate_id}")
        print(f"  其他参数: {decision.params.params}")

    except Exception as e:
        print(f"\n✗ 决策失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_decision_making())
