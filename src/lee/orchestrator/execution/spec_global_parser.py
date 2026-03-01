"""
LEE Orchestrator - spec-global YAML Parser

解析 spec-global 格式的工作流 YAML 文件，转换为 WorkflowIR。

spec-global 格式特点：
- kind: workflow 标识
- stages/steps 嵌套结构
- 完整的状态机定义
- 外部门禁文件引用
- 契约路径定义
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from lee.orchestrator.ir.models import (
    WorkflowIR,
    StageIR,
    StepIR,
    StateMachineIR,
    StateTransitionIR,
    GateIR,
    GateRuleIR,
    ContractIR,
    RuleType,
    RuleSeverity,
    StepKind,
    HumanInTheLoopIR,
    ErrorHandlingIR,
    ObservabilityIR,
    StepInputIR,
    StepOutputIR,
    VariableIR,
)
from lee.orchestrator.execution.variable_resolver import VariableResolver


class SpecGlobalParser:
    """
    spec-global YAML 解析器

    职责：
    1. 解析 workflow.yaml 文件
    2. 解析 gate.yaml 门禁文件
    3. 将 YAML 转换为 IR
    4. 处理相对路径解析
    """

    def __init__(self, workflow_base_dir: Optional[str] = None):
        """
        初始化解析器

        Args:
            workflow_base_dir: 工作流文件的基础目录（用于解析相对路径）
        """
        self.workflow_base_dir = Path(workflow_base_dir) if workflow_base_dir else None
        self.version = "1.0"
        self._variable_resolver = VariableResolver()

    # ========================================================================
    # 主解析方法
    # ========================================================================

    def _parse_value(self, value: Any) -> Any:
        """
        解析值，判断是变量引用还是常量

        Args:
            value: 原始值（字符串、字典、列表等）

        Returns:
            解析后的值（VariableIR 或常量）
        """
        # 如果是字符串，检查是否是变量引用
        if isinstance(value, str):
            # 检查是否是 $inputs.xxx, $sX_yyy, $context.xxx 格式
            if value.startswith("$"):
                try:
                    return self._variable_resolver.parse_reference(value)
                except ValueError:
                    # 如果解析失败，作为常量返回
                    return value
            # 检查是否是 "external" 特殊值（spec-global 格式的外部输入）
            elif value == "external":
                # external 表示从工作流的 data 字段获取输入
                # 返回一个特殊的 VariableIR
                return VariableIR(
                    reference="$inputs.external",
                    source_type="inputs",
                    path=["external"],
                )
            return value
        # 如果是字典或列表，保持不变
        return value

    def parse_workflow_file(self, file_path: str) -> WorkflowIR:
        """
        解析工作流 YAML 文件

        Args:
            file_path: workflow.yaml 文件路径

        Returns:
            WorkflowIR 对象
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")

        # 设置基础目录
        if not self.workflow_base_dir:
            self.workflow_base_dir = file_path.parent

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        docs = list(yaml.safe_load_all(content))
        if not docs or not docs[0]:
            raise ValueError(f"Empty workflow file: {file_path}")

        main_doc = docs[0]
        return self.parse_workflow(main_doc, file_path)

    def parse_workflow(self, doc: Dict[str, Any], file_path: Path) -> WorkflowIR:
        """
        解析工作流文档

        Args:
            doc: YAML 文档字典
            file_path: 文件路径（用于解析相对路径）

        Returns:
            WorkflowIR 对象
        """
        # 验证 kind 和 version
        kind = doc.get("kind")
        if kind != "workflow":
            raise ValueError(f"Expected kind=workflow, got {kind}")

        # 解析基本信息
        workflow_ir = WorkflowIR(
            id=doc.get("id", ""),
            kind=kind,
            version=doc.get("version", "1.0"),
            name=doc.get("name", ""),
            description=doc.get("description", ""),
            owner=doc.get("owner", ""),
            tags=doc.get("tags", []),
        )

        # 解析契约
        if "contracts" in doc:
            workflow_ir.inputs = self._parse_contracts(doc["contracts"], "inputs", file_path)
            workflow_ir.outputs = self._parse_contracts(doc["contracts"], "outputs", file_path)

        # 解析状态机
        if "state_machine" in doc:
            workflow_ir.state_machine = self._parse_state_machine(doc["state_machine"])

        # 解析 stages 和 steps
        # 支持两种格式:
        # 1. 嵌套格式: stages -> steps
        # 2. 扁平格式: 直接 steps (没有 stages)
        if "stages" in doc:
            workflow_ir.stages = self._parse_stages(doc["stages"], file_path)
            # 同时展平到 steps 列表
            workflow_ir.steps = self._flatten_stages_to_steps(workflow_ir.stages)
        elif "steps" in doc:
            # 扁平格式：直接在顶层定义 steps
            workflow_ir.steps = self._parse_flat_steps(doc["steps"])
            # 创建一个虚拟 stage 包含所有 steps
            workflow_ir.stages = []

        # 解析门禁（收集引用）
        # 支持两种格式:
        # 1. 简写格式: gate_id: path/to/gate.yaml
        # 2. 完整格式: gate_id: {ref: path/to/gate.yaml}
        # 3. 内联定义: gate_id: {type: human, timeout: ...}
        if "gates" in doc:
            for gate_id, gate_def in doc["gates"].items():
                gate_ir = None
                # 如果是字典，检查是否有 ref 字段（文件引用）或其他字段（内联定义）
                if isinstance(gate_def, dict):
                    if "ref" in gate_def:
                        # 文件引用格式
                        gate_ref = gate_def["ref"]
                        gate_ir = self._parse_gate_file(gate_ref, file_path)
                    else:
                        # 内联门禁定义，跳过解析（暂不支持）
                        # 这些是配置性质的门禁，不是 spec-global 格式的门禁规范
                        continue
                elif isinstance(gate_def, str):
                    # 简写格式：直接是文件路径
                    gate_ir = self._parse_gate_file(gate_def, file_path)

                # 只添加成功解析的门禁
                if gate_ir is not None:
                    workflow_ir.gates[gate_id] = gate_ir

        # 解析人类介入
        if "human_in_the_loop" in doc:
            workflow_ir.human_in_the_loop = self._parse_human_in_the_loop(doc["human_in_the_loop"])

        # 解析错误处理
        if "error_handling" in doc:
            for error_name, error_config in doc["error_handling"].items():
                workflow_ir.error_handling[error_name] = self._parse_error_handling(error_name, error_config)

        # 解析可观测性
        if "observability" in doc:
            workflow_ir.observability = self._parse_observability(doc["observability"])

        # 解析概念定义
        if "concepts" in doc:
            workflow_ir.concepts = doc["concepts"]

        # 其他配置
        if "config" in doc:
            workflow_ir.config = doc["config"]

        return workflow_ir

    # ========================================================================
    # 契约解析
    # ========================================================================

    def _parse_contracts(
        self,
        contracts_section: Dict[str, Any],
        key: str,
        file_path: Path
    ) -> List[ContractIR]:
        """
        解析契约定义

        Args:
            contracts_section: contracts 部分
            key: "inputs" 或 "outputs"
            file_path: 工作流文件路径

        Returns:
            ContractIR 列表
        """
        contracts = []
        contract_list = contracts_section.get(key, [])

        for contract_def in contract_list:
            if isinstance(contract_def, dict):
                for contract_id, contract_spec in contract_def.items():
                    # 解析相对路径
                    contract_path = contract_spec.get("path", "")
                    full_path = self._resolve_relative_path(contract_path, file_path)

                    contracts.append(ContractIR(
                        contract_id=contract_id,
                        kind=key.rstrip("s"),  # inputs -> input, outputs -> output
                        path=full_path,
                        description=contract_spec.get("description", ""),
                        required=contract_spec.get("required", True),
                        structure=contract_spec.get("structure"),
                    ))

        return contracts

    def _resolve_relative_path(self, relative_path: str, base_path: Path) -> str:
        """
        解析相对路径

        Args:
            relative_path: 相对路径
            base_path: 基础文件路径

        Returns:
            解析后的绝对路径（相对于项目根目录）
        """
        if not relative_path:
            return relative_path

        # 如果已经是绝对路径，直接返回
        if Path(relative_path).is_absolute():
            return relative_path

        # 解析相对路径
        resolved = base_path.parent / relative_path
        try:
            # 转换为相对于项目根目录的路径
            project_root = Path(__file__).parent.parent.parent.parent.parent
            return str(resolved.relative_to(project_root))
        except ValueError:
            # 如果无法计算相对路径，返回原始路径
            return relative_path

    # ========================================================================
    # 状态机解析
    # ========================================================================

    def _parse_state_machine(self, sm_data: Dict[str, Any]) -> StateMachineIR:
        """
        解析状态机定义

        Args:
            sm_data: state_machine 部分的数据

        Returns:
            StateMachineIR 对象
        """
        # 解析状态列表
        # 支持两种格式:
        # 1. 简写格式: - INIT: "初始化"
        # 2. 完整格式: - id: INIT
        #              description: "初始化"
        states = []
        for state_def in sm_data.get("states", []):
            if isinstance(state_def, dict):
                # 简写格式: {"INIT": "初始化"} - 键是状态ID
                if "id" not in state_def:
                    # 获取第一个键作为状态ID
                    state_id = next(iter(state_def.keys()))
                    states.append(state_id)
                else:
                    # 完整格式: {"id": "INIT", ...}
                    states.append(state_def["id"])
            else:
                # 纯字符串格式
                states.append(state_def)

        # 解析转换规则
        transitions = {}
        for state, transitions_list in sm_data.get("transitions", {}).items():
            transitions[state] = []
            for trans in transitions_list:
                transitions[state].append(StateTransitionIR(
                    from_state=state,
                    to_state=trans["to"],
                    trigger=trans["trigger"],
                    note=trans.get("note"),
                    action=trans.get("action"),
                ))

        # 解析初始状态
        first_state = sm_data["states"][0]
        if isinstance(first_state, dict):
            if "id" in first_state:
                initial_state = first_state["id"]
            else:
                # 简写格式，取第一个键
                initial_state = next(iter(first_state.keys()))
        else:
            initial_state = first_state

        return StateMachineIR(
            states=states,
            transitions=transitions,
            initial_state=initial_state,
        )

    # ========================================================================
    # Stage 和 Step 解析
    # ========================================================================

    def _parse_stages(self, stages_data: List[Dict[str, Any]], file_path: Path) -> List[StageIR]:
        """
        解析 stages 列表

        Args:
            stages_data: stages 部分的数据
            file_path: 工作流文件路径

        Returns:
            StageIR 列表
        """
        stages = []
        for stage_data in stages_data:
            stage_ir = StageIR(
                id=stage_data["id"],
                name=stage_data.get("name", ""),
                description=stage_data.get("description", ""),
            )

            # 解析 stage 中的 steps
            for step_data in stage_data.get("steps", []):
                step_ir = self._parse_step(step_data, stage_data["id"])
                stage_ir.steps.append(step_ir)

            stages.append(stage_ir)

        return stages

    def _flatten_stages_to_steps(self, stages: List[StageIR]) -> List[StepIR]:
        """将 stages 展平为步骤列表"""
        steps = []
        for stage in stages:
            for step in stage.steps:
                steps.append(step)
        return steps

    def _parse_flat_steps(self, steps_data: List[Dict[str, Any]]) -> List[StepIR]:
        """
        解析扁平格式的步骤列表（无 stages 嵌套）

        Args:
            steps_data: 步骤数据列表

        Returns:
            StepIR 列表
        """
        steps = []
        for step_data in steps_data:
            # 扁平格式没有 stage_id，使用 "workflow" 作为默认值
            step_ir = self._parse_step(step_data, "workflow")
            steps.append(step_ir)
        return steps

    def _parse_step(self, step_data: Dict[str, Any], stage_id: str) -> StepIR:
        """
        解析单个步骤定义

        Args:
            step_data: 步骤数据
            stage_id: 所属的 stage ID

        Returns:
            StepIR 对象
        """
        # 推断步骤类型（兼容 type/kind 两种写法）
        # 优先级：
        # 1) 显式 kind/type
        # 2) 显式结构字段（subworkflow/skill/gate）
        # 3) run 前缀（run: skill.* / agent.* / workflow.*）
        step_type = step_data.get("kind") or step_data.get("type")
        if not step_type:
            run_ref_for_infer = step_data.get("run")
            if "subworkflow" in step_data or "workflow" in step_data:
                step_type = "subworkflow"
            elif "skill" in step_data:
                step_type = "skill"
            elif "gate" in step_data:
                # 检查 gate.type 以区分 auto_check 和 human_review
                gate_type = step_data.get("gate", {}).get("type", "human_review")
                if gate_type == "auto_check":
                    step_type = "gate"
                else:
                    step_type = "human_gate"
            elif isinstance(run_ref_for_infer, str):
                if run_ref_for_infer.startswith("skill."):
                    step_type = "skill"
                elif run_ref_for_infer.startswith("workflow."):
                    step_type = "subworkflow"
                else:
                    step_type = "agent"
            else:
                step_type = "agent"

        step_type = str(step_type).lower()

        if step_type == "agent":
            kind = StepKind.AGENT
        elif step_type == "skill":
            kind = StepKind.SKILL
        elif step_type == "human_gate" or step_type == "human_decision":
            kind = StepKind.HUMAN_GATE
        elif step_type == "conditional":
            kind = StepKind.CONDITIONAL
        elif step_type in ("workflow_spawn", "subworkflow"):
            kind = StepKind.WORKFLOW_SPAWN
        elif step_type == "orchestrator_cli":
            kind = StepKind.ORCHESTRATOR_CLI
        elif step_type == "compliance_gate":
            kind = StepKind.COMPLIANCE_GATE
        else:
            kind = StepKind.AGENT

        # 解析依赖关系（兼容 dependencies/depends_on）
        raw_dependencies = step_data.get("depends_on")
        if raw_dependencies is None:
            raw_dependencies = step_data.get("dependencies", [])
        if isinstance(raw_dependencies, list):
            depends_on = [dep for dep in raw_dependencies if isinstance(dep, str)]
        elif isinstance(raw_dependencies, dict):
            depends_on = [
                dep for dep in raw_dependencies.get("requires", [])
                if isinstance(dep, str)
            ]
        else:
            depends_on = []

        run_ref = step_data.get("run", "")
        agent_id = None
        skill_id = None
        if run_ref and kind != StepKind.WORKFLOW_SPAWN:
            if isinstance(run_ref, str):
                # 字符串格式
                if run_ref.startswith("agent."):
                    agent_id = run_ref
                elif run_ref.startswith("skill."):
                    skill_id = run_ref
                else:
                    agent_id = run_ref
            elif isinstance(run_ref, dict):
                # 复杂格式（如 Phase OpenSpec Flow 的 selector/fallback）
                # 尝试提取 fallback 或默认值
                fallback = run_ref.get("fallback", "")
                if fallback:
                    agent_id = fallback
                else:
                    # 尝试解析 selector
                    selector = run_ref.get("selector", {})
                    if isinstance(selector, dict):
                        # 查找第一个可用的 agent
                        for key, value in selector.items():
                            if isinstance(value, dict) and "agents" in value:
                                agents = value["agents"]
                                if isinstance(agents, list) and agents:
                                    agent_id = agents[0]
                                    break
                    # 如果仍然没有，使用默认值
                    if not agent_id:
                        agent_id = "agent.dev.implementation_executor"
            else:
                # 其他类型，转为字符串
                agent_id = str(run_ref)

        subworkflow_ref = None
        subworkflow_level = None
        if kind == StepKind.WORKFLOW_SPAWN:
            subworkflow_data = step_data.get("subworkflow")
            if isinstance(subworkflow_data, dict):
                subworkflow_ref = subworkflow_data.get("ref") or subworkflow_data.get("id")
                subworkflow_level = subworkflow_data.get("level")
            elif isinstance(subworkflow_data, str):
                subworkflow_ref = subworkflow_data

            if not subworkflow_ref and isinstance(step_data.get("workflow"), str):
                subworkflow_ref = step_data.get("workflow")

            if not subworkflow_ref and isinstance(run_ref, str) and run_ref.startswith("workflow."):
                subworkflow_ref = run_ref

            if step_data.get("level"):
                subworkflow_level = step_data.get("level")

        # 解析 gate
        gate_ref = step_data.get("gate", {})
        gate_ir = None
        gate_ref_str = None
        if isinstance(gate_ref, dict):
            if "ref" in gate_ref:
                gate_ref_str = gate_ref["ref"]
            else:
                gate_ir = self._parse_gate_inline(gate_ref)
        elif isinstance(gate_ref, str):
            gate_ref_str = gate_ref

        step_config = {"description": step_data.get("description")}
        if "run" in step_data:
            step_config["run"] = step_data.get("run")
        if subworkflow_ref:
            step_config["subworkflow_ref"] = subworkflow_ref
        if subworkflow_level:
            step_config["subworkflow_level"] = subworkflow_level
        if "workflow" in step_data:
            step_config["workflow"] = step_data.get("workflow")
        if "subworkflow" in step_data:
            step_config["subworkflow"] = step_data.get("subworkflow")
        if "input_map" in step_data:
            step_config["input_map"] = step_data.get("input_map")
        if "output_map" in step_data:
            step_config["output_map"] = step_data.get("output_map")
        if "subworkflow_max_steps" in step_data:
            step_config["subworkflow_max_steps"] = step_data.get("subworkflow_max_steps")
        if "verifiers" in step_data:
            step_config["verifiers"] = step_data.get("verifiers")
        if "verify" in step_data:
            step_config["verifiers"] = step_data.get("verify")
        if "success_criteria" in step_data:
            step_config["success_criteria"] = step_data.get("success_criteria")
        if "on_failure" in step_data:
            step_config["on_failure"] = step_data.get("on_failure")

        return StepIR(
            id=step_data["id"],
            kind=kind,
            name=step_data.get("name", ""),
            description=step_data.get("description", ""),
            stage_id=stage_id,
            agent_id=agent_id,
            skill_id=skill_id,
            execution=step_data.get("execution"),
            depends_on=depends_on,
            condition=step_data.get("condition"),
            inputs=self._parse_step_inputs(step_data.get("inputs", [])),
            outputs=self._parse_step_outputs(step_data.get("outputs", [])),
            gate=gate_ir,
            gate_ref=gate_ref_str,
            on_failure=step_data.get("on_failure"),
            config=step_config,
            timeout=step_data.get("timeout"),
        )

    def _parse_step_inputs(self, inputs_data: List[Dict[str, Any]]) -> List[StepInputIR]:
        """
        解析步骤输入

        支持多种格式:
        1. spec-global 格式: - source: step_id, type: [...], required: true
        2. 简化变量格式: - step_id (source 引用)
        3. 纯字符串格式: - value (自动生成名称)
        """
        inputs = []
        for input_item in inputs_data:
            if isinstance(input_item, dict):
                # 检查是否是 spec-global 格式的输入定义
                # 包含 source 字段的是 spec-global 格式
                if "source" in input_item:
                    # spec-global 格式: source 是主要字段
                    source = input_item["source"]
                    if (
                        isinstance(source, str)
                        and source
                        and not source.startswith("$")
                        and "{{" not in source
                    ):
                        source = f"${source}"
                    # 创建一个名为 source 的输入，值为 VariableIR
                    inputs.append(StepInputIR(
                        name="source",
                        value=self._parse_value(source),  # 解析为变量引用
                        required=input_item.get("required", True),
                    ))
                    # 同时保存 type 和其他元数据到 config
                    # 注意：这里不再为 type 和 required 创建单独的输入
                elif "name" in input_item and "value" in input_item:
                    # 明确的 name/value 格式
                    inputs.append(StepInputIR(
                        name=input_item["name"],
                        value=self._parse_value(input_item["value"]),
                        required=input_item.get("required", True),
                    ))
                else:
                    # 兼容旧格式：字典格式 - key: value
                    # 遍历字典的所有键值对
                    for key, value in input_item.items():
                        inputs.append(StepInputIR(
                            name=key,
                            value=self._parse_value(value),
                            required=True,
                        ))
            elif isinstance(input_item, str):
                # 纯字符串格式: - value (可能是变量引用)
                # 使用值本身作为名称
                inputs.append(StepInputIR(
                    name=input_item,  # 或使用生成的名称
                    value=self._parse_value(input_item),
                    required=True,
                ))
            else:
                # 其他类型，直接作为值
                inputs.append(StepInputIR(
                    name=str(input_item),
                    value=input_item,
                    required=True,
                ))
        return inputs

    def _parse_step_outputs(self, outputs_data: List[Dict[str, Any]]) -> List[StepOutputIR]:
        """
        解析步骤输出

        支持多种格式:
        1. 完整格式: - path: "file.yaml", description: "..."
        2. 简写格式: - "file.yaml" (纯字符串)
        """
        outputs = []
        for output_item in outputs_data:
            if isinstance(output_item, dict):
                # 完整格式
                path = output_item.get("path", "")
                output_type = "dir" if path.endswith("/") else "file"
                outputs.append(StepOutputIR(
                    path=path,
                    type=output_type,
                    format=self._infer_format(path),
                    required=output_item.get("required", True),
                    description=output_item.get("description"),
                    include=output_item.get("include"),
                ))
            elif isinstance(output_item, str):
                # 简写格式: 纯字符串路径
                output_type = "dir" if output_item.endswith("/") else "file"
                outputs.append(StepOutputIR(
                    path=output_item,
                    type=output_type,
                    format=self._infer_format(output_item),
                    required=True,
                    description=None,
                    include=None,
                ))
            else:
                # 其他类型，跳过或使用默认值
                pass
        return outputs

    def _infer_format(self, path: str) -> str:
        """根据文件扩展名推断格式"""
        if path.endswith(".yaml") or path.endswith(".yml"):
            return "yaml"
        elif path.endswith(".json"):
            return "json"
        elif path.endswith(".md"):
            return "markdown"
        return "text"

    # ========================================================================
    # 门禁解析
    # ========================================================================

    def _parse_gate_file(self, gate_ref: str, workflow_path: Path) -> Optional[GateIR]:
        """
        解析门禁文件

        Args:
            gate_ref: 门禁引用路径（相对于 workflow 文件）
            workflow_path: 工作流文件路径

        Returns:
            GateIR 对象，如果文件不存在返回 None
        """
        workflow_dir = workflow_path.parent
        full_path = (workflow_dir / gate_ref).resolve()

        # 如果路径不存在，尝试其他可能的路径
        if not full_path.exists():
            # 尝试从部门根目录的 gates/ 查找
            # 提取部门路径 (spec-global/departments/{dept}/)
            parts = workflow_path.parts
            try:
                dept_idx = parts.index('departments')
                if dept_idx + 1 < len(parts):
                    dept = parts[dept_idx + 1]
                    # 尝试 gates/{gate_name}/v1/gate.yaml
                    # gate_ref 格式: ../../gates/design-input-gate/v1/gate.yaml
                    gate_name = Path(gate_ref).parts[-3]  # design-input-gate
                    alt_path = Path(*parts[:dept_idx + 2]) / 'gates' / gate_name / 'v1' / 'gate.yaml'
                    if alt_path.exists():
                        full_path = alt_path.resolve()
            except (ValueError, IndexError):
                pass

        # 如果文件不存在，返回 None（不阻塞解析）
        if not full_path.exists():
            # 打印警告但继续解析
            return None

        with open(full_path, 'r', encoding='utf-8') as f:
            gate_doc = yaml.safe_load(f)

        return self._parse_gate_document(gate_doc)

    def _parse_gate_document(self, gate_doc: Dict[str, Any]) -> GateIR:
        """解析门禁文档"""
        return GateIR(
            gate_id=gate_doc.get("gate_id", ""),
            name=gate_doc.get("name", ""),
            description=gate_doc.get("description", ""),
            mandatory_criteria=self._parse_gate_rules(gate_doc.get("mandatory_criteria", []), RuleType.MANDATORY),
            threshold_criteria=self._parse_gate_rules(gate_doc.get("threshold_criteria", []), RuleType.THRESHOLD),
            risk_acceptance_criteria=self._parse_gate_rules(gate_doc.get("risk_acceptance_criteria", []), RuleType.RISK_ACCEPTANCE),
            exemption_policy=self._parse_exemption_policy(gate_doc.get("exemption_policy")),
            signoff_requirements=self._parse_signoff_requirements(gate_doc.get("signoff_requirements")),
        )

    def _parse_gate_inline(self, gate_data: Dict[str, Any]) -> GateIR:
        """解析内联门禁定义"""
        return GateIR(
            gate_id=gate_data.get("id", ""),
            name=gate_data.get("name", ""),
            description=gate_data.get("description", ""),
            mandatory_criteria=[],
            threshold_criteria=[],
            risk_acceptance_criteria=[],
        )

    def _parse_gate_rules(self, rules_data: List[Dict[str, Any]], rule_type: RuleType) -> List:
        """解析门禁规则列表"""
        from lee.orchestrator.ir.models import ExemptionPolicyIR, SignoffRequirementIR

        rules = []
        for rule in rules_data:
            # 解析 severity
            severity_str = rule.get("severity", "blocker")
            try:
                severity = RuleSeverity(severity_str.lower())
            except ValueError:
                severity = RuleSeverity.BLOCKER

            rules.append(GateRuleIR(
                rule_id=rule.get("criterion_id", rule.get("rule_id", "")),
                name=rule.get("name", ""),
                rule_type=rule_type,
                rule_expression=rule.get("rule", ""),
                severity=severity,
                exemption_allowed=rule.get("exemption", False),
                validation_method=rule.get("validation_method"),
                error_message=rule.get("error_message"),
                rationale=rule.get("rationale"),
            ))

        return rules

    def _parse_exemption_policy(self, policy_data: Optional[Dict[str, Any]]) -> Optional:
        """解析豁免策略"""
        if not policy_data:
            return None

        from lee.orchestrator.ir.models import ExemptionPolicyIR

        allowed = []
        forbidden = []
        for allowed_item in policy_data.get("allowed_exemptions", []):
            if isinstance(allowed_item, dict):
                allowed.append(allowed_item.get("criterion", allowed_item.get("rule")))
            else:
                allowed.append(allowed_item)

        for forbidden_item in policy_data.get("forbidden_exemptions", []):
            if isinstance(forbidden_item, dict):
                forbidden.append(forbidden_item.get("criterion", forbidden_item.get("rule")))
            else:
                forbidden.append(forbidden_item)

        return ExemptionPolicyIR(
            allowed_exemptions=allowed,
            max_exemptions=policy_data.get("max_exemptions", 0),
            requires_approval=policy_data.get("requires_approval", []),
            requires_documentation=policy_data.get("requires_documentation", False),
            condition=policy_data.get("condition"),
            forbidden_exemptions=forbidden,
        )

    def _parse_signoff_requirements(self, signoff_data: Optional[Dict[str, Any]]) -> Optional:
        """解析签字要求"""
        if not signoff_data:
            return None

        from lee.orchestrator.ir.models import SignoffRequirementIR

        required = []
        for approver in signoff_data.get("required_approvers", []):
            if isinstance(approver, dict):
                required.append(approver)

        optional = []
        for approver in signoff_data.get("optional_approvers", []):
            if isinstance(approver, dict):
                optional.append(approver)

        return SignoffRequirementIR(
            required_approvers=required,
            optional_approvers=optional,
            approval_sla=signoff_data.get("approval_sla"),
            inputs_to_review=signoff_data.get("inputs_to_review", []),
        )

    # ========================================================================
    # 人类介入解析
    # ========================================================================

    def _parse_human_in_the_loop(self, hitl_data: Any) -> List[HumanInTheLoopIR]:
        """
        解析人类介入定义

        支持两种格式:
        1. 列表格式: - {stage: ..., step: ...}
        2. 字典格式: hitl_name: {stage: ..., step: ...}
        """
        hitl_list = []

        if isinstance(hitl_data, dict):
            # 字典格式: {hitl_name: {config}}
            for hitl_name, hitl_config in hitl_data.items():
                if isinstance(hitl_config, dict):
                    hitl_list.append(HumanInTheLoopIR(
                        name=hitl_name,
                        stage=hitl_config.get("stage", ""),
                        step=hitl_config.get("step", ""),
                        type=hitl_config.get("type", "approval"),
                        timeout=hitl_config.get("timeout"),
                        approval_criteria=hitl_config.get("approval_criteria"),
                        escalation_policy=hitl_config.get("escalation"),
                    ))
        elif isinstance(hitl_data, list):
            # 列表格式
            for hitl in hitl_data:
                hitl_list.append(HumanInTheLoopIR(
                    name=hitl.get("name", ""),
                    stage=hitl.get("stage", ""),
                    step=hitl.get("step", ""),
                    type=hitl.get("type", "approval"),
                    timeout=hitl.get("timeout"),
                    approval_criteria=hitl.get("approval_criteria"),
                    escalation_policy=hitl.get("escalation_policy"),
                ))

        return hitl_list

    # ========================================================================
    # 错误处理解析
    # ========================================================================

    def _parse_error_handling(self, error_name: str, error_config: Any) -> ErrorHandlingIR:
        """
        解析错误处理定义

        支持两种格式:
        1. 字典格式: {action: ..., state: ...}
        2. 列表格式: [{action: ..., state: ...}]
        """
        # 如果是列表，取第一个元素
        if isinstance(error_config, list) and error_config:
            error_config = error_config[0]

        if not isinstance(error_config, dict):
            return ErrorHandlingIR(
                error_scenario=error_name,
                action="unknown",
                target_state=None,
            )

        # 解析动作和目标状态
        action = error_config.get("action", "")
        target_state = None
        if "state" in error_config:
            target_state = error_config["state"]

        return ErrorHandlingIR(
            error_scenario=error_name,
            action=action,
            target_state=target_state,
            retry_config=error_config.get("retry_config"),
        )

    # ========================================================================
    # 可观测性解析
    # ========================================================================

    def _parse_observability(self, obs_data: Dict[str, Any]) -> ObservabilityIR:
        """解析可观测性定义"""
        return ObservabilityIR(
            metrics=obs_data.get("metrics", []),
            dashboards=obs_data.get("dashboards", []),
            alerts=obs_data.get("alerts", []),
        )
