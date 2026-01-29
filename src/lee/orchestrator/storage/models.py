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


class TaskExecutionStatus(str, Enum):
    """任务执行状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 已失败


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
    executor_type: str  # llm | shell | mcp | metagpt

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
class Step:
    """
    步骤定义（来自 Template）
    """

    # 标识
    id: str

    # 类型
    kind: str  # agent | skill | human_gate | marker

    # 执行器
    executor_type: str  # llm | shell | mcp | metagpt

    # 依赖
    depends_on: List[str] = field(default_factory=list)

    # 输入
    input: Dict[str, Any] = field(default_factory=dict)

    # 配置
    config: Dict[str, Any] = field(default_factory=dict)


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
