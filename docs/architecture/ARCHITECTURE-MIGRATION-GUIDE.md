---
title: 架构迁移指南 - 从 v1.6 到 v2.0
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# 架构迁移指南 - 从 v1.6 到 v2.0

## 概述

本文档对比新旧架构的主要差异，并提供迁移建议。

---

## 架构对比

### 旧架构（v1.6）

```
┌─────────────────────────────┐
│    Claude Code / AI 工具     │
│  (读取上下文 + 执行 + 写文件)  │
└──────────┬──────────────────┘
           │ Agent Context
           ▼
┌─────────────────────────────┐
│       Orchestrator          │
│  - 状态管理                   │
│  - 注入上下文                 │
│  - 等待 AI 完成               │
│  - 验证产物                   │
└─────────────────────────────┘
```

**特点**：
- Orchestrator **依赖外部 AI 工具**执行工作
- AI 工具直接修改项目文件
- Orchestrator 只负责状态管理和验证

---

### 新架构（v2.0）

```
┌─────────────────────────────┐
│       PM Agent (AI)         │
│  - 只做决策                   │
│  - 不执行工作                 │
└──────────┬──────────────────┘
           │ action
           ▼
┌─────────────────────────────┐
│       Orchestrator          │
│  - 流程控制                   │
│  - 状态管理                   │
│  - 调度 Executor             │
└──────────┬──────────────────┘
           │ StepExecutionRequest
           ▼
┌─────────────────────────────┐
│      Engine / Executor      │
│  - LLMExecutor               │
│  - Legacy ExecutorExecutor           │
│  - ShellSkillExecutor        │
└─────────────────────────────┘
```

**特点**：
- Orchestrator **通过统一的 Engine 接口**执行工作
- PM Agent（AI）只负责决策，不执行
- 完全自动化，不依赖外部 AI 工具

---

## 关键差异

### 1. 执行权归属

| 方面 | 旧架构 | 新架构 |
|------|--------|--------|
| 谁执行代码？ | 外部 AI 工具（Claude Code） | Executor (LLMExecutor) |
| 谁做决策？ | AI 工具自主决策 | PM Agent 决策 |
| Orchestrator 角色 | 协调者 | 控制器 + 执行调度器 |

**影响**：
- 旧架构需要人工干预（在 Claude Code 中操作）
- 新架构可以完全自动化运行

---

### 2. Orchestrator 职责

| 职责 | 旧架构 | 新架构 |
|------|--------|--------|
| 状态管理 | ✅ | ✅ |
| 上下文注入 | ✅ | ❌ (移除) |
| 调用 LLM API | ❌ | ✅ (通过 LLMExecutor) |
| 调度执行 | ⚠️ (部分) | ✅ (完整) |

**变化**：
- 新增：通过 EngineFactory 创建 Executor
- 移除：Agent Context 注入功能（已不需要）

---

### 3. Agent 定义

| 方面 | 旧架构 | 新架构 |
|------|--------|--------|
| Agent 是什么？ | 外部 AI 工具 | Executor 的一种类型 |
| Agent 规范用途 | 提供给 AI 工具的上下文 | Executor 的配置 |
| 执行方式 | AI 工具直接执行 | LLMExecutor 调用 LLM API |

**影响**：
- Agent spec 格式保持兼容
- 但语义从"AI 工具说明"变为"Executor 配置"

---

### 4. Skill 定义

| 方面 | 旧架构 | 新架构 |
|------|--------|--------|
| Skill 是什么？ | 预留功能 | Shell/MCP Executor |
| 用途 | 未定义 | 执行确定性操作（测试、部署等） |

**影响**：
- Skill 从"预留"变为"核心功能"
- 需要实现 ShellSkillExecutor 和 MCPSkillExecutor

---

## 文档更新建议

### 需要更新的文档

#### 1. `docs/Orchestrator-Architecture.md`

**需要更新**：
- 整体架构图（添加 PM Agent 和 Engine 层）
- Orchestrator 职责描述（移除"注入上下文"，添加"调度 Executor"）
- Agent 上下文系统（标记为"已废弃"，或移至单独章节）

**建议操作**：
- 保留现有文档作为"Orchestrator Core"的参考
- 在文档开头添加说明：指向新的 `docs/architecture.md`
- 创建"从 v1.6 迁移到 v2.0"章节

---

#### 2. `docs/Orchestrator-PRD.md`

**需要更新**：
- 产品定位（从"依赖外部 AI 工具"到"统一执行接口"）
- 目标用户（添加"需要完全自动化的团队"）
- 功能需求（添加 Engine/Executor 相关）

**建议操作**：
- 更新"产品概述"章节
- 在"背景与问题"中添加"依赖外部工具的不确定性"
- 更新功能需求列表，添加 F16: 统一 Engine 接口

---

#### 3. `docs/Orchestrator-Complete-Guide.md`

**需要更新**：
- 使用流程（从"需要人工操作"到"可完全自动化"）
- 命令参考（添加 `run-engine` 命令）
- 示例（更新为使用新的 Engine 接口）

**建议操作**：
- 在文档开头添加"新旧版本选择"指南
- 保留旧的"基于 Claude Code"的使用方式
- 添加新的"基于 Engine"的使用方式

---

#### 4. `docs/Orchestrator-Engine-Integration-Guide.md`

**状态**：✅ 已是新架构，无需更新

**说明**：这个文档已经反映了新架构的设计

---

## 代码变更建议

### 需要修改的模块

#### 1. `flowcore/orchestrator/agent_context.py`

**状态**：⚠️ 可能废弃

**建议**：
- 保留用于向后兼容
- 在新架构中，Agent context 由 Executor 内部处理

---

#### 2. `flowcore/orchestrator/agent_injector.py`

**状态**：⚠️ 可能废弃

**建议**：
- 保留用于向后兼容
- 新架构不需要注入器

---

#### 3. `flowcore/engines/`

**状态**：✅ 新增

**需要实现**：
- `flowcore/engines/protocol.py` - 统一执行协议
- `flowcore/engines/base.py` - EngineRegistry
- `flowcore/engines/llm/executor.py` - LLMExecutor
- `flowcore/engines/shell/executor.py` - ShellSkillExecutor
- `flowcore/engines/mcp/executor.py` - MCPSkillExecutor

---

## 迁移路径

### 选项 1: 并存（推荐）

保持新旧架构并存，让用户选择：

```yaml
# workflow.yaml - 旧方式
steps:
  - id: step1
    run: agent:developer  # 使用 Claude Code
    # Orchestrator 注入上下文，等待 Claude Code 完成

# workflow.yaml - 新方式
steps:
  - id: step1
    kind: agent
    agent: developer  # 使用 LLMExecutor
    # Orchestrator 直接调用 LLMExecutor 执行
```

**优点**：
- 向后兼容
- 用户可以逐步迁移

---

### 选项 2: 完全替换

移除旧的"依赖外部 AI 工具"的代码：

**优点**：
- 代码更简洁
- 架构更一致

**缺点**：
- 破坏向后兼容性
- 需要更新所有文档和示例

---

## 总结

| 方面 | 建议 |
|------|------|
| 文档 | 保留旧文档，添加"已废弃"标记，指向新文档 |
| 代码 | 新旧并存，逐步迁移 |
| 新项目 | 推荐使用新架构 |
| 旧项目 | 可以继续使用旧架构 |

---

**文档版本**: v1.0
**最后更新**: 2025-01-22
