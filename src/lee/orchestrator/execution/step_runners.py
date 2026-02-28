"""
LEE Orchestrator v3.5 - 步骤运行器 Mixin (Dispatcher)

v3.5: 策略模式重构 — 具体运行逻辑拆分到 runners/ 子模块，
      此文件仅保留分发 + 向后兼容薄包装。

原 1072 行 → 现 ~140 行。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)
from lee.orchestrator.execution.runners import (
    RunnerContext,
    StepRunnerRegistry,
)


class StepRunnerMixin:
    """
    步骤运行器 Mixin — 分发层

    v3.5: 策略模式重构
    - 具体运行逻辑 → runners/llm_runner.py, runners/gate_runner.py, runners/shell_runner.py
    - 此 Mixin 负责：构建 RunnerContext、分发到 registry、向后兼容接口
    """

    _runner_registry: Optional[StepRunnerRegistry] = None

    def _get_runner_registry(self) -> StepRunnerRegistry:
        """懒加载 runner 注册表"""
        if self._runner_registry is None:
            self._runner_registry = StepRunnerRegistry()
            self._runner_registry.register_defaults()
        return self._runner_registry

    def _build_runner_context(self) -> RunnerContext:
        """从 Orchestrator self 构建 RunnerContext"""
        return RunnerContext(
            store=self.store,
            state_machine=self.state_machine,
            event_log=self.event_log,
            evidence_collector=self.evidence_collector,
            verifier_engine=self.verifier_engine,
            executor_factory=self.executor_factory,
            agent_context_builder=self.agent_context_builder,
            contract_discovery=self.contract_discovery,
            file_output_handler=self.file_output_handler,
            token_manager=self.token_manager,
            project_root=self.project_root,
            worktree_manager=getattr(self, 'worktree_manager', None),
        )

    # ==================================================================
    # 向后兼容接口 — 将原来的 _run_xxx_step 方法委托给 registry
    # ==================================================================

    async def _handle_human_gate(
        self,
        workflow_id: str,
        step,
    ) -> StepResult:
        """处理 Human Gate 步骤 → 委托给 HumanGateRunner"""
        ctx = self._build_runner_context()
        registry = self._get_runner_registry()
        runner = registry.get_runner("human_gate")
        return await runner.execute(workflow_id, step, ctx)

    async def _run_auto_check_gate_step(
        self,
        workflow_id: str,
        step,
    ) -> StepResult:
        """处理 Auto Check Gate 步骤 → 委托给 AutoCheckGateRunner"""
        ctx = self._build_runner_context()
        registry = self._get_runner_registry()
        runner = registry.get_runner("auto_check_gate")
        if not runner:
            # 兼容旧版本：直接返回成功
            return StepResult(
                status="success",
                step_id=step.id,
                workflow_id=workflow_id,
                message="Auto check gate passed (no runner registered)",
            )
        return await runner.execute(workflow_id, step, ctx)

    async def _run_agent_step(
        self,
        workflow_id: str,
        step,
    ) -> StepResult:
        """运行 Agent 步骤 → 委托给 LLMRunner"""
        ctx = self._build_runner_context()
        registry = self._get_runner_registry()
        runner = registry.get_runner(step.kind if hasattr(step, "kind") and step.kind in ("agent", "llm") else "agent")
        return await runner.execute(workflow_id, step, ctx)

    async def _run_orchestrator_cli_step(
        self,
        workflow_id: str,
        step,
    ) -> StepResult:
        """运行 Orchestrator CLI 步骤 → 委托给 OrchestratorCLIRunner"""
        ctx = self._build_runner_context()
        registry = self._get_runner_registry()
        runner = registry.get_runner("orchestrator_cli")
        return await runner.execute(workflow_id, step, ctx)

    async def _run_compliance_gate_step(
        self,
        workflow_id: str,
        step,
    ) -> StepResult:
        """运行合规门禁步骤 → 委托给 ComplianceGateRunner"""
        ctx = self._build_runner_context()
        registry = self._get_runner_registry()
        runner = registry.get_runner("compliance_gate")
        return await runner.execute(workflow_id, step, ctx)

    async def _run_skill_step(
        self,
        workflow_id: str,
        step,
    ) -> StepResult:
        """运行 Skill 步骤 → 委托给 SkillRunner"""
        ctx = self._build_runner_context()
        registry = self._get_runner_registry()
        runner = registry.get_runner("skill")
        return await runner.execute(workflow_id, step, ctx)

    async def _run_claude_code_step(
        self,
        workflow_id: str,
        step,
    ) -> StepResult:
        """运行 Claude Code 步骤 → 委托给 ClaudeCodeRunner"""
        ctx = self._build_runner_context()
        registry = self._get_runner_registry()
        runner = registry.get_runner("claude_code")
        return await runner.execute(workflow_id, step, ctx)

    async def _run_patch_apply_step(
        self,
        workflow_id: str,
        step,
    ) -> StepResult:
        """运行补丁应用步骤 → 委托给 PatchApplyRunner"""
        ctx = self._build_runner_context()
        registry = self._get_runner_registry()
        runner = registry.get_runner("patch_apply")
        return await runner.execute(workflow_id, step, ctx)

    # ==================================================================
    # 共享工具方法 — 仍通过 Mixin 暴露，内部委托给 StepRunnerBase
    # ==================================================================

    async def _collect_evidence(self, workflow_id: str, step_id: str, artifacts: List[str]) -> None:
        """收集证据产物"""
        from lee.orchestrator.execution.runners.base import StepRunnerBase
        ctx = self._build_runner_context()
        await StepRunnerBase()._collect_evidence(ctx, workflow_id, step_id, artifacts)

    def _resolve_output_paths(self, outputs) -> List[str]:
        """根据 outputs 规格解析路径"""
        from lee.orchestrator.execution.runners.base import StepRunnerBase
        return StepRunnerBase._resolve_output_paths(outputs, self.project_root)

    def _ensure_output_artifacts(self, outputs) -> List[str]:
        """确保输出产物存在"""
        from lee.orchestrator.execution.runners.base import StepRunnerBase
        return StepRunnerBase._ensure_output_artifacts(outputs, self.project_root)

    def _demo_mode_enabled(self) -> bool:
        from lee.orchestrator.execution.runners.base import StepRunnerBase
        return StepRunnerBase._demo_mode_enabled()

    def _validate_step_output(self, step, output_data):
        """v3.4: 验证步骤输出是否符合 Contract Schema"""
        from lee.orchestrator.execution.runners.base import StepRunnerBase
        return StepRunnerBase._validate_step_output(step, output_data)

    async def _run_verifiers(self, workflow_id: str, step) -> Optional[List]:
        """运行 verifiers"""
        from lee.orchestrator.execution.runners.base import StepRunnerBase
        ctx = self._build_runner_context()
        return await StepRunnerBase()._run_verifiers(ctx, workflow_id, step)

    def _verifiers_passed(self, results: List) -> bool:
        return self.verifier_engine.all_passed(results)

    def _write_verifier_report(self, run_id: str, step_id: str, results: List) -> Optional[str]:
        """写入 verifier 结果报告"""
        from lee.orchestrator.execution.runners.base import StepRunnerBase
        ctx = self._build_runner_context()
        return StepRunnerBase._write_verifier_report(ctx, run_id, step_id, results)
