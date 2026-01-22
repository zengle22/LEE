"""
Workflow Parser - 工作流解析器

将 workflow.yaml 转换为可执行的步骤序列，包括：
- 依赖关系解析
- 输入/输出契约提取
- 验证器配置
- 门禁配置
- 路径别名解析 (通过 ProjectConfig)
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .project_config import ProjectConfig


@dataclass
class StepInput:
    """步骤输入定义"""
    source: str  # 来源 (前置步骤产物路径 / 外部输入)
    required: bool = True
    schema_ref: Optional[str] = None


@dataclass
class StepOutput:
    """步骤输出定义"""
    path: str
    contract_ref: Optional[str] = None
    required: bool = True
    freeze: bool = False


@dataclass
class Validator:
    """验证器定义"""
    type: str  # schema / file_exists / coverage / custom
    config: Dict = field(default_factory=dict)
    fail_action: str = "block"  # block / warn / retry


@dataclass
class GateConfig:
    """门禁配置"""
    gate_id: str
    type: str  # human / auto
    blocking: bool = True
    timeout_hours: int = 24
    timeout_action: str = "escalate"  # skip / fail / escalate
    required_roles: List[str] = field(default_factory=list)
    min_approvals: int = 1


@dataclass
class ExecutableStep:
    """可执行步骤"""
    id: str
    name: str
    agent_id: str
    stage_id: str
    description: Optional[str] = None

    # 依赖
    deps: List[str] = field(default_factory=list)
    parallel_with: List[str] = field(default_factory=list)

    # 输入输出
    inputs: List[StepInput] = field(default_factory=list)
    outputs: List[StepOutput] = field(default_factory=list)

    # 验证
    validators: List[Validator] = field(default_factory=list)

    # 门禁
    gate: Optional[GateConfig] = None

    # 执行配置
    execution_model: str = "prompt_switch"
    timeout_minutes: int = 60

    # 错误处理
    on_error: str = "fail"  # fail / skip / retry / escalate
    max_retries: int = 1

    # 跳过条件
    skip_condition: Optional[str] = None
    skip_reason: Optional[str] = None


class WorkflowParser:
    """工作流解析器"""

    def __init__(self, workflow_path: str = None, workflow_dict: Dict = None,
                 project_config: "ProjectConfig" = None):
        if workflow_path:
            with open(workflow_path, encoding='utf-8') as f:
                self.workflow = yaml.safe_load(f)
        elif workflow_dict:
            self.workflow = workflow_dict
        else:
            raise ValueError("Must provide workflow_path or workflow_dict")

        self.base_path = Path(workflow_path).parent if workflow_path else Path(".")
        self.project_config = project_config

        # 如果没有提供 project_config，尝试自动加载
        if not self.project_config and workflow_path:
            try:
                from .project_config import ProjectConfig
                self.project_config = ProjectConfig.load(str(self.base_path))
            except Exception:
                pass  # 没有 project.yaml，使用原始路径

    def resolve_path(self, path: str) -> str:
        """解析输出路径 (支持别名和变量)"""
        if not path:
            return path
        if self.project_config:
            return self.project_config.resolve_path(path, self.base_path)
        # 如果没有 project_config，返回相对于 workflow 的路径
        return str((self.base_path / path).resolve())

    def parse(self) -> List[ExecutableStep]:
        """解析工作流为可执行步骤列表

        支持两种工作流格式:
        1. 嵌套格式: stages -> steps (旧格式)
        2. 扁平格式: steps 直接在顶层 (phase-openspec-flow 格式)
        """
        steps = []

        # 格式1: 嵌套 stages -> steps
        if "stages" in self.workflow:
            for stage in self.workflow.get("stages", []):
                stage_id = stage.get("id")
                stage_deps = stage.get("depends_on", [])

                for step_def in stage.get("steps", []):
                    step = self._parse_step(step_def, stage_id, stage_deps)
                    steps.append(step)

        # 格式2: 扁平 steps (phase-openspec-flow 格式)
        elif "steps" in self.workflow:
            workflow_id = self.workflow.get("id", "default")
            for step_def in self.workflow.get("steps", []):
                step = self._parse_flat_step(step_def, workflow_id)
                steps.append(step)

        return steps

    def _parse_flat_step(self, step_def: Dict, workflow_id: str) -> ExecutableStep:
        """解析扁平格式的步骤 (phase-openspec-flow 格式)"""
        step_id = step_def.get("id")

        # 依赖直接从 depends_on 获取
        deps = step_def.get("depends_on", [])

        # 解析输入 - 支持字符串和字典格式
        inputs = []
        inputs_def = step_def.get("inputs", {})
        if isinstance(inputs_def, dict):
            for key, value in inputs_def.items():
                if isinstance(value, str):
                    inputs.append(StepInput(source=value))
        elif isinstance(inputs_def, list):
            for inp in inputs_def:
                if isinstance(inp, str):
                    inputs.append(StepInput(source=inp))
                elif isinstance(inp, dict):
                    for key, value in inp.items():
                        if isinstance(value, str):
                            inputs.append(StepInput(source=value))

        # 解析输出
        outputs = []
        for out in step_def.get("outputs", []):
            if isinstance(out, dict):
                outputs.append(StepOutput(
                    path=out.get("path", ""),
                    contract_ref=out.get("contract"),
                    required=out.get("required", True),
                    freeze=out.get("freeze", False)
                ))
            elif isinstance(out, str):
                outputs.append(StepOutput(path=out))

        # 解析门禁
        gate = None
        human_gate_value = step_def.get("human_gate")
        if human_gate_value:
            # 如果是布尔值 True，自动生成 gate_id
            if human_gate_value is True:
                gate_id = f"{step_id}_gate"
            else:
                gate_id = str(human_gate_value)

            gate_config = self._find_gate_config(gate_id)
            if gate_config:
                gate = GateConfig(
                    gate_id=gate_id,
                    type=gate_config.get("type", "human"),
                    blocking=gate_config.get("required", True),
                    timeout_hours=24,
                    required_roles=[],
                    min_approvals=1
                )
            else:
                gate = GateConfig(gate_id=gate_id, type="human")

        # 是否强制步骤
        mandatory = step_def.get("mandatory", False)

        # 获取 agent/skill 引用
        run_ref = step_def.get("run", "")
        if isinstance(run_ref, dict):
            # selector 格式 - 取第一个作为默认
            run_ref = run_ref.get("fallback", "unknown")

        return ExecutableStep(
            id=step_id,
            name=step_def.get("name", step_id),
            agent_id=run_ref,
            stage_id=workflow_id,
            description=step_def.get("description"),
            deps=deps,
            parallel_with=[],
            inputs=inputs,
            outputs=outputs,
            validators=[],
            gate=gate,
            execution_model="prompt_switch",
            timeout_minutes=60,
            on_error="fail" if mandatory else "skip",
            max_retries=step_def.get("remediation", {}).get("max_attempts", 1),
            skip_condition=step_def.get("condition"),
            skip_reason=None
        )

    def _parse_step(self, step_def: Dict, stage_id: str, stage_deps: List[str]) -> ExecutableStep:
        """解析单个步骤"""
        step_id = step_def.get("id")

        # 解析依赖
        deps_config = step_def.get("dependencies", {})
        deps = deps_config.get("requires", [])
        if step_def.get("depends_on"):  # 兼容旧格式
            deps = step_def.get("depends_on", [])
        parallel_with = deps_config.get("parallel_with", [])

        # 解析输入
        inputs = []
        for inp in step_def.get("inputs", []):
            if isinstance(inp, str):
                inputs.append(StepInput(source=inp))
            elif isinstance(inp, dict):
                for key, value in inp.items():
                    if isinstance(value, str):
                        inputs.append(StepInput(source=value))
                    elif isinstance(value, dict):
                        for k, v in value.items():
                            inputs.append(StepInput(source=v))

        # 解析输出
        outputs = []
        for out in step_def.get("outputs", []):
            if isinstance(out, dict):
                outputs.append(StepOutput(
                    path=out.get("path", ""),
                    contract_ref=out.get("contract"),
                    required=out.get("required", True),
                    freeze=out.get("freeze", False)
                ))
            elif isinstance(out, str):
                outputs.append(StepOutput(path=out))

        # 解析验证器
        validators = []
        validation_config = step_def.get("output_validation", {})
        if validation_config:
            # Schema 验证
            if validation_config.get("contract_ref"):
                validators.append(Validator(
                    type="schema",
                    config={"contract_ref": validation_config["contract_ref"]},
                    fail_action=validation_config.get("on_failure", {}).get("action", "block")
                ))

            # 文件存在性验证
            for artifact in validation_config.get("required_artifacts", []):
                validators.append(Validator(
                    type="file_exists",
                    config={
                        "path": artifact.get("path"),
                        "min_count": artifact.get("min_count", 1)
                    }
                ))

        # 解析门禁
        gate = None
        human_gate_value = step_def.get("human_gate")
        if human_gate_value:
            # 如果是布尔值 True，自动生成 gate_id
            if human_gate_value is True:
                gate_id = f"{step_id}_gate"
            else:
                gate_id = str(human_gate_value)

            # 从 workflow 的 human_in_the_loop 查找配置
            gate_config = self._find_gate_config(gate_id)
            if gate_config:
                gate = GateConfig(
                    gate_id=gate_id,
                    type=gate_config.get("gate", {}).get("type", "human"),
                    blocking=gate_config.get("gate", {}).get("blocking", True),
                    timeout_hours=self._parse_duration(
                        gate_config.get("gate", {}).get("timeout", {}).get("duration", "24h")
                    ),
                    timeout_action=gate_config.get("gate", {}).get("timeout", {}).get("action", "escalate"),
                    required_roles=gate_config.get("gate", {}).get("approval", {}).get("required_roles", []),
                    min_approvals=gate_config.get("gate", {}).get("approval", {}).get("min_approvals", 1)
                )
            else:
                # 默认门禁配置
                gate = GateConfig(gate_id=gate_id, type="human")

        # 解析执行配置
        execution = step_def.get("execution", {})
        execution_model = execution.get("model", "prompt_switch")
        timeout_minutes = self._parse_duration(execution.get("timeout", "60m"), unit="m")

        # 解析错误处理
        on_error_config = step_def.get("on_error", {})
        on_error = on_error_config.get("action", "fail")
        max_retries = on_error_config.get("max_retries", 1)

        # 解析跳过条件
        skip_config = step_def.get("skip_when", {})
        skip_condition = skip_config.get("condition")
        skip_reason = skip_config.get("reason")

        return ExecutableStep(
            id=step_id,
            name=step_def.get("name", step_id),
            agent_id=step_def.get("run", ""),
            stage_id=stage_id,
            description=step_def.get("description"),
            deps=deps,
            parallel_with=parallel_with,
            inputs=inputs,
            outputs=outputs,
            validators=validators,
            gate=gate,
            execution_model=execution_model,
            timeout_minutes=timeout_minutes,
            on_error=on_error,
            max_retries=max_retries,
            skip_condition=skip_condition,
            skip_reason=skip_reason
        )

    def _find_gate_config(self, gate_id: str) -> Optional[Dict]:
        """查找门禁配置"""
        for gate in self.workflow.get("human_in_the_loop", []):
            if gate.get("id") == gate_id:
                return gate
        return None

    def _parse_duration(self, duration: str, unit: str = "h") -> int:
        """解析时长字符串"""
        if not duration:
            return 24 if unit == "h" else 60

        try:
            if duration.endswith("h"):
                hours = int(duration[:-1])
                return hours if unit == "h" else hours * 60
            elif duration.endswith("m"):
                minutes = int(duration[:-1])
                return minutes // 60 if unit == "h" else minutes
            elif duration.endswith("d"):
                days = int(duration[:-1])
                return days * 24 if unit == "h" else days * 24 * 60
            else:
                return int(duration)
        except:
            return 24 if unit == "h" else 60

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """获取依赖图"""
        steps = self.parse()
        graph = {}
        for step in steps:
            graph[step.id] = step.deps
        return graph

    def get_execution_order(self) -> List[List[str]]:
        """获取执行顺序 (考虑并行)"""
        steps = self.parse()
        graph = {s.id: set(s.deps) for s in steps}
        completed = set()
        order = []

        while graph:
            # 找出所有依赖已满足的步骤
            ready = [s for s, deps in graph.items() if deps <= completed]

            if not ready:
                # 检测循环依赖
                raise ValueError(f"Circular dependency detected: {list(graph.keys())}")

            order.append(ready)
            completed.update(ready)
            for s in ready:
                del graph[s]

        return order

    def get_agents(self) -> Dict[str, Dict]:
        """获取所有 Agent 资源"""
        agents = {}
        for layer_name, layer in self.workflow.get("agent_resources", {}).items():
            if isinstance(layer, list):
                for agent in layer:
                    agents[agent.get("id")] = {
                        "name": agent.get("name"),
                        "spec": agent.get("spec"),
                        "execution_model": agent.get("execution_model", {})
                    }
        return agents

    def get_contracts(self) -> Dict[str, str]:
        """获取所有契约引用"""
        contracts = {}

        # 从输入输出契约
        contracts["inputs"] = self.workflow.get("inputs_contract")
        contracts["outputs"] = self.workflow.get("outputs_contract")

        # 从步骤输出
        steps = self.parse()
        for step in steps:
            for out in step.outputs:
                if out.contract_ref:
                    contracts[f"{step.id}:{out.path}"] = out.contract_ref

        return contracts

    def to_executable_yaml(self, output_path: str = None) -> str:
        """导出为可执行 YAML 格式"""
        steps = self.parse()

        executable = {
            "version": "1.0",
            "workflow_id": self.workflow.get("id"),
            "workflow_name": self.workflow.get("name"),
            "execution_order": self.get_execution_order(),
            "steps": {},
            "agents": self.get_agents(),
            "contracts": self.get_contracts()
        }

        for step in steps:
            executable["steps"][step.id] = {
                "name": step.name,
                "agent_id": step.agent_id,
                "stage_id": step.stage_id,
                "deps": step.deps,
                "parallel_with": step.parallel_with,
                "inputs": [{"source": i.source, "required": i.required} for i in step.inputs],
                "outputs": [{"path": o.path, "contract": o.contract_ref} for o in step.outputs],
                "validators": [{"type": v.type, "config": v.config} for v in step.validators],
                "gate": {
                    "id": step.gate.gate_id,
                    "type": step.gate.type,
                    "blocking": step.gate.blocking
                } if step.gate else None,
                "timeout_minutes": step.timeout_minutes,
                "on_error": step.on_error,
                "max_retries": step.max_retries
            }

        yaml_content = yaml.dump(executable, allow_unicode=True, default_flow_style=False, sort_keys=False)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)

        return yaml_content
