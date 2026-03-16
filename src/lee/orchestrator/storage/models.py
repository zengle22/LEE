"""
LEE Orchestrator v3.0 - 统一数据模型

本模块定义了 LEE Orchestrator v3.0 的核心数据模型，
采用"统一三层 Workflow"设计，通过 level 和 parent_id 区分层级。

核心原则：
- 单一 WorkflowInstance 模型表达 L1/L2/L3
- SQLite 是唯一状态权威
- 权力边界清晰：Orchestrator > Executor > Tool
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


# ========================================================================
# 枚举定义
# ========================================================================

class WorkflowLevel(str, Enum):
    """工作流层级"""
    PROJECT = "project"      # L1: 项目级
    DEPARTMENT = "department"  # L2: 部门级
    TASK = "task"           # L3: 任务级


class WorkflowStatus(str, Enum):
    """工作流状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    PAUSED = "paused"        # 已暂停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 已失败
    SUPERSEDED = "superseded"  # v1.1: 被新工作流替代


class TaskExecutionStatus(str, Enum):
    """任务执行状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 已失败
    INVALIDATED = "invalidated"  # 已作废（rewind/retry 后的旧执行记录）


# ========================================================================
# 核心数据模型
# ========================================================================

@dataclass
class WorkflowInstance:
    """
    统一的工作流实例模型（L1/L2/L3）

    关键设计：
    - 通过 level 区分层级
    - 通过 parent_id 表达嵌套关系
    - 单表设计，统一建模
    """

    # 标识
    id: str
    level: WorkflowLevel
    parent_id: Optional[str] = None

    # 模板
    template_id: str = ""

    # 状态
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: Optional[str] = None

    # 数据
    data: Dict[str, Any] = field(default_factory=dict)
    """
    数据字典，包含：
    - params: 创建时的参数
    - completed_steps: 已完成的步骤列表
    - last_output: 最后一次执行输出
    - current_step: 当前执行的步骤
    - 其他业务数据
    """

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        """初始化后处理"""
        # 确保 data 中有必要的字段
        if "completed_steps" not in self.data:
            self.data["completed_steps"] = []
        if "params" not in self.data:
            self.data["params"] = {}


@dataclass
class TaskExecution:
    """
    任务执行记录
    """

    # 标识
    id: str
    workflow_id: str
    step_name: str

    # 执行器
    executor_type: str  # llm | shell | mcp | claude_code | codex | langgraph

    # 输入输出
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None

    # 状态
    status: TaskExecutionStatus = TaskExecutionStatus.PENDING
    error_message: Optional[str] = None

    # 时间戳
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Template:
    """
    工作流模板
    """

    # 标识
    id: str
    level: WorkflowLevel
    name: str

    # 模板内容
    content: str  # YAML 格式的模板定义

    # 元数据
    description: str = ""
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OutputSpec:
    """
    输出规格定义
    """
    type: str  # file | dir
    path: str
    format: str  # yaml | json | markdown | text
    required: bool = True
    description: str = ""
    symbol: Optional[str] = None
    contract: Optional[str] = None
    freeze: bool = False
    ssot: Optional[Dict[str, Any]] = None


@dataclass
class Step:
    """
    步骤定义（来自 Template）

    v1.4 更新：
    - 添加 agent_id/skill_id/gate_id 支持
    - 添加 outputs 规格支持
    - 保留 executor_type 用于运行时
    """

    # 标识
    id: str

    # 类型
    kind: str  # agent | skill | human_gate | marker

    # 执行器类型（运行时决定，或由 agent/skill 映射）
    executor_type: Optional[str] = None  # llm | shell | mcp | claude_code | codex | langgraph

    # Agent/Skill/Gate 引用（v1.4 新增）
    agent_id: Optional[str] = None
    skill_id: Optional[str] = None
    gate_id: Optional[str] = None  # post_gate 的 ID

    # 依赖
    depends_on: List[str] = field(default_factory=list)

    # 输入（v1.4 统一结构）
    input: Dict[str, Any] = field(default_factory=dict)
    # input 结构示例：
    # {
    #   "context_files": [
    #     {"path": "...", "required": True, "from_step": "..."}
    #   ],
    #   "params": {...}
    # }

    # 输出规格（v1.4 新增）
    outputs: List[OutputSpec] = field(default_factory=list)

    # 配置
    config: Dict[str, Any] = field(default_factory=dict)

    # 失败策略（由 Orchestrator FailureHandler 消费）
    on_failure: Optional[Dict[str, Any]] = None

    # 兼容字段（历史测试/模板会传入 name）
    name: str = ""


# ========================================================================
# 状态相关数据类
# ========================================================================

@dataclass
class WorkflowState:
    """
    工作流当前状态（对外查询用）
    """
    workflow_id: str
    level: WorkflowLevel
    status: WorkflowStatus
    current_step: Optional[str] = None
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)  # 子工作流 ID 列表
    data: Dict[str, Any] = field(default_factory=dict)
    template_id: Optional[str] = None


@dataclass
class StepResult:
    """
    步骤执行结果
    """
    status: str  # success | failed | blocked | no_ready_step
    step_id: Optional[str]
    workflow_id: str
    message: str
    blocked_reason: Optional[str] = None  # v1.4: 阻塞原因
    next_steps: List[str] = field(default_factory=list)
    output: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionSummary:
    """
    执行摘要（用于 run_until_blocked）
    """
    workflow_id: str
    total_steps: int
    completed_steps: int
    blocked_at: Optional[str]  # 阻塞的 step ID
    status: str
    duration_seconds: float


# ========================================================================
# Gate 相关数据模型
# ========================================================================

class GateStatus(str, Enum):
    """门禁状态"""
    PENDING = "pending"      # 待审批
    APPROVED = "approved"    # 已批准
    REJECTED = "rejected"    # 已拒绝
    REVISED = "revised"      # v1.1: 要求修改
    FLAGGED = "flagged"      # v1.1: 标记问题
    INVALIDATED = "invalidated"  # v1.1: 已作废


class ConcurrentDecisionError(Exception):
    """并发决策冲突异常（v1.1）"""
    pass


@dataclass
class GateApproval:
    """
    门禁审批记录

    v1.1 更新：
    - 添加 version 字段用于乐观锁
    - 添加默认 action 字段
    - 添加决策 action 字段
    - 添加结构化反馈字段
    - 添加作废标记
    """
    workflow_id: str
    gate_id: str
    step_id: str
    status: GateStatus = GateStatus.PENDING
    approver: Optional[str] = None
    comments: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None

    # 审批标准（从 workflow.yaml 复制）
    approval_criteria: List[Dict[str, Any]] = field(default_factory=list)
    # 审批人列表（从 workflow.yaml 复制）
    reviewers: List[Dict[str, str]] = field(default_factory=list)

    # === v1.1 新增字段 ===

    # 乐观锁版本号
    version: int = 1

    # 默认 action（创建 gate 时从配置写入）
    default_reject_action: Optional[str] = None
    default_reject_target: Optional[str] = None
    default_revise_action: Optional[str] = None
    default_revise_target: Optional[str] = None

    # 实际决策 action
    decision_action: Optional[str] = None
    target_step: Optional[str] = None

    # 结构化反馈
    structured_feedback: Optional[Dict[str, Any]] = None
    issues: Optional[List[str]] = None

    # 作废标记
    invalidated_at: Optional[datetime] = None


@dataclass
class GateInfo:
    """
    门禁信息（对外查询用）
    """
    gate_id: str
    workflow_id: str
    step_id: str
    status: GateStatus
    reviewers: List[Dict[str, str]]
    approval_criteria: List[Dict[str, Any]]
    approver: Optional[str] = None
    comments: Optional[str] = None
    created_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None


# ========================================================================
# L2/L3 Workflow Template System Models (P0)
# ========================================================================

class Complexity(str, Enum):
    """Task complexity for L2 phase routing.

    Used to determine execution strategy:
    - S (Simple): Direct execution via helper functions
    - M (Medium): Spawn single L3 instance
    - L (Large): PMA split, spawn multiple L3 instances
    """
    S = "S"  # Simple: direct execution
    M = "M"  # Medium: spawn single L3
    L = "L"  # Large: PMA split, spawn multiple L3s


@dataclass
class Point:
    """PMA-generated feature point.

    Represents a single implementable unit derived from splitting
    a complex L2 phase. Each point becomes an L3 instance.

    Attributes:
        id: Unique point identifier (e.g., "frontend_dev-p1")
        title: Human-readable point title
        desc: Detailed description of what to implement
        layer: Architecture layer (ui, state, api, service)
        estimated_complexity: Expected implementation complexity
        files_hint: Suggested file paths to modify
        depends_on: List of point IDs this point depends on
    """
    id: str
    title: str
    desc: str
    layer: str  # ui, state, api, service
    estimated_complexity: Complexity
    files_hint: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
