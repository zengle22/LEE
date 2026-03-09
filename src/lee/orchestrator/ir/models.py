"""
LEE Orchestrator IR (Intermediate Representation) Models

spec-global 工作流的中间表示（IR）数据模型。

设计原则：
1. 完整表达 spec-global YAML 的所有结构元素
2. 与执行引擎解耦，IR 不依赖 Orchestrator 具体实现
3. 支持类型检查（mypy strict mode）
4. 提供验证和转换方法
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pathlib import Path

from .expression_adapter import ExpressionAdapterError, get_expression_adapter


# ========================================================================
# 枚举定义
# ========================================================================

class IRKind(Enum):
    """IR 类型枚举"""
    WORKFLOW = "workflow"
    STATE_MACHINE = "state_machine"
    STEP = "step"
    GATE = "gate"
    VARIABLE = "variable"
    CONTRACT = "contract"
    STAGE = "stage"


class StepKind(Enum):
    """步骤类型枚举"""
    AGENT = "agent"
    SKILL = "skill"
    GATE = "gate"
    HUMAN_GATE = "human_gate"
    CONDITIONAL = "conditional"
    WORKFLOW_SPAWN = "workflow_spawn"
    ORCHESTRATOR_CLI = "orchestrator_cli"
    COMPLIANCE_GATE = "compliance_gate"
    MARKER = "marker"


class RuleSeverity(Enum):
    """规则严重性"""
    BLOCKER = "blocker"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class RuleType(Enum):
    """规则类型"""
    MANDATORY = "mandatory"
    THRESHOLD = "threshold"
    RISK_ACCEPTANCE = "risk_acceptance"
    QUALITY_ENHANCEMENT = "quality_enhancement"


# ========================================================================
# 变量引用 IR
# ========================================================================

@dataclass
class VariableIR:
    """
    变量引用中间表示

    支持的引用格式：
    - $inputs.xxx: 工作流输入引用
    - $sX_yyy: 步骤输出引用
    - $context.xxx: 上下文变量引用
    """
    reference: str  # 原始引用字符串，如 "$inputs.prd"
    source_type: str  # "inputs" | "step" | "context"
    path: List[str]  # 解析后的路径，如 ["prd"] 或 ["consistency_matrix", "conflicts"]
    step_id: Optional[str] = None  # 如果引用步骤输出，记录步骤 ID

    def __post_init__(self):
        """验证引用格式"""
        if not self.reference.startswith("$"):
            raise ValueError(f"Invalid variable reference: {self.reference}")

        valid_sources = {"inputs", "step", "context"}
        if self.source_type not in valid_sources:
            raise ValueError(f"Invalid variable source type: {self.source_type}")

    def get_full_step_id(self) -> str:
        """获取完整的步骤 ID（用于 step 输出引用）"""
        if self.source_type == "step" and self.step_id:
            return self.step_id
        return ""


# ========================================================================
# 门禁规则 IR
# ========================================================================

@dataclass
class GateRuleIR:
    """
    门禁规则中间表示

    spec-global 支持三种规则类型：
    - mandatory: 强制标准（0 容忍，不可豁免）
    - threshold: 阈值标准（数据驱动，可警告但允许继续）
    - risk_acceptance: 风险可接受标准（需人类签字）
    """
    rule_id: str
    name: str
    rule_type: RuleType
    rule_expression: str  # 规则表达式，如 "prd.is_frozen == true"
    severity: RuleSeverity
    exemption_allowed: bool
    validation_method: Optional[str] = None
    error_message: Optional[str] = None
    rationale: Optional[str] = None

    def evaluate(self, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        评估单个规则

        Args:
            context: 评估上下文，包含相关数据

        Returns:
            (passed, error_message): 通过标志和错误信息
        """
        adapter = get_expression_adapter()

        try:
            result = adapter.evaluate_gate_rule(
                expression=self.rule_expression,
                context=context,
                validation_method=self.validation_method,
            )
        except ExpressionAdapterError as exc:
            return False, f"规则 '{self.rule_id}' 表达式求值失败: {exc}"

        if result.passed:
            return True, None

        error_message = self.error_message or result.error_message
        if not error_message:
            error_message = f"规则 '{self.rule_id}' 未通过: {self.name}"
        return False, error_message


@dataclass
class ExemptionPolicyIR:
    """豁免策略中间表示"""
    allowed_exemptions: List[str] = field(default_factory=list)  # 可豁免的规则 ID 列表
    max_exemptions: int = 0
    requires_approval: List[str] = field(default_factory=list)  # 需要审批的角色
    requires_documentation: bool = False
    condition: Optional[str] = None

    forbidden_exemptions: List[str] = field(default_factory=list)  # 禁止豁免的规则 ID 列表


@dataclass
class SignoffRequirementIR:
    """签字要求中间表示"""
    required_approvers: List[Dict[str, str]] = field(default_factory=list)
    optional_approvers: List[Dict[str, str]] = field(default_factory=list)
    approval_sla: Optional[str] = None  # 如 "48h"
    inputs_to_review: List[str] = field(default_factory=list)


@dataclass
class GateIR:
    """
    门禁中间表示

    spec-global 的门禁是一个完整的质量规则系统，包含：
    - 强制标准（mandatory_criteria）：0 容忍
    - 阈值标准（threshold_criteria）：可警告但继续
    - 风险可接受标准（risk_acceptance_criteria）：需签字
    - 豁免策略（exemption_policy）
    - 签字要求（signoff_requirements）
    """
    gate_id: str
    name: str
    description: str
    mandatory_criteria: List[GateRuleIR] = field(default_factory=list)
    threshold_criteria: List[GateRuleIR] = field(default_factory=list)
    risk_acceptance_criteria: List[GateRuleIR] = field(default_factory=list)
    exemption_policy: Optional[ExemptionPolicyIR] = None
    signoff_requirements: Optional[SignoffRequirementIR] = None

    def evaluate(self, context: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        评估门禁规则

        Args:
            context: 评估上下文

        Returns:
            (passed, issues): 通过标志和问题列表
        """
        issues = []

        # 评估强制标准（0 容忍）
        for rule in self.mandatory_criteria:
            passed, error = rule.evaluate(context)
            if not passed:
                level = f"[{rule.severity.value.upper()}]"
                issues.append(f"{level} {rule.name}: {error or rule.error_message}")

        # 如果有强制标准失败，直接返回不通过
        if len(issues) > 0:
            return False, issues

        # 评估阈值标准（警告但不阻塞）
        for rule in self.threshold_criteria:
            passed, error = rule.evaluate(context)
            if not passed:
                issues.append(f"[WARNING] {rule.name}: {error or '未达到阈值'}")

        # 评估风险可接受标准
        for rule in self.risk_acceptance_criteria:
            passed, error = rule.evaluate(context)
            if not passed:
                issues.append(f"[RISK] {rule.name}: {error or '需要风险评估'}")

        # 警告不影响通过
        return True, issues

    def check_mandatory_only(self, context: Dict[str, Any]) -> List[str]:
        """只检查强制标准，用于快速验证"""
        issues = []
        for rule in self.mandatory_criteria:
            passed, error = rule.evaluate(context)
            if not passed:
                issues.append(f"[BLOCKER] {rule.name}: {error or rule.error_message}")
        return issues


# ========================================================================
# 契约 IR
# ========================================================================

@dataclass
class ContractIR:
    """
    契约中间表示

    spec-global 的契约定义了工作流的输入和输出契约。
    契约包含：
    - 契约路径（相对于工作流文件）
    - 是否必需
    - 契约描述
    - 结构定义（可选）
    """
    contract_id: str
    kind: str  # "input" | "output"
    path: str
    description: str
    required: bool = True
    structure: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None  # JSON Schema，如果有的话


# ========================================================================
# 状态机 IR
# ========================================================================

@dataclass
class StateTransitionIR:
    """状态转换中间表示"""
    from_state: str
    to_state: str
    trigger: str  # 触发事件
    note: Optional[str] = None
    action: Optional[str] = None  # 转换时执行的动作


@dataclass
class StateMachineIR:
    """
    状态机中间表示

    spec-global 的状态机定义：
    - states: 状态列表
    - transitions: 状态转换规则
    - initial_state: 初始状态

    QA 工作流使用 11 个状态：
    INIT, INPUT_VALIDATION, REQUIREMENT_ALIGNMENT, FEATURE_CALIBRATION,
    BRANCH_COVERAGE_DESIGN, SPECIALIZED_TEST_DESIGN, TEST_CASE_REVIEW,
    REVIEW_REVISION, PLAYWRIGHT_GENERATION, COMPLETED, BLOCKED
    """
    states: List[str]
    transitions: Dict[str, List[StateTransitionIR]]
    initial_state: str = "INIT"

    def get_next_states(self, current_state: str, trigger: str) -> List[str]:
        """
        获取触发后的下一个状态

        Args:
            current_state: 当前状态
            trigger: 触发事件

        Returns:
            可能的下一个状态列表
        """
        if current_state not in self.transitions:
            return []

        next_states = []
        for transition in self.transitions[current_state]:
            if transition.trigger == trigger:
                next_states.append(transition.to_state)

        return next_states

    def is_valid_state(self, state: str) -> bool:
        """检查状态是否有效"""
        return state in self.states

    def is_terminal_state(self, state: str) -> bool:
        """检查是否为终止状态（COMPLETED 或 BLOCKED）"""
        return state in {"COMPLETED", "BLOCKED"}


# ========================================================================
# 步骤 IR
# ========================================================================

@dataclass
class StepInputIR:
    """步骤输入中间表示"""
    name: str
    value: Any  # 可以是常量或 VariableIR
    required: bool = True


@dataclass
class StepOutputIR:
    """步骤输出中间表示"""
    path: str  # 输出文件路径
    type: str = "file"  # "file" | "dir"
    format: str = "text"  # "yaml" | "json" | "markdown" | "text"
    required: bool = True
    description: Optional[str] = None
    include: Optional[List[Dict[str, str]]] = None  # 包含的字段


@dataclass
class StepIR:
    """
    步骤中间表示

    spec-global 的步骤定义非常丰富：
    - id: 步骤标识
    - kind: 步骤类型（agent/skill/human_gate/conditional）
    - run: Agent/Skill 引用
    - condition: 条件表达式（用于 conditional 步骤）
    - inputs: 输入定义（包含变量引用）
    - outputs: 输出定义
    - gate: 门禁引用
    - on_failure: 失败处理策略
    """
    id: str
    kind: StepKind
    name: str
    description: str
    stage_id: Optional[str] = None  # 所属的 stage ID

    # 执行配置
    agent_id: Optional[str] = None  # 如 "agent.qa.requirement_alignment_agent"
    skill_id: Optional[str] = None  # 如 "skill.qa.ui_contract_analyzer"
    executor_type: Optional[str] = None  # "llm" | "shell" | "mcp"
    execution: Optional[Dict[str, Any]] = None

    # 依赖和条件
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[str] = None  # 条件表达式，如 "consistency_matrix.conflicts > 0"
    parallel_with: List[str] = field(default_factory=list)

    # 输入输出
    inputs: List[StepInputIR] = field(default_factory=list)
    outputs: List[StepOutputIR] = field(default_factory=list)

    # 门禁
    gate: Optional[GateIR] = None  # 内联门禁
    gate_ref: Optional[str] = None  # 外部门禁引用，如 "gate.qa.design_input_gate"
    post_gate: Optional[GateIR] = None
    human_gate: Optional[str] = None

    # 错误处理
    on_failure: Optional[Dict[str, Any]] = None  # 失败处理策略

    # 其他配置
    config: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None  # 超时时间（秒）

    # L3 跨工作流收敛循环（用于 L2 的 workflow_spawn 步骤）
    cross_workflow_loop: Optional['CrossWorkflowLoopIR'] = None

    def is_ready(self, completed_steps: List[str], context: Dict[str, Any]) -> bool:
        """
        检查步骤是否就绪（可以执行）

        Args:
            completed_steps: 已完成的步骤列表
            context: 执行上下文（包含变量值）

        Returns:
            是否就绪
        """
        # 检查依赖
        for dep in self.depends_on:
            if dep not in completed_steps:
                return False

        # 检查条件
        if self.condition:
            if not self._evaluate_condition(context):
                return False

        return True

    def _evaluate_condition(self, context: Dict[str, Any]) -> bool:
        """
        评估条件表达式

        TODO: P1 阶段实现完整的表达式求值
        当前简化版本：返回 True
        """
        if not self.condition:
            return True

        adapter = get_expression_adapter()
        try:
            return adapter.evaluate_condition(self.condition, context)
        except ExpressionAdapterError:
            return False

    def get_agent_ref(self) -> Optional[str]:
        """获取 Agent 引用"""
        return self.agent_id

    def get_skill_ref(self) -> Optional[str]:
        """获取 Skill 引用"""
        return self.skill_id


# ========================================================================
# Loop Config IR
# ========================================================================

@dataclass
class LoopConfigIR:
    """
    循环配置中间表示

    用于 Stage 级别的自动修复循环：
    patch → test → analyze → retry，带收敛检测。

    也支持变量循环（如遍历 effective_test_sets）：
        loop:
          enabled: true
          over: "$runtime.effective_test_sets"  # 循环变量源
          as: "current_test_set"                # 循环变量名
          max_iterations: 3
          stop_on_same_output: true

    YAML 示例 (自动修复循环):
        loop:
          enabled: true
          max_iterations: 3
          stop_on_same_output: true
          completion_check_step: run_tests
          completion_status: passed

    YAML 示例 (变量循环):
        loop:
          enabled: true
          over: "$runtime.effective_test_sets"
          as: "current_test_set"
          max_iterations: 3
    """
    enabled: bool = False
    max_iterations: int = 3

    # 变量循环支持（新增）
    over: Optional[str] = None  # 循环变量源，如 "$runtime.effective_test_sets"
    as_var: Optional[str] = None  # 循环变量名，如 "current_test_set"

    # 收敛检测
    stop_on_same_output: bool = True       # 检测到相同输出时停止
    # 完成条件
    completion_check_step: Optional[str] = None  # 用哪个步骤的结果判断通过
    completion_status: str = "passed"             # 期望的通过状态值


# ========================================================================
# Cross-Workflow Loop IR（L3 跨工作流收敛循环）
# ========================================================================

@dataclass
class CrossWorkflowLoopConvergenceIR:
    """
    收敛判定条件

    决定循环何时停止的标准：
    - check_phase: 检查哪个 phase 的输出
    - check_field: 用输出中的哪个字段判定
    - pass_values: 哪些值视为通过
    - secondary_check: 辅助收敛条件表达式
    """
    check_phase: str = ""                        # 检查哪个 phase 的输出
    check_field: str = "exit_decision"           # 输出中的判定字段
    pass_values: List[str] = field(default_factory=lambda: ["pass", "conditional_pass"])
    secondary_check: Optional[str] = None        # 辅助条件，例如 "open_bug_count == 0"


@dataclass
class CrossWorkflowLoopPhaseIR:
    """
    循环中的一个阶段定义

    每个 phase 对应一次 L3 workflow_spawn：
    - qa_test phase: spawn QA-L3 执行测试
    - dev_fix phase: spawn Dev-L3 修复 bug
    """
    id: str = ""                                 # phase 标识
    workflow_ref: str = ""                       # 引用的工作流 ID
    role: str = ""                               # 角色标识 (tester/fixer)
    condition: Optional[str] = None              # 执行条件表达式
    inputs_from: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class CrossWorkflowLoopIR:
    """
    L3 跨工作流收敛循环配置

    在 L2 层管理 QA-L3 ↔ Dev-L3 的乒乓循环直到 bug 收敛清零。

    YAML 示例:
        cross_workflow_loop:
          enabled: true
          max_rounds: 3
          phases:
            - id: qa_test
              workflow_ref: workflow.qa.test_plan_execution_v1
              role: tester
            - id: dev_fix
              workflow_ref: workflow.dev.bug_fix
              role: fixer
              condition: "qa_test.exit_decision == 'fail'"
          convergence:
            check_phase: qa_test
            check_field: exit_decision
            pass_values: [pass, conditional_pass]
          on_exceeded:
            action: human_gate
    """
    enabled: bool = False
    max_rounds: int = 3

    # 循环阶段序列
    phases: List[CrossWorkflowLoopPhaseIR] = field(default_factory=list)

    # 收敛条件
    convergence: Optional[CrossWorkflowLoopConvergenceIR] = None

    # 超限行为
    on_exceeded: str = "human_gate"              # human_gate | abort | skip
    on_exceeded_message: str = "Bug 收敛循环超过最大轮次，需人类介入"
    human_gate_ref: Optional[str] = None


# ========================================================================
# Stage IR
# ========================================================================

@dataclass
class StageIR:
    """
    阶段中间表示

    spec-global 的 stage 是步骤的逻辑分组：
    - id: 阶段标识
    - name: 阶段名称
    - description: 阶段描述
    - steps: 阶段包含的步骤列表
    """
    id: str
    name: str
    description: str
    steps: List[StepIR] = field(default_factory=list)
    loop: Optional[LoopConfigIR] = None

    def get_step_by_id(self, step_id: str) -> Optional[StepIR]:
        """根据 ID 获取步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_all_step_ids(self) -> List[str]:
        """获取所有步骤 ID"""
        return [step.id for step in self.steps]


# ========================================================================
# 工作流 IR（顶层）
# ========================================================================

@dataclass
class HumanInTheLoopIR:
    """人类介入中间表示"""
    name: str  # 人类介入点名称
    stage: str  # 触发阶段
    step: str  # 触发步骤
    type: str  # "approval" | "review" | "decision"
    timeout: Optional[int] = None  # 超时时间（小时）
    approval_criteria: Optional[Dict[str, Any]] = None
    escalation_policy: Optional[Dict[str, Any]] = None


@dataclass
class ErrorHandlingIR:
    """错误处理中间表示"""
    error_scenario: str
    action: str  # "block_and_report" | "retry" | "escalate" | "partial_delivery"
    target_state: Optional[str] = None  # 目标状态
    retry_config: Optional[Dict[str, Any]] = None  # 重试配置


@dataclass
class ObservabilityIR:
    """可观测性中间表示"""
    metrics: List[str] = field(default_factory=list)
    dashboards: List[str] = field(default_factory=list)
    alerts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkflowIR:
    """
    工作流中间表示（顶层）

    spec-global 工作流的完整中间表示，包含：
    - 基本信息：id, kind, version, name, description
    - 契约：inputs, outputs
    - 状态机：state_machine
    - 结构：stages, steps
    - 门禁：gates
    - 人类介入：human_in_the_loop
    - 错误处理：error_handling
    - 可观测性：observability
    """
    # 基本信息
    id: str
    kind: str  # "workflow"
    version: str
    name: str
    description: str
    owner: str = ""
    tags: List[str] = field(default_factory=list)

    # 契约
    inputs: List[ContractIR] = field(default_factory=list)
    outputs: List[ContractIR] = field(default_factory=list)

    # 状态机
    state_machine: Optional[StateMachineIR] = None

    # 结构（stages 和 steps 二选一，或者同时存在）
    stages: List[StageIR] = field(default_factory=list)
    steps: List[StepIR] = field(default_factory=list)

    # 门禁
    gates: Dict[str, GateIR] = field(default_factory=dict)

    # 人类介入
    human_in_the_loop: List[HumanInTheLoopIR] = field(default_factory=list)

    # 错误处理
    error_handling: Dict[str, ErrorHandlingIR] = field(default_factory=dict)

    # 可观测性
    observability: Optional[ObservabilityIR] = None

    # 其他配置
    concepts: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    # ========================================================================
    # 查询方法
    # ========================================================================

    def get_step_by_id(self, step_id: str) -> Optional[StepIR]:
        """根据 ID 获取步骤（先在 stages 中查找，再在 steps 中查找）"""
        # 先在 stages 中查找
        for stage in self.stages:
            step = stage.get_step_by_id(step_id)
            if step:
                return step

        # 再在顶层 steps 中查找
        for step in self.steps:
            if step.id == step_id:
                return step

        return None

    def get_gate_by_id(self, gate_id: str) -> Optional[GateIR]:
        """根据 ID 获取门禁"""
        return self.gates.get(gate_id)

    def get_ready_steps(self, completed_steps: List[str], context: Dict[str, Any]) -> List[StepIR]:
        """
        获取就绪的步骤列表

        Args:
            completed_steps: 已完成的步骤 ID 列表
            context: 执行上下文

        Returns:
            就绪的步骤列表
        """
        ready = []

        # 收集所有步骤（从 stages 和顶层 steps）
        all_steps = []
        for stage in self.stages:
            all_steps.extend(stage.steps)
        all_steps.extend(self.steps)

        for step in all_steps:
            if step.is_ready(completed_steps, context):
                ready.append(step)

        return ready

    def get_initial_state(self) -> str:
        """获取初始状态"""
        if self.state_machine:
            return self.state_machine.initial_state
        return "INIT"

    def get_all_step_ids(self) -> List[str]:
        """获取所有步骤 ID"""
        all_ids = []
        for stage in self.stages:
            all_ids.extend(stage.get_all_step_ids())
        all_ids.extend([step.id for step in self.steps])
        return all_ids

    def get_required_inputs(self) -> List[ContractIR]:
        """获取所有必需的输入契约"""
        return [c for c in self.inputs if c.required]

    def validate(self) -> List[str]:
        """
        验证工作流 IR 的完整性

        Returns:
            错误信息列表（空列表表示无错误）
        """
        errors = []

        # 验证基本信息
        if not self.id:
            errors.append("Missing workflow ID")
        if self.kind != "workflow":
            errors.append(f"Invalid kind: {self.kind}, expected 'workflow'")

        # 验证必需的输入契约
        for contract in self.get_required_inputs():
            if not contract.path:
                errors.append(f"Input contract {contract.contract_id} missing path")

        # 验证步骤 ID 唯一性
        all_ids = self.get_all_step_ids()
        duplicates = [id for id in all_ids if all_ids.count(id) > 1]
        if duplicates:
            errors.append(f"Duplicate step IDs: {set(duplicates)}")

        # 验证状态机（如果存在）
        if self.state_machine:
            for state in self.state_machine.states:
                if not self.state_machine.is_valid_state(state):
                    errors.append(f"Invalid state in state machine: {state}")

        # 验证门禁引用
        for stage in self.stages:
            for step in stage.steps:
                if step.gate_ref and step.gate_ref not in self.gates:
                    errors.append(f"Step {step.id} references unknown gate: {step.gate_ref}")

        for step in self.steps:
            if step.gate_ref and step.gate_ref not in self.gates:
                errors.append(f"Step {step.id} references unknown gate: {step.gate_ref}")

        return errors


# ========================================================================
# IR 转换辅助函数
# ========================================================================

def flatten_stages_to_steps(stages: List[StageIR]) -> List[StepIR]:
    """
    将 stages 展平为步骤列表

    Args:
        stages: Stage IR 列表

    Returns:
        Step IR 列表（展平后）
    """
    steps = []
    for stage in stages:
        for step in stage.steps:
            # 确保 stage_id 被记录
            if not step.stage_id:
                step.stage_id = stage.id
            steps.append(step)
    return steps


def extract_variable_references(inputs: List[StepInputIR]) -> List[VariableIR]:
    """
    从步骤输入中提取所有变量引用

    Args:
        inputs: StepInputIR 列表

    Returns:
        VariableIR 列表
    """
    refs = []
    for inp in inputs:
        if isinstance(inp.value, str) and inp.value.startswith("$"):
            # 简单解析，实际应使用 VariableResolver
            if inp.value.startswith("$inputs."):
                path = inp.value[8:].split(".")
                refs.append(VariableIR(
                    reference=inp.value,
                    source_type="inputs",
                    path=path
                ))
            elif inp.value.startswith("$s"):
                # 步骤输出引用
                parts = inp.value[1:].split("_")
                if len(parts) >= 2:
                    step_id = f"{parts[0]}_{parts[1]}"
                    path = parts[2:] if len(parts) > 2 else []
                    refs.append(VariableIR(
                        reference=inp.value,
                        source_type="step",
                        path=path,
                        step_id=step_id
                    ))
    return refs
