"""
兼容性重定向: flowcore.orchestrator -> lee.orchestrator.execution

⚠️ 已弃用: 请直接从 lee.orchestrator.execution 导入
"""
import warnings

warnings.warn(
    "flowcore.orchestrator 已弃用，"
    "请使用 from lee.orchestrator.execution import ...",
    DeprecationWarning,
    stacklevel=2,
)

# 重定向所有导出
from lee.orchestrator.execution import (
    Orchestrator,
    WorkflowStateMachine,
    StateTransition,
    TemplateManager,
    GateAPI,
    run_workflow,
    WorkflowRunner,
    WorkflowRunConfig,
    WorkflowRunResult,
    PlanAgent,
    PlanConfig,
    PlanResult,
    create_plan,
)

__all__ = [
    "Orchestrator",
    "WorkflowStateMachine",
    "StateTransition",
    "TemplateManager",
    "GateAPI",
    "run_workflow",
    "WorkflowRunner",
    "WorkflowRunConfig",
    "WorkflowRunResult",
    "PlanAgent",
    "PlanConfig",
    "PlanResult",
    "create_plan",
]
