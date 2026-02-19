---
title: LEE Orchestrator v3.1 实施计划
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# LEE Orchestrator v3.1 实施计划

> **目标**: 从当前混乱状态（老版本 + 新版本分叉）收敛到统一的 v3.1 架构
> **周期**: 已完成 ✅
> **状态**: ✅ v3.1 实现完成

---

## 一、v3.1 实施状态总结

### 1.1 已完成状态

**v3.1 已成功完成从 v1 (flowcore) 到 v3.1 的增量演进**

- ✅ **Phase 0**: 准备和规划
- ✅ **Phase 1**: 核心功能迁移 (P0)
- ✅ **Phase 2**: 可观测性迁移 (P1)
- ✅ **Phase 3**: 验证系统迁移 (P1)
- ✅ **Phase 4**: 工作流工程迁移 (P2)
- ✅ **Phase 5**: 高级特性迁移 (P2)
- ✅ **Phase 6**: 集成测试和验收

### 1.2 迁移成果

从 `flowcore.backup/` 成功迁移 20+ 核心模块：

**核心模块（Core）**:
- ✅ event_bus.py - 事件总线
- ✅ project_config.py - 项目配置
- ✅ workflow_generator.py - 工作流生成器
- ✅ workflow_parser.py - 工作流解析器
- ✅ template_resolver.py - 模板变量解析器
- ✅ token_manager.py - 令牌管理

**Agent 系统**:
- ✅ agent_loader.py - Agent 加载器
- ✅ agent_resolver.py - Agent 解析器
- ✅ agent_context.py - Agent 上下文构建器
- ✅ agent_injector.py - Agent 依赖注入

**可观测性系统**:
- ✅ trace.py - Span 追踪系统
- ✅ event_log.py - 事件日志
- ✅ sanitization.py - 数据脱敏

**验证器系统**:
- ✅ validators/base.py - 验证器基类
- ✅ validators/schema_validator.py
- ✅ validators/file_validator.py

**高级特性**:
- ✅ retry.py - 重试机制（指数退避）
- ✅ token_manager.py - 令牌管理

---

## 二、迁移策略（已验证）

### 2.1 核心原则

> **"统一收敛，增量演进"** ✅ 已验证

1. **统一数据模型** ✅
   - 保留 v3 的单表设计
   - 兼容 v1 的复杂功能

2. **统一 Executor** ✅
   - 保留 v3 的 Executor 实现
   - v1 迁移后不再需要

3. **统一状态机** ✅
   - 基于 v3 的简化状态机
   - 增强了 v1 的高级功能

4. **统一 API** ✅
   - v3 的 Orchestrator API
   - v1 功能已集成到外圈能力

### 2.2 兼容性保证

**v1 (flowcore) 兼容**:
- ✅ 单层 workflow → L1 Project
- ✅ 所有功能已迁移到 v3.1

**v3.0 兼容**:
- ✅ 三层结构保留
- ✅ SQLite 存储保留
- ✅ 增强了 Agent、可观测性、验证器等能力

---

## 三、实施步骤（已完成）

### 阶段 1: 数据模型统一 ✅

**目标**: 统一两个版本的数据模型

#### 已完成任务

- [x] **1.1 保留 v3 数据模型**
  - [x] 保留 v3 的 `WorkflowInstance`
  - [x] 统一状态枚举（`WorkflowStatus`, `TaskExecutionStatus`）

- [x] **1.2 统一 sqlite_store.py**
  - [x] 使用 v3 的 `SQLiteStore`
  - [x] 统一 CRUD 接口

**产出**:
- ✅ `src/lee/orchestrator/storage/models.py`（保留 v3）
- ✅ `src/lee/orchestrator/storage/sqlite_store.py`（保留 v3）

---

### 阶段 2: Executor 统一 ✅

**目标**: 统一两个版本的 Executor

#### 已完成任务

- [x] **2.1 保留 v3 版本 Executors**
  - [x] `llm_executor.py`（已集成）
  - [x] `shell_executor.py`（已实现）
  - [x] `metagpt_executor.py`（已实现）

- [x] **2.2 v1 Executors 不再需要**
  - [x] 停用 `flowcore/engines/` 目录（备份到 flowcore.backup）
  - [x] v3 Executor 功能已完整

- [x] **2.3 统一 ExecutorFactory**
  - [x] 保留 v3 版本的 `executors.py`
  - [x] 所有 Executor 使用统一接口

**产出**:
- ✅ `src/lee/orchestrator/execution/llm_executor.py`（保留 v3）
- ✅ `src/lee/orchestrator/execution/shell_executor.py`（保留 v3）
- ✅ `src/lee/orchestrator/execution/metagpt_executor.py`（保留 v3）
- ✅ `src/lee/orchestrator/execution/executors.py`（保留 v3）

---

### 阶段 3: v1 功能迁移到外圈能力 ✅

**目标**: 将 v1 的复杂功能迁移为 v3 的外圈能力

#### 已完成任务

- [x] **3.1 Agent 系统迁移**
  - [x] `agent_loader.py` - Agent 加载器
  - [x] `agent_resolver.py` - Agent 解析器
  - [x] `agent_context.py` - Agent 上下文构建器
  - [x] `agent_injector.py` - Agent 依赖注入

- [x] **3.2 可观测性系统迁移**
  - [x] `trace.py` - Span 追踪系统
  - [x] `event_log.py` - 事件日志
  - [x] `sanitization.py` - 数据脱敏

- [x] **3.3 验证器系统迁移**
  - [x] `validators/base.py` - 验证器基类
  - [x] `validators/schema_validator.py`
  - [x] `validators/file_validator.py`

**产出**:
- ✅ `src/lee/orchestrator/execution/agent_*.py`（Agent 系统）
- ✅ `src/lee/orchestrator/execution/trace.py`（追踪系统）
- ✅ `src/lee/orchestrator/storage/event_log.py`（事件日志）
- ✅ `src/lee/orchestrator/utils/sanitization.py`（数据脱敏）
- ✅ `src/lee/orchestrator/execution/validators/`（验证器系统）

---

### 阶段 4: 高级特性迁移 ✅

**目标**: 迁移 v1 的高级特性

#### 已完成任务

- [x] **4.1 工作流工程迁移**
  - [x] `workflow_generator.py` - 工作流生成器
  - [x] `workflow_parser.py` - 工作流解析器
  - [x] `template_resolver.py` - 模板变量解析器

- [x] **4.2 高级特性迁移**
  - [x] `retry.py` - 重试机制（指数退避）
  - [x] `token_manager.py` - 令牌管理

**产出**:
- ✅ `src/lee/orchestrator/core/workflow_generator.py`
- ✅ `src/lee/orchestrator/core/workflow_parser.py`
- ✅ `src/lee/orchestrator/core/template_resolver.py`
- ✅ `src/lee/orchestrator/execution/retry.py`
- ✅ `src/lee/orchestrator/core/token_manager.py`

---

### 阶段 5: 核心功能增强 ✅

**目标**: 增强核心模块功能

#### 已完成任务

- [x] **5.1 事件系统增强**
  - [x] 从 v1 迁移 `event_bus.py`
  - [x] 集成到 `core/` 模块

- [x] **5.2 项目配置增强**
  - [x] 从 v1 迁移 `project_config.py`
  - [x] 路径别名解析功能

**产出**:
- ✅ `src/lee/orchestrator/core/event_bus.py`
- ✅ `src/lee/orchestrator/core/project_config.py`

---

### 阶段 6: 集成测试和验收 ✅

**目标**: 验证所有功能正常

#### 已完成任务

- [x] **6.1 Phase 测试**
  - [x] Phase 1: EventBus, ProjectConfig, Agent 系统
  - [x] Phase 2: Trace, EventLog, Sanitization
  - [x] Phase 3: Validator 系统
  - [x] Phase 4: WorkflowGenerator, WorkflowParser
  - [x] Phase 5: Retry, TokenManager

- [x] **6.2 端到端测试**
  - [x] 工作流执行测试
  - [x] 事件系统测试
  - [x] 追踪系统测试
  - [x] Agent 系统测试
  - [x] 验证器系统测试
  - [x] 重试机制测试
  - [x] 令牌管理测试
  - [x] 项目配置测试
  - [x] 数据完整性测试

**产出**:
- ✅ `tests/test_v3_integration_phase1.py`
- ✅ `tests/test_v3_integration_phase2.py`
- ✅ `tests/test_v3_integration_phase3.py`
- ✅ `tests/test_v3_integration_phase4.py`
- ✅ `tests/test_v3_integration_phase5.py`
- ✅ `tests/test_v3_e2e_integration.py`

---

## 四、里程碑（已完成）

### Milestone 1: 准备和规划 ✅

**验收标准**:
- [x] 创建 `flowcore.backup/` 备份目录
- [x] 规划目录结构
- [x] 制定 7 个阶段计划

### Milestone 2: 核心功能迁移 (P0) ✅

**验收标准**:
- [x] EventBus 迁移完成
- [x] ProjectConfig 迁移完成
- [x] Agent 系统基础迁移完成

### Milestone 3: 可观测性迁移 (P1) ✅

**验收标准**:
- [x] Span 追踪系统迁移完成
- [x] EventLog 迁移完成
- [x] 数据脱敏功能完成

### Milestone 4: 验证系统迁移 (P1) ✅

**验收标准**:
- [x] 验证器基类迁移完成
- [x] SchemaValidator 迁移完成
- [x] FileValidator 迁移完成

### Milestone 5: 工作流工程迁移 (P2) ✅

**验收标准**:
- [x] WorkflowGenerator 迁移完成
- [x] WorkflowParser 迁移完成
- [x] TemplateResolver 迁移完成

### Milestone 6: 高级特性迁移 (P2) ✅

**验收标准**:
- [x] 重试机制迁移完成
- [x] 令牌管理迁移完成

### Milestone 7: 集成测试和验收 ✅

**验收标准**:
- [x] 所有 Phase 测试通过
- [x] 端到端集成测试通过
- [x] 所有功能正常工作

---

## 五、风险与对策（已处理）

### 风险 1: 模块导入错误 ✅ 已解决

**问题**: v1 模块导入路径错误
**解决**:
- 统一使用 `src/lee/orchestrator/` 作为基础路径
- 更新所有 `__init__.py` 文件
- 修复循环导入问题

### 风险 2: 数据类型不兼容 ✅ 已解决

**问题**: v1 和 v3 数据类型定义不一致
**解决**:
- 使用 v3 的简化数据模型
- 通过外圈能力补充 v1 功能

### 风险 3: 测试覆盖不完整 ✅ 已解决

**问题**: 缺少端到端测试
**解决**:
- 创建 6 个 Phase 集成测试
- 创建 1 个端到端集成测试
- 所有测试通过

---

## 六、成功标准（已达成）

### 6.1 技术指标 ✅

- [x] 所有测试通过（6 个 Phase 测试 + 1 个 E2E 测试）
- [x] 功能完整性：20+ 模块成功迁移
- [x] 架构统一：Core + 四个外圈能力

### 6.2 功能指标 ✅

- [x] 支持 L1/L2/L3 workflow
- [x] 支持 LLM/Shell/MetaGPT 执行器
- [x] Agent 系统完整迁移
- [x] 可观测性系统完整迁移
- [x] 验证器系统完整迁移
- [x] 高级特性（重试、令牌）完整迁移

### 6.3 用户体验 ✅

- [x] 文档完整更新
- [x] 示例测试充足
- [x] 端到端测试通过

---

## 七、实施总结

### 7.1 完成情况

| 阶段 | 任务 | 状态 | 完成日期 |
|------|------|------|----------|
| 0 | 准备和规划 | ✅ 完成 | 2026-01-27 |
| 1 | 核心功能迁移 (P0) | ✅ 完成 | 2026-01-27 |
| 2 | 可观测性迁移 (P1) | ✅ 完成 | 2026-01-27 |
| 3 | 验证系统迁移 (P1) | ✅ 完成 | 2026-01-27 |
| 4 | 工作流工程迁移 (P2) | ✅ 完成 | 2026-01-27 |
| 5 | 高级特性迁移 (P2) | ✅ 完成 | 2026-01-27 |
| 6 | 集成测试和验收 | ✅ 完成 | 2026-01-27 |

### 7.2 迁移统计

**模块数量**: 20+ 核心模块
**代码行数**: ~5000+ 行代码迁移
**测试覆盖**: 6 个 Phase 测试 + 1 个 E2E 测试
**文档更新**: 4 个架构文档全部更新

### 7.3 关键成果

1. **架构统一**: "LEE Orchestrator Core + 四个外圈能力" 成功落地
2. **功能完整**: v1 的所有核心功能成功迁移到 v3.1
3. **测试通过**: 所有集成测试通过，端到端验证成功
4. **文档更新**: 架构文档全部更新到 v3.1

---

## 八、后续规划

### 8.1 下一步工作

虽然 v3.1 集成已完成，但仍有一些改进空间：

1. **性能优化**
   - Executor 并行执行
   - 数据库查询优化

2. **功能增强**
   - 循环执行（Loop Back）
   - 外部等待（External Wait）
   - 更多验证器类型

3. **工具完善**
   - CLI 命令增强
   - PM Agent Tools 集成

4. **文档完善**
   - 用户手册
   - 开发者指南
   - API 文档

### 8.2 版本演进

```
v1.0 (flowcore)          →  v3.0 (简化版)
    ↓ 迁移                        ↓ 增强
v3.1 (统一版) ✅          ← 当前版本
    ↓
v4.0 (未来版本)
```

---

**文档版本**: v3.1
**最后更新**: 2026-01-27
**配套文档**: LEE_Orchestrator_v3_Architecture.md
**状态**: ✅ v3.1 实现完成
