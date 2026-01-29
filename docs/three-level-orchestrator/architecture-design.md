# LEE Orchestrator 三层流程架构设计文档

> **版本**: v1.0
> **状态**: Design
> **创建日期**: 2026-01-25
> **目标版本**: LEE Orchestrator v3.0
> **作者**: Backend System Architect

---

## 目录

1. [架构总览](#1-架构总览)
2. [整体系统架构](#2-整体系统架构)
3. [核心模块设计](#3-核心模块设计)
4. [数据模型设计](#4-数据模型设计)
5. [API 接口定义](#5-api-接口定义)
6. [状态转换设计](#6-状态转换设计)
7. [并发控制设计](#7-并发控制设计)
8. [序列图](#8-序列图)
9. [性能优化策略](#9-性能优化策略)
10. [向后兼容与迁移](#10-向后兼容与迁移)
11. [部署架构](#11-部署架构)
12. [监控与可观测性](#12-监控与可观测性)

---

## 1. 架构总览

### 1.1 设计原则

本架构遵循以下核心原则：

#### P1. 统一状态机管理

只有 Orchestrator 可以修改状态，所有外部调用通过窄接口：

```python
# 核心约束：所有状态变更必须通过 Orchestrator
class OrchestratorCore:
    def update_status(self, instance_id: str, new_status: WorkflowStatus):
        """内部方法，外部不可直接调用"""
        pass
```

#### P2. 统一数据模型

所有层级使用同一套 `WorkflowInstance`，通过 `level` 字段区分：

```python
@dataclass
class WorkflowInstance:
    id: str
    level: Literal[1, 2, 3]  # 层级标识
    kind: Literal["project_master", "department", "task"]
    status: WorkflowStatus
    # ... 其他字段统一
```

#### P3. 事件驱动架构

层级之间通过事件松耦合：

```python
# L1 → L2: 通过 department_flow 事件触发
# L2 → L3: 通过 spawn_tasks 事件创建
# L3 → L2: 通过 completion 事件聚合
```

#### P4. 模板驱动

Level-3 基于模板创建，支持参数化和复用。

### 1.2 架构分层图

```
┌──────────────────────────────────────────────────────────────────┐
│                      用户交互层                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ PM Agent     │  │ Gate UI      │  │ CLI Tools    │           │
│  │ (Claude Code)│  │ (Web UI)     │  │ (lee CLI)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────────────────────┬─────────────────────────────────────┘
                             │ 窄接口调用
┌────────────────────────────▼─────────────────────────────────────┐
│                      API 网关层                                    │
│  ┌────────────────────────────────────────────────────────┐      │
│  │           Orchestrator API (Narrow Interface)           │      │
│  │  - get_state()  - run_step()  - pause_workflow()       │      │
│  │  - spawn_workflow()  - gate_decision()                  │      │
│  └────────────────────────────────────────────────────────┘      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                   核心编排层 (Orchestrator Core)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ StateMachine │  │TemplateEngine│  │ SpawnEngine  │           │
│  │              │  │              │  │              │           │
│  │ - 状态管理    │  │ - 模板加载    │  │ - 任务创建    │           │
│  │ - 状态转换    │  │ - 参数化      │  │ - 队列管理    │           │
│  │ - 状态验证    │  │ - 版本控制    │  │ - 并发控制    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  EventBus    │  │AggregationEng│  │ GateEngine   │           │
│  │              │  │              │  │              │           │
│  │ - 事件发布    │  │ - 状态聚合    │  │ - 门禁管理    │           │
│  │ - 事件订阅    │  │ - 完成判断    │  │ - 决策记录    │           │
│  │ - 事件传播    │  │ - 层级同步    │  │ - 权限控制    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────────────────────┬─────────────────────────────────────┘
                             │ StepExecutionRequest
┌────────────────────────────▼─────────────────────────────────────┐
│                   执行引擎层 (Engines/Executors)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ LLMEngine    │  │ShellEngine   │  │ MCP Engine   │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                     外部系统集成层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ LLM Providers│  │ CI/CD        │  │ MCP Servers  │           │
│  │ (OpenAI etc) │  │ (GitHub etc) │  │ (Figma etc)  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└──────────────────────────────────────────────────────────────────┘
```

### 1.3 核心组件职责

| 组件 | 职责 | 依赖 |
|------|------|------|
| **OrchestratorCore** | 统一状态机管理，唯一的状态修改入口 | StateMachine, TemplateEngine, SpawnEngine |
| **StateMachine** | 状态转换验证、状态存储、状态查询 | Storage层 |
| **TemplateEngine** | 模板加载、参数化、版本管理 | Storage层 |
| **SpawnEngine** | L3实例创建、队列管理、并发控制 | StateMachine, TemplateEngine |
| **EventBus** | 事件发布订阅、跨层级事件传播 | StateMachine |
| **AggregationEngine** | 状态聚合、完成条件判断 | StateMachine |
| **GateEngine** | 门禁管理、决策记录、权限控制 | StateMachine |

### 1.4 数据流图

```
┌─────────────┐
│ PM Agent    │
└──────┬──────┘
       │ orchestrator_run_step(instance_id, step_id)
       ▼
┌─────────────────────────────────────────┐
│         OrchestratorCore                 │
│  1. 验证状态                              │
│  2. 更新状态 → IN_PROGRESS               │
│  3. 触发事件: step_started               │
│  4. 创建 StepExecutionRequest            │
└───────────┬─────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│         Executor                        │
│  1. 接收请求                             │
│  2. 执行任务                             │
│  3. 返回 StepExecutionResult            │
└───────────┬─────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│         OrchestratorCore                 │
│  1. 接收结果                             │
│  2. 更新状态 → COMPLETED/FAILED          │
│  3. 触发事件: step_completed             │
│  4. 检查后续步骤                          │
│  5. 触发 spawn (如果需要)                │
│  6. 聚合状态到父级                       │
└─────────────────────────────────────────┘
```

---

## 2. 整体系统架构

### 2.1 系统分层架构

```mermaid
graph TB
    subgraph "Presentation Layer"
        PM[PM Agent]
        Gate[Gate UI]
        CLI[CLI Tools]
    end

    subgraph "API Layer"
        API[Orchestrator API]
        Auth[Authentication]
        RateLimit[Rate Limiting]
    end

    subgraph "Orchestration Layer"
        Core[Orchestrator Core]
        SM[StateMachine]
        TE[TemplateEngine]
        SE[SpawnEngine]
        EB[EventBus]
        AE[AggregationEngine]
        GE[GateEngine]
    end

    subgraph "Execution Layer"
        LLME[LLM Engine]
        ShellE[Shell Engine]
        MCPE[MCP Engine]
    end

    subgraph "Storage Layer"
        DB[(PostgreSQL)]
        Cache[(Redis)]
        File[(File Storage)]
    end

    PM --> API
    Gate --> API
    CLI --> API
    API --> Auth
    API --> RateLimit
    API --> Core
    Core --> SM
    Core --> TE
    Core --> SE
    Core --> EB
    Core --> AE
    Core --> GE
    Core --> LLME
    Core --> ShellE
    Core --> MCPE
    SM --> DB
    SM --> Cache
    TE --> File
    SE --> DB
```

### 2.2 与 v2.0 的集成方案

#### 2.2.1 兼容性策略

```python
class OrchestratorV2Compat:
    """v2.0 兼容层"""

    def migrate_v2_to_v3(self, v2_state: Dict) -> WorkflowInstance:
        """将 v2.0 状态迁移到 v3.0"""
        # v2.0 的单层 workflow 默认为 Level-1
        return WorkflowInstance(
            id=v2_state["run_id"],
            level=1,
            kind="project_master",
            status=self._convert_status(v2_state["run_state"]),
            # ... 映射其他字段
        )

    def wrap_v2_executor(self, v2_executor) -> Executor:
        """包装 v2.0 Executor 为 v3.0 接口"""
        return V3ExecutorWrapper(v2_executor)
```

#### 2.2.2 渐进式迁移路径

```
Phase 1: v2.0 和 v3.0 并存
  - v2.0 处理现有项目
  - v3.0 处理新项目
  - 通过 flag 切换版本

Phase 2: 数据迁移
  - 运行迁移脚本
  - 验证数据一致性
  - 保留 v2.0 快照

Phase 3: 切换到 v3.0
  - 所有新项目使用 v3.0
  - 旧项目逐步迁移
  - v2.0 进入维护模式
```

### 2.3 核心技术栈

| 层级 | 技术选择 | 理由 |
|------|----------|------|
| **API 层** | FastAPI | 高性能、异步支持、自动文档 |
| **状态存储** | PostgreSQL | ACID 保证、复杂查询、JSON 支持 |
| **缓存** | Redis | 高性能、分布式锁、发布订阅 |
| **事件总线** | Redis + asyncio | 轻量级、低延迟 |
| **任务队列** | Celery + Redis | 成熟、可靠、监控工具完善 |
| **模板引擎** | Jinja2 | 功能强大、广泛使用 |
| **日志** | structlog | 结构化日志、上下文支持 |

---

## 3. 核心模块设计

### 3.1 StateMachine 模块

#### 3.1.1 设计目标

- 统一管理所有层级 (L1/L2/L3) 的状态
- 保证状态转换的一致性
- 支持状态查询和聚合
- 提供状态验证和回滚

#### 3.1.2 核心接口

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from abc import ABC, abstractmethod

class WorkflowStatus(Enum):
    """统一工作流状态"""
    INIT = "init"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    QUEUED = "queued"  # L3 排队状态

@dataclass
class StageHistory:
    """阶段历史记录"""
    stage_id: str
    entered_at: datetime
    exited_at: Optional[datetime] = None
    status: str = "completed"

@dataclass
class StepState:
    """步骤状态"""
    step_id: str
    status: str  # pending, in_progress, completed, failed, etc.
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    outputs: List[str] = field(default_factory=list)
    error: Optional[str] = None

@dataclass
class OutputArtifact:
    """输出产物"""
    path: str
    type: str  # file, artifact, url, etc.
    hash: Optional[str] = None
    size: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class EventLog:
    """事件日志"""
    event_id: str
    event_type: str
    timestamp: datetime
    source: str  # instance_id
    data: Dict[str, Any]

@dataclass
class WorkflowInstance:
    """统一工作流实例模型

    所有层级 (L1/L2/L3) 使用同一套模型，通过 level 字段区分。
    """
    # === 通用字段 ===
    id: str                              # 实例 ID (全局唯一)
    workflow_id: str                     # 工作流定义 ID
    level: Literal[1, 2, 3]              # 层级标识
    kind: Literal["project_master", "department", "task"]
    project_id: str                      # 所属项目
    parent_id: Optional[str]             # 父实例 ID (L2->L1, L3->L2)
    status: WorkflowStatus               # 统一状态枚举
    paused: bool = False                 # 是否暂停
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # === 步骤和阶段 ===
    current_stage: Optional[str] = None  # 当前阶段/步骤
    stage_history: List[StageHistory] = field(default_factory=list)
    steps: Dict[str, StepState] = field(default_factory=dict)

    # === 输出和日志 ===
    outputs: List[OutputArtifact] = field(default_factory=list)
    logs: List[EventLog] = field(default_factory=list)

    # === 层级特有字段 ===
    # Level-1 专属
    phases: Optional[List[str]] = None
    current_phase: Optional[str] = None

    # Level-2 专属
    department: Optional[str] = None
    mode: Optional[Literal["mono-department", "cross-department"]] = None
    spawned_tasks: Optional[List[str]] = None  # 挂载的 L3 任务 ID

    # Level-3 专属
    template_id: Optional[str] = None
    template_version: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    owner: Optional[str] = None

class StateTransitionValidator(ABC):
    """状态转换验证器 (抽象基类)"""

    @abstractmethod
    def can_transition(self, from_status: WorkflowStatus,
                      to_status: WorkflowStatus) -> bool:
        """验证是否可以转换状态"""
        pass

    @abstractmethod
    def validate_pause(self, instance: WorkflowInstance) -> tuple[bool, Optional[str]]:
        """验证是否可以暂停"""
        pass

    @abstractmethod
    def validate_resume(self, instance: WorkflowInstance) -> tuple[bool, Optional[str]]:
        """验证是否可以恢复"""
        pass

class OrchestratorStateMachine:
    """统一状态机，管理所有 L1/L2/L3 实例

    这是唯一可以修改状态的地方，所有外部调用必须通过 narrow interface。
    """

    # 状态转换矩阵
    ALLOWED_TRANSITIONS = {
        WorkflowStatus.INIT: [WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED],
        WorkflowStatus.RUNNING: [WorkflowStatus.PAUSED, WorkflowStatus.COMPLETED,
                               WorkflowStatus.FAILED, WorkflowStatus.CANCELLED],
        WorkflowStatus.PAUSED: [WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED],
        WorkflowStatus.QUEUED: [WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED],
        # COMPLETED, FAILED, CANCELLED 是终态
    }

    def __init__(self, storage_backend: 'StorageBackend'):
        self.storage = storage_backend
        self.validator = StateTransitionValidatorImpl()
        self._event_bus: Optional['WorkflowEventBus'] = None

    def set_event_bus(self, event_bus: 'WorkflowEventBus'):
        """设置事件总线"""
        self._event_bus = event_bus

    async def create_instance(self,
                             workflow_id: str,
                             level: int,
                             kind: str,
                             project_id: str,
                             parameters: Dict,
                             parent_id: Optional[str] = None) -> WorkflowInstance:
        """创建新工作流实例"""
        instance = WorkflowInstance(
            id=self._generate_instance_id(workflow_id, level),
            workflow_id=workflow_id,
            level=level,
            kind=kind,
            project_id=project_id,
            parent_id=parent_id,
            status=WorkflowStatus.INIT,
            parameters=parameters
        )

        await self.storage.save_instance(instance)

        # 触发创建事件
        if self._event_bus:
            await self._event_bus.publish(
                event_type="workflow.created",
                source=instance.id,
                data={"instance_id": instance.id, "level": level}
            )

        return instance

    async def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """获取实例"""
        return await self.storage.load_instance(instance_id)

    async def update_status(self,
                           instance_id: str,
                           new_status: WorkflowStatus,
                           operator: str = "system") -> tuple[bool, Optional[str]]:
        """更新实例状态 (内部方法，不对外暴露)

        这是唯一可以修改状态的方法。
        """
        instance = await self.get_instance(instance_id)
        if not instance:
            return False, f"Instance not found: {instance_id}"

        # 验证状态转换
        if new_status not in self.ALLOWED_TRANSITIONS.get(instance.status, []):
            return False, f"Invalid transition: {instance.status} -> {new_status}"

        # 执行转换
        old_status = instance.status
        instance.status = new_status
        instance.updated_at = datetime.now()

        if new_status == WorkflowStatus.RUNNING and not instance.started_at:
            instance.started_at = datetime.now()
        elif new_status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED,
                           WorkflowStatus.CANCELLED]:
            instance.completed_at = datetime.now()

        await self.storage.save_instance(instance)

        # 触发状态变更事件
        if self._event_bus:
            await self._event_bus.publish(
                event_type="workflow.status_changed",
                source=instance_id,
                data={
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "operator": operator
                }
            )

        return True, None

    async def pause_instance(self,
                            instance_id: str,
                            reason: str,
                            operator: str) -> tuple[bool, Optional[str]]:
        """暂停实例"""
        instance = await self.get_instance(instance_id)
        if not instance:
            return False, f"Instance not found: {instance_id}"

        # 验证
        can_pause, error = self.validator.validate_pause(instance)
        if not can_pause:
            return False, error

        instance.paused = True
        instance.updated_at = datetime.now()

        await self.storage.save_instance(instance)

        # 触发暂停事件
        if self._event_bus:
            await self._event_bus.publish(
                event_type="workflow.paused",
                source=instance_id,
                data={"reason": reason, "operator": operator}
            )

        return True, None

    async def resume_instance(self,
                             instance_id: str,
                             note: str,
                             operator: str) -> tuple[bool, Optional[str]]:
        """恢复实例"""
        instance = await self.get_instance(instance_id)
        if not instance:
            return False, f"Instance not found: {instance_id}"

        # 验证
        can_resume, error = self.validator.validate_resume(instance)
        if not can_resume:
            return False, error

        instance.paused = False
        instance.updated_at = datetime.now()

        await self.storage.save_instance(instance)

        # 触发恢复事件
        if self._event_bus:
            await self._event_bus.publish(
                event_type="workflow.resumed",
                source=instance_id,
                data={"note": note, "operator": operator}
            )

        return True, None

    async def get_children(self, instance_id: str) -> List[WorkflowInstance]:
        """获取子实例"""
        return await self.storage.load_children(instance_id)

    def _generate_instance_id(self, workflow_id: str, level: int) -> str:
        """生成实例 ID"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{workflow_id}-L{level}-{timestamp}"

class StateTransitionValidatorImpl(StateTransitionValidator):
    """状态转换验证器实现"""

    PAUSE_BLOCKED_STATES = [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED,
                           WorkflowStatus.CANCELLED]

    def can_transition(self, from_status: WorkflowStatus,
                      to_status: WorkflowStatus) -> bool:
        """验证是否可以转换状态"""
        return to_status in OrchestratorStateMachine.ALLOWED_TRANSITIONS.get(
            from_status, []
        )

    def validate_pause(self, instance: WorkflowInstance) -> tuple[bool, Optional[str]]:
        """验证是否可以暂停"""
        if instance.status in self.PAUSE_BLOCKED_STATES:
            return False, f"Cannot pause workflow in {instance.status} state"
        if instance.paused:
            return False, "Workflow is already paused"
        return True, None

    def validate_resume(self, instance: WorkflowInstance) -> tuple[bool, Optional[str]]:
        """验证是否可以恢复"""
        if not instance.paused:
            return False, "Workflow is not paused"
        return True, None
```

#### 3.1.3 存储抽象层

```python
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    """存储后端抽象接口"""

    @abstractmethod
    async def save_instance(self, instance: WorkflowInstance) -> bool:
        """保存实例"""
        pass

    @abstractmethod
    async def load_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """加载实例"""
        pass

    @abstractmethod
    async def load_children(self, parent_id: str) -> List[WorkflowInstance]:
        """加载子实例"""
        pass

    @abstractmethod
    async def query_instances(self, filters: Dict) -> List[WorkflowInstance]:
        """查询实例"""
        pass

class PostgreSQLStorage(StorageBackend):
    """PostgreSQL 存储实现"""

    def __init__(self, connection_string: str):
        import asyncpg
        self.pool = None
        self.connection_string = connection_string

    async def initialize(self):
        """初始化连接池"""
        self.pool = await asyncpg.create_pool(self.connection_string)

    async def save_instance(self, instance: WorkflowInstance) -> bool:
        """保存实例到 PostgreSQL"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO workflow_instances
                (id, workflow_id, level, kind, project_id, parent_id, status,
                 paused, created_at, updated_at, started_at, completed_at,
                 current_stage, parameters, template_id, template_version,
                 department, owner)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                        $13, $14, $15, $16, $17, $18)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at,
                    paused = EXCLUDED.paused
            """, instance.id, instance.workflow_id, instance.level,
                instance.kind, instance.project_id, instance.parent_id,
                instance.status.value, instance.paused, instance.created_at,
                instance.updated_at, instance.started_at, instance.completed_at,
                instance.current_stage, json.dumps(instance.parameters),
                instance.template_id, instance.template_version,
                instance.department, instance.owner)
        return True

    async def load_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """从 PostgreSQL 加载实例"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_instances WHERE id = $1", instance_id
            )
            if not row:
                return None

            return WorkflowInstance(
                id=row["id"],
                workflow_id=row["workflow_id"],
                level=row["level"],
                kind=row["kind"],
                project_id=row["project_id"],
                parent_id=row["parent_id"],
                status=WorkflowStatus(row["status"]),
                paused=row["paused"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                current_stage=row["current_stage"],
                parameters=json.loads(row["parameters"]) if row["parameters"] else None,
                template_id=row["template_id"],
                template_version=row["template_version"],
                department=row["department"],
                owner=row["owner"]
            )

    async def load_children(self, parent_id: str) -> List[WorkflowInstance]:
        """加载子实例"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM workflow_instances WHERE parent_id = $1", parent_id
            )
            return [self._row_to_instance(row) for row in rows]

    async def query_instances(self, filters: Dict) -> List[WorkflowInstance]:
        """查询实例"""
        # 实现查询逻辑
        pass

    def _row_to_instance(self, row) -> WorkflowInstance:
        """将数据库行转换为 WorkflowInstance"""
        return WorkflowInstance(
            id=row["id"],
            workflow_id=row["workflow_id"],
            level=row["level"],
            kind=row["kind"],
            project_id=row["project_id"],
            parent_id=row["parent_id"],
            status=WorkflowStatus(row["status"]),
            paused=row["paused"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            current_stage=row["current_stage"],
            parameters=json.loads(row["parameters"]) if row["parameters"] else None,
            template_id=row["template_id"],
            template_version=row["template_version"],
            department=row["department"],
            owner=row["owner"]
        )
```

### 3.2 TemplateEngine 模块

#### 3.2.1 设计目标

- 支持模板加载和解析
- 支持参数化 ({{ param }})
- 支持模板继承 (extends)
- 支持版本管理

#### 3.2.2 核心接口

```python
from jinja2 import Environment, BaseLoader, TemplateSyntaxError
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import hashlib

@dataclass
class TemplateParameter:
    """模板参数定义"""
    name: str
    type: Literal["string", "number", "enum", "boolean", "object", "array"]
    required: bool = True
    default: Any = None
    description: Optional[str] = None
    values: Optional[list] = None  # for enum type

@dataclass
class WorkflowTemplate:
    """工作流模板"""
    id: str
    level: Literal[3]  # 模板只用于 L3
    kind: Literal["template"]
    version: str
    name: str
    category: str
    description: Optional[str] = None
    author: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    deprecated: bool = False
    deprecated_by: Optional[str] = None

    # 参数定义
    parameters: List[TemplateParameter] = field(default_factory=list)

    # 模板内容 (stages 定义)
    content: Dict[str, Any] = field(default_factory=dict)

    # 事件处理
    on_event: List[Dict] = field(default_factory=list)

    # 完成条件
    completion: Optional[Dict] = None

    # 继承
    extends: Optional[str] = None  # 继承的模板 ID
    overrides: Optional[Dict] = None  # 覆盖的字段

class TemplateEngine:
    """模板引擎"""

    def __init__(self, template_dir: Path):
        self.template_dir = Path(template_dir)
        self.jinja_env = Environment(loader=BaseLoader())
        self._cache: Dict[str, WorkflowTemplate] = {}

    async def load_template(self,
                           template_id: str,
                           version: Optional[str] = None) -> WorkflowTemplate:
        """加载模板"""
        cache_key = f"{template_id}:{version or 'latest'}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # 构建模板路径
        template_path = self._resolve_template_path(template_id, version)
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_id}")

        # 解析 YAML
        with open(template_path, encoding='utf-8') as f:
            content = yaml.safe_load(f)

        # 处理继承
        if content.get("extends"):
            base_template = await self.load_template(content["extends"])
            content = self._merge_templates(base_template.content, content)

        # 创建模板对象
        template = WorkflowTemplate(
            id=content["id"],
            level=3,
            kind="template",
            version=content.get("version", "v1"),
            name=content["name"],
            category=content["category"],
            description=content.get("description"),
            author=content.get("author"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deprecated=content.get("deprecated", False),
            deprecated_by=content.get("deprecated_by"),
            parameters=self._parse_parameters(content.get("parameters", [])),
            content=content,
            on_event=content.get("on_event", []),
            completion=content.get("completion"),
            extends=content.get("extends"),
            overrides=content.get("overrides")
        )

        self._cache[cache_key] = template
        return template

    async def render_template(self,
                             template: WorkflowTemplate,
                             parameters: Dict[str, Any]) -> Dict[str, Any]:
        """渲染模板 (参数替换)"""
        # 验证参数
        self._validate_parameters(template, parameters)

        # 使用 Jinja2 渲染
        rendered_content = self._render_dict(template.content, parameters)

        return rendered_content

    async def validate_template(self, template: WorkflowTemplate) -> tuple[bool, Optional[str]]:
        """验证模板"""
        # 检查必需字段
        if not template.id or not template.name:
            return False, "Template must have id and name"

        # 检查参数定义
        param_names = set()
        for param in template.parameters:
            if param.name in param_names:
                return False, f"Duplicate parameter: {param.name}"
            param_names.add(param.name)

        # 检查 stages 定义
        if "stages" not in template.content:
            return False, "Template must have stages"

        # 检查语法
        try:
            await self.render_template(template, {})
        except Exception as e:
            return False, f"Template rendering failed: {str(e)}"

        return True, None

    def _resolve_template_path(self, template_id: str, version: Optional[str]) -> Path:
        """解析模板路径"""
        # 全局模板: ai-spec/workflows/templates/
        global_path = self.template_dir / f"{template_id}.yaml"

        # 版本化模板: ai-spec/workflows/templates/{template_id}/v{version}.yaml
        if version:
            versioned_path = self.template_dir / template_id / f"v{version}.yaml"
            if versioned_path.exists():
                return versioned_path

        return global_path

    def _parse_parameters(self, params_def: List[Dict]) -> List[TemplateParameter]:
        """解析参数定义"""
        parameters = []
        for param_def in params_def:
            parameters.append(TemplateParameter(
                name=param_def["name"],
                type=param_def.get("type", "string"),
                required=param_def.get("required", True),
                default=param_def.get("default"),
                description=param_def.get("description"),
                values=param_def.get("values")
            ))
        return parameters

    def _validate_parameters(self, template: WorkflowTemplate, params: Dict):
        """验证参数"""
        # 检查必需参数
        for param in template.parameters:
            if param.required and param.name not in params:
                if param.default is None:
                    raise ValueError(f"Missing required parameter: {param.name}")

            # 检查类型
            if param.name in params:
                value = params[param.name]
                if param.type == "enum" and param.values:
                    if value not in param.values:
                        raise ValueError(
                            f"Parameter {param.name} must be one of {param.values}"
                        )

    def _render_dict(self, data: Any, context: Dict) -> Any:
        """递归渲染字典"""
        if isinstance(data, str):
            # 使用 Jinja2 渲染字符串
            template = self.jinja_env.from_string(data)
            return template.render(**context)

        elif isinstance(data, dict):
            return {k: self._render_dict(v, context) for k, v in data.items()}

        elif isinstance(data, list):
            return [self._render_dict(item, context) for item in data]

        else:
            return data

    def _merge_templates(self, base: Dict, override: Dict) -> Dict:
        """合并模板 (用于继承)"""
        import copy
        result = copy.deepcopy(base)

        def deep_merge(base_dict, override_dict):
            for key, value in override_dict.items():
                if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                    deep_merge(base_dict[key], value)
                else:
                    base_dict[key] = value

        deep_merge(result, override)
        return result
```

### 3.3 SpawnEngine 模块

#### 3.3.1 设计目标

- 基于模板创建 L3 实例
- 队列管理 (最大1000，24h超时)
- 并发控制 (默认50)
- 优先级调度

#### 3.3.2 核心接口

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
import asyncio

class TaskPriority(Enum):
    """任务优先级"""
    P0 = 0   # 最高
    P1 = 1
    P2 = 2
    P3 = 3   # 最低

@dataclass
class QueuedTask:
    """排队中的任务"""
    instance_id: str
    template_id: str
    parameters: Dict
    priority: TaskPriority
    queued_at: datetime = field(default_factory=datetime.now)
    timeout: int = 86400  # 24小时 (秒)

@dataclass
class SpawnConfig:
    """Spawn 配置"""
    max_concurrent: int = 50          # 最大并发数
    queue_max_size: int = 1000        # 队列最大长度
    queue_timeout: int = 86400        # 队列超时 (秒)
    priority_field: str = "severity"  # 优先级字段

class SpawnEngine:
    """L3 任务创建引擎

    职责：
    1. 基于模板创建实例
    2. 队列管理 (并发限制)
    3. 优先级调度
    4. 超时处理
    """

    def __init__(self,
                 state_machine: 'OrchestratorStateMachine',
                 template_engine: 'TemplateEngine',
                 config: SpawnConfig = None):
        self.state_machine = state_machine
        self.template_engine = template_engine
        self.config = config or SpawnConfig()

        # 队列
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=config.queue_max_size)
        self._running_tasks: Dict[str, WorkflowInstance] = {}
        self._queued_tasks: Dict[str, QueuedTask] = {}

        # 后台任务
        self._processor_task: Optional[asyncio.Task] = None
        self._timeout_checker_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动引擎"""
        self._processor_task = asyncio.create_task(self._process_queue())
        self._timeout_checker_task = asyncio.create_task(self._check_timeouts())

    async def stop(self):
        """停止引擎"""
        if self._processor_task:
            self._processor_task.cancel()
        if self._timeout_checker_task:
            self._timeout_checker_task.cancel()

    async def spawn(self,
                   parent_id: str,
                   template_id: str,
                   parameters: Dict,
                   priority: TaskPriority = TaskPriority.P2) -> tuple[bool, Optional[str], Optional[str]]:
        """创建 L3 实例

        Returns:
            (success, instance_id_or_error, queue_status)
            queue_status: "running" | "queued" | "rejected"
        """
        # 检查队列是否已满
        if len(self._queued_tasks) >= self.config.queue_max_size:
            return False, "Queue is full", "rejected"

        # 加载模板
        try:
            template = await self.template_engine.load_template(template_id)
        except Exception as e:
            return False, f"Failed to load template: {str(e)}", "rejected"

        # 检查是否可以立即启动
        if len(self._running_tasks) < self.config.max_concurrent:
            # 立即创建实例
            instance = await self.state_machine.create_instance(
                workflow_id=template_id,
                level=3,
                kind="task",
                project_id=parameters.get("project_id", "unknown"),
                parameters=parameters,
                parent_id=parent_id
            )

            # 启动实例
            await self.state_machine.update_status(instance.id, WorkflowStatus.RUNNING)

            self._running_tasks[instance.id] = instance

            return True, instance.id, "running"

        else:
            # 进入队列
            queued_task = QueuedTask(
                instance_id=f"queued-{template_id}-{datetime.now().timestamp()}",
                template_id=template_id,
                parameters=parameters,
                priority=priority
            )

            self._queued_tasks[queued_task.instance_id] = queued_task

            return True, queued_task.instance_id, "queued"

    async def complete_task(self, instance_id: str, status: WorkflowStatus):
        """标记任务完成"""
        if instance_id in self._running_tasks:
            del self._running_tasks[instance_id]

        await self.state_machine.update_status(instance_id, status)

    async def _process_queue(self):
        """处理队列 (后台任务)"""
        while True:
            try:
                # 检查是否有空闲槽位
                if len(self._running_tasks) >= self.config.max_concurrent:
                    await asyncio.sleep(1)
                    continue

                # 从队列获取任务 (按优先级)
                task = await self._get_next_task()
                if not task:
                    await asyncio.sleep(1)
                    continue

                # 创建实例
                instance = await self.state_machine.create_instance(
                    workflow_id=task.template_id,
                    level=3,
                    kind="task",
                    project_id=task.parameters.get("project_id", "unknown"),
                    parameters=task.parameters,
                    parent_id=task.parameters.get("parent_id")
                )

                # 启动实例
                await self.state_machine.update_status(instance.id, WorkflowStatus.RUNNING)

                self._running_tasks[instance.id] = instance
                del self._queued_tasks[task.instance_id]

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing queue: {e}")
                await asyncio.sleep(1)

    async def _get_next_task(self) -> Optional[QueuedTask]:
        """获取下一个任务 (按优先级)"""
        if not self._queued_tasks:
            return None

        # 按优先级排序
        sorted_tasks = sorted(
            self._queued_tasks.values(),
            key=lambda t: (t.priority.value, t.queued_at.timestamp())
        )

        return sorted_tasks[0]

    async def _check_timeouts(self):
        """检查超时 (后台任务)"""
        while True:
            try:
                now = datetime.now()

                # 检查队列中的超时任务
                timed_out = []
                for task_id, task in self._queued_tasks.items():
                    elapsed = (now - task.queued_at).total_seconds()
                    if elapsed > task.timeout:
                        timed_out.append(task_id)

                # 处理超时任务
                for task_id in timed_out:
                    task = self._queued_tasks[task_id]
                    del self._queued_tasks[task_id]
                    # 标记为失败
                    # TODO: 通知相关方

                await asyncio.sleep(60)  # 每分钟检查一次

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error checking timeouts: {e}")
                await asyncio.sleep(60)

    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        return {
            "running_count": len(self._running_tasks),
            "queued_count": len(self._queued_tasks),
            "max_concurrent": self.config.max_concurrent,
            "queue_max_size": self.config.queue_max_size,
            "queued_tasks": [
                {
                    "instance_id": t.instance_id,
                    "template_id": t.template_id,
                    "priority": t.priority.name,
                    "queued_at": t.queued_at.isoformat()
                }
                for t in sorted(
                    self._queued_tasks.values(),
                    key=lambda x: (x.priority.value, x.queued_at)
                )
            ]
        }
```

### 3.4 EventBus 模块

#### 3.4.1 设计目标

- 事件发布订阅
- 跨层级事件传播
- 事件触发 spawn/pause/resume

#### 3.4.2 核心接口

```python
from dataclasses import dataclass
from typing import Callable, Dict, List, Any
import asyncio
import json

@dataclass
class WorkflowEvent:
    """工作流事件"""
    event_id: str
    event_type: str
    source: str  # instance_id
    timestamp: datetime
    data: Dict[str, Any]
    level: Optional[int] = None  # 事件所属层级

class WorkflowEventBus:
    """工作流事件总线

    支持事件发布订阅和跨层级传播。
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url
        self._subscribers: Dict[str, List[Callable]] = {}
        self._redis = None

    async def initialize(self):
        """初始化"""
        if self.redis_url:
            import aioredis
            self._redis = await aioredis.from_url(self.redis_url)

    async def publish(self, event_type: str, source: str, data: Dict, level: int = None):
        """发布事件"""
        event = WorkflowEvent(
            event_id=f"EVT-{datetime.now().timestamp()}-{source}",
            event_type=event_type,
            source=source,
            timestamp=datetime.now(),
            data=data,
            level=level
        )

        # 本地订阅者
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                await callback(event)

        # Redis 发布 (用于跨进程传播)
        if self._redis:
            channel = f"workflow_events:{level}:{event_type}" if level else f"workflow_events:{event_type}"
            await self._redis.publish(
                channel,
                json.dumps({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "source": event.source,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data,
                    "level": event.level
                })
            )

    async def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    async def propagate_to_parent(self, event: WorkflowEvent, parent_id: str):
        """向父级传播事件"""
        # L3 → L2
        if event.level == 3:
            await self.publish(
                event_type=f"l3.{event.event_type}",
                source=event.source,
                data={"parent_id": parent_id, **event.data},
                level=2
            )

        # L2 → L1
        elif event.level == 2:
            await self.publish(
                event_type=f"l2.{event.event_type}",
                source=event.source,
                data={"parent_id": parent_id, **event.data},
                level=1
            )
```

### 3.5 AggregationEngine 模块

#### 3.5.1 设计目标

- L3 → L2 状态聚合
- L2 → L1 状态聚合
- 完成条件判断

#### 3.5.2 核心接口

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class AggregationType(Enum):
    """聚合类型"""
    ALL = "all"                    # 全部完成
    PERCENTAGE = "percentage"      # 百分比
    COUNT = "count"                # 绝对数量
    CUSTOM = "custom"              # 自定义条件

@dataclass
class CompletionCriteria:
    """完成条件"""
    type: AggregationType
    threshold: Optional[float] = None  # 百分比或数量阈值
    custom_expression: Optional[str] = None  # 自定义表达式

@dataclass
class AggregateState:
    """聚合状态"""
    total: int
    completed: int
    failed: int
    running: int
    paused: int
    queued: int
    by_severity: Dict[str, Dict] = None  # {severity: {total, completed}}
    completion_criteria_met: bool = False

class AggregationEngine:
    """状态聚合引擎

    职责：
    1. L3 → L2 状态聚合
    2. L2 → L1 状态聚合
    3. 完成条件判断
    """

    def __init__(self, state_machine: 'OrchestratorStateMachine'):
        self.state_machine = state_machine

    async def aggregate_children(self, instance_id: str) -> AggregateState:
        """聚合子实例状态"""
        children = await self.state_machine.get_children(instance_id)

        if not children:
            return AggregateState(
                total=0, completed=0, failed=0, running=0, paused=0, queued=0
            )

        # 统计状态
        total = len(children)
        completed = sum(1 for c in children if c.status == WorkflowStatus.COMPLETED)
        failed = sum(1 for c in children if c.status == WorkflowStatus.FAILED)
        running = sum(1 for c in children if c.status == WorkflowStatus.RUNNING)
        paused = sum(1 for c in children if c.paused)
        queued = sum(1 for c in children if c.status == WorkflowStatus.QUEUED)

        # 按 severity 分组 (L3 特有)
        by_severity = {}
        for child in children:
            if child.parameters and "severity" in child.parameters:
                severity = child.parameters["severity"]
                if severity not in by_severity:
                    by_severity[severity] = {"total": 0, "completed": 0}
                by_severity[severity]["total"] += 1
                if child.status == WorkflowStatus.COMPLETED:
                    by_severity[severity]["completed"] += 1

        return AggregateState(
            total=total,
            completed=completed,
            failed=failed,
            running=running,
            paused=paused,
            queued=queued,
            by_severity=by_severity
        )

    async def check_completion_criteria(self,
                                        instance_id: str,
                                        criteria: CompletionCriteria) -> bool:
        """检查完成条件"""
        aggregate = await self.aggregate_children(instance_id)

        if criteria.type == AggregationType.ALL:
            return aggregate.completed == aggregate.total

        elif criteria.type == AggregationType.PERCENTAGE:
            percentage = (aggregate.completed / aggregate.total) * 100 if aggregate.total > 0 else 0
            return percentage >= criteria.threshold

        elif criteria.type == AggregationType.COUNT:
            return aggregate.completed >= criteria.threshold

        elif criteria.type == AggregationType.CUSTOM:
            # 自定义表达式 (如: P0/P1 全部完成)
            return await self._evaluate_custom_criteria(aggregate, criteria.custom_expression)

        return False

    async def _evaluate_custom_criteria(self, aggregate: AggregateState, expression: str) -> bool:
        """评估自定义条件"""
        # 简单实现: 支持 "P0/P1 全部完成"
        if "by_severity" in expression:
            for severity, data in aggregate.by_severity.items():
                if f"{severity}" in expression:
                    if data["completed"] < data["total"]:
                        return False
            return True

        # 更复杂的条件可以使用专门的规则引擎
        return False
```

---

## 4. 数据模型设计

### 4.1 数据库 Schema

```sql
-- 工作流实例表
CREATE TABLE workflow_instances (
    id VARCHAR(255) PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    level INT NOT NULL CHECK (level IN (1, 2, 3)),
    kind VARCHAR(50) NOT NULL CHECK (kind IN ('project_master', 'department', 'task')),
    project_id VARCHAR(255) NOT NULL,
    parent_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    paused BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    current_stage VARCHAR(255),
    parameters JSONB,
    template_id VARCHAR(255),
    template_version VARCHAR(50),
    department VARCHAR(100),
    owner VARCHAR(255),
    FOREIGN KEY (parent_id) REFERENCES workflow_instances(id) ON DELETE CASCADE
);

-- 步骤状态表
CREATE TABLE workflow_steps (
    id SERIAL PRIMARY KEY,
    instance_id VARCHAR(255) NOT NULL,
    step_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    outputs JSONB,
    error TEXT,
    FOREIGN KEY (instance_id) REFERENCES workflow_instances(id) ON DELETE CASCADE,
    UNIQUE (instance_id, step_id)
);

-- 门禁表
CREATE TABLE workflow_gates (
    id SERIAL PRIMARY KEY,
    instance_id VARCHAR(255) NOT NULL,
    gate_id VARCHAR(255) NOT NULL,
    step_id VARCHAR(255) NOT NULL,
    gate_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    blocking BOOLEAN DEFAULT TRUE,
    triggered_at TIMESTAMP,
    approved_at TIMESTAMP,
    approver VARCHAR(255),
    comment TEXT,
    FOREIGN KEY (instance_id) REFERENCES workflow_instances(id) ON DELETE CASCADE,
    UNIQUE (instance_id, gate_id)
);

-- 事件日志表
CREATE TABLE workflow_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    data JSONB,
    level INT
);

CREATE INDEX idx_workflow_instances_level ON workflow_instances(level);
CREATE INDEX idx_workflow_instances_parent ON workflow_instances(parent_id);
CREATE INDEX idx_workflow_instances_status ON workflow_instances(status);
CREATE INDEX idx_workflow_events_source ON workflow_events(source);
CREATE INDEX idx_workflow_events_type ON workflow_events(event_type);
```

### 4.2 Redis 数据结构

```
# 缓存实例状态
workflow:instance:{instance_id} -> JSON

# 队列
workflow:queue:level3 -> List[instance_id]

# 锁
workflow:lock:{instance_id} -> TTL

# 发布订阅
workflow_events:{level}:{event_type} -> Channel
```

---

## 5. API 接口定义

### 5.1 RESTful API

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(title="LEE Orchestrator v3.0 API")

# === Request/Response Models ===

class WorkflowStateResponse(BaseModel):
    """工作流状态响应"""
    instance_id: str
    workflow_id: str
    level: int
    kind: str
    status: str
    paused: bool
    created_at: str
    updated_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    current_stage: Optional[str]
    children: List[str] = []

class StepExecutionRequest(BaseModel):
    """步骤执行请求"""
    instance_id: str
    step_id: str
    executor: str

class StepExecutionResponse(BaseModel):
    """步骤执行响应"""
    success: bool
    step_id: str
    status: str
    outputs: List[str] = []
    error: Optional[str] = None

class SpawnRequest(BaseModel):
    """Spawn 请求"""
    parent_id: str
    template_id: str
    parameters: Dict[str, Any]
    priority: Optional[str] = "P2"

class SpawnResponse(BaseModel):
    """Spawn 响应"""
    success: bool
    instance_id: Optional[str] = None
    queue_status: str  # running | queued | rejected
    message: Optional[str] = None

class PauseRequest(BaseModel):
    """暂停请求"""
    reason: str
    operator: str

class ResumeRequest(BaseModel):
    """恢复请求"""
    note: str
    operator: str

class GateDecisionRequest(BaseModel):
    """门禁决策请求"""
    gate_id: str
    decision: str  # approve | reject
    operator: str
    comment: Optional[str] = None

class AggregateStateResponse(BaseModel):
    """聚合状态响应"""
    total: int
    completed: int
    failed: int
    running: int
    paused: int
    queued: int
    by_severity: Dict[str, Dict] = {}
    completion_criteria_met: bool

# === API Endpoints ===

@app.get("/api/v3/workflows/{instance_id}")
async def get_workflow_state(instance_id: str) -> WorkflowStateResponse:
    """获取工作流状态"""
    # 实现
    pass

@app.post("/api/v3/workflows/{instance_id}/steps/{step_id}/run")
async def run_step(req: StepExecutionRequest) -> StepExecutionResponse:
    """执行步骤"""
    # 实现
    pass

@app.post("/api/v3/workflows/spawn")
async def spawn_workflow(req: SpawnRequest) -> SpawnResponse:
    """创建子工作流"""
    # 实现
    pass

@app.post("/api/v3/workflows/{instance_id}/pause")
async def pause_workflow(instance_id: str, req: PauseRequest):
    """暂停工作流"""
    # 实现
    pass

@app.post("/api/v3/workflows/{instance_id}/resume")
async def resume_workflow(instance_id: str, req: ResumeRequest):
    """恢复工作流"""
    # 实现
    pass

@app.post("/api/v3/workflows/{instance_id}/gates/{gate_id}/decision")
async def gate_decision(instance_id: str, req: GateDecisionRequest):
    """门禁决策"""
    # 实现
    pass

@app.get("/api/v3/workflows/{instance_id}/aggregate")
async def get_aggregate_state(instance_id: str) -> AggregateStateResponse:
    """获取聚合状态"""
    # 实现
    pass

@app.get("/api/v3/workflows/{instance_id}/children")
async def get_children(instance_id: str) -> List[WorkflowStateResponse]:
    """获取子实例"""
    # 实现
    pass
```

### 5.2 PM Agent 工具

```python
class PMAgentTools:
    """PM Agent 使用的工具集"""

    def __init__(self, orchestrator_core: 'OrchestratorCore'):
        self.core = orchestrator_core

    def orchestrator_get_state(self, instance_id: str) -> Dict:
        """获取工作流状态"""
        instance = asyncio.run(self.core.state_machine.get_instance(instance_id))
        if not instance:
            return {"error": "Instance not found"}

        return {
            "instance_id": instance.id,
            "workflow_id": instance.workflow_id,
            "level": instance.level,
            "kind": instance.kind,
            "status": instance.status.value,
            "paused": instance.paused,
            "current_stage": instance.current_stage,
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat()
        }

    def orchestrator_run_step(self, instance_id: str, step_id: str) -> Dict:
        """执行步骤"""
        success, result = asyncio.run(
            self.core.run_step(instance_id, step_id, "pm_agent")
        )
        if success:
            return {"success": True, "step_id": step_id, "result": result}
        else:
            return {"success": False, "error": result}

    def orchestrator_get_children(self, instance_id: str) -> List[Dict]:
        """获取子实例"""
        children = asyncio.run(self.core.state_machine.get_children(instance_id))
        return [
            {
                "instance_id": c.id,
                "level": c.level,
                "status": c.status.value,
                "kind": c.kind
            }
            for c in children
        ]

    def orchestrator_pause(self, instance_id: str, reason: str, operator: str) -> Dict:
        """暂停工作流"""
        success, error = asyncio.run(
            self.core.pause_workflow(instance_id, reason, operator)
        )
        if success:
            return {"success": True}
        else:
            return {"success": False, "error": error}

    def orchestrator_resume(self, instance_id: str, note: str, operator: str) -> Dict:
        """恢复工作流"""
        success, error = asyncio.run(
            self.core.resume_workflow(instance_id, note, operator)
        )
        if success:
            return {"success": True}
        else:
            return {"success": False, "error": error}
```

---

## 6. 状态转换设计

### 6.1 状态转换矩阵

```python
STATE_TRANSITIONS = {
    # WorkflowStatus transitions
    "INIT": ["RUNNING", "CANCELLED"],
    "RUNNING": ["PAUSED", "COMPLETED", "FAILED", "CANCELLED"],
    "PAUSED": ["RUNNING", "CANCELLED"],
    "QUEUED": ["RUNNING", "CANCELLED"],
    "COMPLETED": [],  # 终态
    "FAILED": [],     # 终态
    "CANCELLED": [],  # 终态
}
```

### 6.2 状态转换序列图

```mermaid
sequenceDiagram
    participant PM as PM Agent
    participant API as Orchestrator API
    participant SM as StateMachine
    participant Executor as Executor
    participant EB as EventBus

    PM->>API: run_step(instance_id, step_id)
    API->>SM: get_instance(instance_id)
    SM-->>API: instance

    API->>SM: validate_transition(RUNNING)
    SM-->>API: valid

    API->>SM: update_status(instance_id, RUNNING)
    SM->>EB: publish(status_changed)
    SM-->>API: updated

    API->>Executor: execute(StepExecutionRequest)
    Executor-->>API: StepExecutionResult

    alt Success
        API->>SM: update_status(instance_id, COMPLETED)
        SM->>EB: publish(step_completed)
        SM-->>API: updated
    else Failure
        API->>SM: update_status(instance_id, FAILED)
        SM->>EB: publish(step_failed)
        SM-->>API: updated
    end
```

### 6.3 层级状态同步

```python
async def sync_child_status_to_parent(child_instance: WorkflowInstance):
    """同步子实例状态到父实例"""
    if not child_instance.parent_id:
        return

    parent = await state_machine.get_instance(child_instance.parent_id)
    if not parent:
        return

    # 聚合所有子实例状态
    aggregate = await aggregation_engine.aggregate_children(parent.id)

    # 更新父实例的 spawned_tasks
    if parent.spawned_tasks is None:
        parent.spawned_tasks = []
    if child_instance.id not in parent.spawned_tasks:
        parent.spawned_tasks.append(child_instance.id)

    # 检查完成条件
    if parent.completion_criteria:
        criteria_met = await aggregation_engine.check_completion_criteria(
            parent.id, parent.completion_criteria
        )
        if criteria_met and aggregate.completed == aggregate.total:
            await state_machine.update_status(parent.id, WorkflowStatus.COMPLETED)
```

---

## 7. 并发控制设计

### 7.1 L3 并发控制

```python
class ConcurrencyController:
    """并发控制器"""

    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue = asyncio.Queue()
        self.active_tasks: set = set()

    async def acquire(self, task_id: str) -> bool:
        """获取执行槽位"""
        # 检查是否已达上限
        if len(self.active_tasks) >= self.max_concurrent:
            return False

        await self.semaphore.acquire()
        self.active_tasks.add(task_id)
        return True

    async def release(self, task_id: str):
        """释放执行槽位"""
        if task_id in self.active_tasks:
            self.active_tasks.remove(task_id)
        self.semaphore.release()

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "active": len(self.active_tasks),
            "max": self.max_concurrent,
            "available": self.max_concurrent - len(self.active_tasks)
        }
```

### 7.2 分布式锁

```python
class DistributedLock:
    """分布式锁 (基于 Redis)"""

    def __init__(self, redis_client, lock_name: str, ttl: int = 30):
        self.redis = redis_client
        self.lock_name = f"lock:{lock_name}"
        self.ttl = ttl
        self.identifier = str(uuid.uuid4())

    async def acquire(self) -> bool:
        """获取锁"""
        return await self.redis.set(
            self.lock_name,
            self.identifier,
            nx=True,
            ex=self.ttl
        )

    async def release(self) -> bool:
        """释放锁"""
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        return await self.redis.eval(script, 1, self.lock_name, self.identifier)
```

---

## 8. 序列图

### 8.1 L1 → L2 触发流程

```mermaid
sequenceDiagram
    participant PM as PM Agent
    participant L1 as L1 Orchestrator
    participant L2 as L2 Orchestrator
    participant SM as StateMachine

    PM->>L1: run_step(l1_id, "trigger_qa_phase")
    L1->>SM: validate_step(l1_id, "trigger_qa_phase")
    SM-->>L1: valid

    L1->>SM: create_instance(level=2, department=qa)
    SM-->>L1: l2_instance

    L1->>L2: notify(l2_instance.id)
    L2->>SM: update_status(l2_id, RUNNING)
    SM-->>L1: status updated

    L1->>SM: update_status(l1_id, WAITING_FOR_L2)
    SM-->>PM: state updated
```

### 8.2 L2 → L3 Spawn 流程

```mermaid
sequenceDiagram
    participant L2 as L2 Orchestrator
    participant SE as SpawnEngine
    participant TE as TemplateEngine
    participant SM as StateMachine
    participant L3 as L3 Instance

    L2->>SE: spawn(parent_id=l2_id, template=bug_fix, params={...})
    SE->>TE: load_template("bug_fix")
    TE-->>SE: template

    SE->>SE: check_concurrent_limit()
    alt has_slot
        SE->>SM: create_instance(level=3, template_id=bug_fix)
        SM-->>SE: l3_instance

        SE->>SM: update_status(l3_id, RUNNING)
        SM-->>L2: l3_instance created (status=running)
    else queue_full
        SE->>SE: add_to_queue()
        SE-->>L2: l3_instance queued
    end
```

### 8.3 L3 → L2 聚合流程

```mermaid
sequenceDiagram
    participant L3 as L3 Instance
    participant AE as AggregationEngine
    participant L2 as L2 Instance
    participant SM as StateMachine

    L3->>SM: complete_step(l3_id, last_step)
    SM->>SM: update_status(l3_id, COMPLETED)
    SM->>AE: trigger_aggregation(l2_id)

    AE->>SM: get_children(l2_id)
    SM-->>AE: [l3_1, l3_2, l3_3, ...]

    AE->>AE: aggregate_states()
    AE->>AE: check_completion_criteria()

    alt all_completed
        AE->>SM: update_status(l2_id, COMPLETED)
        SM-->>L2: workflow completed
    else still_running
        AE-->>L2: aggregate_state updated
    end
```

---

## 9. 性能优化策略

### 9.1 缓存策略

```python
class CacheStrategy:
    """缓存策略"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.local_cache: Dict = {}
        self.ttl = {
            "instance": 300,  # 5分钟
            "aggregate": 60,  # 1分钟
            "template": 3600  # 1小时
        }

    async def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """获取实例 (带缓存)"""
        # 先查本地缓存
        if instance_id in self.local_cache:
            return self.local_cache[instance_id]

        # 再查 Redis
        cached = await self.redis.get(f"instance:{instance_id}")
        if cached:
            instance = WorkflowInstance.parse_raw(cached)
            self.local_cache[instance_id] = instance
            return instance

        # 最后查数据库
        return None

    async def set_instance(self, instance: WorkflowInstance):
        """设置实例缓存"""
        self.local_cache[instance.id] = instance
        await self.redis.setex(
            f"instance:{instance.id}",
            self.ttl["instance"],
            instance.json()
        )
```

### 9.2 批量查询优化

```python
async def batch_get_instances(instance_ids: List[str]) -> List[WorkflowInstance]:
    """批量获取实例"""
    # 使用 SQL IN 查询
    query = "SELECT * FROM workflow_instances WHERE id = ANY($1)"
    rows = await db.fetch(query, instance_ids)
    return [row_to_instance(row) for row in rows]
```

### 9.3 数据库索引优化

```sql
-- 常用查询的索引
CREATE INDEX idx_instances_level_status ON workflow_instances(level, status);
CREATE INDEX idx_instances_parent_status ON workflow_instances(parent_id, status);
CREATE INDEX idx_instances_project_level ON workflow_instances(project_id, level);

-- 部分索引 (只索引运行中的实例)
CREATE INDEX idx_instances_running
    ON workflow_instances(parent_id)
    WHERE status = 'RUNNING';
```

---

## 10. 向后兼容与迁移

### 10.1 数据迁移脚本

```python
class MigrationV2ToV3:
    """v2.0 到 v3.0 的数据迁移"""

    async def migrate_workflow_state(self, v2_state: Dict) -> WorkflowInstance:
        """迁移 v2.0 工作流状态"""
        # v2.0 的单层 workflow 默认为 Level-1
        return WorkflowInstance(
            id=v2_state["run_id"],
            workflow_id=v2_state.get("workflow_id", "migrated"),
            level=1,
            kind="project_master",
            project_id=v2_state.get("project_id", "unknown"),
            status=self._convert_status(v2_state["run_state"]),
            created_at=datetime.fromisoformat(v2_state["created_at"]),
            updated_at=datetime.fromisoformat(v2_state["updated_at"]),
            started_at=v2_state.get("started_at"),
            completed_at=v2_state.get("completed_at"),
            current_stage=v2_state.get("current_step")
        )

    def _convert_status(self, v2_status: str) -> WorkflowStatus:
        """转换状态枚举"""
        mapping = {
            "created": WorkflowStatus.INIT,
            "running": WorkflowStatus.RUNNING,
            "paused": WorkflowStatus.PAUSED,
            "completed": WorkflowStatus.COMPLETED,
            "failed": WorkflowStatus.FAILED,
            "aborted": WorkflowStatus.CANCELLED
        }
        return mapping.get(v2_status, WorkflowStatus.INIT)

    async def run_migration(self, project_dir: str):
        """运行迁移"""
        # 加载 v2.0 状态
        v2_state_path = Path(project_dir) / ".workflow" / "state.yaml"
        if not v2_state_path.exists():
            print("No v2.0 state found")
            return

        with open(v2_state_path) as f:
            v2_state = yaml.safe_load(f)

        # 迁移到 v3.0
        v3_instance = await self.migrate_workflow_state(v2_state)

        # 保存到数据库
        await storage.save_instance(v3_instance)

        # 备份 v2.0 状态
        backup_path = v2_state_path.with_suffix(".yaml.bak")
        shutil.move(v2_state_path, backup_path)

        print(f"Migration complete: {v3_instance.id}")
```

### 10.2 API 兼容层

```python
@app.post("/api/v2/workflows/run")
async def v2_run_step(workflow_dir: str, step_id: str):
    """v2.0 兼容接口"""
    # 转换为 v3.0 调用
    instance_id = await resolve_v2_to_v3_instance(workflow_dir)
    return await run_step(instance_id, step_id)
```

---

## 11. 部署架构

### 11.1 单机部署

```
┌─────────────────────────────────────────┐
│              Single Server              │
│  ┌─────────────────────────────────┐   │
│  │  Orchestrator Service           │   │
│  │  - FastAPI (8000)               │   │
│  │  - StateMachine                 │   │
│  │  - TemplateEngine               │   │
│  │  - SpawnEngine                  │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │  PostgreSQL (5432)              │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │  Redis (6379)                   │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 11.2 分布式部署

```
┌──────────────────┐
│   Load Balancer  │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼─────┐
│ App 1 │ │ App 2  │
└───┬───┘ └──┬─────┘
    │         │
    └────┬────┘
         │
    ┌────┴────────┐
    │  PostgreSQL │  (Primary)
    │  Redis      │  (Cluster)
    └─────────────┘
```

### 11.3 Docker Compose 配置

```yaml
version: '3.8'

services:
  orchestrator:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/orchestrator
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=orchestrator
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

## 12. 监控与可观测性

### 12.1 指标定义

```python
from prometheus_client import Counter, Histogram, Gauge

# 工作流指标
workflow_created = Counter('workflow_created_total', 'Total workflows created', ['level', 'kind'])
workflow_completed = Counter('workflow_completed_total', 'Total workflows completed', ['level', 'kind'])
workflow_failed = Counter('workflow_failed_total', 'Total workflows failed', ['level', 'kind'])
workflow_duration = Histogram('workflow_duration_seconds', 'Workflow duration', ['level', 'kind'])

# L3 并发指标
l3_concurrent_tasks = Gauge('l3_concurrent_tasks', 'Current concurrent L3 tasks')
l3_queue_length = Gauge('l3_queue_length', 'L3 queue length')
l3_spawn_rate = Counter('l3_spawn_total', 'Total L3 spawns', ['template'])

# 暂停/恢复指标
workflow_paused = Counter('workflow_paused_total', 'Total workflows paused', ['level', 'reason'])
workflow_resumed = Counter('workflow_resumed_total', 'Total workflows resumed', ['level'])

# 性能指标
api_latency = Histogram('api_latency_seconds', 'API latency', ['endpoint'])
db_query_latency = Histogram('db_query_latency_seconds', 'DB query latency', ['query'])
```

### 12.2 日志策略

```python
import structlog

logger = structlog.get_logger()

# 结构化日志
logger.info(
    "workflow_created",
    instance_id=instance.id,
    level=instance.level,
    kind=instance.kind,
    project_id=instance.project_id
)

logger.error(
    "step_failed",
    instance_id=instance_id,
    step_id=step_id,
    error=str(e),
    traceback=traceback.format_exc()
)
```

### 12.3 告警规则

```yaml
groups:
  - name: orchestrator_alerts
    rules:
      - alert: HighWorkflowFailureRate
        expr: rate(workflow_failed_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High workflow failure rate"

      - alert: LongQueueWait
        expr: l3_queue_length > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "L3 queue is too long"

      - alert: StuckWorkflow
        expr: workflow_duration_seconds{status="running"} > 86400
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "Workflow stuck for more than 24 hours"
```

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| Level-1 | 公司级主流程，表达项目整体生命周期 |
| Level-2 | 部门级子流程，表达部门内部工作阶段 |
| Level-3 | 任务级流程，基于模板创建的具体任务 |
| WorkflowInstance | 工作流实例，运行中的工作流 |
| WorkflowTemplate | 工作流模板，可复用的流程定义 |
| Spawn | 创建 Level-3 任务实例的操作 |
| Phase | 阶段，工作流中的大阶段 |
| Stage | 步骤，工作流中的具体执行步骤 |
| Pause/Resume | 暂停/恢复，控制工作流执行的操作 |
| Aggregation | 聚合，从 L3 收集状态到 L2，从 L2 到 L1 |

### B. 参考文档

1. **现有文档**：
   - [Orchestrator PRD v2.0](./PRD.md)
   - [Orchestrator Architecture v2.0](../architecture.md)

2. **相关项目**：
   - Apache Airflow: DAG 编排
   - Temporal: 工作流引擎
   - Argo Workflows: Kubernetes 工作流

3. **设计模式**：
   - Composite Pattern: 树形层级结构
   - Template Method Pattern: 模板复用
   - Observer Pattern: 事件驱动

---

**文档版本**: v1.0
**最后更新**: 2026-01-25
**维护者**: LEE 架构团队
**审核者**: 待定
