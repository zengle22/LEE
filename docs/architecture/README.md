# LEE Orchestrator v3.1 架构方案总结

> **状态**: ✅ v3.1 实现完成
> **日期**: 2026-01-27
> **目标**: 统一 flowcore 和 src/lee/orchestrator 为单一架构

---

## 📋 快速导航

### 核心文档

1. **[LEE_Orchestrator_v3_Architecture.md](LEE_Orchestrator_v3_Architecture.md)** ⭐
   - 完整的架构设计文档
   - 包含：总体架构、核心定位、数据模型、API 设计
   - **v3.1 更新**：添加四个外圈能力、模块清单、实现状态

2. **[LEE_Orchestrator_v3_Diagrams.md](LEE_Orchestrator_v3_Diagrams.md)**
   - ASCII 架构图和时序图
   - 包含：总体架构图、数据模型图、执行流程图
   - **v3.1 更新**：更新架构图、添加四个外圈能力层

3. **[LEE_Orchestrator_v3_Implementation_Plan.md](LEE_Orchestrator_v3_Implementation_Plan.md)** ⭐
   - 具体的实施计划
   - 包含：迁移步骤、时间表、验收标准
   - **v3.1 更新**：更新为"已完成"状态，记录所有完成的阶段

---

## 🎯 v3.1 核心亮点

### 一句话定位

> **LEE Orchestrator = 统一的工作流状态机 + 唯一的调度中心 + 四个外圈能力**

它**不**思考，只裁决「现在该干什么」。

### v3.1 新增：四个外圈能力

v3.1 在 Core 之外新增四个外圈能力层，这是相比 v3.0 的重要升级：

```
┌─────────────────────────────────────────────────────────────┐
│                    四个外圈能力（v3.1 新增）                     │
├─────────────────────────────────────────────────────────────┤
│  🤖 Agent 系统                                              │
│  - AgentLoader - Agent 规范加载                             │
│  - AgentResolver - Agent 引用解析                           │
│  - AgentContextBuilder - 上下文构建                         │
│  - AgentInjector - 依赖注入                                 │
├─────────────────────────────────────────────────────────────┤
│  👁️ 可观测性系统                                            │
│  - Run/Span/Artifact - 基于 execution-trace contract        │
│  - EventLog - 事件日志记录                                  │
│  - 数据脱敏 - 敏感信息保护                                  │
├─────────────────────────────────────────────────────────────┤
│  ✅ 验证器系统                                              │
│  - Validator - 可扩展验证器框架                             │
│  - SchemaValidator - Schema 验证                            │
│  - FileValidator - 文件验证                                  │
├─────────────────────────────────────────────────────────────┤
│  🔧 工作流工程                                              │
│  - WorkflowGenerator - 工作流生成                          │
│  - WorkflowParser - 工作流解析                             │
│  - TemplateResolver - 模板变量解析                         │
└─────────────────────────────────────────────────────────────┘
```

### 架构分层

```
客户端层（CLI / PM Agent / Gate）
           ↓
   Runtime Core（Orchestrator）
   ↓
   Executors（LLM / Shell / MCP）
   ↓
   Storage（SQLite）
```

### 统一的数据模型

**关键创新**：三个层级用**同一个模型、同一张表**表达

```python
WorkflowInstance:
    id: str
    level: "project" | "department" | "task"  # ← 区分层级
    parent_id: Optional[str]  # L1=null, L2=L1.id, L3=L2.id  # ← 表达关系
    template_id: str
    status: "pending" | "running" | "paused" | "completed" | "failed"
    data: Dict  # params + results
```

**优势**：
- 老版本（单层）= `level="project"`, `parent_id=null`
- 新版本（三层）= L1→L2→L3 嵌套
- **统一架构，不再分叉**

---

## 🏗️ 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    客户端层（Clients）                      │
│  CLI │ FastAPI │ PM Agent │ Gate Assistant │ UI           │
└─────────────────────────────┬───────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 LEE Orchestrator Core（核心）                │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ State       │  │ Template     │  │ Orchestrator    │   │
│  │ Machine     │  │ Manager      │  │（调度器）        │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
│  ┌─────────────┐  ┌──────────────┐                            │
│  │ EventBus    │  │ SQLiteStore  │                            │
│  └─────────────┘  └──────────────┘                            │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    四个外圈能力（v3.1）                       │
├─────────────────────────────────────────────────────────────┤
│  🤖 Agent 系统                                              │
│  - AgentLoader │ AgentResolver │ AgentContextBuilder │ Injector │  │
├─────────────────────────────────────────────────────────────┤
│  👁️ 可观测性系统                                            │
│  - Run │ Span │ Artifact │ EventLog │ Sanitize                   │  │
├─────────────────────────────────────────────────────────────┤
│  ✅ 验证器系统                                              │
│  - Validator │ SchemaValidator │ FileValidator                  │  │
├─────────────────────────────────────────────────────────────┤
│  🔧 工作流工程                                              │
│  - WorkflowGenerator │ WorkflowParser │ TemplateResolver        │  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        执行器层（Executors）                     │
│  LLM │ Shell │ MCP │ MetaGPT │ Custom                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      存储层（Storage）                         │
│  SQLite（workflow_instances, templates, executions, logs）   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 核心模块清单

### Runtime Core

- **`state_machine.py`** - 工作流状态机（v3 原有）
- **`template_manager.py`** - 模板管理器（v3 原有）
- **`event_bus.py`** - 事件总线（v1 迁移）✅
- **`project_config.py`** - 项目配置（v1 迁移）✅
- **`workflow_generator.py`** - 工作流生成器（v1 迁移）✅
- **`workflow_parser.py`** - 工作流解析器（v1 迁移）✅
- **`template_resolver.py`** - 模板变量解析器（v1 迁移）✅
- **`token_manager.py`** - 令牌管理（v1 迁移）✅

### Storage

- **`models.py`** - 数据模型（v3 原有）
- **`sqlite_store.py`** - SQLite 存储（v3 原有）
- **`event_log.py`** - 事件日志（v1 迁移）✅

### Execution

- **`orchestrator.py`** - 核心调度器（v3 原有）
- **`executors.py`** - 执行器工厂（v3 原有）
- **`llm_executor.py`** - LLM 执行器（v3 原有）
- **`shell_executor.py`** - Shell 执行器（v3 原有）
- **`metagpt_executor.py`** - MetaGPT 执行器（v3 原有）
- **`gate_api.py`** - Gate API（v3 原有）

### Agent 系统（v1 迁移）✅

- **`agent_loader.py`** - Agent 加载器
- **`agent_resolver.py`** - Agent 解析器
- **`agent_context.py`** - Agent 上下文构建器
- **`agent_injector.py`** - Agent 依赖注入

### 可观测性（v1 迁移）✅

- **`trace.py`** - Span 追踪系统
- **`event_log.py`** - 事件日志
- **`sanitization.py`** - 数据脱敏

### 验证器系统（v1 迁移）✅

- **`validators/base.py`**** - 验证器基类
- **`validators/schema_validator.py`** - Schema 验证
- **`validators/file_validator.py`** - 文件验证

### 高级特性（v1 迁移）✅

- **`retry.py`** - 重试机制（指数退避）
- **`token_manager.py`**** - 令牌管理

---

## 🚀 v3.1 实施状态

### 总体进度：100% ✅

| 阶段 | 任务 | 状态 | 完成日期 |
|------|------|------|----------|
| 0 | 准备和规划 | ✅ 完成 | 2026-01-27 |
| 1 | 核心功能迁移 (P0) | ✅ 完成 | 2026-01-27 |
| 2 | 可观测性迁移 (P1) | ✅ 完成 | 2026-01-27 |
| 3 | 验证系统迁移 (P1) | ✅ 完成 | 2026-01-27 |
| 4 | 工作流工程迁移 (P2) | ✅ 完成 | 2026-01-27 |
| 5 | 高级特性迁移 (P2) | ✅ 完成 | 2026-01-27 |
| 6 | 集成测试和验收 | ✅ 完成 | 2026-01-27 |

### 测试状态

| 测试文件 | 测试内容 | 状态 |
|----------|----------|------|
| `test_v3_integration_phase1.py` | EventBus, ProjectConfig, Agent 系统 | ✅ 通过 |
| `test_v3_integration_phase2.py` | Trace, EventLog, Sanitization | ✅ 通过 |
| `test_v3_integration_phase3.py` | Validator 系统 | ✅ 通过 |
| `test_v3_integration_phase4.py` | WorkflowGenerator, WorkflowParser | ✅ 通过 |
| `test_v3_integration_phase5.py` | Retry, TokenManager | ✅ 通过 |
| `test_v3_e2e_integration.py` | 端到端集成测试 | ✅ 通过 |

---

## ✅ 成功标准

### 技术指标

- [x] 所有测试通过（6 个 Phase 测试 + 1 个 E2E 测试）
- [x] 功能完整性：20+ 模块成功迁移
- [x] 架构统一：Core + 四个外圈能力

### 功能指标

- [x] 支持 L1/L2/L3 workflow
- [x] 支持 LLM/Shell/MetaGPT 执行器
- [x] Agent 系统完整迁移
- [x] 可观测性系统完整迁移
- [x] 验证器系统完整迁移
- [x] 高级特性（重试、令牌）完整迁移

### 验收标准

> **我可以在 CLI 里从 0 创建一个项目 workflow，spawn 出一个 QA 子流程，再 spawn 一个 bug_fix 任务，跑到 human gate 停下来。**

---

## 📚 参考文档

### 架构设计
- [LEE_Orchestrator_v3_Architecture.md](LEE_Orchestrator_v3_Architecture.md) - v3.1 架构设计
- [LEE_Orchestrator_v3_Diagrams.md](LEE_Orchestrator_v3_Diagrams.md) - v3.1 架构图

### 实施计划
- [LEE_Orchestrator_v3_Implementation_Plan.md](LEE_Orchestrator_v3_Implementation_Plan.md) - v3.1 实施计划（已完成）

### 版本对比
- [../../examples/version_comparison_report.md](../../examples/version_comparison_report.md)

### LLM/MetaGPT 集成
- [../../examples/llm_metagpt_final_report.md](../../examples/llm_metagpt_final_report.md)

### 迁移记录
- `flowcore.backup/` - v1 (flowcore) 备份目录

---

## 🎓 学习路径

### 1. 理解架构（1小时）

1. 阅读 `LEE_Orchestrator_v3_Architecture.md`
2. 查看 `LEE_Orchestrator_v3_Diagrams.md` 中的架构图
3. 理解"统一三层模型"的设计

### 2. 了解实施过程（30分钟）

1. 阅读 `LEE_Orchestrator_v3_Implementation_Plan.md`
2. 确认阶段划分和时间表
3. 识别迁移成果和风险对策

### 3. 查看测试结果（15分钟）

1. 查看各个 Phase 测试文件
2. 运行端到端集成测试
3. 验证所有功能正常

---

## 🤝 贡献指南

### 开发原则

1. **严格遵守权力边界**
   - Orchestrator 不直接调用 LLM
   - Executor 不访问 DB
   - 人类 > Orchestrator > Executor > Tool

2. **SQLite 是唯一状态权威**
   - 所有状态变更必须通过 Orchestrator
   - 不允许绕过 Orchestrator 直接修改状态

3. **统一数据模型**
   - L1/L2/L3 使用同一个 `WorkflowInstance` 模型
   - 通过 `level` 和 `parent_id` 区分

### 代码规范

- 遵循 PEP 8
- 使用类型注解
- 编写单元测试
- 更新文档

---

## 📞 联系方式

如有问题或建议，请：

1. 查阅架构文档
2. 创建 Issue
3. 发起 Pull Request

---

## 🎉 v3.1 成就

- **20+ 核心模块** 成功从 v1 迁移
- **4 个外圈能力** 成功集成到 v3
- **6 个 Phase 测试 + 1 个 E2E 测试** 全部通过
- **4 个架构文档** 全部更新到 v3.1

---

**文档版本**: v3.1
**最后更新**: 2026-01-27
**维护者**: LEE Team
**状态**: ✅ v3.1 实现完成
