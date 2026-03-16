---
title: LEE Orchestrator v3.1 统一架构方案
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# LEE Orchestrator v3.1 统一架构方案

> **版本**: v3.1
> **日期**: 2026-01-27
> **状态**: ✅ 实现完成

---

## 执行摘要

### v3.1 实现状态

**LEE Orchestrator v3.1 已成功整合 v1 (flowcore) 和 v3.0 的所有核心功能**

- ✅ **核心功能迁移**: 从 flowcore 迁移 20+ 核心模块
- ✅ **7 个阶段完成**: Phase 0-6 全部完成并通过测试
- ✅ **端到端验证**: 所有集成测试通过
- ✅ **架构统一**: "LEE Orchestrator Core + 四个外圈能力"架构落地

### 问题现状（已解决）

v3.0 存在两个分叉的版本：

1. **flowcore/** - 老版本，功能完整但复杂度高
   - 20+ 核心模块
   - 复杂的状态机（10+ 状态）
   - 完整的 Agent 规范系统
   - 门禁机制、循环执行、外部等待

2. **src/lee/orchestrator/** - 新版本，极简但功能不足
   - 6 个核心模块
   - 简化状态机（5 状态）
   - 固定三层结构
   - 缺少门禁、Agent 系统

### v3.1 解决方案

**统一收敛为「LEE Orchestrator Core」+「四个外圈能力」的架构**

```
┌─────────────────────────────────────────────────────────────┐
│                    客户端层（Clients）                        │
│  CLI │ FastAPI │ PM Agent │ Gate Assistant │ UI           │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 LEE Orchestrator Core（核心）                │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ State       │  │ Template     │  │ Orchestrator    │   │
│  │ Machine     │  │ Manager      │  │（调度器）        │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
│  ┌─────────────┐  ┌──────────────┐                          │
│  │ EventBus    │  │ SQLiteStore  │                          │
│  └─────────────┘  └──────────────┘                          │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    执行器层（Executors）                      │
│  LLM │ Shell │ MCP │ Legacy Executor │ Custom                     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    存储层（Storage）                         │
│  SQLite（workflow_instances, templates, executions, logs）   │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. 架构总览

### 1.1 五层架构

```
┌───────────────────────────────────────────────────────────────┐
│ ① Spec & Constitution Layer                                 │  ← 规则定义层
│  - Workflow Template (L1/L2/L3)                             │
│  - Agent Spec                                               │
│  - Skill Spec                                               │
│  - Contract Spec                                            │
│  - Constitution（权力边界、执行规则）                         │
├───────────────────────────────────────────────────────────────┤
│ ② Runtime Core (Orchestrator)                               │  ← 唯一状态机 & 调度
│  - WorkflowStateMachine                                     │
│  - TemplateManager                                          │
│  - Orchestrator（调度器）                                   │
│  - EventBus                                                │
├───────────────────────────────────────────────────────────────┤
│ ③ Executors Layer                                           │  ← 执行层
│  - LLMExecutor                                             │
│  - ShellExecutor                                           │
│  - MCPSkillExecutor                                        │
│  - Legacy ExecutorExecutor                                         │
├───────────────────────────────────────────────────────────────┤
│ ④ Interface Layer（客户端）                                  │  ← 入口层
│  - CLI / FastAPI                                           │
│  - PM Agent（Claude Code）                                  │
│  - Gate Assistant                                          │
│  - UI                                                     │
├───────────────────────────────────────────────────────────────┤
│ ⑤ External World                                            │  ← 外部世界
│  - 项目文件系统                                             │
│  - CI/Test 工具                                            │
│  - MCP Servers                                             │
│  - HTTP APIs                                               │
└───────────────────────────────────────────────────────────────┘
```

**关键原则**：

* 上层定义规则，下层保证流程
* 同层之间不越权
* Orchestrator 是唯一状态权威

### 1.2 四个外圈能力（v3.1 新增）

v3.1 在 Core 之外新增四个外圈能力层：

```
┌─────────────────────────────────────────────────────────────┐
│                    四个外圈能力（v3.1）                       │
├─────────────────────────────────────────────────────────────┤
│  🤖 Agent 系统                                              │
│  - AgentLoader - Agent 规范加载                             │
│  - AgentResolver - Agent 引用解析                           │
│  - AgentContextBuilder - 上下文构建                         │
│  - AgentInjector - 依赖注入                                 │
├─────────────────────────────────────────────────────────────┤
│  👁️ 可观测性系统                                            │
│  - Span 追踪 - 基于 execution-trace contract                │
│  - EventLog - 事件日志记录                                  │
│  - 数据脱敏 - 敏感信息保护                                  │
├─────────────────────────────────────────────────────────────┤
│  ✅ 验证器系统                                              │
│  - SchemaValidator - Schema 验证                           │
│  - FileValidator - 文件验证                                 │
│  - 可扩展验证器框架                                         │
├─────────────────────────────────────────────────────────────┤
│  🔧 工作流工程                                              │
│  - WorkflowGenerator - 工作流生成                          │
│  - WorkflowParser - 工作流解析                             │
│  - TemplateResolver - 模板变量解析                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. v3.1 实现的模块清单

### 2.1 核心模块（Core）

| 模块 | 文件 | 功能 | 状态 |
|------|------|------|------|
| EventBus | `event_bus.py` | 事件发布/订阅 | ✅ 已迁移 |
| ProjectConfig | `project_config.py` | 项目配置管理 | ✅ 已迁移 |
| WorkflowStateMachine | `state_machine.py` | 工作流状态机 | ✅ 已有 |
| TemplateManager | `template_manager.py` | 模板管理 | ✅ 已有 |
| Orchestrator | `orchestrator.py` | 核心调度器 | ✅ 已有 |
| WorkflowGenerator | `workflow_generator.py` | 工作流生成 | ✅ 已迁移 |
| WorkflowParser | `workflow_parser.py` | 工作流解析 | ✅ 已迁移 |
| TemplateResolver | `template_resolver.py` | 模板变量解析 | ✅ 已迁移 |
| TokenManager | `token_manager.py` | 令牌管理 | ✅ 已迁移 |

### 2.2 Agent 系统

| 模块 | 文件 | 功能 | 状态 |
|------|------|------|------|
| AgentLoader | `agent_loader.py` | Agent 规范加载 | ✅ 已迁移 |
| AgentResolver | `agent_resolver.py` | Agent 引用解析 | ✅ 已迁移 |
| AgentContextBuilder | `agent_context.py` | 上下文构建 | ✅ 已迁移 |
| AgentInjector | `agent_injector.py` | 依赖注入 | ✅ 已迁移 |
| AgentSpec | `agent_loader.py` | Agent 数据模型 | ✅ 已迁移 |

### 2.3 可观测性系统

| 模块 | 文件 | 功能 | 状态 |
|------|------|------|------|
| Run | `trace.py` | 运行记录 | ✅ 已迁移 |
| Span | `trace.py` | 执行跨度 | ✅ 已迁移 |
| Artifact | `trace.py` | 产物记录 | ✅ 已迁移 |
| EventLog | `event_log.py` | 事件日志 | ✅ 已迁移 |
| sanitize | `sanitization.py` | 数据脱敏 | ✅ 已迁移 |

### 2.4 验证器系统

| 模块 | 文件 | 功能 | 状态 |
|------|------|------|------|
| Validator | `validators/base.py` | 验证器基类 | ✅ 已迁移 |
| SchemaValidator | `validators/schema_validator.py` | Schema 验证 | ✅ 已迁移 |
| FileValidator | `validators/file_validator.py` | 文件验证 | ✅ 已迁移 |
| ValidationResult | `validators/base.py` | 验证结果 | ✅ 已迁移 |

### 2.5 高级特性

| 模块 | 文件 | 功能 | 状态 |
|------|------|------|------|
| RetryPolicy | `retry.py` | 重试策略 | ✅ 已迁移 |
| RetryExecutor | `retry.py` | 重试执行器 | ✅ 已迁移 |
| execute_with_retry | `retry.py` | 便捷重试函数 | ✅ 已迁移 |
| TokenManager | `token_manager.py` | 令牌管理 | ✅ 已迁移 |
| ToolGuard | `token_manager.py` | 工具权限守卫 | ✅ 已迁移 |

### 2.6 存储层

| 模块 | 文件 | 功能 | 状态 |
|------|------|------|------|
| SQLiteStore | `sqlite_store.py` | SQLite 存储 | ✅ 已有 |
| Models | `models.py` | 数据模型 | ✅ 已有 |

### 2.7 执行器层

| 模块 | 文件 | 功能 | 状态 |
|------|------|------|------|
| LLMExecutor | `llm_executor.py` | LLM 执行器 | ✅ 已有 |
| ShellExecutor | `shell_executor.py` | Shell 执行器 | ✅ 已有 |
| Legacy ExecutorExecutor | `legacy_executor_executor.py` | Legacy Executor 执行器 | ✅ 已有 |
| ExecutorFactory | `executors.py` | 执行器工厂 | ✅ 已有 |

---

## 3. 统一数据模型

### 3.1 三层 Workflow 统一建模

**核心原则**：三个层级用**同一个模型、同一张表**表达

```python
@dataclass
class WorkflowInstance:
    """统一的工作流实例模型（L1/L2/L3）"""

    # 标识
    id: str
    level: WorkflowLevel  # project | department | task
    parent_id: Optional[str]  # L1=null, L2=L1.id, L3=L2.id

    # 模板
    template_id: str

    # 状态
    status: WorkflowStatus  # pending | running | paused | completed | failed
    current_step: Optional[str]

    # 数据
    data: Dict[str, Any]  # params + 中间结果 + completed_steps

    # 时间戳
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
```

### 3.2 层级关系

```
L1: Project
  level = "project"
  parent_id = None
  ↓ spawn
L2: Department
  level = "department"
  parent_id = <L1.id>
  ↓ spawn
L3: Task
  level = "task"
  parent_id = <L2.id>
```

---

## 4. 核心定位

### 4.1 Orchestrator 是什么

**Orchestrator = 唯一的工作流状态机 + 唯一的调度中心**

> 它不思考，只裁决「现在该干什么」

### 4.2 Orchestrator 不是什么

* ❌ 不是大模型
* ❌ 不是 agent
* ❌ 不是 skill 执行器
* ❌ 不做业务决策
* ❌ 不直接调用 Claude/OpenAI
* ❌ 不直接读写业务文件

### 4.3 核心职责（8 条）

1. **加载 Workflow Template**
   - 从 YAML 读取模板（project/dept/task 三种 level）
   - 校验节点依赖、kind、参数

2. **创建/恢复 Workflow Instance**
   - 创建 L1/L2/L3 实例，建立 parent-child 关系
   - 进程重启后从 DB 读回所有 instance 状态

3. **计算 ready step**
   - 对某个 workflow_id：
     - 计算满足依赖、未执行、未暂停的 steps
     - 决定执行顺序（拓扑 + priority）

4. **执行一个 step**
   - 基于 step.kind/executor_type 构造请求
   - 调用对应 executor
   - 收集输出（文件路径、结构化结果）

5. **更新状态机**
   - 更新当前 step 状态
   - 更新 workflow 状态
   - 触发 parent 的状态传播

6. **spawn 子 workflow**
   - L1 → L2（部门流程）
   - L2 → L3（任务流程）
   - 管理生命周期与聚合规则

7. **暂停/恢复**
   - 标记 paused/resumed
   - 让 ready step 计算逻辑尊重 paused 状态

8. **提供外部 API**
   - `create_workflow/run_step/run_until_blocked/get_state/spawn/pause/resume`

---

## 5. API 设计

### 5.1 核心API（提供给所有客户端）

```python
# ============ 工作流管理 ============

async def api_create_workflow(
    level: str,  # "project" | "department" | "task"
    template_id: str,
    parent_id: Optional[str] = None,
    data: Optional[Dict] = None,
) -> Dict:
    """创建工作流"""
    pass

async def api_spawn_workflow(
    parent_id: str,
    level: str,
    template_id: str,
    data: Optional[Dict] = None,
) -> Dict:
    """创建子工作流"""
    pass

# ============ 状态查询 ============

async def api_get_state(
    workflow_id: str
) -> Dict:
    """获取工作流状态"""
    pass

async def api_list_ready_steps(
    workflow_id: str
) -> List[Dict]:
    """列出可执行步骤"""
    pass

# ============ 执行控制 ============

async def api_run_step(
    workflow_id: str,
    step_id: Optional[str] = None,
) -> Dict:
    """执行指定步骤"""
    pass

async def api_next_step(
    workflow_id: str
) -> Dict:
    """执行下一个就绪步骤"""
    pass

async def api_run_until_blocked(
    workflow_id: str,
    max_steps: int = 10,
) -> Dict:
    """执行直到阻塞"""
    pass

# ============ 暂停/恢复 ============

async def api_pause(
    workflow_id: str
) -> Dict:
    """暂停工作流"""
    pass

async def api_resume(
    workflow_id: str
) -> Dict:
    """恢复工作流"""
    pass
```

### 5.2 Gate API（供 Gate Assistant 使用）

```python
async def api_gate_list_pending(
    workflow_id: str
) -> List[Dict]:
    """列出待审批门禁"""
    pass

async def api_gate_show(
    workflow_id: str,
    step_id: str
) -> Dict:
    """查看门禁详情"""
    pass

async def api_gate_decide(
    workflow_id: str,
    step_id: str,
    decision: str,  # "approve" | "reject"
    comment: str,
    decided_by: str,
) -> Dict:
    """提交门禁决策"""
    pass
```

---

## 6. 目录结构（v3.1）

### 6.1 标准项目结构

```
src/lee/orchestrator/
├── __init__.py
│
├── core/                       # 核心能力模块
│   ├── __init__.py
│   ├── state_machine.py        # 工作流状态机（v3 原有）
│   ├── template_manager.py     # 模板管理器（v3 原有）
│   ├── event_bus.py           # 事件总线（v1 迁移）
│   ├── project_config.py      # 项目配置（v1 迁移）
│   ├── workflow_generator.py  # 工作流生成器（v1 迁移）
│   ├── workflow_parser.py     # 工作流解析器（v1 迁移）
│   ├── template_resolver.py   # 模板变量解析器（v1 迁移）
│   └── token_manager.py       # 令牌管理（v1 迁移）
│
├── storage/                    # 存储层
│   ├── __init__.py
│   ├── models.py              # 数据模型
│   ├── sqlite_store.py        # SQLite 存储
│   └── event_log.py           # 事件日志（v1 迁移）
│
├── execution/                  # 执行层
│   ├── __init__.py
│   ├── orchestrator.py        # 核心调度器（v3 原有）
│   ├── state_machine.py       # 工作流状态机（v3 原有）
│   ├── template_manager.py    # 模板管理器（v3 原有）
│   ├── executors.py           # 执行器工厂（v3 原有）
│   ├── llm_executor.py        # LLM 执行器（v3 原有）
│   ├── shell_executor.py      # Shell 执行器（v3 原有）
│   ├── legacy_executor_executor.py    # Legacy Executor 执行器（v3 原有）
│   ├── gate_api.py           # Gate API（v3 原有）
│   ├── retry.py              # 重试机制（v1 迁移）
│   │
│   ├── Agent 系统（v1 迁移）
│   ├── agent_loader.py       # Agent 加载器
│   ├── agent_resolver.py     # Agent 解析器
│   ├── agent_context.py      # Agent 上下文构建器
│   ├── agent_injector.py     # Agent 依赖注入
│   │
│   ├── 可观测性（v1 迁移）
│   ├── trace.py              # Span 追踪系统
│   └── tracing_integration.py # 追踪集成
│   │
│   └── validators/           # 验证器系统（v1 迁移）
│       ├── __init__.py
│       ├── base.py           # 验证器基类
│       ├── schema_validator.py
│       └── file_validator.py
│
├── api/                        # API 层
│   └── __init__.py
│
├── cli/                        # CLI 层
│   ├── __init__.py
│   └── main.py
│
└── utils/                      # 工具模块
    ├── __init__.py
    └── sanitization.py        # 数据脱敏（v1 迁移）
```

---

## 7. v3.1 实现状态

### 7.1 已完成功能（✅）

#### P0 - 核心功能（必须实现）

- [x] **模板加载**
  - [x] 加载 L1/L2/L3 模板
  - [x] 支持 YAML 格式
  - [x] 验证模板格式

- [x] **工作流创建**
  - [x] 创建 L1 Project
  - [x] 创建 L2 Department
  - [x] 创建 L3 Task
  - [x] 建立 parent-child 关系

- [x] **步骤执行**
  - [x] 计算 ready steps
  - [x] 执行单个 step
  - [x] 更新状态机
  - [x] 支持依赖关系

- [x] **状态查询**
  - [x] 获取 workflow 状态
  - [x] 列出 ready steps
  - [x] 查看子工作流

- [x] **暂停/恢复**
  - [x] 暂停 workflow
  - [x] 恢复 workflow
  - [x] 尊重 paused 状态

#### P1 - 可选实现

- [x] **run_until_blocked**
  - [x] 执行直到阻塞
  - [x] 支持最大步数限制

- [x] **门禁系统**
  - [x] human_gate step 类型
  - [x] Gate API
  - [x] approve/reject 逻辑

- [x] **EventBus**
  - [x] 发布事件
  - [x] 订阅事件
  - [x] 事件日志

#### P1 - Agent 系统（v3.1 新增）

- [x] **Agent 规范系统**
  - [x] AgentLoader - 加载 Agent 规范
  - [x] AgentResolver - 解析 Agent 引用
  - [x] AgentSpec - Agent 数据模型
  - [x] AgentContextBuilder - 构建执行上下文
  - [x] AgentInjector - 依赖注入

#### P1 - 可观测性（v3.1 新增）

- [x] **追踪系统**
  - [x] Run - 运行记录
  - [x] Span - 执行跨度
  - [x] Artifact - 产物记录
  - [x] EventLog - 事件日志
  - [x] 数据脱敏

#### P1 - 验证器系统（v3.1 新增）

- [x] **验证器框架**
  - [x] Validator 基类
  - [x] ValidationResult
  - [x] ValidationError
  - [x] ValidationSeverity

- [x] **内置验证器**
  - [x] SchemaValidator
  - [x] FileValidator

#### P2 - 高级特性（v3.1 新增）

- [x] **重试机制**
  - [x] RetryPolicy - 重试策略
  - [x] RetryExecutor - 重试执行器
  - [x] 指数退避算法

- [x] **工作流工程**
  - [x] WorkflowGenerator - 生成工作流
  - [x] WorkflowParser - 解析工作流
  - [x] TemplateResolver - 模板变量解析

- [x] **令牌管理**
  - [x] TokenManager - 令牌签发和验证
  - [x] ToolGuard - 工具权限守卫
  - [x] HMAC 签名

### 7.2 测试状态

| 测试文件 | 测试内容 | 状态 |
|----------|----------|------|
| `test_v3_integration_phase1.py` | EventBus, ProjectConfig, Agent 系统 | ✅ 通过 |
| `test_v3_integration_phase2.py` | Trace, EventLog, Sanitization | ✅ 通过 |
| `test_v3_integration_phase3.py` | Validator 系统 | ✅ 通过 |
| `test_v3_integration_phase4.py` | WorkflowGenerator, WorkflowParser | ✅ 通过 |
| `test_v3_integration_phase5.py` | Retry, TokenManager | ✅ 通过 |
| `test_v3_e2e_integration.py` | 端到端集成测试 | ✅ 通过 |

---

## 8. 迁移路径

### 8.1 从 v3.0 到 v3.1

v3.1 已完成从 flowcore 到 v3.0 的增量演进：

#### 阶段 0：准备和规划 ✅
- [x] 创建 `flowcore.backup/` 备份目录
- [x] 规划目录结构

#### 阶段 1：核心功能迁移 (P0) ✅
- [x] `event_bus.py` - 事件总线
- [x] `project_config.py` - 项目配置
- [x] Agent 系统基础模块

#### 阶段 2：可观测性迁移 (P1) ✅
- [x] `trace.py` - Span 追踪系统
- [x] `event_log.py` - 事件日志
- [x] `sanitization.py` - 数据脱敏

#### 阶段 3：验证系统迁移 (P1) ✅
- [x] `validators/base.py` - 验证器基类
- [x] `validators/schema_validator.py`
- [x] `validators/file_validator.py`

#### 阶段 4：工作流工程迁移 (P2) ✅
- [x] `workflow_generator.py` - 工作流生成器
- [x] `workflow_parser.py` - 工作流解析器
- [x] `template_resolver.py` - 模板变量解析器

#### 阶段 5：高级特性迁移 (P2) ✅
- [x] `retry.py` - 重试机制
- [x] `token_manager.py` - 令牌管理

#### 阶段 6：集成测试和验收 ✅
- [x] Phase 1-5 阶段测试全部通过
- [x] 端到端集成测试全部通过

---

## 9. 成功标准

### 9.1 v3.1 完成定义

> **我可以在 CLI 里从 0 创建一个项目 workflow，spawn 出一个 QA 子流程，再 spawn 一个 bug_fix 任务，跑到 human gate 停下来。**

### 9.2 验收标准

- [x] 能创建 L1 Project workflow
- [x] 能 spawn L2 Department workflow
- [x] 能 spawn L3 Task workflow
- [x] 能执行 agent 类型的 step（LLM）
- [x] 能执行 skill 类型的 step（Shell）
- [x] 能执行 human_gate 类型的 step（暂停）
- [x] CLI 能查看 workflow 状态
- [x] PM Agent 能调用 Orchestrator API
- [x] Agent 系统完整迁移
- [x] 可观测性系统完整迁移
- [x] 验证器系统完整迁移
- [x] 高级特性（重试、令牌）完整迁移

---

## 10. 参考资料

### 架构设计
- [LEE_Orchestrator_v3_Diagrams.md](LEE_Orchestrator_v3_Diagrams.md) - 架构图
- [LEE_Orchestrator_v3_Implementation_Plan.md](LEE_Orchestrator_v3_Implementation_Plan.md) - 实施计划

### 版本对比
- [../../examples/version_comparison_report.md](../../examples/version_comparison_report.md)

### LLM/Legacy Executor 集成
- [../../examples/llm_legacy_executor_final_report.md](../../examples/llm_legacy_executor_final_report.md)

### 迁移记录
- `flowcore.backup/` - v1 (flowcore) 备份目录

---

**文档版本**: v3.1
**最后更新**: 2026-01-27
**维护者**: LEE Team
**状态**: ✅ v3.1 实现完成
