---
title: LEE Orchestrator 版本对比：新版本 vs flowcore
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# LEE Orchestrator 版本对比：新版本 vs flowcore

> **日期**: 2026-01-27
> **新版本位置**: `src/lee/orchestrator/`
> **旧版本位置**: `flowcore/`

---

## 执行摘要

### 核心区别

| 维度 | flowcore (旧版本) | src/lee/orchestrator (新版本) |
|------|-------------------|-------------------------------|
| **架构定位** | 通用 AI 工作流编排系统 | 极简三层工作流编排系统 |
| **设计理念** | 功能完整、高度可配置 | 核心功能、简单易用 |
| **复杂度** | 高（20+ 核心模块） | 低（6 个核心模块） |
| **目标用户** | 企业级复杂场景 | 快速开发、学习项目 |
| **依赖关系** | 重（大量外部依赖） | 轻（最小依赖） |
| **状态存储** | 文件系统（.workflow/state.yaml） | SQLite（单数据库） |
| **工作流层级** | 平滑（任意嵌套 stages） | 固定三层（L1/L2/L3） |

---

## 功能对比矩阵

### ✅ 已实现的功能

| 功能模块 | flowcore | 新版本 | 实现状态 |
|---------|----------|--------|---------|
| **工作流创建** | ✅ | ✅ | 完全实现 |
| **工作流执行** | ✅ | ✅ | 完全实现 |
| **状态管理** | ✅ | ✅ | 完全实现 |
| **步骤依赖解析** | ✅ | ✅ | 完全实现 |
| **模板系统** | ✅ | ✅ | 完全实现 |
| **LLM Executor** | ✅ | ✅ | 完全实现 |
| **Shell Executor** | ✅ | ✅ | 完全实现 |
| **MetaGPT Executor** | ✅ | ✅ | 框架就绪 |

### ⚠️ 部分实现/简化实现

| 功能模块 | flowcore | 新版本 | 差异说明 |
|---------|----------|--------|---------|
| **工作流层级** | 任意嵌套 stages | 固定三层 L1/L2/L3 | 新版本简化为固定层级 |
| **状态机** | 复杂状态机（10+ 状态） | 简化状态机（5 状态） | 新版本移除了循环、外部等待等复杂状态 |
| **状态存储** | 文件系统（state.yaml） | SQLite 数据库 | 新版本使用数据库，更可靠 |
| **目录结构** | 强制标准目录结构 | 无强制要求 | 新版本不强制目录结构 |

### ❌ 未实现的功能

| 功能模块 | flowcore | 新版本 | 重要性 |
|---------|----------|--------|-------|
| **门禁机制** | ✅ 人工/自动门禁 | ❌ 未实现 | 高 |
| **循环执行** | ✅ Bug 修复循环 | ❌ 未实现 | 中 |
| **Loop Back** | ✅ 回退到之前步骤 | ❌ 未实现 | 中 |
| **外部事件等待** | ✅ 等待外部修复 | ❌ 未实现 | 中 |
| **Token 管理** | ✅ 执行令牌系统 | ❌ 未实现 | 低 |
| **事件总线** | ✅ 发布-订阅 | ❌ 简化版本 | 低 |
| **Agent 规范系统** | ✅ 完整 Agent Spec | ❌ 未实现 | 高 |
| **项目配置管理** | ✅ 仓库注册表、路径别名 | ❌ 未实现 | 中 |
| **目录结构标准化** | ✅ 强制标准结构 | ❌ 未实现 | 低 |
| **MCP Executor** | ✅ MCP 协议支持 | ❌ 未实现 | 低 |
| **CLI 命令** | ✅ 完整 CLI | ❌ 未实现 | 中 |
| **API 层** | ✅ PM Agent API | ❌ 未实现 | 高 |

---

## 架构对比

### flowcore 架构

```
┌─────────────────────────────────────────────────────┐
│                   API Layer                         │
│         (api.py - PM Agent & Gate APIs)             │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│              Orchestrator Layer                     │
│  - State Machine (复杂状态机)                       │
│  - Workflow Parser (嵌套 stages)                   │
│  - Agent Loader (Agent 规范系统)                   │
│  - Event Bus (事件驱动)                            │
│  - PM Agent Tools                                   │
│  - Project Config (目录结构管理)                   │
│  - Gate Management (门禁系统)                      │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│               Engine Layer                          │
│  - Engine Registry                                  │
│  - Abstract Executor                                │
│  - Execution Protocol                               │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│            Engine Implementations                   │
│  LLM │ MetaGPT │ Shell │ MCP                        │
└─────────────────────────────────────────────────────┘
```

### 新版本架构

```
┌─────────────────────────────────────────────────────┐
│               Application Layer                      │
│         (Runners: Project/Department/Task)           │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│              Orchestrator Layer                     │
│  - SimpleStateMachine (简化状态机)                  │
│  - TemplateManager (模板管理)                       │
│  - WorkflowExecutor (工作流执行器)                  │
│  - TemplateEngine (模板引擎)                        │
│  - MemoryEventBus (内存事件总线)                   │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│            Storage Layer                            │
│  - SQLiteStore (SQLite 存储)                       │
│  - Models (数据模型)                                │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│            Executor Layer                           │
│  - LLM Executor                                     │
│  - Shell Executor                                   │
│  - MetaGPT Executor                                 │
└─────────────────────────────────────────────────────┘
```

---

## 核心模块对比

### 1. 状态机 (State Machine)

#### flowcore - StateMachine

**复杂度**: 高

**状态**:
- RunState: created, running, paused, completed, failed
- StepState: pending, blocked, ready, in_progress, validating, completed, failed, cancelled
- GateStatus: pending, approved, rejected

**功能**:
- ✅ 门禁管理（trigger_gate, approve_gate, reject_gate）
- ✅ 循环执行（start_loop, complete_loop）
- ✅ 外部等待（start_external_wait）
- ✅ 回退（loop_back）
- ✅ 依赖关系验证
- ✅ 输出验证

**代码量**: ~800 行

#### 新版本 - SimpleStateMachine

**复杂度**: 低

**状态**:
- WorkflowStatus: pending, running, paused, completed, failed
- TaskExecutionStatus: pending, running, completed, failed

**功能**:
- ✅ 基本状态转换
- ❌ 无门禁机制
- ❌ 无循环执行
- ❌ 无外部等待
- ❌ 无回退

**代码量**: ~100 行

**差异**: 新版本是 flowcore 状态机的简化子集，去除了复杂的状态管理功能。

---

### 2. 工作流解析 (Workflow Parser)

#### flowcore - WorkflowParser

**功能**:
- ✅ 支持嵌套 stages 格式
- ✅ 支持扁平 steps 格式（phase-openspec-flow）
- ✅ 依赖关系解析
- ✅ 输入/输出契约提取
- ✅ 验证器配置
- ✅ 门禁配置
- ✅ 路径别名解析
- ✅ Agent 规范引用

**代码量**: ~600 行

#### 新版本 - TemplateManager

**功能**:
- ✅ 加载 YAML 模板
- ✅ 获取步骤列表（get_steps）
- ✅ 获取部门列表（get_departments）
- ✅ 获取完成条件（get_completion_criteria）
- ❌ 无嵌套 stages 支持
- ❌ 无契约系统
- ❌ 无门禁配置
- ❌ 无路径别名

**代码量**: ~90 行

**差异**: 新版本只支持固定三层结构，模板格式更简单。

---

### 3. Agent 系统

#### flowcore - Agent Loader & Spec

**AgentSpec 结构**:
```yaml
id: agent-id
name: "Agent Name"
version: "1.0.0"
description: "Agent description"

# 角色定义
persona:
  role: "Role"
  style: "Style"
  tone: "Tone"

# 提示工程
prompting:
  system: "System message"
  instructions: "Instructions"

# 策略
policy:
  decision_rules: [...]
  quality_bar: "..."

# 职责边界
responsibility:
  in_scope: [...]
  out_of_scope: [...]

# 契约
contracts:
  input_schema: {...}
  output_schema: {...}

# 技能引用
skills: [...]
```

**功能**:
- ✅ 完整的 Agent 规范系统
- ✅ Agent 加载和解析
- ✅ Agent 上下文注入
- ✅ Agent 依赖解析
- ✅ 版本管理

**代码量**: ~1000+ 行（agent_loader.py + agent_resolver.py + agent_context.py + agent_injector.py）

#### 新版本 - 无 Agent 系统

**功能**:
- ❌ 无 Agent 规范系统
- ❌ 无 Agent 加载器
- ❌ 无 Agent 上下文管理

**差异**: 新版本不包含 Agent 系统，直接使用 Executor。

---

### 4. 项目配置 (Project Config)

#### flowcore - ProjectConfig

**功能**:
- ✅ 仓库注册表（git/local/remote）
- ✅ 路径别名（@openspec, @frontend, ${repositories.xxx}）
- ✅ 变量展开（${project.id}, ${project.name}）
- ✅ 目录结构标准化
- ✅ 强制路径验证
- ✅ 防止目录飘逸

**标准目录结构**:
```
project-root/
├── .project/
│   ├── dirs.yaml
│   └── schema/
├── .workflow/
│   ├── state.yaml
│   ├── workspace/
│   ├── gates/
│   ├── events/
│   └── cache/
└── {project-name}/
    ├── contracts/
    ├── docs/
    ├── specs/
    ├── src/
    ├── outputs/
    └── tests/
```

**代码量**: ~500 行

#### 新版本 - 无项目配置系统

**功能**:
- ❌ 无仓库注册表
- ❌ 无路径别名
- ❌ 无目录结构标准化

**差异**: 新版本不强制项目结构，更灵活但缺少标准化。

---

### 5. 门禁系统 (Gate Management)

#### flowcore - Gate System

**功能**:
- ✅ 人工门禁（需要人工批准）
- ✅ 自动门禁（基于规则自动审批）
- ✅ 超时处理
- ✅ 升级策略
- ✅ 门禁历史记录

**API**:
- `api_gate_list_pending()` - 列出待审批门禁
- `api_gate_show()` - 查看门禁详情
- `api_gate_decide()` - 提交决策

**代码量**: ~400 行（集成在 state_machine.py 中）

#### 新版本 - 无门禁系统

**功能**:
- ❌ 无门禁机制

**差异**: 新版本不支持人工介入节点。

---

### 6. 执行引擎 (Engines)

#### flowcore - Engines

**引擎类型**:
- LLM Engine ✅
- MetaGPT Engine ✅
- Shell Engine ✅
- MCP Engine ✅

**统一协议**:
```python
class StepExecutionRequest:
    step_id: str
    agent_spec: Dict
    project_dir: str
    inputs: List[ArtifactReference]
    contracts: Dict[str, ContractReference]

class StepExecutionResult:
    status: str  # completed/failed
    outputs: List[ArtifactReference]
    messages: List[Dict]
    error: Optional[str]
```

**代码量**: ~2000 行（4 个引擎）

#### 新版本 - Executors

**执行器类型**:
- LLM Executor ✅
- MetaGPT Executor ✅
- Shell Executor ✅
- MCP Executor ❌

**统一接口**:
```python
async def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "completed",
        "output": {...},
        "error": None
    }
```

**代码量**: ~600 行（3 个执行器）

**差异**: 新版本接口更简单，缺少 MCP 支持。

---

## 使用场景对比

### flowcore 适用场景

✅ **适合**:
- 企业级复杂工作流
- 需要人工介入的审批流程
- 多阶段嵌套工作流
- 需要循环执行和回退
- 需要标准化项目结构
- 需要完整的 Agent 规范系统

❌ **不适合**:
- 快速原型开发
- 学习项目
- 简单自动化任务

### 新版本适用场景

✅ **适合**:
- 快速原型开发
- 学习工作流编排概念
- 简单的三层项目管理
- 不需要人工介入的自动化流程
- 轻量级部署

❌ **不适合**:
- 复杂的企业级工作流
- 需要人工审批的流程
- 需要循环执行的场景
- 需要 Agent 规范系统

---

## 迁移指南

### 从 flowcore 迁移到新版本

#### 1. 状态存储

**flowcore**:
```python
# 文件系统
.workflow/state.yaml
```

**新版本**:
```python
# SQLite
db = SQLiteStore("workflow.db")
await db.create_workflow(workflow)
```

#### 2. 工作流定义

**flowcore**:
```yaml
# 嵌套 stages
stages:
  - stage: design
    steps:
      - step: write_spec
        engine: llm
  - stage: development
    stages:
      - stage: backend
        steps: [...]
      - stage: frontend
        steps: [...]
```

**新版本**:
```yaml
# 固定三层
name: project_main
departments:
  - name: dev
    template: dept_development
    tasks:
      - name: backend
        template: task_backend
```

#### 3. 执行器调用

**flowcore**:
```python
from flowcore.engines.base import EngineRegistry

executor = EngineRegistry.create("llm")
result = await executor.execute(request)
```

**新版本**:
```python
from lee.orchestrator.execution.executors import ExecutorFactory

executor = ExecutorFactory.create("llm", profile="zhipu")
result = await executor.execute(input_data)
```

---

## 总结

### 功能完成度

| 类别 | flowcore 功能数 | 新版本实现数 | 完成度 |
|------|---------------|-------------|--------|
| **核心功能** | 8 | 8 | 100% |
| **高级功能** | 12 | 0 | 0% |
| **辅助功能** | 8 | 2 | 25% |
| **总体** | 28 | 10 | 36% |

### 核心功能 ✅

以下核心功能已完全实现：
1. ✅ 工作流创建和管理
2. ✅ 状态管理和转换
3. ✅ 步骤依赖解析
4. ✅ 模板系统
5. ✅ 执行器集成（LLM/Shell/MetaGPT）
6. ✅ SQLite 状态存储
7. ✅ 事件发布（简化版）
8. ✅ Runners 封装

### 高级功能 ❌

以下高级功能未实现：
1. ❌ 门禁机制
2. ❌ 循环执行
3. ❌ Loop Back
4. ❌ 外部事件等待
5. ❌ Agent 规范系统
6. ❌ 项目配置管理
7. ❌ 目录结构标准化
8. ❌ MCP Executor
9. ❌ CLI 命令
10. ❌ PM Agent API
11. ❌ Token 管理
12. ❌ 复杂事件总线

### 设计权衡

**新版本的简化是有意为之**：

1. **固定三层结构** vs 任意嵌套
   - 优势：简单、清晰、易理解
   - 劣势：不够灵活

2. **SQLite 存储** vs 文件系统
   - 优势：可靠、可查询、事务支持
   - 劣势：需要数据库依赖

3. **简化状态机** vs 复杂状态机
   - 优势：易实现、易维护
   - 劣势：不支持复杂场景

4. **无 Agent 系统** vs 完整 Agent 规范
   - 优势：直接使用 Executor，更灵活
   - 劣势：缺少标准化和约束

### 建议

**如果你需要**:
- 企业级工作流编排 → 使用 flowcore
- 人工审批流程 → 使用 flowcore
- 复杂的状态管理 → 使用 flowcore
- 完整的 Agent 系统 → 使用 flowcore

**如果你需要**:
- 快速原型开发 → 使用新版本
- 学习工作流编排 → 使用新版本
- 简单的自动化流程 → 使用新版本
- 轻量级部署 → 使用新版本

---

**文档版本**: v1.0
**对比日期**: 2026-01-27
**新版本**: src/lee/orchestrator/
**旧版本**: flowcore/
