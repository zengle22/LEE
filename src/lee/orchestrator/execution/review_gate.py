"""
Review Gate - 人类审批机制

支持三种模式：
1. simple - 自动跳过，无需审批
2. suggest - LLM 判断是否需要审批
3. force - 强制审批
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import click


class ReviewMode(str, Enum):
    """Review Gate 模式"""
    SIMPLE = "simple"
    SUGGEST = "suggest"
    FORCE = "force"


@dataclass
class ReviewDecision:
    """审批决策"""
    approved: bool
    reason: str
    reviewer: Optional[str] = None
    mode: ReviewMode = ReviewMode.SIMPLE


class ReviewGate:
    """
    Review Gate - 人类审批门禁

    用法：
        gate = ReviewGate()
        decision = await gate.check(plan_result, mode="suggest")
    """

    def __init__(self, auto_approve: bool = False):
        """
        初始化 Review Gate

        Args:
            auto_approve: 是否自动批准（用于测试）
        """
        self.auto_approve = auto_approve

    async def check(
        self,
        plan_result: Any,
        mode: str = "suggest"
    ) -> ReviewDecision:
        """
        检查是否需要审批

        Args:
            plan_result: Plan 结果
            mode: 审批模式

        Returns:
            ReviewDecision - 审批决策
        """
        if mode == "simple":
            return await self._check_simple(plan_result)
        elif mode == "suggest":
            return await self._check_suggest(plan_result)
        elif mode == "force":
            return await self._check_force(plan_result)
        else:
            return ReviewDecision(approved=True, reason="Unknown mode")

    async def _check_simple(self, plan_result: Any) -> ReviewDecision:
        """Simple 模式：自动跳过"""
        # 检查是否满足跳过条件
        step_count = len(plan_result.instance.get("steps", []))
        if step_count <= 3:
            return ReviewDecision(
                approved=True,
                reason=f"Simple mode: step count ({step_count}) <= 3, auto-skip",
                mode=ReviewMode.SIMPLE
            )

        # 检查 plan 配置
        plan = plan_result.instance.get("plan", {})
        if plan.get("needs_review", False) is False:
            return ReviewDecision(
                approved=True,
                reason="Simple mode: plan says no review needed",
                mode=ReviewMode.SIMPLE
            )

        return ReviewDecision(
            approved=False,
            reason="Simple mode: review needed based on plan",
            mode=ReviewMode.SIMPLE
        )

    async def _check_suggest(self, plan_result: Any) -> ReviewDecision:
        """Suggest 模式：LLM 判断"""
        plan = plan_result.instance.get("plan", {})

        # 如果 LLM 判断需要审批，则触发
        if plan.get("needs_review", False):
            if self.auto_approve:
                return ReviewDecision(
                    approved=True,
                    reason="Suggest mode: auto-approved (testing)",
                    mode=ReviewMode.SUGGEST
                )
            return ReviewDecision(
                approved=False,
                reason="Suggest mode: LLM suggests review required",
                mode=ReviewMode.SUGGEST
            )

        return ReviewDecision(
            approved=True,
            reason="Suggest mode: LLM says no review needed",
            mode=ReviewMode.SUGGEST
        )

    async def _check_force(self, plan_result: Any) -> ReviewDecision:
        """Force 模式：强制审批"""
        if self.auto_approve:
            return ReviewDecision(
                approved=True,
                reason="Force mode: auto-approved (testing)",
                mode=ReviewMode.FORCE
            )

        return ReviewDecision(
            approved=False,
            reason="Force mode: review required",
            mode=ReviewMode.FORCE
        )

    async def request_approval(
        self,
        plan_summary: str,
        workflow_key: str
    ) -> ReviewDecision:
        """
        请求人类审批

        Args:
            plan_summary: Plan 摘要
            workflow_key: Workflow key

        Returns:
            ReviewDecision - 用户决策
        """
        click.echo(f"\n{'='*60}")
        click.echo(f"Workflow Review Gate")
        click.echo(f"{'='*60}")
        click.echo(f"Workflow: {workflow_key}")
        click.echo(f"\n--- Plan Summary ---\n{plan_summary[:500]}...")
        click.echo(f"\n{'='*60}")

        while True:
            response = click.prompt(
                "\nApprove this plan? (y/n/q)",
                type=click.Choice(["y", "n", "q"], case_sensitive=False),
                default="y"
            )

            if response.lower() == "y":
                reviewer = click.prompt("Reviewer name", default="anonymous")
                return ReviewDecision(
                    approved=True,
                    reason="Approved by human",
                    reviewer=reviewer,
                    mode=ReviewMode.FORCE
                )
            elif response.lower() == "n":
                reason = click.prompt("Rejection reason", default="")
                return ReviewDecision(
                    approved=False,
                    reason=reason or "Rejected by human",
                    mode=ReviewMode.FORCE
                )
            else:
                click.echo("Cancelled.")
                return ReviewDecision(
                    approved=False,
                    reason="Cancelled by user",
                    mode=ReviewMode.FORCE
                )


async def check_review_gate(
    plan_result: Any,
    mode: str = "suggest",
    auto_approve: bool = False
) -> ReviewDecision:
    """
    便捷函数：检查 Review Gate

    Args:
        plan_result: Plan 结果
        mode: 审批模式
        auto_approve: 自动批准

    Returns:
        ReviewDecision
    """
    gate = ReviewGate(auto_approve=auto_approve)
    return await gate.check(plan_result, mode)
