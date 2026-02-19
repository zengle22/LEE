"""
LEE Orchestrator — StepRunner 基类 + RunnerContext

RunnerContext 封装了所有 runner 运行所需的依赖（store、state_machine 等），
避免每个 runner 直接持有 orchestrator 引用。
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, TYPE_CHECKING

from lee.orchestrator.storage.models import (
    TaskExecution,
    TaskExecutionStatus,
    StepResult,
)
from lee.orchestrator.execution.retry import AsyncRetryExecutor, DEFAULT_RETRY_POLICY
from lee.orchestrator.execution.validators import SchemaValidator, ValidationResult


class RunnerContext:
    """
    Runner 运行上下文 — 封装所有共享依赖

    由 Orchestrator 构建并传入每个 runner。
    """

    def __init__(
        self,
        store,
        state_machine,
        event_log,
        evidence_collector,
        verifier_engine,
        executor_factory,
        agent_context_builder,
        contract_discovery,
        file_output_handler,
        token_manager,
        project_root: Optional[str] = None,
        repo_registry=None,
        worktree_manager=None,
    ):
        self.store = store
        self.state_machine = state_machine
        self.event_log = event_log
        self.evidence_collector = evidence_collector
        self.verifier_engine = verifier_engine
        self.executor_factory = executor_factory
        self.agent_context_builder = agent_context_builder
        self.contract_discovery = contract_discovery
        self.file_output_handler = file_output_handler
        self.token_manager = token_manager
        self.project_root = project_root
        self.repo_registry = repo_registry
        self.worktree_manager = worktree_manager

    def resolve_workdir(self, step, run_id: str) -> str:
        """
        解析步骤的工作目录

        优先级：
        1. step.repo_scope + worktree_manager → 隔离 worktree
        2. project_root → 回退到项目根目录

        Args:
            step: 步骤对象（可能有 repo_scope 属性）
            run_id: 运行 ID（用于 worktree 分配）

        Returns:
            工作目录绝对路径
        """
        repo_scope = getattr(step, "repo_scope", None)
        if repo_scope and self.worktree_manager:
            try:
                return self.worktree_manager.get_workdir(run_id, repo_scope)
            except ValueError:
                pass  # 未分配则 fallback
        return str(Path(self.project_root or ".").resolve())


class StepRunnerStrategy(ABC):
    """步骤 runner 策略接口"""

    @abstractmethod
    def can_handle(self, step_kind: str) -> bool:
        """是否能处理此类步骤"""
        ...

    @abstractmethod
    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """执行步骤"""
        ...


class StepRunnerBase(StepRunnerStrategy):
    """
    提供所有 runner 共享的工具方法：
    - evidence 收集
    - verifier 运行
    - output 校验
    - demo 模式检测
    """

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    async def _collect_evidence(
        self, ctx: RunnerContext, workflow_id: str, step_id: str, artifacts: List[str]
    ) -> None:
        """收集证据产物"""
        if not artifacts:
            return

        instance = await ctx.store.get_workflow(workflow_id)
        if not instance:
            return

        run_id = instance.data.get("run_id")
        if not run_id:
            run_id = self._generate_run_id()
            instance.data["run_id"] = run_id
            await ctx.store.update_workflow_data(workflow_id, instance.data)

        ctx.evidence_collector.collect(run_id, step_id, artifacts)

    @staticmethod
    def _generate_run_id() -> str:
        import uuid
        return f"RUN-{uuid.uuid4().hex[:8].upper()}"

    # ------------------------------------------------------------------
    # Output path helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_output_paths(outputs, project_root: Optional[str] = None) -> List[str]:
        """根据 outputs 规格解析路径"""
        if not outputs:
            return []
        paths = []
        for out in outputs:
            path = getattr(out, "path", None)
            if not path:
                continue
            if os.path.isabs(path):
                paths.append(path)
            else:
                base = Path(project_root or ".").resolve()
                paths.append(str(base / path))
        return paths

    @staticmethod
    def _ensure_output_artifacts(outputs, project_root: Optional[str] = None) -> List[str]:
        """确保输出产物存在（用于 demo/兜底）"""
        if not outputs:
            return []

        created: List[str] = []
        base = Path(project_root or ".").resolve()

        for out in outputs:
            path = getattr(out, "path", None)
            if not path:
                continue

            target = Path(path)
            if not target.is_absolute():
                target = base / target

            out_type = getattr(out, "type", None) or ("dir" if path.endswith("/") else "file")
            if out_type == "dir":
                target.mkdir(parents=True, exist_ok=True)
                created.append(str(target))
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                continue

            fmt = (getattr(out, "format", None) or "text").lower()
            if fmt == "json":
                payload = {"placeholder": True, "path": path, "status": "demo"}
                content = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
            elif fmt in ("yaml", "yml"):
                content = "placeholder: true\nstatus: demo\n"
            elif fmt in ("markdown", "md"):
                content = "# Placeholder\n\nGenerated in demo mode.\n"
            else:
                content = "placeholder\n"

            target.write_text(content, encoding="utf-8")
            created.append(str(target))

        return created

    # ------------------------------------------------------------------
    # Demo mode
    # ------------------------------------------------------------------

    @staticmethod
    def _demo_mode_enabled() -> bool:
        return os.getenv("LEE_DEMO_MODE", "").lower() in ("1", "true", "yes")

    # ------------------------------------------------------------------
    # Output validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_step_output(step, output_data) -> Optional[ValidationResult]:
        """v3.4: 验证步骤输出是否符合 Contract Schema"""
        config = step.config or {}

        schema_path = config.get("output_contract")
        if not schema_path:
            execution_config = config.get("execution", {})
            schema_path = execution_config.get("output_contract") if isinstance(execution_config, dict) else None
        if not schema_path:
            return None

        try:
            validator = SchemaValidator()
            result = validator.validate(output_data, {"schema_path": schema_path})
            return result
        except Exception as e:
            print(f"[OutputValidation] Error validating step {step.id}: {e}")
            return None

    def _handle_validation_result(
        self, validation_result: Optional[ValidationResult], step, strict: bool
    ) -> Optional[str]:
        """处理校验结果，返回错误消息（strict 模式）或 None"""
        if validation_result and not validation_result.passed:
            if strict:
                return f"Output schema validation failed: {validation_result.errors[0].message if validation_result.errors else 'unknown'}"
            else:
                print(f"[OutputValidation] Warning: Step {step.id} output schema validation failed (soft mode)")
        return None

    # ------------------------------------------------------------------
    # Verifiers
    # ------------------------------------------------------------------

    async def _run_verifiers(self, ctx: RunnerContext, workflow_id: str, step) -> Optional[List]:
        """运行 verifiers，返回结果列表或 None"""
        verifiers = step.config.get("verifiers") if step.config else None
        if not verifiers:
            return None

        if self._demo_mode_enabled():
            from lee.orchestrator.verifiers.base import VerifyResult, VerifyStatus
            results = []
            for item in verifiers or []:
                vtype = item.get("type") if isinstance(item, dict) else None
                results.append(VerifyResult(
                    status=VerifyStatus.PASSED,
                    verifier_id=vtype or "unknown",
                    message="verifier skipped in demo mode",
                    details={"mode": "demo"},
                ))

            instance = await ctx.store.get_workflow(workflow_id)
            run_id = instance.data.get("run_id") if instance else None
            if instance and not run_id:
                run_id = self._generate_run_id()
                instance.data["run_id"] = run_id
                await ctx.store.update_workflow_data(workflow_id, instance.data)

            report_path = self._write_verifier_report(ctx, run_id or "RUN-UNKNOWN", step.id, results)
            if report_path:
                await self._collect_evidence(ctx, workflow_id, step.id, [report_path])

            return results

        instance = await ctx.store.get_workflow(workflow_id)
        run_id = instance.data.get("run_id") if instance else None
        if instance and not run_id:
            run_id = self._generate_run_id()
            instance.data["run_id"] = run_id
            await ctx.store.update_workflow_data(workflow_id, instance.data)

        context = {
            "workflow_id": workflow_id,
            "step_id": step.id,
            "run_id": run_id,
        }

        results = ctx.verifier_engine.run(verifiers, context)

        report_path = self._write_verifier_report(ctx, run_id or "RUN-UNKNOWN", step.id, results)
        if report_path:
            await self._collect_evidence(ctx, workflow_id, step.id, [report_path])

        return results

    def _verifiers_passed(self, ctx: RunnerContext, results: List) -> bool:
        return ctx.verifier_engine.all_passed(results)

    @staticmethod
    def _write_verifier_report(
        ctx: RunnerContext, run_id: str, step_id: str, results: List
    ) -> Optional[str]:
        """写入 verifier 结果报告到 .workflow/verifiers/"""
        base = Path(ctx.project_root or ".").resolve()
        report_dir = base / ".workflow" / "verifiers"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{run_id}-{step_id}.json"

        payload = []
        for r in results:
            payload.append({
                "verifier_id": r.verifier_id,
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "message": r.message,
                "details": r.details,
            })

        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(report_path)

    # ------------------------------------------------------------------
    # Workflow completion check (delegate to orchestrator)
    # ------------------------------------------------------------------

    async def _check_workflow_completion(self, ctx: RunnerContext, workflow_id: str) -> None:
        """检查工作流是否完成 — 由 orchestrator 实现"""
        # 这个方法在 Orchestrator 中有具体实现
        # Runner 层面不需要做任何事情，由 StepRunnerMixin dispatch 层调用
        pass
