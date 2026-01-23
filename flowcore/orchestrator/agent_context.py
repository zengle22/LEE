"""
Agent Context Builder

构建步骤执行的完整上下文，整合 Agent spec 和 Step metadata。
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .agent_resolver import AgentResolver, AgentSpecNotFound
from .agent_loader import AgentLoader, AgentSpec, AgentSpecInvalid
from .agent_injector import InjectorRegistry, InjectionResult, AgentContext


class AgentContextBuilder:
    """Agent 上下文构建器

    整合 workflow 步骤信息和 agent spec，生成完整的执行上下文。
    """

    def __init__(self, project_root: str, phase_dir: str = None):
        """初始化构建器

        Args:
            project_root: 项目根目录 (ai-spec 所在目录)
            phase_dir: Phase 目录 (workflow.yaml 所在目录)
        """
        self.project_root = Path(project_root)
        self.phase_dir = Path(phase_dir) if phase_dir else None
        self.loader = AgentLoader(project_root)
        self._debug = os.environ.get("ORCHESTRATOR_DEBUG_AGENT") == "1"

    def build(
        self,
        step_id: str,
        step_data: Dict[str, Any],
        workflow_data: Dict[str, Any],
        state_data: Dict[str, Any] = None,
    ) -> AgentContext:
        """构建步骤的完整上下文

        Args:
            step_id: 步骤 ID
            step_data: 步骤定义数据 (来自 workflow.yaml)
            workflow_data: 工作流数据 (来自 workflow.yaml)
            state_data: 运行状态数据 (来自 state.yaml)

        Returns:
            AgentContext 对象
        """
        # 1. 提取步骤信息
        step_name = step_data.get("name", step_id)
        step_description = step_data.get("description", "")
        step_inputs = self._extract_paths(step_data.get("inputs", []))
        step_outputs = self._extract_paths(step_data.get("outputs", []))

        # 2. 获取 agent 引用
        agent_ref = step_data.get("run", "")

        # 3. 加载 agent spec
        agent_spec = self._load_agent_spec(agent_ref)

        # 4. 提取工作流信息
        workflow_id = workflow_data.get("id", "")
        workflow_name = workflow_data.get("name", "")
        run_id = state_data.get("run_id", "") if state_data else ""

        # 5. 提取契约信息
        input_contract = None
        output_contract = None
        if agent_spec:
            contracts = agent_spec.contracts
            input_contract = contracts.get("input_schema")
            output_contract = contracts.get("output_schema")

        # 6. 构建上下文
        context = AgentContext(
            # 步骤信息
            step_id=step_id,
            step_name=step_name,
            step_description=step_description,
            step_inputs=step_inputs,
            step_outputs=step_outputs,

            # Agent 信息
            agent_id=agent_spec.id if agent_spec else "",
            agent_name=agent_spec.name if agent_spec else "",
            agent_version=agent_spec.version if agent_spec else "",
            agent_system_prompt=agent_spec.get_system_prompt() if agent_spec else "",
            agent_instructions=agent_spec.get_instructions() if agent_spec else [],
            agent_persona=agent_spec.persona if agent_spec else {},
            agent_forbidden_behaviors=agent_spec.forbidden_behaviors if agent_spec else [],
            agent_quality_bar=agent_spec.get_quality_bar() if agent_spec else [],
            agent_decision_rules=agent_spec.get_decision_rules() if agent_spec else [],
            agent_responsibility=agent_spec.responsibility if agent_spec else {},

            # 契约
            input_contract=input_contract,
            output_contract=output_contract,

            # 工作流
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            run_id=run_id,

            # 其他
            knowledge_access=agent_spec.knowledge_access if agent_spec else None,
            human_confirmation=agent_spec.human_confirmation if agent_spec else None,
            generated_at=datetime.now().isoformat(),
            spec_path=agent_spec.spec_path if agent_spec else None,
        )

        if self._debug:
            print(f"[DEBUG] Built context for step '{step_id}':")
            print(f"  Agent: {context.agent_id} ({context.agent_name})")
            print(f"  Spec: {context.spec_path}")

        return context

    def _load_agent_spec(self, agent_ref: str) -> Optional[AgentSpec]:
        """加载 agent spec"""
        if not agent_ref:
            if self._debug:
                print("[DEBUG] No agent reference, using default")
            return AgentSpec.default()

        try:
            return self.loader.load(agent_ref)
        except AgentSpecNotFound as e:
            if self._debug:
                print(f"[DEBUG] Agent spec not found: {e}")
            return AgentSpec.default()
        except AgentSpecInvalid as e:
            # 格式错误应该报告，但不阻断
            print(f"Warning: Invalid agent spec: {e}")
            return AgentSpec.default()

    def _extract_paths(self, items: List) -> List[str]:
        """从输入/输出定义中提取路径"""
        paths = []
        for item in items:
            if isinstance(item, str):
                paths.append(item)
            elif isinstance(item, dict):
                path = item.get("path", "")
                if path:
                    paths.append(path)
        return paths

    def build_and_inject(
        self,
        step_id: str,
        step_data: Dict[str, Any],
        workflow_data: Dict[str, Any],
        state_data: Dict[str, Any] = None,
        injector_name: str = None,
    ) -> InjectionResult:
        """构建上下文并注入到 AI 工具

        Args:
            step_id: 步骤 ID
            step_data: 步骤定义数据
            workflow_data: 工作流数据
            state_data: 运行状态数据
            injector_name: 指定注入器名称 (可选，不指定则自动检测)

        Returns:
            注入结果
        """
        # 构建上下文
        context = self.build(step_id, step_data, workflow_data, state_data)

        # 获取注入器
        inject_path = self.phase_dir if self.phase_dir else self.project_root
        injector = InjectorRegistry.create_injector(inject_path, injector_name)

        if injector is None:
            return InjectionResult(
                success=False,
                injector_name=injector_name or "auto",
                context_location="",
                message="No suitable injector found for this project",
            )

        # 注入上下文
        return injector.inject(context, step_id)


class ContextManager:
    """上下文管理器

    提供高层 API 用于管理步骤执行上下文。
    """

    def __init__(self, project_root: str, phase_dir: str):
        """初始化管理器

        Args:
            project_root: 项目根目录
            phase_dir: Phase 目录
        """
        self.project_root = Path(project_root)
        self.phase_dir = Path(phase_dir)
        self.builder = AgentContextBuilder(project_root, phase_dir)

    def inject_context_for_step(
        self,
        step_id: str,
        workflow_parser,  # WorkflowParser 实例
        state_data: Dict[str, Any],
        injector_name: str = None,
    ) -> InjectionResult:
        """为步骤注入上下文

        Args:
            step_id: 步骤 ID
            workflow_parser: WorkflowParser 实例
            state_data: 运行状态数据
            injector_name: 注入器名称 (可选)

        Returns:
            注入结果
        """
        # 获取步骤数据
        steps = workflow_parser.parse()
        step_data = None
        for step in steps:
            if step.id == step_id:
                step_data = {
                    "id": step.id,
                    "name": step.name,
                    "description": getattr(step, 'description', ''),
                    "run": step.agent_id,
                    "inputs": [{"path": inp.path} for inp in step.inputs],
                    "outputs": [{"path": out.path} for out in step.outputs],
                }
                break

        if step_data is None:
            return InjectionResult(
                success=False,
                injector_name=injector_name or "auto",
                context_location="",
                message=f"Step '{step_id}' not found in workflow",
            )

        # 获取工作流数据
        workflow_data = {
            "id": workflow_parser.workflow.get("id", ""),
            "name": workflow_parser.workflow.get("name", ""),
        }

        return self.builder.build_and_inject(
            step_id,
            step_data,
            workflow_data,
            state_data,
            injector_name,
        )

    def get_current_context(self, injector_name: str = None) -> Optional[AgentContext]:
        """获取当前已注入的上下文

        Args:
            injector_name: 注入器名称 (可选)

        Returns:
            当前上下文或 None
        """
        injector = InjectorRegistry.create_injector(self.phase_dir, injector_name)
        if injector:
            return injector.get_current_context()
        return None

    def clear_context(self, injector_name: str = None) -> bool:
        """清除已注入的上下文

        Args:
            injector_name: 注入器名称 (可选)

        Returns:
            是否成功
        """
        injector = InjectorRegistry.create_injector(self.phase_dir, injector_name)
        if injector:
            return injector.clear_context()
        return False
