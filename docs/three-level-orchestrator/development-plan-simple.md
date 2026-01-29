# LEE Orchestrator v3.0 - 极简版开发计划

> **版本**: v1.2 (工程细节优化)
> **状态**: Draft
> **创建日期**: 2026-01-26
> **修订日期**: 2026-01-26
> **预计周期**: 4-6 周
> **预计工作量**: 25-35 人天
> **架构定位**: 本地单实例工具

---

## 设计原则

### 核心定位
- **本地工具**: 每个项目运行一个实例
- **单进程**: 无需考虑分布式、并发
- **快速实现**: 优先功能完整性，非性能/可靠性
- **单一权威**: 状态机由 Orchestrator 统一管理，SQLite 为唯一状态存储

### 关键原则

> **原则 #1: 状态机唯一权威**
>
> 三层工作流（L1/L2/L3）的所有状态（创建、执行、完成、暂停、恢复），全部由
> `core/state_machine.py` + `execution/orchestrator.py` 统一管理。
> 任何 Executor / 工具 / 外部系统都不得直接修改 SQLite 状态，只能通过 Orchestrator API 间接操作。

> **原则 #2: 统一多级 Workflow 建模**
>
> L1/L2/L3 都是 `workflow_instance`，通过 `level` 字段区分：
> - L1: level='project'
> - L2: level='department'
> - L3: level='task'
>
> 通过 `parent_id` + `parent_level` 表达嵌套关系，避免未来重构。

> **原则 #3: 唯一 Orchestrator**
>
> 系统只有一个 Orchestrator 作为状态机/调度中心，管理所有 level 的 workflow_instance。
> Runner 只是对 Orchestrator 的视图封装，Executor 只负责执行步骤，不跑自己的状态机。

> **原则 #4: Executor 权力边界（宪法）**
>
> ```python
> """
> ⚠️ EXECUTOR 宪法 ⚠️
>
> Executor 必须遵守以下绝对规则：
> 1. 不得直接访问 SQLite（任何 INSERT/UPDATE/DELETE 操作）
> 2. 不得直接访问 Orchestrator（不调状态机 API）
> 3. 只接收输入数据，产生输出数据
> 4. 所有状态持久化由 Orchestrator 负责
>
> 违反者将被视为架构叛徒，未来重构时优先清除。
> """
> ```

### 简化决策

| 原复杂设计 | 简化方案 | 理由 |
|-----------|---------|------|
| PostgreSQL JSONB | SQLite | 本地工具，无需并发 |
| Redis Streams | 内存事件总线 | 单进程，内存足够 |
| Celery/自研队列 | `asyncio.Queue` | 单进程异步即可 |
| StateMachine 并发锁 | 无需锁 | 单线程事件循环 |
| Redis 持久化/Sentinel | 无需 | SQLite 已持久化 |
| L3 并发(>1000) | 串行执行(预留并发) | 本地工具，但留扩展点 |
| 分布式追踪 | 简单日志 | 单进程无分布式问题 |

---

## 技术栈（极简）

```yaml
数据存储:
  - SQLite: 唯一状态存储权威
  - JSON1 扩展: 灵活数据字段
  - 外键: 仅引用 parent_id（避免复合主键复杂度）

异步框架:
  - asyncio: 单进程事件循环
  - aiofiles: 异步文件操作

事件系统:
  - 内存: 简单的发布订阅
  - 无需 Redis

执行模型:
  - asyncio.Semaphore: 预留并发扩展点
  - concurrency=1: 极简版默认串行

API (可选):
  - FastAPI: 如需 Web UI
  - 或 CLI: 命令行工具
  - 预留: PM agent / Gate 集成接口
```

---

## 核心模块（简化）

### 模块架构

```
lee-orchestrator/
├── core/
│   ├── state_machine.py      # 状态机（无锁，DB 为权威）
│   ├── template_engine.py    # 模板引擎（Jinja2）
│   └── event_bus.py          # 内存事件总线
├── storage/
│   ├── sqlite_store.py       # SQLite 存储（唯一权威）
│   └── models.py             # 数据模型
├── execution/
│   ├── orchestrator.py       # 唯一 Orchestrator（所有状态机逻辑）
│   ├── runners.py            # 视图封装（project_runner / dept_runner）
│   └── executors.py          # LLMExecutor / ShellExecutor 等
├── api/
│   ├── main.py               # FastAPI (可选)
│   └── schemas.py            # API schemas（预留 PM agent 接口）
└── cli/
    └── main.py               # 命令行工具
```

### 命名说明

```text
orchestrator.py  ← 核心 Orchestrator（唯一状态机）
                   ↓ 调用
runners.py       ← 视图封装（project_runner / dept_runner）
                   非第二状态机，只是便捷操作封装
                   ↓ 调用
executors.py     ← 纯执行器（LLMExecutor / ShellExecutor）
                   ⚠️ 宪法：不访问 SQLite，不调 Orchestrator
```

### 状态机（DB 为唯一权威）

```python
# SQLite 为唯一权威，内存只是可重建的缓存
class SimpleStateMachine:
    def __init__(self, db: SQLiteStore):
        self.db = db
        self._cache = {}  # 可重建的内存缓存

    async def transition(self, instance_id: str, new_state: str):
        # 先写 DB（唯一权威）
        await self.db.update_state(instance_id, new_state)
        # 后更新缓存（加速读）
        self._cache[instance_id] = new_state

    async def get_state(self, instance_id: str) -> str:
        # 优先读缓存
        if instance_id in self._cache:
            return self._cache[instance_id]
        # 缓存未命中，查 DB
        state = await self.db.get_state(instance_id)
        self._cache[instance_id] = state
        return state

    async def load_from_db(self):
        """启动时从 DB 重建缓存"""
        instances = await self.db.get_all_instances()
        for inst in instances:
            self._cache[inst.id] = inst.status
```

### 事件总线（内存）

```python
# 简单的内存发布订阅
class MemoryEventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable):
        self.subscribers[event_type].append(callback)

    async def publish(self, event: Event):
        for callback in self.subscribers[event.type]:
            await callback(event)
```

### 任务执行（预留并发扩展）

```python
# concurrency=1 串行执行，但预留并发扩展点
async def execute_tasks(tasks: List[Task], concurrency: int = 1):
    sem = asyncio.Semaphore(concurrency)

    async def _run(task: Task):
        async with sem:
            result = await run_task(task)
            await save_result(task.id, result)
            return result

    results = await asyncio.gather(*(_run(t) for t in tasks))
    return results

# 极简版使用
await execute_tasks(tasks, concurrency=1)

# 未来改并发只需改一个参数
await execute_tasks(tasks, concurrency=5)
```

---

## 数据模型（统一多级 Workflow）

### 核心设计

**关键决策**: 用统一的 `workflow_instances` 表 + `level` 字段建模 L1/L2/L3

**优点**:
- 避免 L2/L3 未来重构成 workflow_instances
- Orchestrator 逻辑统一，无需区分"stage orchestrator" vs "task orchestrator"
- 通过 `parent_id` + `parent_level` 清晰表达嵌套关系

### 表结构（v1.2 优化）

```sql
-- 统一工作流实例表（L1/L2/L3 都用这张表）
CREATE TABLE workflow_instances (
    id TEXT PRIMARY KEY,
    level TEXT NOT NULL,           -- 'project' | 'department' | 'task'
    parent_id TEXT,                -- 父实例 ID（外键只引用 id）
    parent_level TEXT,             -- 父实例 level（冗余字段，用于校验和加速查询）
    template_id TEXT,              -- 模板 ID
    status TEXT NOT NULL,          -- 'pending' | 'running' | 'completed' | 'failed' | 'paused'
    data JSON,                     -- 实例数据（输入/输出/上下文）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,

    -- 外键优化：只引用 parent_id，避免复合主键
    FOREIGN KEY (parent_id) REFERENCES workflow_instances(id)
);

-- 索引优化
CREATE INDEX idx_workflow_parent ON workflow_instances(parent_id);
CREATE INDEX idx_workflow_status ON workflow_instances(status);
CREATE INDEX idx_workflow_level ON workflow_instances(level);

-- 任务执行记录表（L3 的单步执行缓存）
CREATE TABLE task_executions (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,     -- 关联的 L3 workflow_instance
    task_name TEXT NOT NULL,
    executor_type TEXT,            -- 'llm' | 'shell' | 'metagpt'
    input_data JSON,
    output_data JSON,
    status TEXT,                   -- 'pending' | 'running' | 'completed' | 'failed'
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    FOREIGN KEY (workflow_id) REFERENCES workflow_instances(id)
);

-- 模板定义表
CREATE TABLE templates (
    id TEXT PRIMARY KEY,
    level TEXT NOT NULL,           -- 'project' | 'department' | 'task'
    name TEXT NOT NULL,
    content TEXT NOT NULL,         -- YAML/JSON 模板内容
    version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 事件日志表（可选，用于调试）
CREATE TABLE event_logs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT,
    event_type TEXT NOT NULL,
    event_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (workflow_id) REFERENCES workflow_instances(id)
);
```

### 数据模型类

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class WorkflowLevel(str, Enum):
    PROJECT = "project"        # L1
    DEPARTMENT = "department"  # L2
    TASK = "task"             # L3

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

# TaskExecution 使用简化状态（不含 PAUSED）
class TaskExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class WorkflowInstance:
    id: str
    level: WorkflowLevel
    parent_id: Optional[str]
    parent_level: Optional[WorkflowLevel]
    template_id: str
    status: WorkflowStatus
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

@dataclass
class TaskExecution:
    id: str
    workflow_id: str
    task_name: str
    executor_type: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    status: TaskExecutionStatus  # 使用独立的状态枚举
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

### 层级关系示例

```python
# L1: 项目工作流
project_wf = WorkflowInstance(
    id="wf_proj_001",
    level=WorkflowLevel.PROJECT,
    parent_id=None,
    parent_level=None,
    template_id="project_main.yaml",
    status=WorkflowStatus.RUNNING,
    ...
)

# L2: 部门工作流（嵌套在 L1 下）
dev_wf = WorkflowInstance(
    id="wf_dept_001",
    level=WorkflowLevel.DEPARTMENT,
    parent_id="wf_proj_001",
    parent_level=WorkflowLevel.PROJECT,
    template_id="dept_dev.yaml",
    status=WorkflowStatus.RUNNING,
    ...
)

# L3: 任务工作流（嵌套在 L2 下）
bug_fix_wf = WorkflowInstance(
    id="wf_task_001",
    level=WorkflowLevel.TASK,
    parent_id="wf_dept_001",
    parent_level=WorkflowLevel.DEPARTMENT,
    template_id="task_bug_fix.yaml",
    status=WorkflowStatus.RUNNING,
    ...
)
```

---

## 开发计划（4-6 周）

### Week 1-2: 核心基础设施

| 任务 | 工作量 | 交付物 |
|------|--------|--------|
| SQLite 数据模型实现 | 2 天 | `storage/models.py`, `storage/sqlite_store.py` |
| 状态机（DB 为权威） | 2 天 | `core/state_machine.py` |
| 内存事件总线 | 1 天 | `core/event_bus.py` |
| 模板引擎（Jinja2） | 2 天 | `core/template_engine.py` |
| CLI 基础框架 | 3 天 | `cli/main.py` |

**里程碑**: 能通过 CLI 创建 workflow_instance 并查询状态

**验收标准**:
- [ ] SQLite 表结构创建完成（外键只引用 parent_id）
- [ ] 能创建 L1/L2/L3 workflow_instance
- [ ] 状态转换正确（pending → running → completed）
- [ ] 进程重启后状态从 DB 正确恢复

### Week 3-4: Orchestrator 核心逻辑

| 任务 | 工作量 | 交付物 |
|------|--------|--------|
| Orchestrator 核心 | 3 天 | `execution/orchestrator.py` |
| Runners 视图封装 | 2 天 | `execution/runners.py` |
| LLM / Shell Executor | 2 天 | `execution/executors.py` |
| 层级嵌套逻辑 | 2 天 | spawn_workflow, 状态传播 |
| 单元测试 | 3 天 | `tests/test_orchestrator.py` |

**里程碑**: 完整的三层编排功能可用

**核心接口**（v1.2 规范化）:
```python
class StepResult(BaseModel):
    """run_step 返回结果"""
    status: Literal["success", "no_ready_step", "blocked", "failed"]
    step_id: Optional[str]
    workflow_id: str
    message: str
    next_steps: List[str] = []  # 下一步可执行的 step_id 列表

class Orchestrator:
    async def create_workflow(
        self,
        level: WorkflowLevel,
        template_id: str,
        parent_id: Optional[str] = None
    ) -> WorkflowInstance

    async def run_step(
        self,
        workflow_id: str,
        step_id: Optional[str] = None  # 可选：指定执行某一步
    ) -> StepResult:
        """
        执行 workflow 的一个步骤

        行为规范：
        1. 如果指定 step_id，执行该步骤
        2. 如果未指定 step_id，自动选择一个 ready step：
           - 优先级：按模板定义顺序选择第一个满足依赖的 step
           - 如果没有 ready step，返回 StepResult(status="no_ready_step")
        3. 执行失败不抛异常，返回 StepResult(status="failed")

        Args:
            workflow_id: 工作流实例 ID
            step_id: 可选，指定执行的步骤 ID

        Returns:
            StepResult: 包含执行状态和下一步信息
        """

    async def get_state(self, workflow_id: str) -> WorkflowState

    async def spawn_workflow(
        self,
        parent_id: str,
        level: WorkflowLevel,
        template_id: str
    ) -> WorkflowInstance

    async def pause(self, workflow_id: str)
    async def resume(self, workflow_id: str)

    # Future work（v3.5+）
    # async def run_until_blocked(
    #     self,
    #     workflow_id: str,
    #     max_steps: int = 100
    # ) -> List[StepResult]:
    #     """
    #     自动执行 workflow 直到遇到阻塞点（human_gate / 外部依赖）
    #     或达到 max_steps 上限
    #
    #     适用场景：
    #     - CLI: lee run wf_proj_001 → 自动跑到下一个 Gate
    #     - PM agent: "帮我推进这个 workflow 到下一步需要人工介入"
    #     """
```

**验收标准**:
- [ ] L1 workflow 能 spawn L2 children
- [ ] L2 workflow 能 spawn L3 children
- [ ] L3 全部完成时，自动更新父 L2 状态
- [ ] 状态传播正确（子完成 → 父更新）
- [ ] 所有状态操作通过 Orchestrator，无直接 DB 写入
- [ ] Executor 严格遵守"宪法"，无越权访问

### Week 5-6: 可选增强 + 集成

| 任务 | 工作量 | 交付物 |
|------|--------|--------|
| FastAPI Web UI | 4 天 | `api/main.py`, `api/schemas.py` |
| 预留 PM agent 接口 | 1 天 | OpenAPI specs |
| 示例模板 | 2 天 | `templates/*.yaml` |
| 集成测试 | 3 天 | `tests/test_integration.py` |
| 文档 | 2 天 | `README.md`, 使用指南 |

**里程碑**: 可发布的本地工具

**预留接口**（供未来 PM agent / Gate 使用）:
```yaml
# API endpoints（FastAPI）
POST   /api/v1/workflows                  # 创建 workflow
GET    /api/v1/workflows/{id}             # 查询状态
POST   /api/v1/workflows/{id}/run        # 执行一步
POST   /api/v1/workflows/{id}/pause
POST   /api/v1/workflows/{id}/resume
POST   /api/v1/workflows/{id}/spawn      # spawn 子 workflow
GET    /api/v1/workflows/{id}/children

# Future: v3.5+
POST   /api/v1/workflows/{id}/run-until-blocked  # 自动执行到阻塞点
```

---

## 工作量估算（极简）

### 人员配置

| 角色 | 人数 | 工作量 | 说明 |
|------|------|--------|------|
| Python 开发 | 1 | 25-30 人天 | 全栈开发 |
| 测试 | 0.5 | 5 人天 | 基础测试 |

**总计**: 30-35 人天（vs 原复杂计划 122 人天，**节省 70%**）

### 时间线

```
Week 1-2: 核心基础设施     (10 天)
Week 3-4: Orchestrator 逻辑 (10 天)
Week 5-6: 可选增强 + 集成  (10 天)

总周期: 4-6 周
```

---

## 风险管理（极简）

### 已移除的风险

| 原风险 | 状态 |
|--------|------|
| StateMachine 并发安全性 | ✅ 无需考虑（单进程） |
| Redis Streams 性能 | ✅ 无需考虑（内存事件） |
| L3 并发队列复杂度 | ✅ 无需考虑（asyncio.Queue） |
| Celery vs 自研决策 | ✅ 无需考虑（串行 + 预留并发） |
| Redis 持久化/恢复 | ✅ 无需考虑（SQLite） |
| 分布式追踪 | ✅ 无需考虑（单进程） |

### v1.2 新增缓解措施

| 风险 | 缓解措施 |
|------|---------|
| SQLite 外键复杂度 | 只引用 parent_id，parent_level 作为冗余字段 |
| Executor 越权访问 | 添加"宪法"注释，明确边界 |
| run_step 行为模糊 | 规范化接口文档，明确 step 选择逻辑 |
| TaskExecution 状态混淆 | 使用独立的 TaskExecutionStatus 枚举 |

### 剩余风险

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| SQLite 性能（单实例） | 低 | 低 | 本地工具数据量小 |
| 状态机双权威问题 | 低 | 低 | DB 为唯一权威，缓存可重建 |
| L3 串行延迟 | 中 | 中 | 预留 concurrency 参数 |
| 模板复杂度 | 中 | 中 | 限制模板深度 |

---

## 功能对比

### 核心功能保留

| 功能 | 复杂版 | 极简版 v1.2 | 说明 |
|------|--------|-----------|------|
| 三层编排 | ✅ | ✅ | L1/L2/L3 全保留 |
| 统一建模 | ❌ | ✅ | 统一 workflow_instances + level |
| 状态管理 | ✅ | ✅ | 简化为单进程 |
| 模板渲染 | ✅ | ✅ | Jinja2 不变 |
| 事件系统 | ✅ | ✅ | 简化为内存 |

### 非核心功能移除

| 功能 | 复杂版 | 极简版 | 理由 |
|------|--------|--------|------|
| 高并发支持 | ✅ | ❌ | 本地工具无需 |
| 分布式 | ✅ | ❌ | 单实例 |
| Redis Streams | ✅ | ❌ | 内存足够 |
| Celery 队列 | ✅ | ❌ | asyncio.Queue |
| 并发安全锁 | ✅ | ❌ | 单线程 |
| 主从复制 | ✅ | ❌ | 无需高可用 |

### v1.2 架构改进点

| 改进点 | v1.1 | v1.2 |
|--------|------|------|
| L1/L2/L3 建模 | 统一 workflow_instances + level | ✅ 保持 |
| Orchestrator | 唯一 Orchestrator + runners | ✅ 保持 |
| 状态权威 | DB 为唯一权威 | ✅ 保持 |
| 外键设计 | 复合外键 (id, level) | **简化为只引用 parent_id** |
| TaskExecution 状态 | 复用 WorkflowStatus | **独立 TaskExecutionStatus** |
| Executor 边界 | 文档描述 | **添加"宪法"注释** |
| run_step 接口 | 签名模糊 | **规范化行为说明** |
| Future 接口 | 无 | **预留 run_until_blocked** |

---

## 实现示例

### 创建三层嵌套工作流

```python
# L1: 创建项目工作流
project = await orchestrator.create_workflow(
    level=WorkflowLevel.PROJECT,
    template_id="project_main.yaml"
)
print(f"Created L1: {project.id}")

# L2: Spawn 开发部门工作流
dev_dept = await orchestrator.spawn_workflow(
    parent_id=project.id,
    level=WorkflowLevel.DEPARTMENT,
    template_id="dept_dev.yaml"
)
print(f"Spawned L2: {dev_dept.id}")

# L3: Spawn bug fix 任务工作流
bug_fix = await orchestrator.spawn_workflow(
    parent_id=dev_dept.id,
    level=WorkflowLevel.TASK,
    template_id="task_bug_fix.yaml"
)
print(f"Spawned L3: {bug_fix.id}")

# 执行 L3 步骤（自动选择 ready step）
result = await orchestrator.run_step(bug_fix.id)
if result.status == "success":
    print(f"Step {result.step_id} completed")
    print(f"Next ready steps: {result.next_steps}")
elif result.status == "no_ready_step":
    print("No ready steps available, workflow blocked")

# 查询层级状态
state = await orchestrator.get_state(bug_fix.id)
print(f"L3 status: {state.status}")
print(f"Parent L2: {state.parent_id}")
print(f"Root L1: {state.root_id}")
```

### CLI 使用示例

```bash
# 创建项目工作流
$ lee create workflow --level project --template project_main.yaml
Created L1 workflow: wf_proj_001

# 启动执行（自动跑到下一个阻塞点）
$ lee run wf_proj_001
Starting L1 workflow: wf_proj_001
  ├─ Spawned L2 (dept_dev): wf_dept_001
  │   ├─ Spawned L3 (task_setup): wf_task_001
  │   │   └─ Step 1/3 completed
  │   │   └─ Step 2/3 completed
  │   │   └─ Step 3/3 completed ✓
  │   └─ L3 completed, updating L2 status
  └─ L2 completed, updating L1 status

L1 workflow completed ✓

# 查询状态
$ lee status wf_proj_001
Workflow: wf_proj_001 (L1: project)
Status: completed
Children (L2):
  - wf_dept_001 (department): completed
    Children (L3):
      - wf_task_001 (task): completed

# Future: v3.5+ 自动执行到阻塞点
$ lee run-until-blocked wf_proj_001
Running workflow until blocked or gate encountered...
Step 1/5 completed ✓
Step 2/5 completed ✓
Step 3/5 blocked: waiting for human approval
Run stopped at gate: approve_design
```

---

## 下一步

### 立即开始

无需 Sprint 0 POC，直接开始开发：

1. **Week 1**: SQLite 数据模型 + 状态机
2. **Week 2**: 模板引擎 + CLI 框架
3. **Week 3**: Orchestrator 核心逻辑
4. **Week 4**: 层级嵌套 + Executors
5. **Week 5-6**: Web UI（可选）+ 测试 + 文档

### 交付物结构

```
lee-orchestrator/
├── lee/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── state_machine.py      # 状态机（DB 为权威）
│   │   ├── template_engine.py    # Jinja2 模板
│   │   └── event_bus.py          # 内存事件
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── sqlite_store.py       # SQLite 存储
│   │   └── models.py             # 数据模型
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # 唯一 Orchestrator
│   │   ├── runners.py            # 视图封装
│   │   └── executors.py          # 执行器（含宪法注释）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI
│   │   └── schemas.py            # API schemas
│   └── cli/
│       ├── __init__.py
│       └── main.py               # CLI 工具
├── templates/
│   ├── project_main.yaml
│   ├── dept_dev.yaml
│   └── task_bug_fix.yaml
├── tests/
│   ├── test_orchestrator.py
│   └── test_integration.py
├── examples/
│   └── basic_workflow.py
├── pyproject.toml
└── README.md
```

### 代码规范（宪法级别）

```python
# execution/executors.py 顶部必须包含

"""
⚠️ EXECUTOR 宪法 ⚠️

本模块内的所有 Executor 必须遵守以下绝对规则：

1. 不得直接访问 SQLite
   - ❌ 禁止: from lee.storage.sqlite_store import db; await db.update(...)
   - ✅ 正确: 只通过 Orchestrator 传递的数据执行

2. 不得直接调用 Orchestrator
   - ❌ 禁止: from lee.execution.orchestrator import orch; await orch.create_workflow(...)
   - ✅ 正确: 只接收输入参数，返回执行结果

3. 职责边界
   - ✅ 接收: input_data (dict)
   - ✅ 执行: 业务逻辑（LLM 调用 / Shell 命令 / 数据处理）
   - ✅ 返回: output_data (dict)
   - ❌ 越界: 状态持久化、事件发布、workflow 创建

违反者将被视为架构叛徒，未来重构时优先清除。
"""
```

---

## 总结

### v1.2 工程细节优化

相比 v1.1，v1.2 在不增加复杂度的前提下完成了以下关键优化：

1. **外键简化**: 只引用 `parent_id`，避免复合主键
2. **状态分离**: `TaskExecution` 使用独立的状态枚举
3. **接口规范**: `run_step` 添加完整的行为说明文档
4. **宪法保护**: Executor 添加"权力边界"注释
5. **Future 预留**: 规划 `run_until_blocked` 接口

### 开发周期

| 指标 | 复杂版 | 极简版 v1.2 | 节省 |
|------|--------|-----------|------|
| 开发周期 | 14-16 周 | **4-6 周** | -70% |
| 工作量 | 122 人天 | **30-35 人天** | -70% |
| 技术栈 | PostgreSQL+Redis+Celery | **SQLite+asyncio** | 大幅简化 |

### 核心价值

- ✅ 保留三层编排核心功能
- ✅ 统一建模避免未来重构
- ✅ 单一权威状态管理
- ✅ Executor 宪法保护架构边界
- ✅ 接口规范化，便于 PM agent 集成
- ✅ 4-6 周快速交付

### 架构成熟度

v1.2 已经是一个**可以直接开工实现、且未来能平滑演进**的方案：

- 三大关键原则到位（状态权威、统一建模、唯一 Orchestrator）
- 工程细节优化（外键简化、状态分离、接口规范）
- 宪法保护（Executor 权力边界）
- Future 预留（run_until_blocked）

**可以愉快地开 Week 1 了！** 🎉
