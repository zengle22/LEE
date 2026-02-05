"""
LEE Orchestrator IR (Intermediate Representation)

spec-global 工作流的中间表示（IR）模块。

这个模块定义了从 spec-global YAML 解析出的数据结构，
作为 YAML 和执行引擎之间的桥梁。
"""

from lee.orchestrator.ir.models import (
    # 枚举
    IRKind,
    StepKind,
    RuleSeverity,
    RuleType,
    # IR 模型
    VariableIR,
    GateRuleIR,
    ExemptionPolicyIR,
    SignoffRequirementIR,
    GateIR,
    ContractIR,
    StateTransitionIR,
    StateMachineIR,
    StepInputIR,
    StepOutputIR,
    StepIR,
    StageIR,
    HumanInTheLoopIR,
    ErrorHandlingIR,
    ObservabilityIR,
    WorkflowIR,
    # 辅助函数
    flatten_stages_to_steps,
    extract_variable_references,
)

__all__ = [
    # 枚举
    "IRKind",
    "StepKind",
    "RuleSeverity",
    "RuleType",
    # IR 模型
    "VariableIR",
    "GateRuleIR",
    "ExemptionPolicyIR",
    "SignoffRequirementIR",
    "GateIR",
    "ContractIR",
    "StateTransitionIR",
    "StateMachineIR",
    "StepInputIR",
    "StepOutputIR",
    "StepIR",
    "StageIR",
    "HumanInTheLoopIR",
    "ErrorHandlingIR",
    "ObservabilityIR",
    "WorkflowIR",
    # 辅助函数
    "flatten_stages_to_steps",
    "extract_variable_references",
]
