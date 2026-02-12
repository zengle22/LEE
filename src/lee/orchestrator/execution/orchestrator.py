"""
LEE Orchestrator v3.0 - 核心调度器

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
"""

import uuid
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from lee.orchestrator.storage.models import (
    WorkflowLevel,
    WorkflowStatus,
    WorkflowInstance,
    TaskExecution,
    TaskExecutionStatus,
    Step,
    WorkflowState,
    StepResult,
    ExecutionSummary,
    GateInfo,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.state_machine import WorkflowStateMachine, StateTransition
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.execution.executors import ExecutorFactory
from lee.orchestrator.execution.agent_context_builder import AgentContextBuilder
from lee.orchestrator.execution.agent_loader import AgentLoader
from lee.orchestrator.execution.file_output_handler import FileOutputHandler
from lee.orchestrator.evidence_collector import EvidenceCollector
from lee.orchestrator.verifier_engine import VerifierEngine

# v3.1: 注册 LangGraph 执行器，支持 executor: langgraph
from lee.orchestrator.execution.langgraph_executor import register_langgraph_executor
register_langgraph_executor()


# ========================================================================
# 核心调度器（Orchestrator）
# ========================================================================

class Orchestrator:
    """
    LEE Orchestrator v3.0 - 核心调度器

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
            return StepResult(
                status="failed",
                step_id=step_to_execute.id,
                workflow_id=workflow_id,
                message=f"Step execution failed: {e}",
            )

    async def _handle_human_gate(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        处理 Human Gate 步骤

        Human Gate 不调用 Executor，而是暂停工作流等待人工审批。
        """
        from lee.orchestrator.storage.models import WorkflowStatus, GateApproval, GateStatus

        # 暂停工作流
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)

        # 提取 gate 配置（从独立 gate 或 post_gate）
        gate_config = step.config.get("gate", {})
        if not gate_config and hasattr(step, 'gate_id'):
            # 从 workflow.yaml 的 gate 节点获取配置
            gate_config = {
                "id": step.gate_id,
                "reviewers": step.config.get("reviewers", []),
                "approval_criteria": step.config.get("approval_criteria", []),
            }

        # 创建门禁审批记录
        gate_approval = GateApproval(
            workflow_id=workflow_id,
            gate_id=step.gate_id or f"gate_{step.id}",
            step_id=step.id,
            status=GateStatus.PENDING,
            approval_criteria=gate_config.get("approval_criteria", []),
            reviewers=gate_config.get("reviewers", []),
        )
        await self.store.create_gate_approval(gate_approval)

        return StepResult(
            status="blocked",
            blocked_reason="human_gate",
            step_id=step.id,
            workflow_id=workflow_id,
            message=f"Waiting for human approval at gate: {step.gate_id or step.id}",
            next_steps=[],
        )

    async def _run_subworkflow_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行子工作流步骤（workflow_spawn/subworkflow）。

        语义：
        1. 首次执行时创建子工作流实例
        2. 驱动子工作流执行到阻塞点
        3. 子工作流完成后，结构化回填输出到父工作流 data
        """
        parent = await self.store.get_workflow(workflow_id)
        if not parent:
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Parent workflow not found: {workflow_id}",
            )

        subworkflow_ref, requested_level = self._resolve_subworkflow_ref(step)
        if not subworkflow_ref:
            await self.state_machine.fail_step(workflow_id, step.id, "Missing subworkflow ref")
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Step {step.id} missing subworkflow ref",
            )

        parent_data = dict(parent.data or {})
        subworkflow_children = dict(parent_data.get("subworkflow_children", {}))

        child_workflow_id = subworkflow_children.get(step.id)
        child = await self.store.get_workflow(child_workflow_id) if child_workflow_id else None

        # 子流程不存在时创建
        if not child:
            child_level = self._resolve_subworkflow_level(requested_level, parent.level)
            child_data = self._build_subworkflow_input_data(parent, step)

            child = await self.spawn_workflow(
                parent_id=workflow_id,
                level=child_level,
                template_id=subworkflow_ref,
                data=child_data,
            )

            subworkflow_children[step.id] = child.id
            parent_data["subworkflow_children"] = subworkflow_children
            await self.store.update_workflow_data(workflow_id, parent_data)

        # 驱动子流程执行（直到阻塞）
        if child.status in (WorkflowStatus.PENDING, WorkflowStatus.RUNNING):
            max_steps = 20
            if step.config and isinstance(step.config.get("subworkflow_max_steps"), int):
                max_steps = step.config.get("subworkflow_max_steps")
            await self.run_until_blocked(child.id, max_steps=max_steps)
            child = await self.store.get_workflow(child.id)

        if not child:
            await self.state_machine.fail_step(workflow_id, step.id, "Child workflow disappeared")
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Child workflow disappeared for step {step.id}",
            )

        if child.status == WorkflowStatus.COMPLETED:
            backfill_output = await self._backfill_subworkflow_output(workflow_id, step, child)
            await self.state_machine.complete_step(workflow_id, step.id, backfill_output)
            await self._check_workflow_completion(workflow_id)
            return StepResult(
                status="success",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Subworkflow {child.id} completed",
                output=backfill_output,
            )

        if child.status == WorkflowStatus.FAILED:
            error_message = child.data.get("error", "Child workflow failed")
            await self.state_machine.fail_step(workflow_id, step.id, str(error_message))
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Subworkflow {child.id} failed: {error_message}",
            )

        # 子流程仍阻塞/暂停，父步骤保持阻塞状态（不完成）
        return StepResult(
            status="blocked",
            blocked_reason="subworkflow_blocked",
            step_id=step.id,
            workflow_id=workflow_id,
            message=f"Subworkflow {child.id} waiting (status={child.status.value})",
            output={
                "child_workflow_id": child.id,
                "child_status": child.status.value,
            },
        )

    async def _run_agent_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行 Agent 步骤

        v1.5: 添加 task_execution 记录
        v1.4: 从 agent spec 加载 prompt，执行后处理输出文件
        """
        from lee.orchestrator.storage.models import TaskExecution, TaskExecutionStatus
        import uuid
        from datetime import datetime

        # 获取工作流上下文
        instance = await self.store.get_workflow(workflow_id)
        workflow_context = {
            "workflow_id": workflow_id,
            "project_name": instance.data.get("project_name", "ai-marathon-coach"),
            "data": instance.data,
        }

        # 1. 构建 Agent 执行上下文（包含 prompt）
        ctx = await self.agent_context_builder.build(step, workflow_context)

        # 2. 调用 LLM Executor
        # 默认使用环境变量 LLM_PROFILE 或 zhipu
        executor = self.executor_factory.create(
            step.executor_type or "llm",
            profile=os.getenv("LLM_PROFILE", "zhipu"),
            agent_id=step.agent_id or ""
        )

        # 构建输入数据（包含 system_message 和 prompt）
        input_data = {
            "system_message": ctx.system_prompt,
            "prompt": ctx.user_prompt,
            "temperature": ctx.temperature,
            "max_tokens": ctx.max_tokens,
        }

        # 创建 task_execution 记录
        execution_id = uuid.uuid4().hex
        execution = TaskExecution(
            id=execution_id,
            workflow_id=workflow_id,
            step_name=step.id,
            executor_type=step.executor_type or "llm",
            input_data=input_data,
            status=TaskExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
        await self.store.create_task_execution(execution)

        try:
            llm_output = await executor.execute(input_data)

            # 检查 LLM 调用是否成功
            if llm_output.get("status") == "failed":
                # LLM 调用失败
                error_msg = llm_output.get("error", "Unknown error")
                await self.state_machine.fail_step(workflow_id, step.id, error_msg)
                await self.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message=error_msg,
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"LLM execution failed: {error_msg}",
                )

            generated_text = llm_output.get("generated_text", "")

            # 检查是否生成了内容
            if not generated_text or not generated_text.strip():
                await self.state_machine.fail_step(workflow_id, step.id, "LLM returned empty response")
                await self.store.update_task_execution(
                    execution_id,
                    TaskExecutionStatus.FAILED,
                    error_message="LLM returned empty response",
                    completed_at=datetime.now()
                )
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="LLM returned empty response",
                )

            # 3. 处理输出文件
            written_files = []
            if step.outputs:
                try:
                    written_files = await self.file_output_handler.handle(
                        generated_text,
                        step.outputs,
                        workflow_context
                    )
                except Exception as e:
                    # 输出处理失败，记录但不终止步骤
                    print(f"[FileOutputHandler] Warning: {e}")
            if written_files:
                await self._collect_evidence(workflow_id, step.id, written_files)

            # 4. Verifiers (if configured)
            verifier_results = await self._run_verifiers(workflow_id, step)
            if verifier_results is not None and not self._verifiers_passed(verifier_results):
                await self.state_machine.fail_step(workflow_id, step.id, "Verifier failed")
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="Verifier failed",
                    output={"verifiers": [r.__dict__ for r in verifier_results]},
                )

            # 5. 完成步骤
            output_data = {
                "generated_text": generated_text,
                "written_files": written_files,
                "agent_id": step.agent_id,
            }

            result = await self.state_machine.complete_step(
                workflow_id,
                step.id,
                output_data
            )

            # 更新 task_execution 记录
            await self.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.COMPLETED,
                output_data=output_data,
                completed_at=datetime.now()
            )

            # 检查工作流是否完成
            await self._check_workflow_completion(workflow_id)

            # 返回结果，包含写入的文件信息
            if written_files:
                result.message = f"Step {step.id} completed. Files written: {', '.join(written_files)}"
            else:
                result.message = f"Step {step.id} completed. No files written (outputs may be empty)"

            return result

        except Exception as e:
            # 捕获未预期的异常
            await self.state_machine.fail_step(workflow_id, step.id, str(e))
            await self.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.FAILED,
                error_message=str(e),
                completed_at=datetime.now()
            )
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Unexpected error: {e}",
            )

        return result

    async def _run_orchestrator_cli_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行 Orchestrator CLI 步骤

        由 Orchestrator 直接执行，AI 无法干预。
        用于环境探测、证据收集等安全敏感操作。
        """
        from lee.orchestrator.tools.check_env import run_check_env

        # 获取工作流上下文
        instance = await self.store.get_workflow(workflow_id)
        workflow_context = {
            "workflow_id": workflow_id,
            "data": instance.data if instance else {},
        }

        # 获取步骤配置
        step_config = step.config or {}
        run_command = getattr(step, "run", None) or step_config.get("run", "")

        try:
            if run_command == "check_env":
                # 环境检查
                checks = []
                inputs = step.input or []
                for inp in inputs:
                    if isinstance(inp, dict) and "checks" in inp:
                        checks = inp["checks"]
                        break

                # 构建输出路径
                run_id = instance.data.get("run_id", "RUN-UNKNOWN") if instance else "RUN-UNKNOWN"
                output_path = str(Path(self.project_root or ".") / f".workflow/env-check/{run_id}-{step.id}.json")

                # 执行检查
                result = run_check_env(checks, output_path)

                output_data = {
                    "all_passed": result.all_passed,
                    "failures": result.failures,
                    "output_path": output_path,
                    "source": "orchestrator",  # 标记来源为 orchestrator
                }

                # 完成步骤
                step_result = await self.state_machine.complete_step(
                    workflow_id,
                    step.id,
                    output_data
                )

                # 收集证据
                await self._collect_evidence(workflow_id, step.id, [output_path])

                # 检查是否通过
                if not result.all_passed:
                    step_result.message = f"Environment check failed: {', '.join(result.failures)}"

                return step_result

            else:
                # 未知的 orchestrator CLI 命令
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=f"Unknown orchestrator CLI command: {run_command}",
                )

        except Exception as e:
            await self.state_machine.fail_step(workflow_id, step.id, str(e))
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Orchestrator CLI execution failed: {e}",
            )

    async def _run_compliance_gate_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行合规门禁步骤

        检查 AI 行为是否违规（mock/借口等）。
        违规 → 本轮测试无效。
        """
        from lee.orchestrator.verifiers.behavior_compliance import BehaviorComplianceVerifier

        # 获取工作流上下文
        instance = await self.store.get_workflow(workflow_id)

        # 获取输入数据
        inputs = step.input or []
        runner_output = {}
        confirmed_env_errors = []

        for inp in inputs:
            if isinstance(inp, dict):
                if "runner_output" in inp:
                    runner_output = inp["runner_output"]
                if "confirmed_env_errors" in inp:
                    confirmed_env_errors = inp["confirmed_env_errors"]

        # 执行合规检查
        verifier = BehaviorComplianceVerifier()
        context = {
            "runner_output": runner_output,
            "confirmed_env_errors": confirmed_env_errors,
            "config": step.config.get("config", {}) if step.config else {},
        }
        result = verifier.verify(context)

        # 保存检查结果
        run_id = instance.data.get("run_id", "RUN-UNKNOWN") if instance else "RUN-UNKNOWN"
        output_path = Path(self.project_root or ".") / f".workflow/compliance/{run_id}-{step.id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps({
            "status": result.status.value,
            "message": result.message,
            "details": result.details,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        output_data = {
            "compliant": result.status.value == "passed",
            "violations": result.details.get("violations", []) if result.details else [],
            "output_path": str(output_path),
        }

        if result.status.value == "passed":
            # 合规通过
            step_result = await self.state_machine.complete_step(
                workflow_id,
                step.id,
                output_data
            )
            return step_result
        else:
            # 合规失败 → 标记为 invalid_run
            await self.state_machine.fail_step(workflow_id, step.id, result.message)
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"AI behavior violation detected: {result.message}",
                output=output_data,
            )

    async def _run_skill_step(
        self,
        workflow_id: str,
        step
    ) -> StepResult:
        """
        运行 Skill 步骤

        v1.5: 添加 task_execution 记录
        v1.4: 从 inputs.params 和 config.execution 构建命令
        """
        from lee.orchestrator.storage.models import TaskExecution, TaskExecutionStatus
        import uuid
        from datetime import datetime

        # 构建输入数据
        # 优先使用 input.params；否则使用 input 本身
        raw_input = step.input if step.input else {}
        if isinstance(raw_input, dict):
            params = raw_input.get("params", raw_input)
        elif isinstance(raw_input, list):
            params = {}
            for item in raw_input:
                if isinstance(item, dict):
                    params.update(item)
        else:
            params = {}

        execution_config = step.config.get("execution", {}) if step.config else {}

        # 合并配置
        input_data = {**params, **execution_config}

        demo_mode = self._demo_mode_enabled()
        used_fallback_command = False

        # 创建 task_execution 记录
        execution_id = uuid.uuid4().hex
        execution = TaskExecution(
            id=execution_id,
            workflow_id=workflow_id,
            step_name=step.id,
            executor_type=step.executor_type or "shell",
            input_data=input_data,
            status=TaskExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )
        await self.store.create_task_execution(execution)

        try:
            # 根据配置构建命令
            if "commands" in input_data:
                # 多命令执行（如 dev/test 分别执行）
                results = []
                for env, command in input_data["commands"].items():
                    command_input = {
                        "command": command,
                        "timeout": input_data.get("timeout", 600),
                    }
                    result = await self.executor_factory.create("shell").execute(command_input)
                    results.append(result)

                # 合并结果
                combined_output = "\n".join([
                    f"=== {env} ===\n{r.get('stdout', '')}" for r in results
                ])
                output = {"stdout": combined_output, "status": "completed"}
            else:
                # 单命令执行
                if "command" not in input_data:
                    # 缺少命令时的兜底（保持流程可运行）
                    input_data["command"] = "true"
                    used_fallback_command = True
                executor = self.executor_factory.create(step.executor_type or "shell")
                output = await executor.execute(input_data)

            # Demo/兜底模式：确保输出产物存在
            if demo_mode or used_fallback_command:
                self._ensure_output_artifacts(step.outputs)

            # Verifiers (if configured)
            verifier_results = await self._run_verifiers(workflow_id, step)
            if verifier_results is not None and not self._verifiers_passed(verifier_results):
                await self.state_machine.fail_step(workflow_id, step.id, "Verifier failed")
                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message="Verifier failed",
                    output={"verifiers": [r.__dict__ for r in verifier_results]},
                )

            # 完成步骤
            result = await self.state_machine.complete_step(
                workflow_id,
                step.id,
                output
            )

            # 收集证据（基于 outputs 规格）
            evidence_paths = self._resolve_output_paths(step.outputs)
            if evidence_paths:
                await self._collect_evidence(workflow_id, step.id, evidence_paths)

            # 更新 task_execution 记录
            await self.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.COMPLETED,
                output_data=output,
                completed_at=datetime.now()
            )

            # 检查工作流是否完成
            await self._check_workflow_completion(workflow_id)

            return result

        except Exception as e:
            # 捕获未预期的异常
            await self.state_machine.fail_step(workflow_id, step.id, str(e))
            await self.store.update_task_execution(
                execution_id,
                TaskExecutionStatus.FAILED,
                error_message=str(e),
                completed_at=datetime.now()
            )
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Unexpected error: {e}",
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

    # ============ Gate API ============

    async def approve_gate(
        self,
        workflow_id: str,
        gate_id: str,
        approver: str,
        comments: str = ""
    ) -> StepResult:
        """
        批准人工门禁，恢复工作流执行

        Args:
            workflow_id: 工作流 ID
            gate_id: 门禁 ID
            approver: 审批人
            comments: 审批意见

        Returns:
            步骤执行结果
        """
        from lee.orchestrator.storage.models import GateStatus, WorkflowStatus

        # 更新门禁审批状态
        gate_approval = await self.store.update_gate_approval(
            workflow_id,
            gate_id,
            GateStatus.APPROVED,
            approver,
            comments
        )

        # 恢复工作流状态
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

        # 完成门禁步骤
        result = await self.state_machine.complete_step(
            workflow_id,
            gate_approval.step_id,
            {"gate_approved": True, "approver": approver, "comments": comments}
        )

        # 检查工作流是否完成
        await self._check_workflow_completion(workflow_id)

        return StepResult(
            status="success",
            step_id=gate_approval.step_id,
            workflow_id=workflow_id,
            message=f"Gate {gate_id} approved by {approver}",
            output={"gate_approved": True, "approver": approver},
        )

    async def reject_gate(
        self,
        workflow_id: str,
        gate_id: str,
        rejecter: str,
        reason: str
    ) -> StepResult:
        """
        拒绝人工门禁，终止工作流

        Args:
            workflow_id: 工作流 ID
            gate_id: 门禁 ID
            rejecter: 拒绝人
            reason: 拒绝原因

        Returns:
            步骤执行结果
        """
        from lee.orchestrator.storage.models import GateStatus, WorkflowStatus

        # 更新门禁审批状态
        gate_approval = await self.store.update_gate_approval(
            workflow_id,
            gate_id,
            GateStatus.REJECTED,
            rejecter,
            reason
        )

        # 将工作流标记为失败
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.FAILED)

        return StepResult(
            status="failed",
            step_id=gate_approval.step_id,
            workflow_id=workflow_id,
            message=f"Gate {gate_id} rejected by {rejecter}: {reason}",
        )

    async def get_pending_gates(
        self,
        workflow_id: str
    ) -> List:
        """
        获取工作流的待审批门禁列表

        Args:
            workflow_id: 工作流 ID

        Returns:
            待审批门禁列表
        """
        from lee.orchestrator.storage.models import GateInfo

        gate_approvals = await self.store.get_pending_gates(workflow_id)

        return [
            GateInfo(
                gate_id=g.gate_id,
                workflow_id=g.workflow_id,
                step_id=g.step_id,
                status=g.status,
                reviewers=g.reviewers,
                approval_criteria=g.approval_criteria,
                approver=g.approver,
                comments=g.comments,
                created_at=g.created_at,
                decided_at=g.decided_at,
            )
            for g in gate_approvals
        ]

    # ============ 辅助方法 ============

    def _resolve_subworkflow_ref(self, step) -> Tuple[Optional[str], Optional[str]]:
        """从步骤配置中解析子工作流引用与层级。"""
        config = step.config or {}

        subworkflow_ref = config.get("subworkflow_ref")
        subworkflow_level = config.get("subworkflow_level")

        subworkflow_cfg = config.get("subworkflow")
        if isinstance(subworkflow_cfg, dict):
            if not subworkflow_ref:
                subworkflow_ref = subworkflow_cfg.get("ref") or subworkflow_cfg.get("id")
            if not subworkflow_level:
                subworkflow_level = subworkflow_cfg.get("level")
        elif isinstance(subworkflow_cfg, str) and not subworkflow_ref:
            subworkflow_ref = subworkflow_cfg

        if not subworkflow_ref and isinstance(config.get("workflow"), str):
            subworkflow_ref = config.get("workflow")

        run_ref = config.get("run")
        if not subworkflow_ref and isinstance(run_ref, str) and run_ref.startswith("workflow."):
            subworkflow_ref = run_ref

        return subworkflow_ref, subworkflow_level

    def _resolve_subworkflow_level(
        self,
        requested_level: Optional[str],
        parent_level: WorkflowLevel,
    ) -> WorkflowLevel:
        """将配置层级字符串映射到 WorkflowLevel。"""
        if requested_level:
            normalized = str(requested_level).strip().lower()
            level_map = {
                "project": WorkflowLevel.PROJECT,
                "department": WorkflowLevel.DEPARTMENT,
                "task": WorkflowLevel.TASK,
                "l1": WorkflowLevel.PROJECT,
                "l2": WorkflowLevel.DEPARTMENT,
                "l3": WorkflowLevel.TASK,
            }
            if normalized in level_map:
                return level_map[normalized]

        if parent_level == WorkflowLevel.PROJECT:
            return WorkflowLevel.DEPARTMENT
        if parent_level == WorkflowLevel.DEPARTMENT:
            return WorkflowLevel.TASK
        return WorkflowLevel.TASK

    def _build_subworkflow_input_data(self, parent, step) -> Dict[str, Any]:
        """构造子工作流初始化数据。"""
        input_map = (step.config or {}).get("input_map")

        normalized_input: Dict[str, Any]
        if isinstance(input_map, dict):
            normalized_input = {
                str(key): self._resolve_input_reference(value, parent.data)
                for key, value in input_map.items()
            }
        else:
            raw_input = step.input or {}
            if isinstance(raw_input, dict):
                normalized_input = {
                    key: self._resolve_input_reference(value, parent.data)
                    for key, value in raw_input.items()
                }
            elif isinstance(raw_input, list):
                normalized_input = {}
                for item in raw_input:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            normalized_input[key] = self._resolve_input_reference(value, parent.data)
            else:
                normalized_input = {"input": self._resolve_input_reference(raw_input, parent.data)}

        return {
            "params": normalized_input,
            "parent_workflow_id": parent.id,
            "parent_step_id": step.id,
            "parent_template_id": parent.template_id,
            "parent_run_id": parent.data.get("run_id"),
        }

    def _resolve_input_reference(self, value: Any, parent_data: Dict[str, Any]) -> Any:
        """解析步骤输入中的简单变量引用。"""
        if isinstance(value, dict):
            return {k: self._resolve_input_reference(v, parent_data) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_input_reference(v, parent_data) for v in value]
        if not isinstance(value, str):
            return value

        if value == "$inputs":
            return parent_data.get("params", {})

        if value.startswith("$inputs."):
            path = value[len("$inputs."):]
            return self._resolve_dotted_path(parent_data.get("params", {}), path)

        if value.startswith("$context."):
            path = value[len("$context."):]
            return self._resolve_dotted_path(parent_data, path)

        return value

    def _resolve_dotted_path(self, obj: Any, dotted_path: str) -> Any:
        """按 a.b.c 形式解析嵌套路径。"""
        if not dotted_path:
            return obj

        current = obj
        for part in dotted_path.split("."):
            if isinstance(current, dict):
                if part not in current:
                    return None
                current = current.get(part)
            elif isinstance(current, list):
                if not part.isdigit():
                    return None
                index = int(part)
                if index < 0 or index >= len(current):
                    return None
                current = current[index]
            else:
                return None
        return current

    async def _backfill_subworkflow_output(
        self,
        parent_workflow_id: str,
        step,
        child,
    ) -> Dict[str, Any]:
        """将子工作流核心产物结构化回填到父流程 data。"""
        parent_step_id = step.id
        parent = await self.store.get_workflow(parent_workflow_id)
        if not parent:
            return {
                "child_workflow_id": child.id,
                "child_status": child.status.value,
            }

        child_data = child.data or {}
        child_run_id = child_data.get("run_id")

        evidence_refs: List[str] = []
        if child_run_id:
            manifest_path = Path(self.project_root or ".").resolve() / "evidence" / child_run_id / "manifest.yaml"
            if manifest_path.exists():
                evidence_refs.append(str(manifest_path))

        child_executions = await self.store.get_task_executions(child.id)
        completed_jobs = [
            execution.step_name
            for execution in child_executions
            if execution.status == TaskExecutionStatus.COMPLETED
        ]

        backfill_output = {
            "child_workflow_id": child.id,
            "child_template_id": child.template_id,
            "child_level": child.level.value,
            "child_status": child.status.value,
            "child_run_id": child_run_id,
            "completed_steps": child_data.get("completed_steps", []),
            "completed_jobs": completed_jobs,
            "child_error": child_data.get("error"),
            "evidence_refs": evidence_refs,
        }

        parent_data = dict(parent.data or {})
        subworkflow_outputs = dict(parent_data.get("subworkflow_outputs", {}))
        subworkflow_outputs[parent_step_id] = backfill_output
        parent_data["subworkflow_outputs"] = subworkflow_outputs

        output_map = (step.config or {}).get("output_map")
        if isinstance(output_map, dict):
            artifacts = dict(parent_data.get("artifacts", {}))
            for target_key, source in output_map.items():
                if not isinstance(target_key, str):
                    continue
                artifacts[target_key] = self._resolve_output_map_value(source, backfill_output, child_data)
            parent_data["artifacts"] = artifacts

        parent_data["last_output"] = {parent_step_id: backfill_output}
        await self.store.update_workflow_data(parent_workflow_id, parent_data)

        return backfill_output

    def _resolve_output_map_value(
        self,
        source: Any,
        backfill_output: Dict[str, Any],
        child_data: Dict[str, Any],
    ) -> Any:
        """解析 output_map 映射值。"""
        if not isinstance(source, str):
            return source

        if source == "$child":
            return backfill_output
        if source.startswith("$child."):
            return self._resolve_dotted_path(backfill_output, source[len("$child."):])
        if source == "$child_data":
            return child_data
        if source.startswith("$child_data."):
            return self._resolve_dotted_path(child_data, source[len("$child_data."):])
        return source

    def _generate_run_id(self) -> str:
        """生成 run_id"""
        return f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"

    async def _collect_evidence(self, workflow_id: str, step_id: str, artifacts: List[str]) -> None:
        """收集证据产物"""
        if not artifacts:
            return

        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return

        run_id = instance.data.get("run_id")
        if not run_id:
            run_id = self._generate_run_id()
            instance.data["run_id"] = run_id
            await self.store.update_workflow_data(workflow_id, instance.data)

        self.evidence_collector.collect(run_id, step_id, artifacts)

    def _resolve_output_paths(self, outputs) -> List[str]:
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
                base = Path(self.project_root or ".").resolve()
                paths.append(str(base / path))
        return paths

    def _ensure_output_artifacts(self, outputs) -> List[str]:
        """确保输出产物存在（用于 demo/兜底）"""
        if not outputs:
            return []

        created: List[str] = []
        base = Path(self.project_root or ".").resolve()

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

    def _demo_mode_enabled(self) -> bool:
        return os.getenv("LEE_DEMO_MODE", "").lower() in ("1", "true", "yes")

    async def _run_verifiers(self, workflow_id: str, step) -> Optional[List]:
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

            instance = await self.store.get_workflow(workflow_id)
            run_id = instance.data.get("run_id") if instance else None
            if instance and not run_id:
                run_id = self._generate_run_id()
                instance.data["run_id"] = run_id
                await self.store.update_workflow_data(workflow_id, instance.data)

            report_path = self._write_verifier_report(run_id or "RUN-UNKNOWN", step.id, results)
            if report_path:
                await self._collect_evidence(workflow_id, step.id, [report_path])

            return results

        instance = await self.store.get_workflow(workflow_id)
        run_id = instance.data.get("run_id") if instance else None
        if instance and not run_id:
            run_id = self._generate_run_id()
            instance.data["run_id"] = run_id
            await self.store.update_workflow_data(workflow_id, instance.data)

        context = {
            "workflow_id": workflow_id,
            "step_id": step.id,
            "run_id": run_id,
        }

        results = self.verifier_engine.run(verifiers, context)

        report_path = self._write_verifier_report(run_id or "RUN-UNKNOWN", step.id, results)
        if report_path:
            await self._collect_evidence(workflow_id, step.id, [report_path])

        return results

    def _verifiers_passed(self, results: List) -> bool:
        return self.verifier_engine.all_passed(results)

    def _write_verifier_report(self, run_id: str, step_id: str, results: List) -> Optional[str]:
        """写入 verifier 结果报告到 .workflow/verifiers/"""
        base = Path(self.project_root or ".").resolve()
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
