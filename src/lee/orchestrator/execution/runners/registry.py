"""
LEE Orchestrator — Step Runner Registry

根据 step.kind 分发到对应的 StepRunnerStrategy 实现。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from lee.orchestrator.execution.runners.base import (
    StepRunnerStrategy,
    RunnerContext,
)
from lee.orchestrator.storage.models import StepResult


class StepRunnerRegistry:
    """
    步骤 runner 注册表

    用法:
        registry = StepRunnerRegistry()
        registry.register(LLMRunner())
        registry.register(ClaudeCodeRunner())
        result = await registry.dispatch(workflow_id, step, ctx)
    """

    def __init__(self):
        self._runners: List[StepRunnerStrategy] = []

    def register(self, runner: StepRunnerStrategy) -> None:
        """注册 runner"""
        self._runners.append(runner)

    def get_runner(self, step_kind: str) -> Optional[StepRunnerStrategy]:
        """根据 step kind 查找 runner"""
        for runner in self._runners:
            if runner.can_handle(step_kind):
                return runner
        return None

    async def dispatch(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """分发执行"""
        runner = self.get_runner(step.kind)
        if not runner:
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"No runner registered for step kind: {step.kind}",
            )
        return await runner.execute(workflow_id, step, ctx)

    def register_defaults(self) -> None:
        """注册所有内置 runner"""
        from lee.orchestrator.execution.runners.llm_runner import LLMRunner, ClaudeCodeRunner
        from lee.orchestrator.execution.runners.gate_runner import HumanGateRunner, ComplianceGateRunner
        from lee.orchestrator.execution.runners.shell_runner import SkillRunner, OrchestratorCLIRunner
        from lee.orchestrator.execution.runners.patch_apply_runner import PatchApplyRunner

        self.register(LLMRunner())
        self.register(ClaudeCodeRunner())
        self.register(PatchApplyRunner())
        self.register(HumanGateRunner())
        self.register(ComplianceGateRunner())
        self.register(SkillRunner())
        self.register(OrchestratorCLIRunner())

    @property
    def registered_kinds(self) -> List[str]:
        """列出所有已注册的 step kind"""
        kinds = []
        for runner in self._runners:
            kinds.append(type(runner).__name__)
        return kinds
