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
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from lee.orchestrator.storage.models import (
    WorkflowLevel,
    WorkflowStatus,
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
    ):
        """
        初始化 Orchestrator

        Args:
            store: SQLite 存储层
            template_manager: 模板管理器（可选）
            project_root: 项目根目录（用于文件路径解析）
        """
        self.store = store
        self.db = store  # 兼容 Runners 的 db 属性
        self.state_machine = WorkflowStateMachine(store)
        self.template_manager = template_manager or TemplateManager()
        self.executor_factory = ExecutorFactory

        # v1.5: 创建 AgentLoader 用于加载 agent spec
        # spec_root 默认为 {project_root}/lee/spec-global
        spec_root = str(Path(project_root) / "lee" / "spec-global") if project_root else None
        agent_loader = AgentLoader(project_root or ".", spec_root=spec_root)

        # v1.4 新增组件
        self.agent_context_builder = AgentContextBuilder(
            agent_loader=agent_loader,
            project_root=project_root
        )
        self.file_output_handler = FileOutputHandler(
            project_root=project_root
        )
        self.evidence_collector = EvidenceCollector(project_root or ".")
        self.verifier_engine = VerifierEngine(project_root or ".")
        self.project_root = project_root

        # v3.1: P1 功能集成
        self.contract_discovery = ContractDiscovery(project_root or ".")
        self.token_manager = TokenManager(project_root or ".")
        self.tool_guard = ToolGuard(self.token_manager)
        self.gate_engine = GateEngine()

        # v3.2: EventLog 事件日志
        self.event_log = EventLog(project_root or ".", run_id=None)

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
        if instance.status == WorkflowStatus.PENDING:
            await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)
            instance = await self.store.get_workflow(workflow_id)  # 刷新实例状态

        # 获取可执行步骤
        ready_steps = await self.get_ready_steps(workflow_id)

        if not ready_steps:
            return StepResult(
                status="no_ready_step",
                step_id=None,
                workflow_id=workflow_id,
                message="No ready steps available",
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

        # v3.2: 记录步骤开始事件
        self.event_log.run_id = instance.data.get("run_id", workflow_id)
        self.event_log.log_step_started(
            step_id=step_to_execute.id,
            agent_id=getattr(step_to_execute, 'agent_id', None) or step_to_execute.kind,
        )

        # 根据 step.kind 分支处理（v1.4）
        # v1.5: 新增 orchestrator_cli 和 compliance_gate 类型
        try:
            if step_to_execute.kind in ("workflow_spawn", "subworkflow"):
                # 子工作流步骤：由 orchestrator 负责编排执行
                return await self._run_subworkflow_step(workflow_id, step_to_execute)

            elif step_to_execute.kind == "human_gate":
                # Human Gate：不调用 Executor，直接暂停等待人工审批
                return await self._handle_human_gate(workflow_id, step_to_execute)

            elif step_to_execute.kind == "orchestrator_cli":
                # Orchestrator CLI：直接由 Python 执行，AI 无法干预
                return await self._run_orchestrator_cli_step(workflow_id, step_to_execute)

            elif step_to_execute.kind == "compliance_gate":
                # 合规门禁：检查 AI 行为是否违规
                return await self._run_compliance_gate_step(workflow_id, step_to_execute)

            elif step_to_execute.kind == "agent":
                # v3.3: Claude Code executor — 多轮闭环执行
                if step_to_execute.executor_type == "claude_code":
                    return await self._run_claude_code_step(workflow_id, step_to_execute)
                # Agent 步骤：调用 LLM Executor
                return await self._run_agent_step(workflow_id, step_to_execute)

            elif step_to_execute.kind == "skill":
                # Skill 步骤：调用对应 Executor（Shell/MCP 等）
                return await self._run_skill_step(workflow_id, step_to_execute)

            else:
                # 其他类型：保持原有逻辑
                executor = self.executor_factory.create(step_to_execute.executor_type or "llm")
                input_data = step_to_execute.input or {}
                output = await executor.execute(input_data)

                # 完成步骤
                result = await self.state_machine.complete_step(
                    workflow_id,
                    step_to_execute.id,
                    output
                )

                # 检查工作流是否完成
                await self._check_workflow_completion(workflow_id)

                return result

        except Exception as e:
            # 步骤失败
            await self.state_machine.fail_step(workflow_id, step_to_execute.id, str(e))
            # v3.2: 记录步骤失败事件
            self.event_log.log_step_failed(
                step_id=step_to_execute.id,
                agent_id=getattr(step_to_execute, 'agent_id', None) or step_to_execute.kind,
                error=str(e),
            )
            return StepResult(
                status="failed",
                step_id=step_to_execute.id,
                workflow_id=workflow_id,
                message=f"Step execution failed: {e}",
            )

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
