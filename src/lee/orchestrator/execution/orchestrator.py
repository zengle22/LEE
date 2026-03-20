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

import asyncio
import uuid
import json
import hashlib
import os
from datetime import datetime, timezone
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
    Complexity,
    Point,
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
from lee.orchestrator.config import is_coding_executor_type
from lee.orchestrator.core.event_bus import get_event_bus, Event, EventType
# Mixin 模块
from lee.orchestrator.execution.step_runners import StepRunnerMixin
from lee.orchestrator.execution.gate_operations import GateOperationsMixin
from lee.orchestrator.execution.subworkflow_ops import SubworkflowMixin
from lee.orchestrator.execution.instance_loader import InstanceLoaderMixin


# ========================================================================
# 核心调度器（Orchestrator）
# ========================================================================

class Orchestrator(StepRunnerMixin, GateOperationsMixin, SubworkflowMixin, InstanceLoaderMixin):
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

    RUNNING_EXECUTION_POLL_SECONDS = 1.0

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
        # v3.5: 传递配置到 TemplateManager 以使用正确的 executor.default_type
        self.template_manager = template_manager or TemplateManager(
            project_root=project_root,
            config=self.config
        )
        self.state_machine = WorkflowStateMachine(store, template_manager=self.template_manager)
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
        # 创建模板引擎用于路径渲染
        from lee.orchestrator.core.template_engine import TemplateEngine
        self.template_engine = TemplateEngine()
        self.agent_context_builder = AgentContextBuilder(
            agent_loader=agent_loader,
            project_root=project_root,
            context_index=self.context_index,
            template_engine=self.template_engine
        )
        self.file_output_handler = FileOutputHandler(
            project_root=project_root
        )
        self.evidence_collector = EvidenceCollector(project_root or ".")
        self.verifier_engine = VerifierEngine(project_root or ".")
        self.project_root = project_root

        # v3.2: EventLog 事件日志
        self.event_log = EventLog(project_root or ".", run_id=None)
        self.state_machine.event_log = self.event_log

        # v3.4: TraceLog 追踪日志
        self.trace_log = TraceLog(project_root or ".")

        # v3.6: ArtifactManager 产出物管理
        from lee.orchestrator.execution.artifacts import ArtifactManager, ManifestManager
        artifacts_root = Path(project_root or ".") / ".artifacts"
        self.artifact_manager = ArtifactManager(artifacts_root)
        self.manifest_manager = ManifestManager(
            artifacts_root,
            registry=self.artifact_manager.registry
        )

    # ============ 工作流管理 ============

    async def create_workflow(
        self,
        level: WorkflowLevel,
        template_id: str,
        parent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """创建工作流实例。"""
        workflow_id = f"wf_{level.value}_{uuid.uuid4().hex[:8]}"
        template_ref = template_id
        template = self.template_manager.get_template(template_ref)
        if not template and template_id.startswith(("template.", "workflow.")):
            try:
                resolved_template_path = self._resolve_l3_template_path(template_id)
            except FileNotFoundError:
                resolved_template_path = None
            if resolved_template_path is not None:
                template_ref = str(resolved_template_path)
                template = self.template_manager.get_template(template_ref)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

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

        data = data or {}
        if self.project_root:
            data.setdefault("project_root", str(Path(self.project_root).resolve()))
        data.setdefault("run_id", self._generate_run_id())
        parent = await self.store.get_workflow(parent_id) if parent_id else None
        if parent and isinstance(parent.data, dict):
            data.setdefault("root_run_id", parent.data.get("root_run_id") or parent.data.get("run_id"))
        instance = WorkflowInstance(
            id=workflow_id,
            level=level,
            parent_id=parent_id,
            template_id=template_ref,
            status=WorkflowStatus.PENDING,
            data=data,
        )

        # 写入数据库
        await self.store.create_workflow(instance)

        # v3.6: 创建产出物 Manifest
        try:
            run_id = data.get("run_id", workflow_id)
            parent_run_id = parent.data.get("run_id") if parent and isinstance(parent.data, dict) else None
            department = data.get("department") or (
                template.owner if hasattr(template, "owner") else None
            )
            self.manifest_manager.create(
                run_id=run_id,
                workflow_id=workflow_id,
                department=department,
                executor=data.get("executor"),
                executor_version=data.get("executor_version"),
                parent_run_id=parent_run_id,
                root_run_id=data.get("root_run_id")
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to create manifest: {e}")

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

        # 检查是否从 Instance 文件加载
        if self._is_instance_path(instance.template_id):
            instance_data = self._load_instance_file(instance.template_id)
            if instance_data:
                all_steps = self._get_steps_from_instance(instance_data)
            else:
                all_steps = []
        else:
            # 从模板加载
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

        v3.6 新增：在执行属于带循环 stage 的步骤前，注入循环变量到 instance.data

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

        # v3.6 新增：在执行步骤前，检查是否属于带循环的 stage，如果是则注入循环变量
        # 这确保模板渲染时能访问 current_test_set 等循环变量
        await self._inject_loop_variables_if_needed(workflow_id, instance)

        # 获取可执行步骤
        ready_steps = await self.get_ready_steps(workflow_id)

        # 继续执行 run_step 的剩余逻辑
        return await self._continue_run_step(
            workflow_id, instance, reopened_from_failed, ready_steps, step_id
        )

    async def _inject_loop_variables_if_needed(
        self,
        workflow_id: str,
        instance: WorkflowInstance,
    ) -> None:
        """
        检查就绪步骤是否属于带循环的 stage，如果是则注入循环变量

        Args:
            workflow_id: 工作流 ID
            instance: WorkflowInstance 对象
        """
        try:
            # 获取就绪步骤
            ready_steps = await self.get_ready_steps(workflow_id)
            if not ready_steps:
                return

            # 获取第一个就绪步骤（我们即将执行的步骤）
            step = ready_steps[0]

            # 获取步骤所属的 stage_id
            stage_id = step.config.get("stage_id") if step.config else None
            if not stage_id:
                return

            # 从模板获取 stage 信息
            template = self.template_manager.get_template(instance.template_id)
            if not template:
                return

            # 从 template 的 departments/tasks 中查找 stage 配置
            # spec-global 格式的 stage 信息存储在 config 中
            stages = template.config.get("stages", []) if template.config else []

            # 查找对应的 stage
            stage_config = None
            for stage in stages:
                if stage.get("id") == stage_id:
                    stage_config = stage
                    break

            if not stage_config:
                return

            # 检查 stage 是否有 loop.over 配置
            loop_config = stage_config.get("loop", {})
            if not loop_config or not loop_config.get("over"):
                return

            # 获取循环变量配置
            loop_over = loop_config.get("over")  # 如 "$runtime.effective_test_sets"
            loop_as = loop_config.get("as")  # 如 "current_test_set"

            if not loop_over or not loop_as:
                return

            # 解析 loop.over 表达式获取变量列表
            from lee.orchestrator.execution.variable_resolver import VariableResolver
            resolver = VariableResolver()

            # 构建解析上下文
            context = {
                "runtime": instance.data.get("runtime", {}),
                "inputs": instance.data.get("inputs", {}),
                "step_outputs": instance.data.get("step_outputs", {}),
            }

            try:
                loop_over_value = resolver.resolve_reference(loop_over, context)
            except ValueError:
                # 无法解析，尝试直接从 instance.data 获取
                if loop_over.startswith("$runtime."):
                    key = loop_over[9:]  # 去掉 "$runtime."
                    loop_over_value = instance.data.get("runtime", {}).get(key, [])
                else:
                    loop_over_value = []

            if not loop_over_value:
                return

            if not isinstance(loop_over_value, list):
                loop_over_value = [loop_over_value]

            # 确定当前应该执行哪个循环迭代
            # 简单策略：使用第一个未被执行的循环变量
            # 更复杂的策略：跟踪已执行的循环变量

            # 检查 instance.data 中是否已有当前循环变量
            current_loop_value = instance.data.get(loop_as)

            # 如果是第一次执行这个 stage 的步骤，注入第一个循环变量
            if current_loop_value is None:
                # 使用第一个循环变量
                current_loop_value = loop_over_value[0] if loop_over_value else None

            if current_loop_value:
                # 注入循环变量到 instance.data
                if isinstance(current_loop_value, dict):
                    # 如果是字典，将键值对展开到 data 中
                    instance.data[loop_as] = current_loop_value
                    # 同时展开顶层变量（支持 {{ current_test_set.test_set_id }} 访问）
                    for key, value in current_loop_value.items():
                        instance.data[f"{loop_as}.{key}"] = value
                else:
                    instance.data[loop_as] = current_loop_value

                # 保存更新后的 instance.data
                await self.store.update_workflow_data(workflow_id, instance.data)
                import logging
                logging.getLogger(__name__).info(f"[LOOP] Injected loop variable '{loop_as}' = {current_loop_value}")

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to inject loop variables: {e}")

    async def _continue_run_step(
        self,
        workflow_id: str,
        instance: WorkflowInstance,
        reopened_from_failed: bool,
        ready_steps: List[Step],
        step_id: Optional[str] = None,
    ):
        """继续执行 run_step 方法的剩余逻辑"""
        # v3.6: Check for L2 instance with complexity routing
        # If this is an L2 instance, route phases through complexity-based execution
        if self._is_l2_instance(instance):
            instance = await self._reconcile_l2_subworkflow_phases(instance)
            # For L2 instances, phases act as steps
            # Find the first pending phase
            pending_phase = self._get_next_pending_phase(instance)
            if pending_phase:
                phase_id = pending_phase["id"]
                complexity = self._get_phase_complexity(instance, phase_id)
                return await self._execute_l2_phase_with_complexity(
                    workflow_id, phase_id, complexity
                )
            else:
                failed_phase = self._get_failed_phase(instance)
                if failed_phase:
                    failed_phase_id = failed_phase.get("id") or "<unknown-phase>"
                    failed_reason = failed_phase.get("error") or "L2 phase failed"
                    await self.store.update_workflow_status(
                        workflow_id,
                        WorkflowStatus.FAILED,
                        completed_at=datetime.now(),
                    )
                    return StepResult(
                        status="failed",
                        step_id=failed_phase_id,
                        workflow_id=workflow_id,
                        message=f"L2 phase {failed_phase_id} failed: {failed_reason}",
                    )
                # All phases completed
                instance.data["lifecycle_state"] = "Closed"
                await self.store.update_workflow_data(workflow_id, instance.data)
                await self.store.update_workflow_status(
                    workflow_id, WorkflowStatus.COMPLETED,
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="success",
                    step_id=None,
                    workflow_id=workflow_id,
                    message="All L2 phases completed",
                )

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

        trace_span = None
        try:
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
                timestamp=datetime.now(timezone.utc).isoformat(),
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
        except Exception as e:
            await self.state_machine.fail_step(workflow_id, step_to_execute.id, str(e))
            try:
                self.event_log.log_step_failed(
                    step_id=step_to_execute.id,
                    agent_id=getattr(step_to_execute, 'agent_id', None) or step_to_execute.kind,
                    error=f"step_start_instrumentation_failed: {e}",
                )
            except Exception:
                pass
            return StepResult(
                status="failed",
                step_id=step_to_execute.id,
                workflow_id=workflow_id,
                message=f"Step startup failed before runner dispatch: {e}",
            )

        # 根据 step.kind 分支处理（v1.4）
        # v1.5: 新增 orchestrator_cli 和 compliance_gate 类型
        # v3.5: on_failure 策略包裹
        try:
            run_id = instance.data.get("run_id", workflow_id)

            # 构建步骤执行器
            async def _dispatch_step() -> StepResult:
                if step_to_execute.kind in ("workflow_spawn", "subworkflow"):
                    return await self._run_subworkflow_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "human_gate":
                    return await self._handle_human_gate(workflow_id, step_to_execute)
                elif step_to_execute.kind == "gate":
                    # 处理 kind: gate，根据 type 分发到 auto_check 或 human_review
                    gate_type = step_to_execute.config.get("gate", {}).get("type", "auto_check") if step_to_execute.config else "auto_check"
                    if gate_type == "auto_check":
                        return await self._run_auto_check_gate_step(workflow_id, step_to_execute)
                    elif gate_type in ("human_review", "human_decision", "human_approval"):
                        return await self._handle_human_gate(workflow_id, step_to_execute)
                    else:
                        # 默认当作 auto_check 处理
                        return await self._run_auto_check_gate_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "orchestrator_cli":
                    return await self._run_orchestrator_cli_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "compliance_gate":
                    return await self._run_compliance_gate_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "phase":
                    result = await self.state_machine.complete_step(
                        workflow_id,
                        step_to_execute.id,
                        {"phase_id": step_to_execute.id, "status": "completed"},
                        step_outputs=step_to_execute.outputs if hasattr(step_to_execute, "outputs") else None,
                    )
                    get_event_bus().publish(Event(
                        type=EventType.STEP_COMPLETED,
                        payload={
                            "run_id": run_id,
                            "step_id": step_to_execute.id,
                            "result": asdict(result) if hasattr(result, "to_dict") else result.__dict__,
                        },
                        source_workflow=workflow_id,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        event_id=uuid.uuid4().hex,
                    ))
                    await self._check_workflow_completion(workflow_id)
                    return result
                elif step_to_execute.kind == "claude_code":
                    return await self._run_claude_code_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "patch_apply":
                    return await self._run_patch_apply_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "agent":
                    executor_override = str(
                        (instance.data or {}).get("executor_override") or ""
                    ).strip().lower()
                    if (
                        step_to_execute.executor_type == "claude_code"
                        and (not executor_override or is_coding_executor_type(executor_override))
                    ):
                        return await self._run_claude_code_step(workflow_id, step_to_execute)
                    else:
                        return await self._run_agent_step(workflow_id, step_to_execute)
                elif step_to_execute.kind == "skill":
                    return await self._run_skill_step(workflow_id, step_to_execute)
                else:
                    executor = self.executor_factory.create(step_to_execute.executor_type or "claude_code")
                    input_data = step_to_execute.input or {}

                    # v3.5: worktree 强制隔离
                    if getattr(step_to_execute, "repo_scope", None):
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
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                executor_type=step_to_execute.executor_type or "claude_code",
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

                    # v3.6: 记录步骤产出物到 ArtifactManager
                    try:
                        self._record_step_artifacts(
                            workflow_id,
                            step_to_execute.id,
                            output,
                            run_id=run_id,
                        )
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Failed to record artifacts: {e}")

                    # v3.5: Publish EventBus event
                    get_event_bus().publish(Event(
                        type=EventType.STEP_COMPLETED,
                        payload={
                            "run_id": run_id,
                            "step_id": step_to_execute.id,
                            "result": asdict(r) if hasattr(r, 'to_dict') else r.__dict__
                        },
                        source_workflow=workflow_id,
                        timestamp=datetime.now(timezone.utc).isoformat(),
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
            if trace_span is not None:
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
                timestamp=datetime.now(timezone.utc).isoformat(),
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
        context: Optional[Dict[str, Any]] = None,
    ) -> List[StepResult]:
        """
        执行带循环的 Stage

        支持两种循环模式：
        1. 自动修复循环（loop.enabled=True, loop.over=None）：patch → test → analyze → retry
        2. 变量循环（loop.over 不为空）：遍历变量源（如 effective_test_sets）

        Args:
            workflow_id: 工作流 ID
            stage: StageIR 对象（需要有 loop、steps 属性）
            context: 执行上下文（包含 inputs、step_outputs 等）

        Returns:
            所有迭代中产生的 StepResult 列表
        """
        from lee.orchestrator.execution.loop_controller import LoopController
        from lee.orchestrator.storage.event_log import EventType
        from lee.orchestrator.execution.variable_resolver import VariableResolver
        from lee.orchestrator.storage.models import WorkflowInstance

        resolver = VariableResolver()
        all_results: List[StepResult] = []

        # 获取工作流实例用于更新 data
        instance = await self.store.get_workflow(workflow_id)

        # 检查是否是变量循环（loop.over 不为空）
        if stage.loop and stage.loop.over:
            # 变量循环模式：遍历 loop.over 指定的变量源
            try:
                # 解析 loop.over 表达式获取变量列表
                loop_over_value = resolver.resolve_reference(stage.loop.over, context or {})

                if not isinstance(loop_over_value, list):
                    # 如果是字典，转换为列表
                    if isinstance(loop_over_value, dict):
                        loop_over_value = [loop_over_value]
                    else:
                        logger.warning(f"loop.over value is not a list: {type(loop_over_value)}")
                        loop_over_value = [loop_over_value]

                loop_variable_name = stage.loop.as_var or "item"

                # 遍历每个变量值
                for idx, loop_value in enumerate(loop_over_value):
                    iteration = idx + 1

                    # 记录循环迭代开始
                    self.event_log.log(
                        event_type=EventType.STEP_STARTED,
                        data={
                            "type": "loop_iteration_start",
                            "stage_id": stage.id,
                            "iteration": iteration,
                            "loop_variable": loop_variable_name,
                            "loop_value": loop_value if isinstance(loop_value, (str, int, float)) else str(loop_value),
                        },
                    )

                    # 注入循环变量到 instance.data（这样步骤执行时可以访问）
                    # 同时支持直接访问（如 data.current_test_set）和嵌套访问（如 data.current_test_set.test_set_id）
                    if isinstance(loop_value, dict):
                        # 如果是字典，将键值对展开到 data 中
                        instance.data[loop_variable_name] = loop_value
                        # 同时展开顶层变量（支持 {{ current_test_set.test_set_id }} 访问）
                        for key, value in loop_value.items():
                            instance.data[f"{loop_variable_name}.{key}"] = value
                    else:
                        instance.data[loop_variable_name] = loop_value

                    # 保存更新后的 instance.data
                    await self.store.update_workflow_data(workflow_id, instance.data)

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

                    # 记录循环迭代完成
                    self.event_log.log(
                        event_type=EventType.STEP_COMPLETED,
                        data={
                            "type": "loop_iteration_end",
                            "stage_id": stage.id,
                            "iteration": iteration,
                            "loop_variable": loop_variable_name,
                        },
                    )

                    # 检查是否达到最大迭代次数
                    if iteration >= stage.loop.max_iterations:
                        logger.warning(f"Loop reached max iterations: {stage.loop.max_iterations}")
                        break

                # 记录循环总结
                self.event_log.log(
                    event_type=EventType.STEP_COMPLETED,
                    data={
                        "type": "loop_summary",
                        "stage_id": stage.id,
                        "total_iterations": len(loop_over_value),
                        "loop_variable": loop_variable_name,
                    },
                )

            except Exception as e:
                logger.error(f"Variable loop execution failed: {e}")
                self.event_log.log(
                    event_type=EventType.STEP_FAILED,
                    data={
                        "type": "loop_error",
                        "stage_id": stage.id,
                        "error": str(e),
                    },
                )
        else:
            # 自动修复循环模式（原有逻辑）
            controller = LoopController(
                config=stage.loop,
                evidence_collector=self.evidence_collector,
                run_id=workflow_id,
            )

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
        if not run_instance:
            return ExecutionSummary(
                workflow_id=workflow_id,
                total_steps=0,
                completed_steps=0,
                blocked_at=None,
                status="failed",
                duration_seconds=0.0,
            )
        self.event_log.run_id = run_instance.data.get("run_id", workflow_id)
        from lee.orchestrator.storage.event_log import EventType
        self.event_log.log(
            event_type=EventType.RUN_STARTED,
            data={"workflow_id": workflow_id, "max_steps": max_steps},
        )
        completed_steps = 0
        blocked_at = None
        final_status = "completed"

        step_attempts = 0
        while step_attempts < max_steps:
            # 执行一个步骤
            result = await self.run_step(workflow_id)

            if result.status == "success":
                step_attempts += 1
                total_steps += 1
                completed_steps += 1
            elif result.status in ("waiting_approval", "blocked"):
                step_attempts += 1
                total_steps += 1
                blocked_at = result.step_id
                final_status = "blocked"
                break
            elif result.status == "no_ready_step":
                # 没有可执行的步骤，可能是完成或阻塞
                instance = await self.store.get_workflow(workflow_id)
                if instance is None:
                    final_status = "failed"
                    break
                if instance.status == WorkflowStatus.COMPLETED:
                    break
                if instance.status == WorkflowStatus.FAILED:
                    final_status = "failed"
                    break
                if await self._has_running_task_executions(workflow_id):
                    await asyncio.sleep(self.RUNNING_EXECUTION_POLL_SECONDS)
                    continue
                blocked_at = None  # 没有步骤可执行
                final_status = "blocked"
                break
            elif result.status == "failed":
                step_attempts += 1
                total_steps += 1
                final_status = "failed"
                break

        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()

        # 获取最终状态
        instance = await self.store.get_workflow(workflow_id)
        if instance is None:
            final_status = "failed"
        elif instance.status == WorkflowStatus.COMPLETED:
            final_status = "completed"
        elif instance.status == WorkflowStatus.FAILED:
            final_status = "failed"
        elif instance.status == WorkflowStatus.RUNNING:
            final_status = "running"
        elif instance.status == WorkflowStatus.PAUSED:
            final_status = "paused"

        # v3.2: 记录 RUN 完成/失败事件
        run_event_type = (
            EventType.RUN_COMPLETED
            if final_status == "completed"
            else (
                EventType.RUN_FAILED
                if final_status == "failed"
                else EventType.RUN_PAUSED
            )
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

    async def _has_running_task_executions(self, workflow_id: str) -> bool:
        executions = await self.store.get_task_executions(workflow_id)
        return any(exe.status == TaskExecutionStatus.RUNNING for exe in executions)

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

    async def check_stale_task_executions(
        self,
        threshold_minutes: int = 30,
    ) -> Dict[str, Any]:
        """
        检查长时间处于 RUNNING 状态的 task_executions（BUG-2026-0038 监控）

        Args:
            threshold_minutes: 阈值（分钟），默认 30 分钟

        Returns:
            摘要字典，包含：
            - count: stale 记录数量
            - oldest_started_at: 最早的启动时间
            - workflows: 受影响的工作流 ID 列表
            - alert: 是否需要告警
        """
        summary = await self.store.get_stale_task_executions_summary(threshold_minutes)
        summary["alert"] = summary["count"] > 0
        return summary

    async def cleanup_stale_task_executions(
        self,
        threshold_minutes: int = 30,
        error_message: str = "Task execution timeout; marked as failed by monitoring",
    ) -> int:
        """
        清理长时间处于 RUNNING 状态的 task_executions

        Args:
            threshold_minutes: 阈值（分钟），默认 30 分钟
            error_message: 错误信息

        Returns:
            清理的记录数量
        """
        stale_executions = await self.store.find_stale_task_executions(threshold_minutes)
        cleaned_count = 0

        for execution in stale_executions:
            # 检查对应的工作流是否还在运行
            workflow = await self.store.get_workflow(execution.workflow_id)
            if workflow and workflow.status == WorkflowStatus.RUNNING:
                # 工作流仍在运行，标记 task_execution 为 FAILED
                await self.store.update_task_execution(
                    execution.id,
                    TaskExecutionStatus.FAILED,
                    error_message=error_message,
                    completed_at=datetime.now(),
                )
                cleaned_count += 1

        return cleaned_count

    async def _check_workflow_completion(self, workflow_id: str) -> None:
        """
        检查工作流是否完成

        Args:
            workflow_id: 工作流 ID
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return

        # 检查是否从 Instance 文件加载
        if self._is_instance_path(instance.template_id):
            instance_data = self._load_instance_file(instance.template_id)
            if instance_data:
                all_steps = self._get_steps_from_instance(instance_data)
            else:
                all_steps = []
        else:
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

    # ============ L2 Complexity Routing (P0) ============

    def _is_l2_instance(self, instance: WorkflowInstance) -> bool:
        """Check if workflow is an L2 instance.

        L2 instances are identified by:
        1. Level is DEPARTMENT
        2. data.kind is "l2_workflow_instance"
        3. data.phases exists (L2 specific structure)

        Args:
            instance: WorkflowInstance to check

        Returns:
            True if this is an L2 workflow instance
        """
        return (
            instance.level == WorkflowLevel.DEPARTMENT and
            instance.data.get("kind") == "l2_workflow_instance" and
            "phases" in instance.data
        )

    def _get_phase_complexity(
        self,
        instance: WorkflowInstance,
        phase_id: str
    ) -> Complexity:
        """Get complexity for a phase from instance data.

        Args:
            instance: L2 workflow instance
            phase_id: Phase identifier

        Returns:
            Complexity level (S/M/L)
        """
        phases = instance.data.get("phases", [])
        for phase in phases:
            if phase.get("id") == phase_id:
                comp_str = phase.get("complexity", "M")
                try:
                    return Complexity(comp_str)
                except ValueError:
                    return Complexity.M  # Default to M if invalid
        return Complexity.M  # Default

    def _get_phase_info(
        self,
        instance: WorkflowInstance,
        phase_id: str
    ) -> Dict[str, Any]:
        """Get full phase information from instance data.

        Args:
            instance: L2 workflow instance
            phase_id: Phase identifier

        Returns:
            Phase dictionary or empty dict if not found
        """
        phases = instance.data.get("phases", [])
        for phase in phases:
            if phase.get("id") == phase_id:
                return phase
        return {}

    async def _update_l2_phase(
        self,
        workflow_id: str,
        phase_id: str,
        *,
        status: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update one L2 phase payload and persist the workflow data."""
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return {}

        phases = instance.data.get("phases", [])
        updated_phase: Dict[str, Any] = {}
        for phase in phases:
            if phase.get("id") != phase_id:
                continue
            if status is not None:
                phase["status"] = status
            if extra:
                phase.update(extra)
            updated_phase = dict(phase)
            break

        instance.data["lifecycle_state"] = self._derive_l2_lifecycle_state(instance.data)
        await self.store.update_workflow_data(workflow_id, instance.data)
        return updated_phase

    def _derive_l2_lifecycle_state(self, workflow_data: Dict[str, Any]) -> str:
        """Derive canonical L2 lifecycle state from phase progression."""
        phases = workflow_data.get("phases", [])
        if not phases:
            return "Ready"

        phase_status = {phase.get("id"): phase.get("status") for phase in phases}
        if phase_status.get("smoke_gate") == "completed":
            return "Closed"
        if phase_status.get("merge_or_reject") == "completed":
            return "Closed"
        if phase_status.get("evidence_pack") == "completed":
            return "Evidence Pack Produced"
        if any(status in {"running", "completed", "blocked"} for status in phase_status.values()):
            return "In Progress"
        return "Ready"

    async def _merge_l2_phase_outputs(
        self,
        workflow_id: str,
        phase_id: str,
        output: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge canonical L3 handoff refs back into the parent L2 params/artifacts."""
        instance = await self.store.get_workflow(workflow_id)
        if not instance or not isinstance(output, dict):
            return {}

        parent_data = dict(instance.data or {})
        params = dict(parent_data.get("params", {}) or {})
        artifacts = dict(parent_data.get("artifacts", {}) or {})
        phase_outputs = dict(parent_data.get("phase_outputs", {}) or {})

        handoff_refs = dict(output.get("handoff_refs", {}) or {})
        for key in self.L3_HANDOFF_KEYS:
            value = output.get(key)
            if value is not None:
                handoff_refs.setdefault(key, value)

        for key, value in handoff_refs.items():
            params[key] = value
            artifacts[key] = value

        phase_outputs[phase_id] = output
        parent_data["params"] = params
        parent_data["artifacts"] = artifacts
        parent_data["phase_outputs"] = phase_outputs
        parent_data["last_output"] = {phase_id: output}

        await self.store.update_workflow_data(workflow_id, parent_data)
        return handoff_refs

    async def _run_l2_phase_subworkflow(
        self,
        workflow_id: str,
        phase_id: str,
        phase_info: Dict[str, Any],
    ) -> StepResult:
        """Execute an L2 phase by delegating to its explicit subworkflow."""
        parent = await self.store.get_workflow(workflow_id)
        if not parent:
            return StepResult(
                status="failed",
                step_id=phase_id,
                workflow_id=workflow_id,
                message=f"Parent workflow not found: {workflow_id}",
            )

        subworkflow_ref = phase_info.get("workflow") or phase_info.get("l3_template_id")
        if not isinstance(subworkflow_ref, str) or not subworkflow_ref.strip():
            return StepResult(
                status="failed",
                step_id=phase_id,
                workflow_id=workflow_id,
                message=f"Phase {phase_id} missing workflow ref",
            )

        parent_data = dict(parent.data or {})
        subworkflow_children = dict(parent_data.get("subworkflow_children", {}))
        child_workflow_id = subworkflow_children.get(phase_id)
        child = await self.store.get_workflow(child_workflow_id) if child_workflow_id else None

        await self._update_l2_phase(workflow_id, phase_id, status="running")

        if not child:
            requested_level = phase_info.get("level")
            child_level = self._resolve_subworkflow_level(requested_level, parent.level)
            child_data = {
                "params": dict(parent_data.get("params", {})),
                "parent_workflow_id": parent.id,
                "parent_step_id": phase_id,
                "parent_template_id": parent.template_id,
                "parent_run_id": parent_data.get("run_id"),
            }
            executor_override = parent_data.get("executor_override")
            if executor_override:
                child_data["executor_override"] = executor_override
            executor_selection_source = parent_data.get("executor_selection_source")
            if executor_selection_source:
                child_data["executor_selection_source"] = executor_selection_source
            llm_profile = parent_data.get("llm_profile") or os.getenv("LLM_PROFILE")
            if llm_profile:
                child_data["llm_profile"] = llm_profile

            child = await self.spawn_workflow(
                parent_id=workflow_id,
                level=child_level,
                template_id=subworkflow_ref,
                data=child_data,
            )

            subworkflow_children[phase_id] = child.id
            parent_data["subworkflow_children"] = subworkflow_children
            await self.store.update_workflow_data(workflow_id, parent_data)

        if child.status in (WorkflowStatus.PENDING, WorkflowStatus.RUNNING):
            await self.run_until_blocked(child.id, max_steps=20)
            child = await self.store.get_workflow(child.id)

        if not child:
            await self._update_l2_phase(workflow_id, phase_id, status="failed")
            return StepResult(
                status="failed",
                step_id=phase_id,
                workflow_id=workflow_id,
                message=f"Child workflow disappeared for phase {phase_id}",
            )

        if child.status == WorkflowStatus.COMPLETED:
            step = Step(
                id=phase_id,
                kind="subworkflow",
                config={
                    "subworkflow_ref": subworkflow_ref,
                    "subworkflow_level": phase_info.get("level"),
                    "output_map": phase_info.get("output_map", {}),
                },
            )
            backfill_output = await self._backfill_subworkflow_output(workflow_id, step, child)
            await self._update_l2_phase(
                workflow_id,
                phase_id,
                status="completed",
                extra={"last_output": backfill_output, "child_workflow_id": child.id},
            )
            return StepResult(
                status="success",
                step_id=phase_id,
                workflow_id=workflow_id,
                message=f"Phase {phase_id} completed via subworkflow {child.id}",
                output=backfill_output,
            )

        if child.status == WorkflowStatus.FAILED:
            error_message = child.data.get("error", "Child workflow failed")
            await self._update_l2_phase(
                workflow_id,
                phase_id,
                status="failed",
                extra={"error": error_message, "child_workflow_id": child.id},
            )
            return StepResult(
                status="failed",
                step_id=phase_id,
                workflow_id=workflow_id,
                message=f"Subworkflow {child.id} failed: {error_message}",
            )

        await self._update_l2_phase(
            workflow_id,
            phase_id,
            status="pending",
            extra={"child_workflow_id": child.id},
        )
        return StepResult(
            status="blocked",
            blocked_reason="subworkflow_blocked",
            step_id=phase_id,
            workflow_id=workflow_id,
            message=f"Subworkflow {child.id} waiting (status={child.status.value})",
            output={"child_workflow_id": child.id, "child_status": child.status.value},
        )

    def _get_next_pending_phase(
        self,
        instance: WorkflowInstance
    ) -> Optional[Dict[str, Any]]:
        """Get the next pending phase from an L2 instance.

        P1: Respects phase dependencies - only returns phases whose
        dependencies are all completed.

        Args:
            instance: L2 workflow instance

        Returns:
            Next pending phase dict or None if all complete
        """
        phases = instance.data.get("phases", [])

        # Build completion map
        phase_status = {}
        for phase in phases:
            phase_status[phase.get("id")] = phase.get("status")

        # Find first pending phase with all dependencies satisfied
        for phase in phases:
            if phase.get("status") == "pending":
                # Check dependencies
                depends_on = phase.get("depends_on", [])
                all_deps_complete = True
                for dep_id in depends_on:
                    if phase_status.get(dep_id) != "completed":
                        all_deps_complete = False
                        break

                if all_deps_complete:
                    return phase

        return None

    def _get_ready_phases(
        self,
        instance: WorkflowInstance
    ) -> List[Dict[str, Any]]:
        """Get all phases that are ready to execute (dependencies satisfied).

        P1: Enables parallel phase execution when dependencies allow.

        Args:
            instance: L2 workflow instance

        Returns:
            List of ready phase dicts
        """
        phases = instance.data.get("phases", [])

        # Build completion map
        phase_status = {}
        for phase in phases:
            phase_status[phase.get("id")] = phase.get("status")

        # Find all pending phases with all dependencies satisfied
        ready_phases = []
        for phase in phases:
            if phase.get("status") == "pending":
                # Check dependencies
                depends_on = phase.get("depends_on", [])
                all_deps_complete = True
                for dep_id in depends_on:
                    if phase_status.get(dep_id) != "completed":
                        all_deps_complete = False
                        break

                if all_deps_complete:
                    ready_phases.append(phase)

        return ready_phases

    def _get_failed_phase(
        self,
        instance: WorkflowInstance,
    ) -> Optional[Dict[str, Any]]:
        """Return the first failed L2 phase, if any."""
        phases = instance.data.get("phases", [])
        for phase in phases:
            if phase.get("status") == "failed":
                return phase
        return None

    async def _reconcile_l2_subworkflow_phases(
        self,
        instance: WorkflowInstance,
    ) -> WorkflowInstance:
        """Reconcile persisted L2 phase state with the latest child workflow state.

        This lets a parent L2 workflow recover when a previously failed child
        subworkflow is rerun to completion out-of-band.
        """
        if not self._is_l2_instance(instance):
            return instance

        phases = instance.data.get("phases", [])
        if not isinstance(phases, list) or not phases:
            return instance

        parent_data = dict(instance.data or {})
        subworkflow_children = parent_data.get("subworkflow_children")
        if not isinstance(subworkflow_children, dict) or not subworkflow_children:
            return instance

        mutated = False
        for phase in phases:
            if not isinstance(phase, dict):
                continue
            phase_id = phase.get("id")
            if not isinstance(phase_id, str) or not phase_id.strip():
                continue

            child_workflow_id = subworkflow_children.get(phase_id)
            if not isinstance(child_workflow_id, str) or not child_workflow_id.strip():
                continue

            child = await self.store.get_workflow(child_workflow_id)
            if not child:
                continue

            if child.status == WorkflowStatus.COMPLETED and phase.get("status") != "completed":
                step = Step(
                    id=phase_id,
                    kind="subworkflow",
                    config={
                        "subworkflow_ref": phase.get("workflow"),
                        "subworkflow_level": phase.get("level"),
                        "output_map": phase.get("output_map", {}),
                    },
                )
                backfill_output = await self._backfill_subworkflow_output(instance.id, step, child)
                await self._update_l2_phase(
                    instance.id,
                    phase_id,
                    status="completed",
                    extra={"last_output": backfill_output, "child_workflow_id": child.id},
                )
                mutated = True
                continue

            if child.status == WorkflowStatus.FAILED and phase.get("status") != "failed":
                error_message = child.data.get("error", "Child workflow failed")
                await self._update_l2_phase(
                    instance.id,
                    phase_id,
                    status="failed",
                    extra={"error": error_message, "child_workflow_id": child.id},
                )
                mutated = True

        if not mutated:
            return instance

        refreshed = await self.store.get_workflow(instance.id)
        if not refreshed:
            return instance

        refreshed_failed_phase = self._get_failed_phase(refreshed)
        refreshed_pending_phase = self._get_next_pending_phase(refreshed)
        target_status = WorkflowStatus.RUNNING
        completed_at = None
        if refreshed_failed_phase:
            target_status = WorkflowStatus.FAILED
            completed_at = datetime.now()
        elif refreshed_pending_phase is None:
            target_status = WorkflowStatus.COMPLETED
            completed_at = datetime.now()

        if refreshed.status != target_status:
            await self.store.update_workflow_status(
                refreshed.id,
                target_status,
                completed_at=completed_at,
            )
            refreshed = await self.store.get_workflow(refreshed.id) or refreshed

        return refreshed

    async def _execute_l2_phase_with_complexity(
        self,
        workflow_id: str,
        phase_id: str,
        complexity: Complexity
    ) -> StepResult:
        """Route L2 phase execution by complexity and explicit workflow refs."""
        instance = await self.store.get_workflow(workflow_id)
        phase_info = self._get_phase_info(instance, phase_id) if instance else {}
        subworkflow_ref = phase_info.get("workflow") or phase_info.get("l3_template_id")
        if isinstance(subworkflow_ref, str) and subworkflow_ref.startswith("workflow."):
            return await self._run_l2_phase_subworkflow(workflow_id, phase_id, phase_info)
        if phase_info.get("spawns_l3") is False and not subworkflow_ref:
            return await self._execute_complexity_s(workflow_id, phase_id)

        if complexity == Complexity.S:
            return await self._execute_complexity_s(workflow_id, phase_id)
        elif complexity == Complexity.M:
            return await self._execute_complexity_m(workflow_id, phase_id)
        else:  # Complexity.L
            return await self._execute_complexity_l(workflow_id, phase_id)

    async def _execute_complexity_s(
        self,
        workflow_id: str,
        phase_id: str
    ) -> StepResult:
        """Direct execution - run phase as simple workflow steps.

        For complexity=S, we execute the phase directly without spawning L3s.
        This is a simplified implementation for P0.

        Args:
            workflow_id: L2 workflow ID
            phase_id: Phase identifier

        Returns:
            StepResult indicating success/failure
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return StepResult(
                status="failed",
                step_id=phase_id,
                workflow_id=workflow_id,
                message=f"Workflow not found: {workflow_id}",
            )

        phase_info = self._get_phase_info(instance, phase_id)
        direct_output = self._build_direct_phase_output(instance.data or {}, phase_id)
        gate_id = self._resolve_direct_phase_gate_id(phase_id, phase_info)
        if gate_id:
            gate_type = str(phase_info.get("gate_type") or "").strip().lower()
            if gate_type == "auto_check":
                gate_result = await self._run_auto_check_gate_step(
                    workflow_id,
                    Step(id=phase_id, kind="gate", gate_id=gate_id, config={"gate": {"type": gate_type, "gate_id": gate_id}}),
                )
                if gate_result.status != "success":
                    return gate_result
            else:
                return await self._trigger_l2_phase_gate(
                    workflow_id=workflow_id,
                    phase_id=phase_id,
                    gate_id=gate_id,
                    output=direct_output,
                )

        await self._merge_l2_phase_outputs(workflow_id, phase_id, direct_output)
        await self._update_l2_phase(
            workflow_id,
            phase_id,
            status="completed",
            extra={"last_output": direct_output},
        )

        return StepResult(
            status="success",
            step_id=phase_id,
            workflow_id=workflow_id,
            message=f"Phase {phase_id} (complexity=S) executed directly",
            output=direct_output,
        )

    @staticmethod
    def _resolve_direct_phase_gate_id(phase_id: str, phase_info: Dict[str, Any]) -> Optional[str]:
        gate_id = phase_info.get("gate_id")
        if gate_id:
            return gate_id
        if phase_id == "merge_or_reject":
            return "gate.dev.merge_approval"
        return None

    def _build_direct_phase_output(
        self,
        workflow_data: Dict[str, Any],
        phase_id: str,
    ) -> Dict[str, Any]:
        params = dict(workflow_data.get("params", {}) or {})
        if phase_id == "smoke_gate":
            return {
                "phase_id": phase_id,
                "status": "passed",
                "evidence_pack_ref": params.get("evidence_pack_ref"),
                "smoke_gate_inputs": params.get("smoke_gate_inputs"),
            }
        if phase_id == "merge_or_reject":
            merge_input = params.get("merge_or_reject_input")
            return {
                "phase_id": phase_id,
                "status": "approved",
                "evidence_pack_ref": params.get("evidence_pack_ref"),
                "closure_summary_ref": params.get("closure_summary_ref"),
                "merge_or_reject_input": merge_input,
                "merge_decision_ref": self._derive_merge_decision_ref(merge_input),
            }
        return {"phase_id": phase_id, "status": "completed"}

    @staticmethod
    def _derive_merge_decision_ref(merge_input: Any) -> Optional[str]:
        if isinstance(merge_input, str) and merge_input:
            return merge_input
        if isinstance(merge_input, dict):
            for key in ("merge_decision_ref", "decision_ref", "ref", "id"):
                value = merge_input.get(key)
                if isinstance(value, str) and value:
                    return value
        return None

    async def _trigger_l2_phase_gate(
        self,
        *,
        workflow_id: str,
        phase_id: str,
        gate_id: str,
        output: Dict[str, Any],
    ) -> StepResult:
        from lee.orchestrator.storage.models import GateApproval, GateStatus, WorkflowStatus

        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return StepResult(
                status="failed",
                step_id=phase_id,
                workflow_id=workflow_id,
                message=f"Workflow not found: {workflow_id}",
            )

        existing_gate = await self.store.get_gate_approval(workflow_id, gate_id)
        if existing_gate and existing_gate.status == GateStatus.PENDING:
            await self._update_l2_phase(workflow_id, phase_id, status="blocked")
            return StepResult(
                status="blocked",
                blocked_reason="human_gate",
                step_id=phase_id,
                workflow_id=workflow_id,
                message=f"Waiting for human approval at gate: {gate_id}",
                output=output,
            )

        gate_approval = GateApproval(
            workflow_id=workflow_id,
            gate_id=gate_id,
            step_id=phase_id,
            status=GateStatus.PENDING,
        )
        await self.store.create_gate_approval(gate_approval)
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)

        phase_gate_outputs = dict((instance.data or {}).get("phase_gate_outputs", {}) or {})
        phase_gate_outputs[phase_id] = output
        instance.data["phase_gate_outputs"] = phase_gate_outputs
        await self.store.update_workflow_data(workflow_id, instance.data)
        await self._update_l2_phase(workflow_id, phase_id, status="blocked")
        self.event_log.log_gate_triggered(
            gate_id=gate_id,
            step_id=phase_id,
            gate_type="human",
            blocking=True,
        )
        return StepResult(
            status="blocked",
            blocked_reason="human_gate",
            step_id=phase_id,
            workflow_id=workflow_id,
            message=f"Waiting for human approval at gate: {gate_id}",
            output=output,
        )

    async def _execute_complexity_m(
        self,
        workflow_id: str,
        phase_id: str
    ) -> StepResult:
        """Spawn single L3 instance and execute.

        For complexity=M, we spawn a single L3 task for the entire phase.

        Args:
            workflow_id: L2 workflow ID
            phase_id: Phase identifier

        Returns:
            StepResult from L3 execution
        """
        # P0: Create a single point from the phase
        instance = await self.store.get_workflow(workflow_id)
        phase_info = self._get_phase_info(instance, phase_id)
        context = instance.data.get("context", {})

        # Determine repo_id based on phase
        repo_id = self._get_repo_id_for_phase(phase_id, context.get("repos", []))

        # Create single point for the entire phase
        point = Point(
            id=f"{phase_id}-single",
            title=phase_info.get("name", f"Phase {phase_id}"),
            desc=phase_info.get("description", ""),
            layer=self._get_layer_for_phase(phase_id),
            estimated_complexity=Complexity.M,
            files_hint=[],
            depends_on=[]
        )

        # Spawn L3 for this point
        l3_id = await self._spawn_l3_for_point(
            point=point,
            parent_l2_id=workflow_id,
            parent_phase_id=phase_id,
            repo_id=repo_id,
            l3_template_id=phase_info.get("l3_template_id"),
        )

        # Update phase with L3 reference
        phases = instance.data.get("phases", [])
        for phase in phases:
            if phase.get("id") == phase_id:
                phase["l3_instance_ids"] = [l3_id]
                phase["status"] = "running"
                break

        await self.store.update_workflow_data(workflow_id, instance.data)

        return StepResult(
            status="blocked",
            blocked_reason="waiting_for_l3_completion",
            step_id=phase_id,
            workflow_id=workflow_id,
            message=f"Phase {phase_id} (complexity=M) spawned L3 {l3_id}",
            output={"l3_instance_ids": [l3_id]},
        )

    async def _execute_complexity_l(
        self,
        workflow_id: str,
        phase_id: str
    ) -> StepResult:
        """Use PMA to split, spawn multiple L3 instances.

        For complexity=L, we use the PMA task splitter to divide the phase
        into multiple points, then spawn an L3 for each.

        P1: Parallel L3 spawning with asyncio.gather
        P1: Failure handling with partial success tracking

        Args:
            workflow_id: L2 workflow ID
            phase_id: Phase identifier

        Returns:
            StepResult from L3 executions
        """
        import asyncio
        from lee.orchestrator.execution.pm_agent.task_splitter import SimpleTaskSplitter

        # Get context
        instance = await self.store.get_workflow(workflow_id)
        phase_info = self._get_phase_info(instance, phase_id)
        context = instance.data.get("context", {})

        # Create splitter
        splitter = SimpleTaskSplitter(llm_executor=self.executor_factory.create("llm"))

        # Load PRD content if available
        prd_content = ""
        prd_path = context.get("prd_path", "")
        if prd_path:
            try:
                prd_full_path = Path(self.project_root) / prd_path if self.project_root else Path(prd_path)
                if prd_full_path.exists():
                    with open(prd_full_path, 'r', encoding='utf-8') as f:
                        prd_content = f.read()
            except Exception:
                pass

        # Build repo context
        repo_context = {}
        repos = context.get("repos", [])
        for repo in repos:
            if self._get_repo_id_for_phase(phase_id, [repo]) == repo.get("id"):
                repo_context = repo
                break

        # Split phase
        split_result = await splitter.split_phase(
            phase_id=phase_id,
            phase_description=phase_info.get("description", ""),
            prd_content=prd_content,
            repo_context=repo_context
        )

        # Store PMA result
        instance.data.setdefault("pma_splits", []).append({
            "phase_id": phase_id,
            "points": [p.__dict__ for p in split_result.points],
            "confidence": split_result.confidence,
            "original_estimate": split_result.original_estimate,
            "split_estimate": split_result.split_estimate,
        })
        await self.store.update_workflow_data(workflow_id, instance.data)

        # P1: Spawn L3s in parallel, respecting dependencies
        # Group points by dependency level
        point_groups = self._group_points_by_dependency(split_result.points)

        all_l3_ids = []
        all_l3_results = []
        failed_points = []

        for group in point_groups:
            # Spawn L3s in parallel within the same dependency level
            spawn_tasks = []
            for point in group:
                repo_id = self._get_repo_id_for_layer(point.layer, context.get("repos", []))
                task = self._spawn_l3_for_point(
                    point=point,
                    parent_l2_id=workflow_id,
                    parent_phase_id=phase_id,
                    repo_id=repo_id,
                    l3_template_id=phase_info.get("l3_template_id"),
                )
                spawn_tasks.append(task)

            # Parallel spawn
            group_l3_ids = await asyncio.gather(*spawn_tasks, return_exceptions=True)

            # Process results
            for i, l3_result in enumerate(group_l3_ids):
                if isinstance(l3_result, Exception):
                    failed_points.append({
                        "point": group[i].id,
                        "error": str(l3_result),
                    })
                else:
                    all_l3_ids.append(l3_result)
                    all_l3_results.append({"point": group[i].id, "l3_id": l3_result})

        # Update phase with L3 references
        phases = instance.data.get("phases", [])
        for phase in phases:
            if phase.get("id") == phase_id:
                phase["l3_instance_ids"] = all_l3_ids
                phase["l3_results"] = all_l3_results
                phase["status"] = "running" if all_l3_ids else phase.get("status", "pending")
                if failed_points:
                    phase["failed_points"] = failed_points
                break

        await self.store.update_workflow_data(workflow_id, instance.data)

        # P1: Handle failures
        if failed_points:
            # Option 1: Fail the phase if any L3 spawn failed
            # Option 2: Continue with successful L3s (P0 behavior)
            # For P1, we log and continue - can be configured later
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Phase {phase_id}: {len(failed_points)} points failed to spawn L3")

        return StepResult(
            status="blocked" if all_l3_ids else "partial_success",
            blocked_reason="waiting_for_l3_completion" if all_l3_ids else None,
            step_id=phase_id,
            workflow_id=workflow_id,
            message=f"Phase {phase_id} (complexity=L) split into {len(all_l3_ids)} L3s" +
                    (f", {len(failed_points)} failed" if failed_points else ""),
            output={
                "l3_count": len(all_l3_ids),
                "l3_results": all_l3_results,
                "failed_points": failed_points,
            },
        )

    def _group_points_by_dependency(self, points: List) -> List[List]:
        """Group points by dependency level for parallel execution.

        Args:
            points: List of Point objects

        Returns:
            List of point groups, where each group can be executed in parallel
        """
        # Build dependency graph
        point_map = {p.id: p for p in points}
        in_degree = {p.id: len(p.depends_on) for p in points}
        adj_list = {p.id: [] for p in points}

        for point in points:
            for dep in point.depends_on:
                if dep in adj_list:
                    adj_list[dep].append(point.id)

        # Topological sort with grouping
        from collections import deque
        queue = deque([pid for pid, degree in in_degree.items() if degree == 0])
        groups = []

        while queue:
            current_level = list(queue)
            groups.append([point_map[pid] for pid in current_level if pid in point_map])

            # Process next level
            next_queue = deque()
            for pid in current_level:
                for neighbor in adj_list.get(pid, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            queue = next_queue

        return groups

    async def _collect_l3_outputs(self, l3_ids: List[str]) -> Dict[str, Any]:
        """Collect outputs from completed L3 instances.

        Args:
            l3_ids: List of L3 workflow IDs

        Returns:
            Aggregated outputs dictionary
        """
        outputs = {
            "l3_count": len(l3_ids),
            "l3_outputs": {},
        }
        aggregated_handoffs: Dict[str, Any] = {}

        for l3_id in l3_ids:
            l3_instance = await self.store.get_workflow(l3_id)
            if l3_instance:
                handoff_refs = self._extract_l3_handoff_refs(l3_instance.data)
                aggregated_handoffs.update(handoff_refs)
                outputs["l3_outputs"][l3_id] = {
                    "status": l3_instance.status.value,
                    "data": l3_instance.data,
                    "handoff_refs": handoff_refs,
                }

        if aggregated_handoffs:
            outputs["handoff_refs"] = aggregated_handoffs

        return outputs

    @staticmethod
    def _extract_l3_handoff_refs(instance_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract canonical handoff refs from an L3 instance payload."""
        if not isinstance(instance_data, dict):
            return {}

        collected: Dict[str, Any] = {}
        step_outputs = instance_data.get("step_outputs", {}) or {}

        for key in Orchestrator.L3_HANDOFF_KEYS:
            if key in instance_data:
                collected[key] = instance_data[key]
                continue
            for step_payload in step_outputs.values():
                if isinstance(step_payload, dict) and key in step_payload:
                    collected[key] = step_payload[key]
                    break
        return collected

    # ============ L2/L3 Progress Tracking (P2) ============

    async def get_l2_progress(self, workflow_id: str) -> Dict[str, Any]:
        """Get progress information for an L2 workflow.

        Args:
            workflow_id: L2 workflow ID

        Returns:
            Progress dictionary with phase completion status
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance or not self._is_l2_instance(instance):
            return {
                "error": "Not an L2 workflow instance",
                "workflow_id": workflow_id,
            }

        phases = instance.data.get("phases", [])
        total_phases = len(phases)
        completed_phases = sum(1 for p in phases if p.get("status") == "completed")
        running_phases = sum(1 for p in phases if p.get("status") == "running")
        pending_phases = sum(1 for p in phases if p.get("status") == "pending")

        # Count L3 instances
        total_l3 = sum(len(p.get("l3_instance_ids", [])) for p in phases)
        completed_l3 = 0
        for phase in phases:
            for l3_id in phase.get("l3_instance_ids", []):
                l3 = await self.store.get_workflow(l3_id)
                if l3 and l3.status == WorkflowStatus.COMPLETED:
                    completed_l3 += 1

        return {
            "workflow_id": workflow_id,
            "status": instance.status.value,
            "progress_percent": int(completed_phases / total_phases * 100) if total_phases > 0 else 0,
            "phases": {
                "total": total_phases,
                "completed": completed_phases,
                "running": running_phases,
                "pending": pending_phases,
            },
            "l3_instances": {
                "total": total_l3,
                "completed": completed_l3,
                "pending": total_l3 - completed_l3,
            },
            "phase_details": [
                {
                    "id": p.get("id"),
                    "status": p.get("status"),
                    "complexity": p.get("complexity"),
                    "l3_count": len(p.get("l3_instance_ids", [])),
                }
                for p in phases
            ],
        }

    def get_phase_progress(self, workflow_id: str, phase_id: str) -> Dict[str, Any]:
        """Get progress for a specific phase within an L2 workflow.

        Args:
            workflow_id: L2 workflow ID
            phase_id: Phase identifier

        Returns:
            Phase progress dictionary
        """
        # This is a synchronous method that reads from data
        # For real-time status, use async methods
        return {
            "workflow_id": workflow_id,
            "phase_id": phase_id,
            "note": "Use get_l2_progress for detailed phase information",
        }

    # P2: Publish L2/L3 lifecycle events
    def _publish_l2_phase_started(self, workflow_id: str, phase_id: str, complexity: str) -> None:
        """Publish event when L2 phase starts."""
        try:
            get_event_bus().publish(Event(
                type=EventType.L2_PHASE_STARTED,
                payload={
                    "workflow_id": workflow_id,
                    "phase_id": phase_id,
                    "complexity": complexity,
                },
                source_workflow=workflow_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=uuid.uuid4().hex
            ))
        except Exception:
            pass  # Event publishing failure shouldn't break workflow

    def _publish_l2_phase_completed(self, workflow_id: str, phase_id: str, l3_count: int) -> None:
        """Publish event when L2 phase completes."""
        try:
            get_event_bus().publish(Event(
                type=EventType.L2_PHASE_COMPLETED,
                payload={
                    "workflow_id": workflow_id,
                    "phase_id": phase_id,
                    "l3_count": l3_count,
                },
                source_workflow=workflow_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=uuid.uuid4().hex
            ))
        except Exception:
            pass

    def _publish_l3_spawned(self, parent_l2_id: str, phase_id: str, l3_id: str, point_id: str) -> None:
        """Publish event when L3 is spawned."""
        try:
            get_event_bus().publish(Event(
                type=EventType.L3_SPAWNED,
                payload={
                    "parent_l2_id": parent_l2_id,
                    "phase_id": phase_id,
                    "l3_id": l3_id,
                    "point_id": point_id,
                },
                source_workflow=parent_l2_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=uuid.uuid4().hex
            ))
        except Exception:
            pass

    def _record_step_artifacts(
        self,
        workflow_id: str,
        step_id: str,
        output: Any,
        run_id: Optional[str] = None,
    ) -> None:
        """Record step output as artifacts.

        Args:
            workflow_id: Workflow ID
            step_id: Step ID
            output: Step output data
        """
        from lee.orchestrator.execution.artifacts import ArtifactType

        run_id = run_id or workflow_id

        # 记录文件类型产出物
        if isinstance(output, dict):
            # 检查输出中的文件路径
            # 优先匹配后缀规则，再匹配特定关键字（无标准后缀的）
            for key, value in output.items():
                if key.endswith("_file") or key.endswith("_path") or key in [
                    # 无标准后缀的关键字需要显式列出：
                    "code_diff",        # 代码差异输出
                    "test_report",      # 测试报告
                    "coverage_report",  # 覆盖率报告
                    "review_report",    # 代码审查报告
                    # 注意：patch_file, output_file 等已被 *_file 后缀覆盖，无需显式列出
                ]:
                    if isinstance(value, str) and value:
                        try:
                            # 判断产出物类型
                            artifact_type = ArtifactType.PATCH
                            if "test" in key.lower():
                                artifact_type = ArtifactType.TEST
                            elif "review" in key.lower():
                                artifact_type = ArtifactType.DOCUMENT
                            elif "contract" in key.lower():
                                artifact_type = ArtifactType.CONTRACT

                            # adopt 外部文件
                            self.artifact_manager.adopt(
                                run_id=run_id,
                                artifact_type=artifact_type,
                                file_path=value,
                                category=f"step_{step_id}",
                                metadata={"step_id": step_id, "output_key": key}
                            )
                        except Exception:
                            pass  # 文件不存在或其他错误，静默处理

            # 记录日志类型产出物（非文件输出）
            if "message" in output or "summary" in output or "result" in output:
                try:
                    import json
                    content = json.dumps(output, ensure_ascii=False, indent=2)
                    self.artifact_manager.create(
                        run_id=run_id,
                        artifact_type=ArtifactType.LOG,
                        category=f"step_{step_id}",
                        content=content.encode("utf-8"),
                        filename=f"{step_id}_output.json",
                        metadata={"step_id": step_id}
                    )
                except Exception:
                    pass

    def _publish_pma_split_completed(self, workflow_id: str, phase_id: str, point_count: int, confidence: float) -> None:
        """Publish event when PMA split completes."""
        try:
            get_event_bus().publish(Event(
                type=EventType.PMA_SPLIT_COMPLETED,
                payload={
                    "workflow_id": workflow_id,
                    "phase_id": phase_id,
                    "point_count": point_count,
                    "confidence": confidence,
                },
                source_workflow=workflow_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=uuid.uuid4().hex
            ))
        except Exception:
            pass

    def _get_repo_id_for_phase(self, phase_id: str, repos: List[Dict]) -> str:
        """Determine which repo a phase should use.

        Args:
            phase_id: Phase identifier
            repos: List of repo configs

        Returns:
            Repo ID

        Raises:
            ValueError: If repos list is empty or no matching repo found
        """
        if not repos:
            import logging
            logging.getLogger(__name__).warning(
                "No repos configured for phase %s; falling back to empty repo context",
                phase_id,
            )
            return ""

        frontend_phases = {"frontend_dev"}
        backend_phases = {
            "backend_dev",
            "api_align",
            "contract_design",
            "root_cause",
            "fix_design",
            "fix_implementation",
            "verification",
        }
        shared_phases = {"tech_design", "integration", "evidence_pack", "smoke_gate", "triage", "merge_or_reject"}

        for repo in repos:
            repo_id = repo.get("id", "")
            repo_type = repo.get("type", "")

            if phase_id in frontend_phases and repo_type == "frontend":
                return repo_id
            elif phase_id in backend_phases and repo_type == "backend":
                return repo_id
            elif phase_id in shared_phases and repo_type in {"backend", "frontend"}:
                return repo_id

        # Fallback to first repo with warning
        return repos[0].get("id", "")

    def _get_layer_for_phase(self, phase_id: str) -> str:
        """Determine the architectural layer for a phase.

        Args:
            phase_id: Phase identifier

        Returns:
            Layer string (ui, state, api, service)
        """
        layer_map = {
            "plan": "ui",
            "api_align": "api",
            "tech_design": "service",
            "contract_design": "api",
            "frontend_dev": "ui",
            "backend_dev": "service",
            "integration": "api",
            "evidence_pack": "service",
            "smoke_gate": "ui",
            "triage": "service",
            "root_cause": "service",
            "fix_design": "service",
            "fix_implementation": "service",
            "verification": "service",
            "merge_or_reject": "service",
        }
        return layer_map.get(phase_id, "ui")

    def _get_repo_id_for_layer(self, layer: str, repos: List[Dict]) -> str:
        """Map point layer to repo ID.

        Args:
            layer: Architectural layer (ui, state, api, service)
            repos: List of repo configs

        Returns:
            Repo ID

        Raises:
            ValueError: If repos list is empty or no matching repo found
        """
        if not repos:
            import logging
            logging.getLogger(__name__).warning(
                "No repos configured for layer %s; falling back to empty repo context",
                layer,
            )
            return ""

        # Map layers to repo types
        frontend_layers = {"ui", "state"}
        backend_layers = {"api", "service"}

        for repo in repos:
            repo_type = repo.get("type", "")
            if layer in frontend_layers and repo_type == "frontend":
                return repo.get("id", "")
            elif layer in backend_layers and repo_type == "backend":
                return repo.get("id", "")

        # Fallback to first repo with warning
        return repos[0].get("id", "")

    def _resolve_l3_template_path(self, l3_template_id: str) -> Path:
        """Resolve a canonical L3 template ID to an on-disk template path."""
        dev_template_roots = []
        qa_template_roots = []
        framework_root = Path(__file__).resolve().parents[4]
        if l3_template_id.startswith("workflow."):
            spec_roots = []
            if self.project_root:
                project_root_path = Path(self.project_root)
                spec_roots.extend([project_root_path / "lee" / "spec-global", project_root_path / "spec-global"])
            else:
                spec_roots.extend([Path("lee/spec-global"), Path("spec-global")])
            spec_roots.append(framework_root / "spec-global")
            for spec_root in spec_roots:
                if not spec_root.exists():
                    continue
                for candidate in spec_root.rglob("workflow.yaml"):
                    try:
                        for line in candidate.read_text(encoding="utf-8").splitlines():
                            stripped = line.strip()
                            if stripped.startswith("id:") and stripped[3:].strip().strip("'\"") == l3_template_id:
                                return candidate
                    except Exception:
                        continue
            raise FileNotFoundError(f"Workflow template not found: {l3_template_id}")
        if self.project_root:
            project_root_path = Path(self.project_root)
            dev_template_roots.extend([
                project_root_path / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "templates",
                project_root_path / "spec-global" / "departments" / "dev" / "workflows" / "templates",
            ])
            qa_template_roots.extend([
                project_root_path / "lee" / "spec-global" / "departments" / "qa" / "workflows" / "templates",
                project_root_path / "spec-global" / "departments" / "qa" / "workflows" / "templates",
            ])
        else:
            dev_template_roots.extend([
                Path("lee/spec-global/departments/dev/workflows/templates"),
                Path("spec-global/departments/dev/workflows/templates"),
            ])
            qa_template_roots.extend([
                Path("lee/spec-global/departments/qa/workflows/templates"),
                Path("spec-global/departments/qa/workflows/templates"),
            ])
        dev_template_roots.extend([
            framework_root / "spec-global" / "departments" / "dev" / "workflows" / "templates",
        ])
        qa_template_roots.extend([
            framework_root / "spec-global" / "departments" / "qa" / "workflows" / "templates",
        ])

        template_file_map = {
            "template.dev.task_l3_v3": ("dev", "l3/task-l3-v3-template.yaml"),
            "template.dev.tech_design_l3": ("dev", "tech-design-l3-template.yaml"),
            "template.dev.feature_contract_l3": ("dev", "feature-contract-l3-template.yaml"),
            "template.dev.feature_fe_l3": ("dev", "feature-fe-l3-template.yaml"),
            "template.dev.feature_be_l3": ("dev", "feature-be-l3-template.yaml"),
            "template.dev.feature_integration_l3": ("dev", "feature-integration-l3-template.yaml"),
            "template.dev.evidence_pack_l3": ("dev", "evidence-pack-l3-template.yaml"),
            "template.dev.bugfix_triage_l3": ("dev", "bugfix-triage-l3-template.yaml"),
            "template.dev.bugfix_root_cause_l3": ("dev", "bugfix-root-cause-l3-template.yaml"),
            "template.dev.bugfix_fix_design_l3": ("dev", "bugfix-fix-design-l3-template.yaml"),
            "template.dev.bugfix_fix_impl_l3": ("dev", "bugfix-fix-impl-l3-template.yaml"),
            "template.dev.bugfix_verification_l3": ("dev", "bugfix-verification-l3-template.yaml"),
            "template.dev.bugfix_evidence_pack_l3": ("dev", "bugfix-evidence-pack-l3-template.yaml"),
            "template.qa.test_set_execute": ("qa", "test-set-execute-l3-template.yaml"),
            "template.qa.test_set_production": ("qa", "test-set-production-l3-template.yaml"),
        }
        template_spec = template_file_map.get(l3_template_id)
        if template_spec is None:
            raise FileNotFoundError(f"Unsupported L3 template ID: {l3_template_id}")
        domain, relative_path = template_spec
        template_roots = qa_template_roots if domain == "qa" else dev_template_roots

        for template_root in template_roots:
            candidate = template_root / relative_path
            if candidate.exists():
                return candidate

        search_roots = ", ".join(str(root / relative_path) for root in template_roots)
        raise FileNotFoundError(f"L3 template {l3_template_id} not found under: {search_roots}")

    async def _spawn_l3_for_point(
        self,
        point: Point,
        parent_l2_id: str,
        parent_phase_id: str,
        repo_id: str,
        l3_template_id: Optional[str] = None,
    ) -> str:
        """Generate and spawn an L3 instance for one point."""
        from lee.orchestrator.core.workflow_generator import WorkflowGenerator, L3InstanceConfig

        parent = await self.store.get_workflow(parent_l2_id)
        if parent is None:
            raise ValueError(f"Parent L2 workflow not found: {parent_l2_id}")
        context = parent.data.get("context", {})
        parent_params = dict(parent.data.get("params", {}) or {})
        parent_artifacts = dict(parent.data.get("artifacts", {}) or {})
        config = L3InstanceConfig(
            point=point,
            parent_l2_id=parent_l2_id,
            parent_phase_id=parent_phase_id,
            repo_id=repo_id,
            prd_path=context.get("prd_path", ""),
            template_id=l3_template_id or "template.dev.task_l3_v3",
            metadata={
                "params": dict(parent_params),
                "artifacts": dict(parent_artifacts),
            },
        )

        l3_template_id = config.template_id
        l3_template_path = self._resolve_l3_template_path(l3_template_id)
        generator = WorkflowGenerator(template_path=str(l3_template_path))
        from lee.orchestrator.core.path_policy import TOOL_DIRECTORIES
        workflow_dir = next(d for d in TOOL_DIRECTORIES if d == ".workflow")
        runtime_dir = Path(self.project_root) / workflow_dir if self.project_root else Path(workflow_dir)
        l3_path = runtime_dir / "instances" / "l3" / f"{point.id}.yaml"
        result = generator.generate_l3_instance(config, str(l3_path))

        if not result.success:
            raise RuntimeError(f"Failed to generate L3 instance: {result.errors}")

        l3_params = dict(parent_params)
        if "test_run_id" not in l3_params:
            parent_run_id = parent.data.get("run_id", "")
            if parent_run_id.startswith("RUN-"):
                l3_params["test_run_id"] = parent_run_id.replace("RUN-", "TR-", 1)
            else:
                from datetime import datetime
                now = datetime.now()
                l3_params["test_run_id"] = f"TR-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"

        l3_instance = await self.spawn_workflow(
            parent_id=parent_l2_id,
            level=WorkflowLevel.TASK,
            template_id=l3_template_id,
            data={
                "kind": "l3_workflow_instance",
                "params": l3_params,
                "artifacts": dict(parent_artifacts),
                "point_id": point.id,
                "point_title": point.title,
                "point_desc": point.desc,
                "point_layer": point.layer,
                "point_complexity": point.estimated_complexity.value,
                "parent_phase_id": parent_phase_id,
                "parent_l2_id": parent_l2_id,
                "repo_id": repo_id,
                "l3_template_id": l3_template_id,
                "step_index": 0,
            }
        )
        self._publish_l3_spawned(parent_l2_id, parent_phase_id, l3_instance.id, point.id)
        return l3_instance.id

    async def _wait_for_l3_completion(self, l3_ids: List[str]) -> None:
        """Wait for all L3 instances to complete or fail."""
        max_wait_seconds = 3600
        check_interval = 10

        import asyncio
        start_time = asyncio.get_event_loop().time()

        while True:
            all_done = True
            for l3_id in l3_ids:
                l3 = await self.store.get_workflow(l3_id)
                if l3 is None or l3.status not in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
                    all_done = False
                    break

            if all_done:
                break

            if asyncio.get_event_loop().time() - start_time > max_wait_seconds:
                raise TimeoutError(f"L3 completion timeout after {max_wait_seconds}s")

            await asyncio.sleep(check_interval)
    L3_HANDOFF_KEYS = (
        "tech_spec_ref",
        "decision_refs",
        "api_contract_ref",
        "data_contract_ref",
        "event_contract_ref",
        "contract_review_ref",
        "contract_freeze_ref",
        "contract_hash",
        "be_artifact_ref",
        "fe_artifact_ref",
        "integration_outputs",
        "verification_results",
        "integration_report_ref",
        "evidence_pack_ref",
        "smoke_gate_inputs",
        "merge_or_reject_input",
        "triage_decision_ref",
        "granularity_decision_ref",
        "batch_approval_record",
        "root_cause_ref",
        "affected_scope_ref",
        "verification_scope_ref",
        "rollback_strategy_ref",
        "fix_design_ref",
        "fix_artifact_ref",
        "verification_report_ref",
        "closure_summary_ref",
        "merge_decision_ref",
    )
