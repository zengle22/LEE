"""
LEE Orchestrator Execution - 执行层模块
"""

from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.state_machine import WorkflowStateMachine, StateTransition
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.execution.gate_api import GateAPI
from lee.orchestrator.execution.executors import ExecutorFactory, BaseExecutor
from lee.orchestrator.execution.langgraph_executor import LangGraphExecutor, register_langgraph_executor
from lee.orchestrator.execution.claude_code_executor import ClaudeCodeExecutor, register_claude_code_executor

# Agent 系统（从 v1 迁移）
from lee.orchestrator.execution.agent_loader import AgentLoader, AgentSpec
from lee.orchestrator.execution.agent_injector import AgentContext, InjectorRegistry

# 追踪系统（从 v1 迁移）
from lee.orchestrator.execution.trace import (
    Span, Artifact, Run, TraceContext, TraceLog,
    SpanType, SpanStatus, RunStatus, ArtifactType,
    compute_hash, generate_id, sanitize as trace_sanitize,
)

# 重试机制（从 v1 迁移）
from lee.orchestrator.execution.retry import (
    RetryPolicy, RetryExecutor, RetryAttempt, RetryResult, RetryErrorType,
    DEFAULT_RETRY_POLICY, FAST_FAIL_POLICY, AGGRESSIVE_RETRY_POLICY,
    execute_with_retry, execute_step_with_retry,
    can_retry_step, prepare_step_retry,
)

__all__ = [
    # 核心
    "Orchestrator",
    "WorkflowStateMachine",
    "StateTransition",
    "TemplateManager",
    "GateAPI",
    "ExecutorFactory",
    "BaseExecutor",
    "LangGraphExecutor",
    "register_langgraph_executor",
    "ClaudeCodeExecutor",
    "register_claude_code_executor",
    # Agent 系统
    "AgentLoader",
    "AgentSpec",
    "AgentContext",
    "InjectorRegistry",
    # 追踪系统
    "Span",
    "Artifact",
    "Run",
    "TraceContext",
    "TraceLog",
    "SpanType",
    "SpanStatus",
    "RunStatus",
    "ArtifactType",
    "compute_hash",
    "generate_id",
    "trace_sanitize",
    # 重试机制
    "RetryPolicy",
    "RetryExecutor",
    "RetryAttempt",
    "RetryResult",
    "RetryErrorType",
    "DEFAULT_RETRY_POLICY",
    "FAST_FAIL_POLICY",
    "AGGRESSIVE_RETRY_POLICY",
    "execute_with_retry",
    "execute_step_with_retry",
    "can_retry_step",
    "prepare_step_retry",
]

# 自动注册执行器
register_langgraph_executor()
register_claude_code_executor()
