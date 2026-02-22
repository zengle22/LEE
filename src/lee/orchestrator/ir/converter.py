"""
LEE Orchestrator - IR Converter

将 WorkflowIR 转换为 Orchestrator 的 WorkflowTemplate。

这是 IR 和现有执行引擎之间的桥梁。
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pathlib import Path

from lee.orchestrator.ir.models import (
    WorkflowIR,
    StepIR,
    StageIR,
    StepKind,
    flatten_stages_to_steps,
)
from lee.orchestrator.storage.models import (
    WorkflowLevel,
    Step,
    OutputSpec,
)

# 避免 WorkflowTemplate 的循环导入
if TYPE_CHECKING:
    from lee.orchestrator.execution.template_manager import WorkflowTemplate

# WorkflowTemplate 在 template_manager 中定义，避免循环导入
# 从 template_manager 导入会导致循环依赖
# 所以我们在这里定义一个简化版本，在需要时再导入


class IRConverter:
    """
    IR 转换器

    职责：
    1. 将 WorkflowIR 转换为字典（兼容 WorkflowTemplate）
    2. 将 StepIR 转换为字典（兼容 Step）
    3. 保留 IR 在 template.config 中供后续使用
    """

    def __init__(self, config: Optional[Any] = None):
        """
        初始化 IR 转换器

        Args:
            config: LeeConfig 实例（可选，用于读取 executor.default_type）
        """
        self.config = config
        if config is None:
            # 使用默认配置
            from lee.orchestrator.config_loader import LeeConfig
            self.config = LeeConfig()

    def ir_to_template_dict(self, ir: WorkflowIR) -> Dict[str, Any]:
        """
        将 WorkflowIR 转换为字典（可用来构建 WorkflowTemplate）

        Args:
            ir: WorkflowIR 对象

        Returns:
            模板字典
        """
        # 推断层级
        level = self._infer_level(ir)

        # 转换步骤
        steps = [self._ir_to_step_dict(step_ir) for step_ir in ir.steps]

        # 构建配置（包含 IR 和其他元数据）
        config = {
            "_ir": ir,  # 缓存 IR 供后续使用
            "_spec_global_format": True,
            "state_machine": self._state_machine_to_dict(ir.state_machine) if ir.state_machine else None,
            "contracts": self._contracts_to_dict(ir.inputs, ir.outputs),
        }

        return {
            "id": ir.id,
            "level": level.value if isinstance(level, WorkflowLevel) else level,
            "name": ir.name,
            "description": ir.description,
            "steps": steps,
            "departments": [],  # spec-global 不使用 departments
            "tasks": [],  # spec-global 不使用 tasks
            "completion_criteria": {},  # 可从 state_machine 推断
            "config": config,
        }

    def _ir_to_step_dict(self, step_ir: StepIR) -> Dict[str, Any]:
        """
        将 StepIR 转换为字典（可用来构建 Step）

        Args:
            step_ir: StepIR 对象

        Returns:
            步骤字典
        """
        # 推断 executor_type (v3.5: 使用配置中的 default_type)
        executor_type = step_ir.executor_type
        if not executor_type:
            if step_ir.kind == StepKind.AGENT:
                executor_type = self.config.executor.default_type
            elif step_ir.kind == StepKind.SKILL:
                executor_type = "shell"
            elif step_ir.kind in (
                StepKind.HUMAN_GATE,
                StepKind.WORKFLOW_SPAWN,
                StepKind.ORCHESTRATOR_CLI,
                StepKind.COMPLIANCE_GATE,
            ):
                executor_type = None

        return {
            "id": step_ir.id,
            "kind": step_ir.kind.value,
            "executor_type": executor_type,
            "agent_id": step_ir.agent_id,
            "skill_id": step_ir.skill_id,
            "gate_id": step_ir.gate_ref or step_ir.human_gate,
            "on_failure": step_ir.on_failure,
            "depends_on": step_ir.depends_on,
            "input": self._convert_step_inputs(step_ir.inputs),
            "outputs": self._convert_step_outputs_dict(step_ir.outputs),
            "config": {
                **step_ir.config,
                "stage_id": step_ir.stage_id,
                "condition": step_ir.condition,
                "timeout": step_ir.timeout,
                "on_failure": step_ir.on_failure,
            },
        }

    def _infer_level(self, ir: WorkflowIR) -> WorkflowLevel:
        """
        推断工作流层级

        spec-global 不使用 level 字段，根据内容推断：
        - 有 stages 且包含嵌套 steps → DEPARTMENT
        - 有 steps 但没有 stages → TASK
        """
        if ir.stages:
            return WorkflowLevel.DEPARTMENT
        elif ir.steps:
            return WorkflowLevel.TASK
        else:
            return WorkflowLevel.DEPARTMENT  # 默认

    def _ir_to_step(self, step_ir: StepIR) -> Step:
        """
        将 StepIR 转换为 Step

        Args:
            step_ir: StepIR 对象

        Returns:
            Step 对象
        """
        # 推断 executor_type (v3.5: 使用配置中的 default_type)
        executor_type = step_ir.executor_type
        if not executor_type:
            if step_ir.kind == StepKind.AGENT:
                executor_type = self.config.executor.default_type
            elif step_ir.kind == StepKind.SKILL:
                executor_type = "shell"
            elif step_ir.kind in (
                StepKind.HUMAN_GATE,
                StepKind.WORKFLOW_SPAWN,
                StepKind.ORCHESTRATOR_CLI,
                StepKind.COMPLIANCE_GATE,
            ):
                executor_type = None

        return Step(
            id=step_ir.id,
            kind=step_ir.kind.value,
            executor_type=executor_type,
            agent_id=step_ir.agent_id,
            skill_id=step_ir.skill_id,
            gate_id=step_ir.human_gate,
            on_failure=step_ir.on_failure,
            depends_on=step_ir.depends_on,
            input=self._convert_step_inputs(step_ir.inputs),
            outputs=self._convert_step_outputs(step_ir.outputs),
            config={
                **step_ir.config,
                "stage_id": step_ir.stage_id,
                "condition": step_ir.condition,
                "timeout": step_ir.timeout,
                "on_failure": step_ir.on_failure,
            },
        )

    def _convert_step_inputs(self, inputs: List) -> Dict[str, Any]:
        """
        转换步骤输入为 Orchestrator 格式

        Args:
            inputs: StepInputIR 列表

        Returns:
            输入字典
        """
        result = {}
        for inp in inputs:
            # 保留原始值（可能是变量引用）
            result[inp.name] = inp.value
        return result

    def _convert_step_outputs(self, outputs: List) -> List[OutputSpec]:
        """
        转换步骤输出为 OutputSpec 列表

        Args:
            outputs: StepOutputIR 列表

        Returns:
            OutputSpec 列表
        """
        result = []
        for out in outputs:
            result.append(OutputSpec(
                type=out.type,
                path=out.path,
                format=out.format,
                required=out.required,
                description=out.description or "",
            ))
        return result

    def _convert_step_outputs_dict(self, outputs: List) -> List[Dict[str, Any]]:
        """
        转换步骤输出为字典列表

        Args:
            outputs: StepOutputIR 列表

        Returns:
            输出字典列表
        """
        result = []
        for out in outputs:
            result.append({
                "path": out.path,
                "type": out.type,
                "format": out.format,
                "required": out.required,
                "description": out.description or "",
            })
        return result

    def _state_machine_to_dict(self, sm_ir) -> Dict[str, Any]:
        """将 StateMachineIR 转换为字典"""
        if not sm_ir:
            return {}

        transitions = {}
        for state, trans_list in sm_ir.transitions.items():
            transitions[state] = [
                {
                    "to": trans.to_state,
                    "trigger": trans.trigger,
                    "note": trans.note,
                }
                for trans in trans_list
            ]

        return {
            "states": sm_ir.states,
            "transitions": transitions,
            "initial_state": sm_ir.initial_state,
        }

    def _contracts_to_dict(self, inputs: List, outputs: List) -> Dict[str, Any]:
        """将契约转换为字典"""
        return {
            "inputs": [
                {
                    "id": c.contract_id,
                    "path": c.path,
                    "required": c.required,
                    "description": c.description,
                }
                for c in inputs
            ],
            "outputs": [
                {
                    "id": c.contract_id,
                    "path": c.path,
                    "description": c.description,
                }
                for c in outputs
            ],
        }


class TemplateToIRConverter:
    """
    反向转换器：将 Orchestrator 模板转换为 spec-global IR

    用于迁移旧格式工作流到 spec-global 格式。
    """

    def template_to_ir(self, template: "WorkflowTemplate", kind: str = "workflow") -> WorkflowIR:
        """
        将 WorkflowTemplate 转换为 WorkflowIR

        Args:
            template: WorkflowTemplate 对象
            kind: 工作流类型（默认 "workflow"）

        Returns:
            WorkflowIR 对象
        """
        # 构建基本的 WorkflowIR
        ir = WorkflowIR(
            id=template.id,
            kind=kind,
            version="1.0",  # 默认版本
            name=template.name,
            description=template.description,
            owner="",
            tags=[],
            steps=[],
            config=template.config.copy(),
        )

        # 转换步骤
        for step in template.steps:
            step_ir = self._template_step_to_ir(step)
            ir.steps.append(step_ir)

        return ir

    def _template_step_to_ir(self, step: Step) -> StepIR:
        """将 Step 转换为 StepIR"""
        # 推断步骤类型
        if step.kind == "agent":
            kind = StepKind.AGENT
        elif step.kind == "skill":
            kind = StepKind.SKILL
        elif step.kind == "human_gate":
            kind = StepKind.HUMAN_GATE
        elif step.kind in ("workflow_spawn", "subworkflow"):
            kind = StepKind.WORKFLOW_SPAWN
        elif step.kind == "orchestrator_cli":
            kind = StepKind.ORCHESTRATOR_CLI
        elif step.kind == "compliance_gate":
            kind = StepKind.COMPLIANCE_GATE
        else:
            kind = StepKind.AGENT

        return StepIR(
            id=step.id,
            kind=kind,
            name=step.config.get("name", step.id),
            description=step.config.get("description", ""),
            agent_id=step.agent_id,
            skill_id=step.skill_id,
            executor_type=step.executor_type,
            depends_on=step.depends_on,
            config=step.config,
            human_gate=step.gate_id,
        )

    def ir_to_spec_global_yaml(self, ir: WorkflowIR, output_path: str) -> None:
        """
        将 WorkflowIR 导出为 spec-global 格式的 YAML 文件

        Args:
            ir: WorkflowIR 对象
            output_path: 输出文件路径
        """
        import yaml

        # 构建字典
        doc = {
            "kind": ir.kind,
            "version": ir.version,
            "id": ir.id,
            "name": ir.name,
            "description": ir.description,
        }

        # 添加元数据
        if ir.owner:
            doc["owner"] = ir.owner
        if ir.tags:
            doc["tags"] = ir.tags

        # 添加契约
        if ir.inputs or ir.outputs:
            doc["contracts"] = {}
            if ir.inputs:
                doc["contracts"]["inputs"] = [
                    {
                        c.contract_id: {
                            "path": c.path,
                            "description": c.description,
                            "required": c.required,
                        }
                    }
                    for c in ir.inputs
                ]
            if ir.outputs:
                doc["contracts"]["outputs"] = [
                    {
                        c.contract_id: {
                            "path": c.path,
                            "description": c.description,
                        }
                    }
                    for c in ir.outputs
                ]

        # 添加步骤
        if ir.steps:
            doc["steps"] = [self._step_ir_to_dict(s) for s in ir.steps]

        # 写入文件
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(doc, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def _step_ir_to_dict(self, step_ir: StepIR) -> Dict[str, Any]:
        """将 StepIR 转换为字典"""
        doc = {
            "id": step_ir.id,
            "name": step_ir.name,
            "description": step_ir.description,
        }

        # 添加执行配置
        if step_ir.agent_id:
            doc["run"] = step_ir.agent_id
            doc["type"] = "agent"
        elif step_ir.skill_id:
            doc["run"] = step_ir.skill_id
            doc["type"] = "skill"
        elif step_ir.kind == StepKind.WORKFLOW_SPAWN:
            doc["kind"] = "workflow_spawn"
            subworkflow_ref = step_ir.config.get("subworkflow_ref") if step_ir.config else None
            if subworkflow_ref:
                doc["workflow"] = subworkflow_ref
            subworkflow_level = step_ir.config.get("subworkflow_level") if step_ir.config else None
            if subworkflow_level:
                doc["level"] = subworkflow_level
        elif step_ir.kind == StepKind.HUMAN_GATE:
            doc["type"] = "human_gate"
        elif step_ir.kind == StepKind.ORCHESTRATOR_CLI:
            doc["type"] = "orchestrator_cli"
        elif step_ir.kind == StepKind.COMPLIANCE_GATE:
            doc["type"] = "compliance_gate"

        # 添加依赖
        if step_ir.depends_on:
            doc["dependencies"] = {"requires": step_ir.depends_on}

        # 添加输入输出
        if step_ir.inputs:
            doc["inputs"] = [{inp.name: inp.value} for inp in step_ir.inputs]
        if step_ir.outputs:
            doc["outputs"] = [
                {
                    "path": out.path,
                    "type": out.type,
                    "format": out.format,
                    "required": out.required,
                }
                for out in step_ir.outputs
            ]

        # 添加门禁
        if step_ir.human_gate:
            doc["human_gate"] = step_ir.human_gate

        return doc
