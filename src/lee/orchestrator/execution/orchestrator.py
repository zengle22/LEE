"""
LEE Orchestrator v3.1 - 核心调度器

本模块定义了 Orchestrator 的核心实现，是整个系统的调度中心。

核心职责（8条）：
1. 管理 Workflow 模板
2. 创建/恢复 Workflow 实例
3. 计算 ready step
4. 执行一个 step
5. 根据执行结果更新状态机
6. spawn 子 workflow
7. 暂停/恢复
8. 提供外部 API

设计原则：
- 不思考，只裁决「现在该干什么」
- 不直接调用 LLM，只通过 Executor
- 不直接读写业务文件
- SQLite 是唯一状态权威

v3.1 重构：
- 抽取 StepRunnerMixin  → step_runners.py
- 抽取 GateOperationsMixin → gate_operations.py
- 抽取 SubworkflowMixin  → subworkflow_ops.py
"""

import uuid
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from lee.orchestrator.storage.models import (
    WorkflowLevel,
    WorkflowStatus,
    TaskExecutionStatus,
    WorkflowInstance,
    Step,
    WorkflowState,
    StepResult,
    ExecutionSummary,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.state_machine import WorkflowStateMachine
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.execution.executors import ExecutorFactory
from lee.orchestrator.execution.agent_context_builder import AgentContextBuilder
from lee.orchestrator.execution.agent_loader import AgentLoader
from lee.orchestrator.execution.file_output_handler import FileOutputHandler
from lee.orchestrator.evidence_collector import EvidenceCollector
from lee.orchestrator.verifier_engine import VerifierEngine
from lee.orchestrator.core.contract_discovery import ContractDiscovery
from lee.orchestrator.core.token_manager import TokenManager, ToolGuard
from lee.orchestrator.execution.gate_engine import GateEngine
from lee.orchestrator.storage.event_log import EventLog
from lee.orchestrator.execution.trace import TraceLog, SpanType, Metrics
from lee.orchestrator.execution.failure_handler import FailureHandler
from lee.runtime.worktree_manager import WorktreeManager
from lee.runtime.repo_registry import RepoRegistry
from lee.orchestrator.execution.patch_output import PatchCollector
from lee.orchestrator.execution.receipt import ReceiptStore, ExecutionReceipt
from lee.orchestrator.execution.context_index import ContextIndex
from lee.orchestrator.core.event_bus import get_event_bus, Event, EventType
import uuid
# Mixin 模块
from lee.orchestrator.execution.step_runners import StepRunnerMixin
from lee.orchestrator.execution.gate_operations import GateOperationsMixin
from lee.orchestrator.execution.subworkflow_ops import SubworkflowMixin


# ========================================================================
# 核心调度器（Orchestrator）
# ========================================================================

class Orchestrator(StepRunnerMixin, GateOperationsMixin, SubworkflowMixin):
    """
    LEE Orchestrator v3.1 - 核心调度器

    这是整个系统的"脊柱"，唯一的调度中心，唯一的状态权威。

    核心职责（8条）：
    1. 管理 Workflow 模板
    2. 创建/恢复 Workflow 实例
    3. 计算 ready step
    4. 执行一个 step
    5. 根据执行结果更新状态机
    6. spawn 子 workflow
    7. 暂停/恢复
    8. 提供外部 API

    设计原则：
    - 不思考，只裁决「现在该干什么」
    - 不直接调用 LLM，只通过 Executor
    - 不直接读写业务文件
    - SQLite 是唯一状态权威

    v3.1 Mixin 分层：
    - StepRunnerMixin: agent/skill/CLI/gate 步骤执行
    - GateOperationsMixin: 门禁审批/拒绝/查询
    - SubworkflowMixin: 子工作流 spawn/执行/回填
    """

    def __init__(
        self,
        store: SQLiteStore,
        template_manager: Optional[TemplateManager] = None,
        project_root: Optional[str] = None,
        config_path: Optional[str] = None,
    ):
        """
        初始化 Orchestrator

        Args:
            store: SQLite 存储层
            template_manager: 模板管理器（可选）
            project_root: 项目根目录（用于文件路径解析）
            config_path: 可选配置文件路径（默认 {project_root}/.lee/config.yaml）
        """
        # v3.5 M4: 加载项目配置
        from lee.orchestrator.config_loader import load_config
        self.config = load_config(project_root, config_path)

        self.store = store
        self.db = store  # 兼容 Runners 的 db 属性
        self.state_machine = WorkflowStateMachine(store)
        # v3.5: 传递配置到 TemplateManager 以使用正确的 executor.default_type
        self.template_manager = template_manager or TemplateManager(
            project_root=project_root,
            config=self.config
        )
        self.executor_factory = ExecutorFactory

        # v1.5: 创建 AgentLoader 用于加载 agent spec
        # spec_root: 优先使用配置文件中的 spec_root，再使用默认值
        if self.config.spec_root and project_root:
            spec_root = str(Path(project_root) / self.config.spec_root)
        else:
            spec_root = str(Path(project_root) / "lee" / "spec-global") if project_root else None
        agent_loader = AgentLoader(project_root or ".", spec_root=spec_root)

        # v3.1: P1 功能集成
        self.contract_discovery = ContractDiscovery(project_root or ".")
        repo_root = Path(project_root or ".")
        registry_candidates = [
            repo_root / ".lee" / "repos.yaml",
            repo_root / ".lee" / "repo-registry.yaml",
            repo_root / "config" / "repo-registry.yaml",
        ]
        registry_path = next((p for p in registry_candidates if p.exists()), registry_candidates[0])

        self.repo_registry = RepoRegistry.from_yaml(
            config_path=str(registry_path),
            workspace_root=project_root
        )
        self.worktree_manager = WorktreeManager(
            runs_root=str(Path(project_root or ".") / ".lee" / "runs"),
            registry=self.repo_registry
        )
        self.patch_collector = PatchCollector(self.worktree_manager)
        self.receipt_store = ReceiptStore(
            runs_root=str(Path(project_root or ".") / ".lee" / "runs")
        )
        self.token_manager = TokenManager(project_root or ".")
        self.tool_guard = ToolGuard(self.token_manager)
        self.gate_engine = GateEngine()

        # v1.4 新增组件
        self.context_index = ContextIndex(self.repo_registry)
        self.agent_context_builder = AgentContextBuilder(
            agent_loader=agent_loader,
            project_root=project_root,
            context_index=self.context_index
        )
        self.file_output_handler = FileOutputHandler(
            project_root=project_root
        )
        self.evidence_collector = EvidenceCollector(project_root or ".")
        self.verifier_engine = VerifierEngine(project_root or ".")
        self.project_root = project_root

        # v3.2: EventLog 事件日志
        self.event_log = EventLog(project_root or ".", run_id=None)

        # v3.4: TraceLog 追踪日志
        self.trace_log = TraceLog(project_root or ".")

    # ============ 工作流管理 ============

    async def create_workflow(
        self,
        level: WorkflowLevel,
        template_id: str,
        parent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """
        创建工作流实例

        Args:
            level: 工作流层级（project/department/task）
            template_id: 模板 ID
            parent_id: 父工作流 ID（L1 为 null）
            data: 工作流数据

        Returns:
            创建的 WorkflowInstance
        """
        # 生成唯一 ID
        workflow_id = f"wf_{level.value}_{uuid.uuid4().hex[:8]}"

        # 验证模板存在
        template = self.template_manager.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # v3.1: 契约发现 - 验证工作流所需输入契约
        try:
            self.contract_discovery.discover_all()
            is_complete, missing = self.contract_discovery.validate_workflow_inputs(template_id)
            if not is_complete:
                import logging
                logging.getLogger(__name__).warning(
                    f"Workflow {template_id}: missing contracts: {missing}"
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Contract discovery error: {e}")

        # 创建 WorkflowInstance
        data = data or {}
        data.setdefault("run_id", self._generate_run_id())
        instance = WorkflowInstance(
            id=workflow_id,
            level=level,
            parent_id=parent_id,
            template_id=template_id,
            status=WorkflowStatus.PENDING,
            data=data,
        )

        # 写入数据库
        await self.store.create_workflow(instance)

        # v3.2: 记录工作流创建事件
        self.event_log.run_id = data.get("run_id", workflow_id)
        self.event_log.log_run_created(workflow_id, template_id)

        # 如果是 L1/L2，自动创建子工作流
        if level == WorkflowLevel.PROJECT and template.departments:
            for dept_config in template.departments:
                # 支持 template 和 template_id 两种键名
                dept_template_id = dept_config.get("template_id") or dept_config.get("template")
                await self.spawn_workflow(
                    parent_id=workflow_id,
                    level=WorkflowLevel.DEPARTMENT,
                    template_id=dept_template_id,
                    data=dept_config.get("data", {}),
                )
        elif level == WorkflowLevel.DEPARTMENT and template.tasks:
            for task_config in template.tasks:
                # 支持 template 和 template_id 两种键名
                task_template_id = task_config.get("template_id") or task_config.get("template")
                await self.spawn_workflow(
                    parent_id=workflow_id,
                    level=WorkflowLevel.TASK,
                    template_id=task_template_id,
                    data=task_config.get("data", {}),
                )

        return instance

    async def spawn_workflow(
        self,
        parent_id: str,
        level: WorkflowLevel,
        template_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """
        创建子工作流

        Args:
            parent_id: 父工作流 ID
            level: 工作流层级
            template_id: 模板 ID
            data: 工作流数据

        Returns:
            创建的子工作流
        """
        # 验证 parent_id 存在
        parent = await self.store.get_workflow(parent_id)
        if not parent:
            raise ValueError(f"Parent workflow not found: {parent_id}")

        # 调用 create_workflow，指定 parent_id
        return await self.create_workflow(level, template_id, parent_id, data)

    # ============ 状态查询 ============

    async def get_state(
        self,
        workflow_id: str
    ) -> WorkflowState:
        """
        获取工作流状态

        Args:
            workflow_id: 工作流 ID

        Returns:
            工作流当前状态
        """
        # 从数据库加载实例
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # 获取子工作流列表
        children = await self.store.get_children(workflow_id)
        children_ids = [c.id for c in children]

        # 构造 WorkflowState
        return WorkflowState(
            workflow_id=instance.id,
            level=instance.level,
            status=instance.status,
            current_step=instance.current_step,
            parent_id=instance.parent_id,
            children=children_ids,
            data=instance.data,
            template_id=instance.template_id,
        )

    async def get_ready_steps(
        self,
        workflow_id: str
    ) -> List[Step]:
        """
        获取可执行步骤列表

        Args:
            workflow_id: 工作流 ID

        Returns:
            可执行的步骤列表
        """
        # 加载模板
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return []

        # 获取模板步骤
        all_steps = self.template_manager.get_steps(instance.template_id)

        # 调用 WorkflowStateMachine.get_ready_steps
        return await self.state_machine.get_ready_steps(workflow_id, all_steps)

    # ============ 执行控制 ============

    async def run_step(
        self,
        workflow_id: str,
        step_id: Optional[str] = None
    ) -> StepResult:
        """
        执行单个步骤

        Args:
            workflow_id: 工作流 ID
            step_id: 步骤 ID（可选，不指定则执行第一个就绪步骤）

        Returns:
            步骤执行结果
        """
        # 获取 WorkflowInstance
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return StepResult(
                status="failed",
                step_id=None,
                workflow_id=workflow_id,
                message=f"Workflow not found: {workflow_id}",
            )

        # 自动启动工作流：如果状态是 PENDING，先转换为 RUNNING
        # 这样 get_ready_steps() 才能正确返回就绪步骤
        reopened_from_failed = False
        if instance.status == WorkflowStatus.PENDING:
            await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)
            instance = await self.store.get_workflow(workflow_id)  # 刷新实例状态
        elif instance.status == WorkflowStatus.FAILED:
            # 允许通过 "继续工作流" 从失败状态重试未完成步骤。
            # 先收敛遗留 running 记录，避免状态与执行记录不一致。
            try:
                await self.store.fail_running_task_executions(
                    workflow_id,
                    error_message="Workflow retry requested after failure",
                )
            except Exception:
                pass
            await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)
            reopened_from_failed = True
            instance = await self.store.get_workflow(workflow_id)  # 刷新实例状态

        # 获取可执行步骤
        ready_steps = await self.get_ready_steps(workflow_id)

        if not ready_steps:
            # 提供更可诊断的无就绪步骤信息（尤其是失败场景）。
            latest_failed_step = None
            latest_failed_reason = None
            if instance.status == WorkflowStatus.FAILED:
                executions = await self.store.get_task_executions(workflow_id)
                failed_exec = next(
                    (
                        exe for exe in reversed(executions)
                        if exe.status == TaskExecutionStatus.FAILED
                    ),
                    None,
                )
                if failed_exec is not None:
                    latest_failed_step = failed_exec.step_name
                    latest_failed_reason = failed_exec.error_message

            status_suffix = f"workflow_status={instance.status.value}"
            if reopened_from_failed:
                status_suffix += ", reopened_from_failed=true"
            if latest_failed_step:
                status_suffix += f", last_failed_step={latest_failed_step}"
            if latest_failed_reason:
                status_suffix += f", reason={latest_failed_reason}"
            return StepResult(
                status="no_ready_step",
                step_id=latest_failed_step,
                workflow_id=workflow_id,
                message=f"No ready steps available ({status_suffix})",
            )

        # 选择要执行的步骤
        step_to_execute = None
        if step_id:
            # 查找指定的步骤
            for step in ready_steps:
                if step.id == step_id:
                    step_to_execute = step
                    break
            if not step_to_execute:
                return StepResult(
                    status="failed",
                    step_id=step_id,
                    workflow_id=workflow_id,
                    message=f"Step {step_id} is not ready",
                )
        else:
            # 执行第一个就绪步骤
            step_to_execute = ready_steps[0]

        # 开始步骤
        await self.state_machine.start_step(workflow_id, step_to_execute.id)

        # v3.2: 记录步骤开始事件 (Legacy EventLog)
        self.event_log.log_step_started(
            step_id=step_to_execute.id,
            agent_id=getattr(step_to_execute, 'agent_id', None) or step_to_execute.kind,
        )

        # v3.5: Publish EventBus event (PM Agent)
        get_event_bus().publish(Event(
            type=EventType.STEP_STARTED,
            payload={
                "run_id": instance.data.get("run_id", workflow_id),
                "step_id": step_to_execute.id,
                "kind": step_to_execute.kind
            },
            source_workflow=workflow_id,
            timestamp=datetime.utcnow().isoformat(),
            event_id=uuid.uuid4().hex
        ))

        # v3.4: 开始追踪 Span
        trace_span = self.trace_log.start_span(
            span_type=SpanType.ORCHESTRATOR,
            name=f"step.{step_to_execute.id}",
            input_data={
                "step_id": step_to_execute.id,
                "step_kind": step_to_execute.kind,
                "executor_type": getattr(step_to_execute, 'executor_type', None),
                "agent_id": getattr(step_to_execute, 'agent_id', None),
            },
            tags=[f"kind:{step_to_execute.kind}"],
        )

        # 根据 step.kind 分支处理（v1.4）
        # v1.5: 新增 orchestrator_cli 和 compliance_gate 类型
        # v3.5: on_failure 策略包裹
        try:
            # 构建步骤执行器
            async def _dispatch_step() -> StepResult:
                if step_to_execute.kind in ("workflow_spawn", "subworkflow"):
                    return await self._run_subworkflow_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "human_gate":
                    return await self._handle_human_gate(workflow_id, step_to_execute)
                elif step_to_execute.kind == "orchestrator_cli":
                    return await self._run_orchestrator_cli_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "compliance_gate":
                    return await self._run_compliance_gate_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "claude_code":
                    return await self._run_claude_code_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "patch_apply":
                    return await self._run_patch_apply_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "agent":
                    if step_to_execute.executor_type == "claude_code":
                        return await self._run_claude_code_step(workflow_id, step_to_execute)
                    else:
                        return await self._run_agent_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "skill":
                    return await self._run_skill_step(workflow_id, step_to_execute)
                else:
                    executor = self.executor_factory.create(step_to_execute.executor_type or "llm")
                    input_data = step_to_execute.input or {}

                    # v3.5: worktree 强制隔离
                    if getattr(step_to_execute, "repo_scope", None):
                        run_id = instance.data.get("run_id", workflow_id)
                        repo_id = step_to_execute.repo_scope
                        
                        # 并行安全：检查是否有其他活跃 run 使用同一 repo
                        active_runs = self.worktree_manager.list_active_runs_for_repo(repo_id)
                        # 如果有其他 run，或者当前 run 已被标记为并行模式，则使用 worktree 模式
                        mode = "worktree" if len(active_runs) > 0 and run_id not in active_runs else None
                        
                        wt_info = self.worktree_manager.allocate(run_id, repo_id, mode=mode)
                        if not self.worktree_manager.validate_workdir(run_id, repo_id):
                             raise RuntimeError(f"Worktree validation failed for {repo_id}")
                        input_data["workspace"] = wt_info.workdir
                        
                        # P0-4: Capture state before
                        commit_before = self.worktree_manager.get_current_commit(run_id, repo_id) or ""

                    output = await executor.execute(input_data)
                    
                    # v3.5: P0-3: Patch-first 强制产出
                    patch_bundle = None
                    if getattr(step_to_execute, "repo_scope", None):
                        try:
                            run_id = instance.data.get("run_id", workflow_id)
                            repo_id = step_to_execute.repo_scope
                            # 收集 patch 三件套
                            patch_bundle = self.patch_collector.collect(
                                run_id, step_to_execute.id, repo_id
                            )
                            # 注入 output.evidence
                            if patch_bundle and not patch_bundle.is_empty:
                                if isinstance(output, dict):
                                    evidence = output.get("evidence", {})
                                    evidence["patch"] = {
                                        # 基本元数据
                                        "files_changed": patch_bundle.files_changed,
                                        "insertions": patch_bundle.insertions,
                                        "deletions": patch_bundle.deletions,
                                        "is_empty": patch_bundle.is_empty,
                                        # 关键校验和
                                        "hash": patch_bundle.patch_hash,
                                        # 文件路径（用于后续查看/gate）
                                        "path": patch_bundle.patch_path,
                                        "stat_path": patch_bundle.stat_path,
                                    }
                                    output["evidence"] = evidence
                            
                            # v3.5 P0-4: 生成 Receipt (仅 repo_scope 步骤)
                            commit_after = self.worktree_manager.get_current_commit(run_id, repo_id) or ""
                            
                            # Inputs hash
                            try:
                                inputs_json = json.dumps(input_data, sort_keys=True)
                            except TypeError:
                                inputs_json = str(input_data) # Fallback for non-serializable objects
                            inputs_hash = hashlib.sha256(inputs_json.encode("utf-8")).hexdigest()
                            
                            receipt = ExecutionReceipt(
                                run_id=run_id,
                                step_id=step_to_execute.id,
                                repo_id=repo_id,
                                commit_before=commit_before,
                                commit_after=commit_after,
                                inputs_hash=inputs_hash,
                                patch_hash=patch_bundle.patch_hash if patch_bundle else "",
                                exit_code=0,
                                timestamp=datetime.utcnow().isoformat(),
                                executor_type=step_to_execute.executor_type or "llm",
                            )
                            self.receipt_store.save(receipt)

                        except Exception as e:
                            # 记录但不阻断主流程（Patch 收集失败可以算 warning）
                            # logging.warning(f"Failed to collect patch: {e}")
                            pass

                    r = await self.state_machine.complete_step(
                        workflow_id,
                        step_to_execute.id,
                        output,
                        step_outputs=step_to_execute.outputs if hasattr(step_to_execute, 'outputs') else None
                    )
                    
                    # v3.5: Publish EventBus event
                    get_event_bus().publish(Event(
                        type=EventType.STEP_COMPLETED,
                        payload={
                            "run_id": run_id,
                            "step_id": step_to_execute.id,
                            "result": asdict(r) if hasattr(r, 'to_dict') else r.__dict__
                        },
                        source_workflow=workflow_id,
                        timestamp=datetime.utcnow().isoformat(),
                        event_id=uuid.uuid4().hex
                    ))

                    await self._check_workflow_completion(workflow_id)
                    return r

            # v3.5: 使用 on_failure 策略包裹执行
            failure_handler = FailureHandler()
            if failure_handler.has_policy(step_to_execute):
                # 定义 human_review fallback 回调
                async def _on_human_review(step_id: str, message: str) -> StepResult:
                    from lee.orchestrator.storage.models import WorkflowStatus
                    await self.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)
                    self.event_log.log_gate_triggered(
                        gate_id=f"on_failure_{step_id}",
                        step_id=step_id,
                        gate_type="on_failure_human_review",
                        blocking=True,
                    )
                    return StepResult(
                        status="blocked",
                        blocked_reason="on_failure_human_review",
                        step_id=step_id,
                        workflow_id=workflow_id,
                        message=f"Step failed after retries, awaiting human review: {message}",
                    )

                result = await failure_handler.execute_with_policy(
                    step=step_to_execute,
                    runner_fn=_dispatch_step,
                    on_human_review=_on_human_review,
                )
            else:
                result = await _dispatch_step()

            # v3.5.1: 确保所有步骤类型完成后都检查工作流完成状态
            # （之前只有 default executor 路径调用了 _check_workflow_completion）
            if result.status == "success":
                await self._check_workflow_completion(workflow_id)

            # v3.4: 完成追踪 Span
            self.trace_log.complete_span(
                trace_span.span_id,
                output_data={
                    "status": getattr(result, 'status', 'unknown'),
                    "message": getattr(result, 'message', ''),
                },
                tags=[f"result:{getattr(result, 'status', 'unknown')}"],
            )

            return result

        except Exception as e:
            # v3.4: 失败追踪 Span
            self.trace_log.fail_span(
                trace_span.span_id,
                error_code=type(e).__name__,
                error_message=str(e),
            )
            # 步骤失败
            await self.state_machine.fail_step(workflow_id, step_to_execute.id, str(e))
            # v3.2: 记录步骤失败事件
            self.event_log.log_step_failed(
                step_id=step_to_execute.id,
                agent_id=getattr(step_to_execute, 'agent_id', None) or step_to_execute.kind,
                error=str(e),
            )
            
            # v3.5: Publish EventBus event
            get_event_bus().publish(Event(
                type=EventType.STEP_FAILED,
                payload={
                    "run_id": instance.data.get("run_id", workflow_id),
                    "step_id": step_to_execute.id,
                    "error": str(e)
                },
                source_workflow=workflow_id,
                timestamp=datetime.utcnow().isoformat(),
                event_id=uuid.uuid4().hex
            ))
            return StepResult(
                status="failed",
                step_id=step_to_execute.id,
                workflow_id=workflow_id,
                message=f"Step execution failed: {e}",
            )

    # ============ Stage 循环执行 ============

    async def _run_stage_with_loop(
        self,
        workflow_id: str,
        stage,
    ) -> List[StepResult]:
        """
        执行带循环的 Stage

        当 stage.loop.enabled=True 时，执行 patch → test → analyze → retry 的
        收敛循环，直到满足停止条件。

        Args:
            workflow_id: 工作流 ID
            stage: StageIR 对象（需要有 loop、steps 属性）

        Returns:
            所有迭代中产生的 StepResult 列表
        """
        from lee.orchestrator.execution.loop_controller import LoopController
        from lee.orchestrator.storage.event_log import EventType

        controller = LoopController(
            config=stage.loop,
            evidence_collector=self.evidence_collector,
            run_id=workflow_id,
        )

        all_results: List[StepResult] = []

        while controller.should_continue():
            loop_ctx = controller.get_loop_context()
            iteration = loop_ctx.get("iteration", 0) + 1

            # 记录循环迭代开始
            self.event_log.log(
                event_type=EventType.STEP_STARTED,
                data={
                    "type": "loop_iteration_start",
                    "stage_id": stage.id,
                    "iteration": iteration,
                    "max_iterations": stage.loop.max_iterations,
                },
            )

            # 执行 stage 内的所有步骤
            stage_results: Dict[str, Any] = {}
            blocked = False

            for step in stage.steps:
                result = await self.run_step(workflow_id, step.id)
                stage_results[step.id] = {
                    "status": result.status,
                    "message": getattr(result, "message", ""),
                    "output": getattr(result, "output", None),
                }
                all_results.append(result)

                # Gate 阻塞则暂停循环
                if result.status in ("blocked", "waiting_approval"):
                    blocked = True
                    break

            if blocked:
                break

            # 记录本轮结果 + 收敛判断
            decision = controller.record_iteration(stage_results)
            controller.write_iteration_evidence(
                controller.state.current_iteration, stage_results
            )

            # 记录循环迭代完成事件
            self.event_log.log(
                event_type=EventType.STEP_COMPLETED,
                data={
                    "type": "loop_iteration_end",
                    "stage_id": stage.id,
                    "iteration": controller.state.current_iteration,
                    "decision": decision,
                    "loop_status": controller.state.status,
                },
            )

            if decision != "continue":
                break

        # 记录循环总结
        summary = controller.get_summary()
        self.event_log.log(
            event_type=EventType.STEP_COMPLETED,
            data={
                "type": "loop_summary",
                "stage_id": stage.id,
                **summary,
            },
        )

        return all_results

    async def run_until_blocked(
        self,
        workflow_id: str,
        max_steps: int = 10
    ) -> ExecutionSummary:
        """
        执行直到阻塞

        Args:
            workflow_id: 工作流 ID
            max_steps: 最大执行步数

        Returns:
            执行摘要
        """
        start_time = datetime.now()
        total_steps = 0

        # v3.2: 记录 RUN_STARTED
        run_instance = await self.store.get_workflow(workflow_id)
        if run_instance:
            self.event_log.run_id = run_instance.data.get("run_id", workflow_id)
        from lee.orchestrator.storage.event_log import EventType
        self.event_log.log(
            event_type=EventType.RUN_STARTED,
            data={"workflow_id": workflow_id, "max_steps": max_steps},
        )
        completed_steps = 0
        blocked_at = None
        final_status = "completed"

        for _ in range(max_steps):
            # 执行一个步骤
            result = await self.run_step(workflow_id)

            total_steps += 1

            if result.status == "success":
                completed_steps += 1
            elif result.status in ("waiting_approval", "blocked"):
                blocked_at = result.step_id
                final_status = "blocked"
                break
            elif result.status == "no_ready_step":
                # 没有可执行的步骤，可能是完成或阻塞
                instance = await self.store.get_workflow(workflow_id)
                if instance.status == WorkflowStatus.COMPLETED:
                    break
                blocked_at = None  # 没有步骤可执行
                final_status = "blocked"
                break
            elif result.status == "failed":
                final_status = "failed"
                break

        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()

        # 获取最终状态
        instance = await self.store.get_workflow(workflow_id)
        if instance.status == WorkflowStatus.COMPLETED:
            final_status = "completed"
        elif instance.status == WorkflowStatus.FAILED:
            final_status = "failed"

        # v3.2: 记录 RUN 完成/失败事件
        run_event_type = EventType.RUN_COMPLETED if final_status == "completed" else (
            EventType.RUN_FAILED if final_status == "failed" else EventType.RUN_PAUSED
        )
        self.event_log.log(
            event_type=run_event_type,
            data={
                "workflow_id": workflow_id,
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "blocked_at": blocked_at,
                "duration_seconds": duration,
            },
        )

        return ExecutionSummary(
            workflow_id=workflow_id,
            total_steps=total_steps,
            completed_steps=completed_steps,
            blocked_at=blocked_at,
            status=final_status,
            duration_seconds=duration,
        )

    # ============ 暂停/恢复 ============

    async def pause(
        self,
        workflow_id: str
    ) -> None:
        """
        暂停工作流

        Args:
            workflow_id: 工作流 ID
        """
        await self.state_machine.pause_workflow(workflow_id)
        # 收敛遗留的 running task 记录，避免出现 workflow=paused 但 task=running。
        try:
            await self.store.fail_running_task_executions(
                workflow_id,
                error_message="Workflow paused; running step interrupted",
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to fail running tasks for workflow {workflow_id}: {e}"
            )

    async def resume(
        self,
        workflow_id: str
    ) -> None:
        """
        恢复工作流

        Args:
            workflow_id: 工作流 ID
        """
        await self.state_machine.resume_workflow(workflow_id)

    # ============ 完成/失败 ============

    async def complete_workflow(
        self,
        workflow_id: str
    ) -> None:
        """
        完成工作流

        Args:
            workflow_id: 工作流 ID
        """
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.COMPLETED)

    async def fail_workflow(
        self,
        workflow_id: str,
        error_message: str
    ) -> None:
        """
        失败工作流

        Args:
            workflow_id: 工作流 ID
            error_message: 错误信息
        """
        # 获取当前工作流
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # 将错误信息存储在 data 中
        instance.data["error"] = error_message
        await self.store.update_workflow_data(workflow_id, instance.data)
        try:
            await self.store.fail_running_task_executions(
                workflow_id,
                error_message=error_message,
            )
        except Exception:
            pass
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.FAILED)

    # ============ 辅助方法 ============

    def _generate_run_id(self) -> str:
        """生成 run_id"""
        return f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"

    async def _check_workflow_completion(self, workflow_id: str) -> None:
        """
        检查工作流是否完成

        Args:
            workflow_id: 工作流 ID
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return

        # 获取模板的所有步骤
        all_steps = self.template_manager.get_steps(instance.template_id)
        completed_steps = instance.data.get("completed_steps", [])

        # 检查是否所有步骤都已完成
        if len(all_steps) > 0 and len(completed_steps) >= len(all_steps):
            await self.store.update_workflow_status(
                workflow_id,
                WorkflowStatus.COMPLETED,
                completed_at=datetime.now()
            )
