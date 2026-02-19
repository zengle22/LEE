---
title: LEE Orchestrator v3.1 架构图
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# LEE Orchestrator v3.1 架构图

> **版本**: v3.1
> **更新**: 2026-01-27
> **状态**: ✅ 实现完成

---

## 1. 总体架构图（v3.1）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         客户端层（Clients）                              │
│                                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │   CLI    │  │ FastAPI  │  │ PM Agent │  │   Gate   │  │   UI   │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│                                                                           │
│  全部使用相同的 Orchestrator API，权限完全一致                              │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      LEE Orchestrator Core（核心）                          │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        Orchestrator（调度器）                        │  │
│  │  ┌────────────────────────────────────────────────────────────┐   │  │
│  │  │  create_workflow │ spawn │ run_step │ pause │ get_state    │   │  │
│  │  └────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐    │
│  │   State      │  │   Template   │  │       EventBus          │    │
│  │   Machine    │  │   Manager    │  │  (StepCompleted/Failed)  │    │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘    │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      SQLiteStore（存储）                            │  │
│  │  ┌────────────────────────────────────────────────────────────┐   │  │
│  │  │  workflow_instances │ templates │ task_executions │ logs  │   │  │
│  │  └────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    四个外圈能力（v3.1 新增）                             │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  🤖 Agent 系统                                                    │  │
│  │  AgentLoader │ AgentResolver │ AgentContextBuilder │ Injector │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  👁️ 可观测性系统                                                 │  │
│  │  Run │ Span │ Artifact │ EventLog │ Sanitize                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  ✅ 验证器系统                                                   │  │
│  │  Validator │ SchemaValidator │ FileValidator                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  🔧 工作流工程                                                  │  │
│  │  WorkflowGenerator │ WorkflowParser │ TemplateResolver        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        执行器层（Executors）                             │
│                                                                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐      │
│  │    LLM     │  │   Shell    │  │    MCP     │  │  MetaGPT   │      │
│  │  Executor  │  │  Executor  │  │  Executor  │  │  Executor  │      │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘      │
│                                                                           │
│  统一接口：execute(input_data: Dict) -> Dict                              │
│  权力边界：不得访问 DB、不得调用 Orchestrator                              │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      存储层（Storage）                                 │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                         SQLite Database                            │  │
│  │  ┌────────────────────────────────────────────────────────────┐   │  │
│  │  │ workflow_instances │ templates │ task_executions │ logs  │   │  │
│  │  └────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  SQLite 是唯一状态权威                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 三层 Workflow 数据模型

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WorkflowInstance 统一模型                              │
│                                                                           │
│  id: TEXT                                                                  │
│  level: "project" | "department" | "task"                                  │
│  parent_id: TEXT (NULL for L1, L1.id for L2, L2.id for L3)               │
│  template_id: TEXT                                                          │
│  status: "pending" | "running" | "paused" | "completed" | "failed"           │
│  current_step: TEXT                                                          │
│  data: JSON (params + results + completed_steps)                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 层级关系示例

```
                    WorkflowInstance
                           │
            ┌──────────────┼──────────────┐
            │              │              │
        L1:Project      L2:Department   L3:Task
        level=         level=         level=
        "project"      "department"    "task"
        parent_id=NULL  parent_id=L1    parent_id=L2
            │              │              │
            └──────────────┴──────────────┘
                    │
         同一张表，统一建模
```

---

## 3. 工作流执行流程

```
1. 创建 Workflow
   ┌─────────────┐
   │ Client      │
   │ (CLI/Agent) │
   └──────┬──────┘
          │ api_create_workflow(level="project", template_id="project_main")
          ▼
   ┌─────────────┐
   │Orchestrator  │
   │             │
   │ ┌─────────┐ │
   │ │   DB    │ │
   │ └────┬────┘ │
   └──────┼──────┘
          │ INSERT INTO workflow_instances
          ▼
   ┌─────────────┐
   │   SQLite    │
   └─────────────┘

2. 执行 Step
   ┌─────────────┐
   │ Client      │
   │ (CLI/Agent) │
   └──────┬──────┘
          │ api_run_step(workflow_id)
          ▼
   ┌─────────────┐
   │Orchestrator  │
   │             │
   │ ┌─────────┐ │ → 计算 ready steps
   │ │ State   │ │
   │ │ Machine │ │
   │ └────┬────┘ │
   └──────┼──────┘
          │ 选一个 ready step
          ▼
   ┌─────────────┐
   │  Executor   │
   │             │
   │ ┌─────────┐ │
   │ │   LLM   │ │ → 调用 LLM API
   │ │  Shell  │ │ → 执行 Shell 命令
   │ │   MCP   │ │ → 调用 MCP 工具
   │ └────┬────┘ │
   └──────┼──────┘
          │ return {"status": "completed", "output": ...}
          ▼
   ┌─────────────┐
   │Orchestrator  │
   │             │
   │ ┌─────────┐ │
   │ │   DB    │ │ → 更新 workflow 状态
   │ └─────────┘ │
   └─────────────┘

3. Spawn 子 Workflow
   ┌─────────────┐
   │ Client      │
   │ (CLI/Agent) │
   └──────┬──────┘
          │ api_spawn_workflow(parent_id, level="department")
          ▼
   ┌─────────────┐
   │Orchestrator  │
   │             │
   │ ┌─────────┐ │
   │ │ Template│ │ → 读取 dept 模板
   │ │ Manager │ │
   │ └────┬────┘ │
   └──────┼──────┘
          │ 创建 L2 实例，parent_id=L1.id
          ▼
   ┌─────────────┐
   │   SQLite    │
   └─────────────┘
```

---

## 4. Gate 流程

```
1. 遇到 human_gate Step
   ┌─────────────┐
   │Orchestrator  │
   │             │
   │ ┌─────────┐ │
   │ │ State   │ │ → 发现 step.kind = "human_gate"
   │ │ Machine │ │
   │ └────┬────┘ │
   └──────┼──────┘
          │ 暂停 workflow，等待人工决策
          ▼
   ┌─────────────┐
   │   SQLite    │
   │ status=     │
   │ "paused"    │
   └─────────────┘

2. 人工审批
   ┌─────────────┐
   │   Gate      │
   │  Assistant │
   └──────┬──────┘
          │ api_gate_list_pending()
          ▼
   ┌─────────────┐
   │Orchestrator  │
   │             │
   │ ┌─────────┐ │
   │ │   DB    │ │ → 查询待审批 gate
   │ └─────────┘ │
   └──────┼──────┘
          │ 返回 gate 列表
          ▼
   ┌─────────────┐
   │   Gate      │
   │  Assistant │
   └──────┬──────┘
          │ api_gate_decide(workflow_id, step_id, "approve")
          ▼
   ┌─────────────┐
   │Orchestrator  │
   │             │
   │ ┌─────────┐ │
   │ │ State   │ │ → 更新 step 状态
   │ │ Machine │ │ → 恢复 workflow
   │ └────┬────┘ │
   └──────┼──────┘
          │ 继续执行下一步
          ▼
   ┌─────────────┐
   │   SQLite    │
   │ status=     │
   │ "running"   │
   └─────────────┘
```

---

## 5. 状态转换图

```
Workflow 状态转换:

┌─────────┐
│ PENDING │
└────┬────┘
     │ run_step()
     ▼
┌─────────┐
│ RUNNING │ ◄───┐ pause()
└────┬────┘     │ resume()
     │            │
     │ completed/   │
     │ failed       │
     ▼              │
┌─────────┐      ┌────────┐
│COMPLETED│      │ PAUSED │
└─────────┘      └────────┘

Step 状态转换:

┌─────────┐
│ PENDING │ ◄──┐ depends_on satisfied
└────┬────┘    │
     │           │
     │ ready     │
     ▼           │
┌─────────┐     │
│RUNNING  │     │
└────┬────┘     │
     │           │
     │ completed/ │
     │ failed     │
     ▼           │
┌─────────┐   ┌──┴───┐
│COMPLETED│   │BLOCKED│ (依赖未满足)
└─────────┘   └───────┘
```

---

## 6. 调用时序图

### 6.1 创建三层 Workflow

```
Client      Orchestrator    TemplateManager    SQLite
  │              │                │            │
  │ create_workflow("project") │            │
  │──────────────>│                │            │
  │              │ load_template() │            │
  │              │────────────────>│            │
  │              │<─────────────────│            │
  │              │                │            │
  │              │ INSERT workflow(L1)           │
  │              │──────────────────────>       │
  │              │<───────────────────────       │
  │              │                │            │
  │              │ spawn_department()│            │
  │              │──────────────────────>       │
  │              │ load_template() │            │
  │              │────────────────>│            │
  │              │<─────────────────│            │
  │              │                │            │
  │              │ INSERT workflow(L2)           │
  │              │──────────────────────>       │
  │              │<───────────────────────       │
  │              │                │            │
  │              │ spawn_task()      │            │
  │              │──────────────────────>       │
  │              │ load_template() │            │
  │              │────────────────>│            │
  │              │<─────────────────│            │
  │              │                │            │
  │              │ INSERT workflow(L3)           │
  │              │──────────────────────>       │
  │              │<───────────────────────       │
  │              │                │            │
  │<─────────────│                │            │
```

### 6.2 执行 Step（v3.1 带可观测性）

```
Client      Orchestrator    StateMachine    Executor    TraceLog    SQLite
  │              │               │           │          │          │
  │ run_step()   │               │           │          │          │
  │──────────────>│               │           │          │          │
  │              │ get_ready_steps()           │          │          │
  │              │────────────────>          │          │          │
  │              │<─────────────────          │          │          │
  │              │               │           │          │          │
  │              │ start_step()              │          │          │
  │              │────────────────>          │          │          │
  │              │<─────────────────          │          │ log_step_started()
  │              │               │           │          │────────────────>│
  │              │ UPDATE status=running                │          │
  │              │──────────────────────────>       │          │
  │              │<───────────────────────────       │          │
  │              │               │           │          │          │
  │              │ execute_step()  │           │          │          │
  │              │───────────────────>│          │          │
  │              │               │           │          │          │
  │              │               │ call LLM/Shell│          │          │
  │              │               │────────────>│          │          │
  │              │               │<────────────│          │          │
  │              │<───────────────────│          │          │          │
  │              │               │           │          │          │
  │              │ complete_step()             │          │ log_step_completed()
  │              │────────────────>          │          │────────────────>│
  │              │<─────────────────          │          │          │
  │              │ UPDATE status=completed             │          │
  │              │──────────────────────────>       │          │
  │              │<───────────────────────────       │          │
  │              │               │           │          │          │
  │<─────────────│               │           │          │          │
```

---

## 7. 目录结构映射（v3.1）

```
docs/
├── architecture/
│   ├── LEE_Orchestrator_v3_Architecture.md  # 本文档
│   └── LEE_Orchestrator_v3_Diagrams.md        # 架构图（v3.1）
│
specs/                          # Spec 层
├── workflows/                   # Workflow 模板
│   ├── project_*.yaml         # L1 模板
│   ├── dept_*.yaml            # L2 模板
│   └── task_*.yaml            # L3 模板
│
├── agents/                     # Agent 规范
│   ├── pm.yaml
│   ├── dev.yaml
│   └── qa.yaml
│
└── skills/                     # Skill 规范
    ├── shell.yaml
    └── mcp.yaml

src/lee/orchestrator/
├── core/                       # 核心能力模块
│   ├── state_machine.py       # 工作流状态机（v3 原有）
│   ├── template_manager.py    # 模板管理器（v3 原有）
│   ├── event_bus.py           # 事件总线（v1 迁移）✅
│   ├── project_config.py      # 项目配置（v1 迁移）✅
│   ├── workflow_generator.py  # 工作流生成器（v1 迁移）✅
│   ├── workflow_parser.py     # 工作流解析器（v1 迁移）✅
│   ├── template_resolver.py   # 模板变量解析器（v1 迁移）✅
│   └── token_manager.py       # 令牌管理（v1 迁移）✅
│
├── storage/                    # 存储层
│   ├── models.py              # 数据模型
│   ├── sqlite_store.py        # SQLite 存储
│   └── event_log.py           # 事件日志（v1 迁移）✅
│
├── execution/                  # 执行层
│   ├── orchestrator.py        # 核心调度器（v3 原有）
│   ├── state_machine.py       # 工作流状态机（v3 原有）
│   ├── template_manager.py    # 模板管理器（v3 原有）
│   ├── executors.py           # 执行器工厂（v3 原有）
│   ├── llm_executor.py        # LLM 执行器（v3 原有）
│   ├── shell_executor.py      # Shell 执行器（v3 原有）
│   ├── metagpt_executor.py    # MetaGPT 执行器（v3 原有）
│   ├── gate_api.py           # Gate API（v3 原有）
│   │
│   ├── Agent 系统（v1 迁移）✅
│   ├── agent_loader.py       # Agent 加载器
│   ├── agent_resolver.py     # Agent 解析器
│   ├── agent_context.py      # Agent 上下文构建器
│   └── agent_injector.py     # Agent 依赖注入
│   │
│   ├── 可观测性（v1 迁移）✅
│   ├── trace.py              # Span 追踪系统
│   └── tracing_integration.py # 追踪集成
│   │
│   ├── 验证器系统（v1 迁移）✅
│   └── validators/
│       ├── base.py           # 验证器基类
│       ├── schema_validator.py
│       └── file_validator.py
│   │
│   └── retry.py              # 重试机制（v1 迁移）✅
│
├── api/                        # API 层
│   └── __init__.py
│
├── cli/                        # CLI 层
│   └── main.py
│
└── utils/                      # 工具模块
    └── sanitization.py        # 数据脱敏（v1 迁移）✅

tests/                          # 测试（v3.1 新增）
├── test_v3_integration_phase1.py  # Phase 1 测试 ✅
├── test_v3_integration_phase2.py  # Phase 2 测试 ✅
├── test_v3_integration_phase3.py  # Phase 3 测试 ✅
├── test_v3_integration_phase4.py  # Phase 4 测试 ✅
├── test_v3_integration_phase5.py  # Phase 5 测试 ✅
└── test_v3_e2e_integration.py     # 端到端测试 ✅
```

---

## 8. 权力边界

```
┌─────────────────────────────────────────────────────────────┐
│                       权力层级                              │
│                                                             │
│  ┌──────────────┐                                          │
│  │   人类       │  最高权力                                 │
│  │  (Human)     │  - Gate 审批                               │
│  │              │  - 最终决策                               │
│  └──────┬───────┘                                          │
│         │                                                  │
│  ┌──────▼───────┐                                          │
│  │ Orchestrator │  流程控制权                               │
│  │              │  - 状态管理                               │
│  │              │  - 步骤调度                               │
│  │              │  - spawn 子流程                           │
│  └──────┬───────┘                                          │
│         │                                                  │
│  ┌──────▼───────┐                                          │
│  │   Executor   │  执行权                                 │
│  │              │  - 执行具体任务                            │
│  │              │  - 调用外部服务                            │
│  └──────┬───────┘                                          │
│         │                                                  │
│  ┌──────▼───────┐                                          │
│  │  Tool/MCP    │  工具权                                  │
│  │              │  - 实际执行                               │
│  └──────────────┘                                          │
│                                                             │
│  ⚠️  禁止反向越权                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. 数据流（v3.1）

```
1. Template → WorkflowInstance

   Template(YAML)                    WorkflowInstance(DB)
   ┌──────────────┐                   ┌──────────────────┐
   │name: project │                   │id: wf_proj_001 │
   │level: project│                   │level: project   │
   │steps: [...] │                   │template_id: ...  │
   │              │                   │status: pending  │
   └──────────────┘                   └──────────────────┘
         │                                     │
         │ create_workflow()              │
         └─────────────────────────────>│

2. WorkflowInstance → Step Execution

   WorkflowInstance                    StepExecution
   ┌──────────────────┐                ┌──────────────────┐
   │id: wf_proj_001  │                │workflow_id: ... │
   │status: running  │                │step_id: step1   │
   │current_step: ...│                │executor: llm    │
   └──────────────────┘                └──────────────────┘
         │                                     │
         │ run_step()                         │
         └─────────────────────────────>│

3. Step Execution → Output（带 Trace）

   StepExecution                      Trace            Output
   ┌──────────────────┐                ┌──────┐         ┌──────────────────┐
   │executor: llm     │                │ Run  │────────>│status: completed │
   │input: {...}     │                │ Span │         │output: {...}    │
   └──────────────────┘                │Artifact│       └──────────────────┘
                                         └──────┘
```

---

## 10. 集成点

```
┌─────────────────────────────────────────────────────────────┐
│                    LEE Ecosystem                            │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Claude     │  │  Project     │  │    CI/CD     │     │
│  │   Code       │  │   Files      │  │    Tools     │     │
│  │              │  │              │  │              │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │             │
│         │ PM Tools         │ MCP             │             │
│         │                  │                 │             │
│         └──────────────────┴─────────────────┴────────────>│
│                             │                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                 LEE Orchestrator Core               │  │
│  │                                                             │
│  │  统一 API: create_workflow │ run_step │ get_state       │  │
│  │                                                             │
│  │  + 四个外圈能力（v3.1 新增）:                             │  │
│  │    🤖 Agent 系统 | 👁️ 可观测性 | ✅ 验证器 | 🔧 工程化  │  │
│  │                                                             │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

**本文档版本**: v3.1
**最后更新**: 2026-01-27
**配套文档**: LEE_Orchestrator_v3_Architecture.md
**状态**: ✅ v3.1 实现完成
