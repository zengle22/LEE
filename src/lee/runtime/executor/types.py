"""
LEE Executor 核心类型定义

定义 Orchestrator -> Executor 之间的统一数据契约。

Version: MVP v2
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TypedDict
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ExecutorTaskSpec:
    """
    Executor 任务规格

    Orchestrator 填写此规格并传递给 Executor.run_task()
    """
    # 基础标识
    task_id: str                           # 任务唯一标识
    task_type: str                         # 任务类型，映射到 Graph Builder

    # 输入输出映射（逻辑名 -> 真实路径）
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)

    # 执行参数
    params: Dict[str, Any] = field(default_factory=dict)

    # LLM 配置
    llm_profile: Optional[str] = None         # LLM Profile 名称
    llm_temperature: Optional[float] = None   # LLM 温度
    llm_max_tokens: Optional[int] = None      # LLM 最大 token

    # 约束配置
    timeout_seconds: int = 3600              # 超时时间
    max_retries: int = 3                     # 最大重试次数

    # 上下文信息
    context: Dict[str, Any] = field(default_factory=dict)

    # 追踪信息
    trace_id: Optional[str] = None             # 关联 Execution Trace
    parent_span_id: Optional[str] = None       # 父 Span ID

    # 安全边界
    workspace_root: Optional[str] = None       # 工作区根目录
    allowed_write_patterns: List[str] = field(default_factory=list)

    # Repo 管理
    repo_id: Optional[str] = None              # 目标 repo_id（由 runtime 解析为 cwd）
    repo_scope: List[str] = field(default_factory=list)  # 允许的 repo_id 列表


@dataclass
class ExecutionResult:
    """
    Executor 执行结果

    Executor 返回给 Orchestrator 的统一出参
    """
    task_id: str
    status: TaskStatus
    message: str                            # 状态描述

    # 产物信息
    artifacts: Dict[str, str] = field(default_factory=dict)
    artifact_metadata: Dict[str, Any] = field(default_factory=dict)

    # 执行日志
    logs: List[str] = field(default_factory=list)
    error_details: Optional[str] = None

    # 度量信息
    metrics: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    tokens_used: int = 0
    retry_count: int = 0

    # 时间戳
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 自由扩展字段
    extra: Dict[str, Any] = field(default_factory=dict)


# ============================================
# Graph State 类型定义
# ============================================

class BaseState(TypedDict, total=False):
    """
    LangGraph State 的基础类型

    所有 Graph 的 State 都应该包含这些基础字段。
    """
    task: ExecutorTaskSpec               # 任务规格（入参）
    logs: List[str]                      # 执行日志
    errors: List[str]                    # 错误日志
    current_step: str                    # 当前步骤名，初始为 "start"
    retry_count: int                     # 重试次数，初始为 0
    started_at: datetime                 # 开始时间
    completed_at: datetime               # 完成时间（可选）
    metrics: Dict[str, Any]              # 执行过程中收集的指标
    tokens_used: int                     # 累计 token 消耗
    should_stop: bool                    # 是否应该停止执行
    exec_result: ExecutionResult         # 最终执行结果


class ImplCodingState(BaseState, total=False):
    """实现类任务 State"""
    inputs: Dict[str, str]               # 加载的输入内容
    prd: str                             # PRD 内容
    design: str                          # 设计文档内容
    contract: str                        # 实现契约内容
    impl_plan: str                       # 实现方案
    code_changes: Dict[str, str]         # 代码变更（文件路径 -> 内容）


class UnitTestState(BaseState, total=False):
    """单元测试任务 State"""
    test_command: str                    # 测试命令
    test_config: Dict[str, Any]          # 测试配置
    test_report: str                     # 测试报告内容
    test_results: Dict[str, Any]         # 测试结果
