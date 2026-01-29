# LEE Orchestrator 三层流程架构开发计划

> **版本**: v1.1 (Architecture Review Revision)
> **状态**: Draft - Revision
> **创建日期**: 2026-01-25
> **修订日期**: 2026-01-26
> **目标版本**: LEE Orchestrator v3.0
> **预计周期**: 14-16 周 (含 2 周预 Sprint 0 改进 + 6-7 个 Sprint)
> **预计工作量**: 70-90 人天 (含改进后调整)
> **变更说明**: v1.1 针对 8 项架构评审意见进行修订 (R1-R8)

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [Sprint 规划](#2-sprint-规划)
3. [工作分解结构 (WBS)](#3-工作分解结构-wbs)
4. [关键里程碑](#4-关键里程碑)
5. [风险管理计划](#5-风险管理计划)
6. [质量保证计划](#6-质量保证计划)
7. [资源计划](#7-资源计划)
8. [Must-Fix 项实施计划](#8-must-fix-项实施计划)

---

## 1. 执行摘要

### 1.1 项目概述

LEE Orchestrator v3.0 将引入三层流程架构 (Level-1: 项目级, Level-2: 部门级, Level-3: 任务级)，实现：

- **统一状态机管理**：所有层级状态由 Orchestrator 统一管理
- **事件驱动架构**：层级间通过事件松耦合
- **模板驱动**：L3 任务基于模板快速创建
- **细粒度控制**：支持实例级别的暂停/恢复

### 1.2 时间线概览 (含 2 周预 Sprint 0 改进阶段)

```
总周期: 14-16 周 (含 2 周改进 + 6-7 个 Sprint)

Phase 1: 预 Sprint 0 改进 (2 周)  ────────► 2026-02-08
  - R1-R8: 8 项架构评审改进
  - 团队组建 + 环境准备 + 技术培训

Phase 2: Sprint 0 技术预研 (2 周)  ────────► 2026-02-22
  - POC 验证 (StateMachine, Redis Streams, L3 队列)
  - 测试基础设施搭建
  - Celery vs 自研队列决策

Sprint 1:  核心模块开发   (2.5 周) ────────► 2026-03-12
Sprint 2:  模板和Spawn    (2 周)   ────────► 2026-03-26
Sprint 3:  事件和聚合     (2 周)  ────────► 2026-04-09
Sprint 4:  API和工具      (2 周)   ────────► 2026-04-23
Sprint 5:  L1→L2集成      (2 周)   ────────► 2026-05-07
Sprint 6:  兼容性和发布   (2 周)   ────────► 2026-05-21

Milestone 0: 架构评审改进完成       (Phase 1 结束)
Milestone 1: 技术可行性验证        (Sprint 0 结束)
Milestone 2: 核心状态机完成         (Sprint 1 结束)
Milestone 3: L3 任务创建完成         (Sprint 2 结束)
Milestone 4: 事件驱动完成           (Sprint 3 结束)
Milestone 5: API 集成完成           (Sprint 4 结束)
Milestone 6: 三层流程端到端完成     (Sprint 5 结束)
Milestone 7: v3.0 发布              (Sprint 6 结束)
```

### 1.3 关键里程碑

| 里程碑 | 日期 | 交付物 | 成功标准 |
|--------|------|--------|----------|
| M1: 技术可行性验证 | Week 2 | 技术可行性报告 + POC 代码 | 所有关键技术风险得到验证 |
| M2: 核心状态机完成 | Week 4 | StateMachine + 数据模型 | 可创建/查询/更新实例 |
| M3: L3 任务创建完成 | Week 6 | TemplateEngine + SpawnEngine | 可基于模板创建 L3 实例 |
| M4: 事件驱动完成 | Week 8 | EventBus + AggregationEngine | L3 完成触发 L2 更新 |
| M5: API 集成完成 | Week 10 | FastAPI + PM Agent 工具 | PM Agent 可调用 API |
| M6: 三层流程端到端 | Week 12 | 完整三层流程运行 | L1→L2→L3 完整执行 |
| M7: v3.0 发布 | Week 14 | v3.0.0 发布 + 文档 | 通过所有验收测试 |

### 1.4 资源需求

| 角色 | 级别 | 人数 | 工作量 | 技能要求 |
|------|------|------|--------|----------|
| 后端工程师 1 | **Senior** (5+ 年) | 1 | 52 人天 | **Must have**: FastAPI, PostgreSQL JSONB, Redis Streams. **Role**: 技术负责人，负责 StateMachine、AggregationEngine 等核心模块 |
| 后端工程师 2 | **Mid-level** (2-3 年) | 1 | 42 人天 | **Must have**: Python, asyncio, PostgreSQL 基础. **Nice-to-have**: FastAPI. **Role**: API 层、TemplateEngine、SpawnEngine |
| 测试工程师 | - | 1 | 22 人天 (R2 修订) | pytest, 性能测试, 集成测试, E2E 测试 |
| DevOps 工程师 | - | 0.5 | 6 人天 | Docker, CI/CD, 监控, Redis 运维 |
| **总计** | - | **3.5** | **122 人天** (含缓冲) | - |

**有效利用率调整** (R7 修订):
- **实际工作量**: 83 人天 (上限)
- **有效容量**: 122 × 70% = 85 人天
- **说明**: 考虑 10% 病假/休假、15% 会议/沟通、20% 意外 Bug 修复、10% 上下文切换，有效利用率为 70%

**团队组建要求** (R1 修订):
- [ ] **Senior 后端工程师**: 必须有 FastAPI + Redis Streams 生产经验，负责技术难点攻关
- [ ] **Mid-level 后端工程师**: 有 Python 异步编程经验，负责 API 和业务逻辑
- [ ] **测试工程师**: 必须有 pytest 性能测试经验，熟悉 Docker Compose 测试环境

---

## 2. Sprint 规划

### Sprint 0: 技术预研 (2 周)

**目标**：验证关键技术可行性，识别并缓解技术风险

**优先级**: P0 (必须完成，阻塞后续实施)

#### 任务分解

| ID | 任务 | 工作量 | 依赖 | 交付物 | 验收标准 |
|----|------|--------|------|--------|----------|
| S0-1 | StateMachine 并发安全性 POC | 3 天 | - | POC 代码 + 测试报告 | 证明并发场景下状态转换正确 |
| S0-2 | Redis Streams 性能压测 | 3 天 | - | 压测报告 | 10000 events/s 吞吐量 |
| S0-3 | L3 并发队列原型验证 | 3 天 | - | 原型代码 + 性能数据 | 支持 1000+ 并发任务 |
| S0-4 | 模板参数化性能测试 | 2 天 | - | 性能报告 | 模板渲染 < 10ms |
| S0-5 | 编写技术可行性报告 | 2 天 | S0-1~S0-4 | technical-feasibility.md | 通过架构评审 |
| S0-6 | 测试基础设施搭建 (R3) | 2 天 | - | 测试框架 + CI 管道 | pytest 环境 ready，CI < 15min |
| S0-7 | Celery vs 自研队列评估 (R4) | 1 天 | - | 决策文档 | 技术选型确定 |

#### R3: 测试基础设施搭建 (新增任务)

```yaml
任务 S0-6: 测试基础设施搭建 (2 天)
交付物:
  - pytest + pytest-asyncio + pytest-mock 配置完成
  - docker-compose-test.yml (PostgreSQL, Redis 测试环境)
  - 测试数据工厂 (test data factory for seeding)
  - Mock 基础设施 (StateMachine mocks, Storage mocks)
  - 覆盖率报告 (Codecov 集成)
  - CI pipeline stub (GitHub Actions / GitLab CI)
验收标准:
  - 本地测试执行时间 < 5 分钟
  - CI 测试执行时间 < 15 分钟
  - 可运行示例测试用例
```

#### R4: Celery vs 自研队列评估 (新增任务)

```yaml
任务 S0-7: Celery vs 自研队列评估 (1 天)
POC 内容:
  - Celery POC (2 小时): 基础队列 + worker 配置
  - 自研队列 POC (4 小时): 并发队列 + semaphore 实现

对比矩阵:
  | 维度 | Celery | 自研 |
  |------|--------|------|
  | 复杂度 | Low (成熟框架) | High (需从头实现) |
  | 实现时间 | 2 天 | 3-5 天 |
  | 维护成本 | Low (社区支持) | High (自维护) |
  | 功能匹配度 | 需评估 | 100% 匹配 |
  | 学习曲线 | 中等 | 低 (自研) |

决策标准:
  - 如果 Celery: 添加 Celery 安装到 Sprint 1 任务
  - 如果自研: 添加详细设计文档到 Sprint 2

验收标准:
  - 决策文档包含详细对比分析
  - 明确选择及理由
  - 后续 Sprint 任务已更新
```

#### 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Redis Streams 性能不达标 | 高 | 提前压测，准备备用方案 (RabbitMQ) |
| L3 并发控制复杂度超预期 | 中 | 简化队列逻辑，考虑使用 Celery |
| 并发安全性难以保证 | 高 | 使用事务 + 乐观锁，编写充分测试 |

#### Sprint 目标

- [ ] 完成所有技术验证 POC
- [ ] 输出完整的技术可行性报告
- [ ] 所有性能指标达到预期目标
- [ ] 识别的技术风险有明确缓解方案

---

### Sprint 1: 核心模块开发 (2.5 周) (R5 修订)

**目标**：实现统一状态机和数据模型（采用重构设计）

**优先级**: P0

**架构决策** (R5: StateMachine 重构):
根据架构评审 P2 建议，采用职责分离设计：

```python
# 重构前（单一类）
class StateMachine:
    - 状态管理
    - 状态存储
    - 状态验证
    - 事件发布

# 重构后（三个类）
class StateRepository:      # 状态存储
class StateValidator:       # 状态验证
class StateMachine:         # 状态机逻辑（仅此）
```

#### 任务分解

| ID | 任务 | 工作量 | 依赖 | 交付物 | 验收标准 |
|----|------|--------|------|--------|----------|
| S1-1 | 设计 PostgreSQL Schema | 2 天 | S0-5 | SQL DDL + 索引设计 | 通过 DBA 审核 |
| S1-2 | 设计重构后的 StateMachine 架构 | 1 天 | S1-1 | 架构设计文档 | 三个类职责清晰 |
| S1-3 | 实现 WorkflowInstance 数据模型 | 2 天 | S1-1 | Python dataclass | 覆盖所有 PRD 字段 |
| S1-4 | 实现 StateRepository (PostgreSQL) | 3 天 | S1-3 | StateRepository 类 | CRUD 操作完整 |
| S1-5 | 实现 StateValidator | 2 天 | S1-2 | StateValidator 类 | 状态转换验证正确 |
| S1-6 | 实现 StateMachine (状态机逻辑) | 3 天 | S1-4, S1-5 | StateMachine 类 | 支持创建/查询/更新状态 |
| S1-7 | Redis 缓存集成 | 1 天 | S1-4 | 缓存层 | 状态查询命中缓存 |
| S1-8 | 编写单元测试 (所有模块) | 2 天 | S1-6 | 测试用例 | 覆盖率 > 80% |

#### R5: StateMachine 重构影响分析

```yaml
重构优点:
  - 单一职责原则 (SRP): 每个类职责明确
  - 更易测试: StateRepository 可 mock，StateValidator 可独立测试
  - 更易维护: 修改存储逻辑不影响状态机逻辑

重构成本:
  - Sprint 1 延长: 2 周 → 2.5 周 (+3 天)
  - 设计复杂度: 需要设计三个类的接口
  - 测试复杂度: 需要编写三个类的测试

重构风险:
  - 接口设计不完善可能导致返工
  - 三个类之间的依赖关系可能引入 bug

验收标准:
  - [ ] 三个类的接口定义清晰
  - [ ] StateMachine 不直接访问 PostgreSQL
  - [ ] 所有状态转换通过 StateValidator 验证
  - [ ] 单元测试覆盖率 > 80%
```

#### 技术难点

1. **统一状态机设计**：需同时支持 L1/L2/L3 三种层级
2. **并发安全性**：状态更新需使用乐观锁
3. **数据模型灵活性**：JSONB 字段存储层级特有数据

#### Sprint 目标

- [ ] StateMachine 可创建和查询实例
- [ ] 状态转换验证逻辑正确
- [ ] 单元测试覆盖率 > 80%
- [ ] 所有测试用例通过

---

### Sprint 2: 模板和 Spawn (2 周)

**目标**：实现模板引擎和 L3 任务创建

**优先级**: P0

#### 任务分解

| ID | 任务 | 工作量 | 依赖 | 交付物 | 验收标准 |
|----|------|--------|------|--------|----------|
| S2-1 | 设计模板 Schema | 1 天 | S1-7 | YAML Schema 定义 | 覆盖 PRD 所有字段 |
| S2-2 | 实现 TemplateEngine | 3 天 | S2-1 | TemplateEngine 类 | 支持加载/渲染模板 |
| S2-3 | 实现模板参数化 (Jinja2) | 2 天 | S2-2 | 参数化逻辑 | 支持所有表达式类型 |
| S2-4 | 实现 SpawnEngine 基础功能 | 3 天 | S2-3, S1-7 | SpawnEngine 类 | 可创建 L3 实例 |
| S2-5 | 实现 L3 并发队列 | 3 天 | S2-4 | 队列管理器 | 支持并发限制 + 排队 |
| S2-6 | 实现增量聚合 (Redis) | 2 天 | S2-5 | AggregateCache | 聚合查询 < 100ms |
| S2-7 | 编写集成测试 | 2 天 | S2-6 | 测试用例 | L3 spawn 流程测试通过 |

#### 技术难点

1. **模板继承和覆盖**：需支持 extends 和 overrides
2. **并发队列管理**：优先级队列 + 超时处理
3. **增量聚合性能**：Redis HINCRBY 性能优化

#### Sprint 目标

- [ ] 可基于模板创建 L3 实例
- [ ] L3 并发限制和队列正常工作
- [ ] 增量聚合性能达标 (< 100ms)
- [ ] 集成测试通过

---

### Sprint 3: 事件和聚合 (2 周)

**目标**：实现事件驱动和状态聚合

**优先级**: P0

#### 任务分解

| ID | 任务 | 工作量 | 依赖 | 交付物 | 验收标准 |
|----|------|--------|------|--------|----------|
| S3-1 | 设计事件 Schema | 1 天 | S2-7 | 事件类型定义 | 覆盖所有场景 |
| S3-2 | 实现 EventBus (Redis Streams) | 3 天 | S3-1 | EventBus 类 | 支持发布/订阅 |
| S3-3 | 实现事件订阅和分发 | 2 天 | S3-2 | 订阅管理器 | 事件正确路由 |
| S3-4 | 实现 AggregationEngine | 3 天 | S3-3, S2-6 | AggregationEngine | L3→L2 状态聚合 |
| S3-5 | 实现完成条件判断 | 2 天 | S3-4 | 完成判断器 | 支持自定义条件 |
| S3-6 | L3→L2 状态同步 | 2 天 | S3-5 | 同步逻辑 | L3 完成触发 L2 更新 |
| S3-7 | 性能压测和优化 | 2 天 | S3-6 | 压测报告 | 聚合查询 < 100ms |

#### 技术难点

1. **Redis Streams 可靠性**：消息持久化 + 消费者组
2. **事件传播顺序**：保证父子实例事件顺序
3. **聚合查询优化**：增量聚合 + 缓存策略

#### Sprint 目标

- [ ] 事件发布订阅正常工作
- [ ] L3 完成触发 L2 更新
- [ ] 聚合查询性能达标
- [ ] 通过压测验证

---

### Sprint 4: API 和工具 (2 周)

**目标**：暴露 API 接口和 PM Agent 工具

**优先级**: P0

#### 任务分解

| ID | 任务 | 工作量 | 依赖 | 交付物 | 验收标准 |
|----|------|--------|------|--------|----------|
| S4-1 | 设计 FastAPI 接口 | 1 天 | S3-7 | API 设计文档 | 覆盖所有核心功能 |
| S4-2 | 实现 RESTful API (CRUD) | 3 天 | S4-1 | FastAPI 应用 | API 可正常调用 |
| S4-3 | 实现 PM Agent 工具封装 | 3 天 | S4-2 | 工具函数 | PM Agent 可调用 |
| S4-4 | 实现 Gate 决策流程 | 2 天 | S4-3 | GateEngine | 门禁决策正常 |
| S4-5 | API 认证和授权 | 2 天 | S4-4 | Auth 中间件 | 权限控制正确 |
| S4-6 | API 文档 (OpenAPI) | 1 天 | S4-5 | API 文档 | 文档完整准确 |
| S4-7 | 编写集成测试 | 2 天 | S4-6 | 测试用例 | API 集成测试通过 |

#### 技术难点

1. **窄接口设计**：只暴露必要操作，隐藏内部状态
2. **权限控制**：基于角色的访问控制 (RBAC)
3. **API 版本管理**：v2.0 兼容性

#### Sprint 目标

- [ ] RESTful API 完整可用
- [ ] PM Agent 可通过工具调用 API
- [ ] Gate 决策流程正常
- [ ] API 文档完整

---

### Sprint 5: L1→L2 集成 (2 周)

**目标**：实现完整的三层流程

**优先级**: P0

#### 任务分解

| ID | 任务 | 工作量 | 依赖 | 交付物 | 验收标准 |
|----|------|--------|------|--------|----------|
| S5-1 | 定义 L1 workflow 模板 | 2 天 | S4-7 | project_master.yaml | 覆盖所有阶段 |
| S5-2 | 实现 department_flow 步骤 | 3 天 | S5-1 | DepartmentFlowExecutor | L1 可触发 L2 |
| S5-3 | 实现 L1→L2 事件触发 | 2 天 | S5-2 | 触发逻辑 | L1 阶段完成触发 L2 |
| S5-4 | 实现 L2→L3 spawn 配置 | 2 天 | S5-3 | SpawnConfigExecutor | L2 可触发 L3 |
| S5-5 | 实现端到端测试用例 | 3 天 | S5-4 | E2E 测试 | L1→L2→L3 完整执行 |
| S5-6 | 性能优化和调优 | 2 天 | S5-5 | 优化报告 | 性能达标 |
| S5-7 | Bug 修复和稳定性 | 2 天 | S5-6 | Bug 修复 | 所有关键 Bug 修复 |

#### 技术难点

1. **三层状态同步**：L3→L2→L1 状态传播
2. **完成条件判断**：复杂的聚合条件
3. **性能优化**：减少数据库查询

#### Sprint 目标

- [ ] 完整的三层流程可运行
- [ ] L1→L2→L3 状态正确同步
- [ ] 端到端测试通过
- [ ] 性能达标

---

### Sprint 6: 兼容性和发布 (2 周)

**目标**：v2.0 兼容性 + v3.0 发布

**优先级**: P0

#### 任务分解

| ID | 任务 | 工作量 | 依赖 | 交付物 | 验收标准 |
|----|------|--------|------|--------|----------|
| S6-1 | 实现 v2.0 数据迁移脚本 | 3 天 | S5-7 | 迁移脚本 | v2.0 数据可迁移到 v3.0 |
| S6-2 | 实现 v2.0 兼容层 | 3 天 | S6-1 | CompatLayer | v2.0 API 可调用 |
| S6-3 | 编写迁移指南 | 1 天 | S6-2 | 迁移文档 | 用户可按指南迁移 |
| S6-4 | 实现回滚方案 | 2 天 | S6-3 | 回滚脚本 | 支持回滚到 v2.0 |
| S6-5 | 完善用户文档 | 2 天 | S6-4 | 用户文档 | 文档完整清晰 |
| S6-6 | 准备发布 (Release Notes) | 1 天 | S6-5 | Release Notes | 发布说明完整 |
| S6-7 | v3.0.0 发布 | 1 天 | S6-6 | v3.0.0 tag | 成功发布 |

#### 技术难点

1. **数据迁移**：v2.0 YAML → v3.0 数据库
2. **API 兼容**：v2.0 API 映射到 v3.0
3. **回滚方案**：快速回滚机制

#### Sprint 目标

- [ ] v2.0 数据可完整迁移
- [ ] v2.0 兼容层正常工作
- [ ] 文档完整
- [ ] v3.0.0 成功发布

---

## 3. 工作分解结构 (WBS)

### 3.1 工作包分解

```
LEE Orchestrator v3.0 开发
├─ WP1: 技术预研 (10 人天)
│  ├─ 1.1 StateMachine 并发安全性验证 (3 人天)
│  ├─ 1.2 Redis Streams 性能压测 (3 人天)
│  ├─ 1.3 L3 并发队列原型 (3 人天)
│  └─ 1.4 技术可行性报告 (1 人天)
├─ WP2: 核心模块开发 (14 人天)
│  ├─ 2.1 数据模型设计 (4 人天)
│  ├─ 2.2 StateMachine 实现 (7 人天)
│  └─ 2.3 单元测试 (3 人天)
├─ WP3: 模板和 Spawn (14 人天)
│  ├─ 3.1 TemplateEngine (6 人天)
│  ├─ 3.2 SpawnEngine (8 人天)
│  └─ 3.3 集成测试 (2 人天)
├─ WP4: 事件和聚合 (14 人天)
│  ├─ 4.1 EventBus (6 人天)
│  ├─ 4.2 AggregationEngine (6 人天)
│  └─ 4.3 性能压测 (2 人天)
├─ WP5: API 和工具 (14 人天)
│  ├─ 5.1 FastAPI 接口 (8 人天)
│  ├─ 5.2 PM Agent 工具 (4 人天)
│  └─ 5.3 API 测试 (2 人天)
├─ WP6: L1→L2 集成 (14 人天)
│  ├─ 6.1 三层流程实现 (10 人天)
│  └─ 6.2 E2E 测试 (4 人天)
├─ WP7: 兼容性和发布 (12 人天)
│  ├─ 7.1 数据迁移 (6 人天)
│  ├─ 7.2 兼容层 (4 人天)
│  └─ 7.3 文档和发布 (2 人天)
└─ WP8: 项目管理 (10 人天)
   ├─ 8.1 Sprint 规划和回顾 (6 人天)
   ├─ 8.2 风险管理 (2 人天)
   └─ 8.3 质量保证 (2 人天)

总计: 102 人天 (包含 20% 缓冲)
实际工作量: 65-83 人天 (不含缓冲)
```

### 3.2 依赖关系图

```
Sprint 0 (技术预研)
    │
    ▼
Sprint 1 (核心模块) ────────┐
    │                      │
    ▼                      │
Sprint 2 (模板和Spawn) ─────┤
    │                      │
    ▼                      │
Sprint 3 (事件和聚合) ◄─────┤
    │                      │
    ▼                      │
Sprint 4 (API和工具) ◄──────┘
    │
    ▼
Sprint 5 (L1→L2集成)
    │
    ▼
Sprint 6 (兼容性和发布)

关键路径: Sprint 0 → 1 → 2 → 3 → 4 → 5 → 6
```

### 3.3 工作量估算

| 工作包 | 乐观 | 正常 | 悲观 | 期望值 | 标准差 |
|--------|------|------|------|--------|--------|
| WP1: 技术预研 | 8 | 10 | 14 | 10.3 | 1.0 |
| WP2: 核心模块 | 12 | 14 | 18 | 14.3 | 1.0 |
| WP3: 模板和Spawn | 12 | 14 | 20 | 14.7 | 1.3 |
| WP4: 事件和聚合 | 12 | 14 | 20 | 14.7 | 1.3 |
| WP5: API和工具 | 12 | 14 | 18 | 14.3 | 1.0 |
| WP6: L1→L2集成 | 12 | 14 | 20 | 14.7 | 1.3 |
| WP7: 兼容性和发布 | 10 | 12 | 16 | 12.3 | 1.0 |
| WP8: 项目管理 | 8 | 10 | 14 | 10.3 | 1.0 |
| **总计** | **86** | **102** | **140** | **105.6** | **9.0** |

**说明**：采用 PERT (Program Evaluation and Review Technique) 估算
- 期望值 = (乐观 + 4 × 正常 + 悲观) / 6
- 标准差 = (悲观 - 乐观) / 6

**工作量调整**：
- 总期望工作量: 105.6 人天
- 包含缓冲后: 105.6 × 1.2 ≈ 127 人天
- 实际开发工作量: 65-83 人天 (不含项目管理)

---

## 4. 关键里程碑

### 4.1 里程碑详细计划

#### M1: 技术可行性验证 (Week 2)

**日期**: 2026-02-08

**交付物**:
- [ ] technical-feasibility.md 报告
- [ ] StateMachine 并发安全性 POC 代码
- [ ] Redis Streams 压测报告
- [ ] L3 并发队列原型代码
- [ ] 模板参数化性能测试报告

**成功标准**:
- StateMachine 在 1000 并发下状态转换正确率 100%
- Redis Streams 吞吐量 > 10000 events/s
- L3 并发队列支持 > 1000 实例
- 模板渲染延迟 < 10ms
- 所有技术风险有明确缓解方案

**依赖**: 无

**负责人**: 后端工程师

---

#### M2: 核心状态机完成 (Week 4)

**日期**: 2026-02-22

**交付物**:
- [ ] WorkflowInstance 数据模型
- [ ] StateMachine 核心代码
- [ ] PostgreSQL Schema
- [ ] 单元测试 (覆盖率 > 80%)

**成功标准**:
- 可创建、查询、更新工作流实例
- 状态转换验证逻辑正确
- 所有单元测试通过
- 测试覆盖率 > 80%

**依赖**: M1 (技术可行性验证)

**负责人**: 后端工程师

---

#### M3: L3 任务创建完成 (Week 6)

**日期**: 2026-03-08

**交付物**:
- [ ] TemplateEngine 代码
- [ ] SpawnEngine 代码
- [ ] L3 并发队列实现
- [ ] 增量聚合实现 (Redis)
- [ ] 集成测试用例

**成功标准**:
- 可基于模板创建 L3 实例
- L3 并发限制正常工作 (默认 50)
- 队列排队机制正常
- 增量聚合查询延迟 < 100ms (1000 实例)
- 集成测试通过

**依赖**: M2 (核心状态机完成)

**负责人**: 后端工程师

---

#### M4: 事件驱动完成 (Week 8)

**日期**: 2026-03-22

**交付物**:
- [ ] EventBus (Redis Streams)
- [ ] AggregationEngine
- [ ] 完成条件判断器
- [ ] L3→L2 状态同步逻辑
- [ ] 性能压测报告

**成功标准**:
- 事件发布订阅正常工作
- L3 完成触发 L2 更新
- 聚合查询延迟 < 100ms
- 完成条件判断正确
- 压测通过 (1000 L3 实例)

**依赖**: M3 (L3 任务创建完成)

**负责人**: 后端工程师

---

#### M5: API 集成完成 (Week 10)

**日期**: 2026-04-05

**交付物**:
- [ ] FastAPI RESTful API
- [ ] PM Agent 工具封装
- [ ] GateEngine
- [ ] API 认证和授权
- [ ] API 文档 (OpenAPI)
- [ ] API 集成测试

**成功标准**:
- 所有核心 API 可正常调用
- PM Agent 可通过工具操作 Orchestrator
- Gate 决策流程正常
- 权限控制正确
- API 文档完整准确
- 集成测试通过

**依赖**: M4 (事件驱动完成)

**负责人**: 后端工程师

---

#### M6: 三层流程端到端完成 (Week 12)

**日期**: 2026-04-19

**交付物**:
- [ ] L1 workflow 模板
- [ ] L1→L2 触发逻辑
- [ ] L2→L3 spawn 配置
- [ ] 端到端测试用例
- [ ] 性能优化报告

**成功标准**:
- 完整三层流程可执行
- L1→L2→L3 状态正确同步
- 端到端测试通过
- API 响应延迟 P95 < 100ms
- L3 spawn 延迟 P95 < 200ms

**依赖**: M5 (API 集成完成)

**负责人**: 后端工程师

---

#### M7: v3.0 发布 (Week 14)

**日期**: 2026-05-03

**交付物**:
- [ ] v2.0 数据迁移脚本
- [ ] v2.0 兼容层
- [ ] 迁移指南
- [ ] 回滚方案
- [ ] 用户文档
- [ ] Release Notes
- [ ] v3.0.0 发布

**成功标准**:
- v2.0 数据可完整迁移
- v2.0 API 兼容层正常工作
- 文档完整清晰
- 所有验收测试通过
- 成功发布 v3.0.0

**依赖**: M6 (三层流程端到端完成)

**负责人**: 后端工程师 + DevOps 工程师

---

### 4.2 里程碑依赖图

```
M1: 技术可行性验证 (Week 2)
    │
    ▼
M2: 核心状态机完成 (Week 4)
    │
    ▼
M3: L3 任务创建完成 (Week 6)
    │
    ▼
M4: 事件驱动完成 (Week 8)
    │
    ▼
M5: API 集成完成 (Week 10)
    │
    ▼
M6: 三层流程端到端完成 (Week 12)
    │
    ▼
M7: v3.0 发布 (Week 14)
```

**关键路径**: M1 → M2 → M3 → M4 → M5 → M6 → M7

**总工期**: 14 周 (包含 20% 缓冲)

---

## 5. 风险管理计划

### 5.1 技术风险 Top 5

#### 风险 1: L3 并发控制复杂度超预期

**描述**: L3 并发队列 + 优先级调度 + 超时处理组合复杂，分布式环境下并发控制难度大

**影响**: 高
**概率**: 中 (40%)

**缓解措施**:
1. **Sprint 0 提前验证**: 并发队列原型 POC
2. **简化设计**: 考虑使用 Celery/RQ 替代自研
3. **充分测试**: 编写完整的并发测试用例
4. **降级方案**: 并发限制可配置，必要时降低并发数

**应急预案**:
- 如果自研队列复杂度过高，采用 Celery
- 预留 1 周缓冲时间处理并发问题

**监控指标**:
- POC 完成时间: Week 2
- 并发测试通过率: > 95%

---

#### 风险 2: 聚合查询性能不达标

**描述**: `get_children` 可能返回数千条记录，PostgreSQL JSONB 查询可能较慢

**影响**: 高
**概率**: 中 (30%)

**缓解措施**:
1. **增量聚合**: 使用 Redis 预聚合 (HINCRBY)
2. **分页查询**: 支持分页，避免一次性加载全部数据
3. **索引优化**: 优化数据库索引
4. **性能压测**: Sprint 3 进行压测验证

**应急预案**:
- 如果增量聚合仍不够，考虑使用 ClickHouse
- 降低聚合粒度，按时间段聚合

**监控指标**:
- 聚合查询延迟: P95 < 100ms
- 压测通过时间: Week 8

---

#### 风险 3: Redis Streams 消息丢失

**描述**: Redis Streams 在高并发下可能丢失消息，未考虑消息持久化和重试机制

**影响**: 高
**概率**: 低 (20%)

**缓解措施**:
1. **Sprint 0 压测**: 验证 Redis Streams 可靠性
2. **消费者组**: 使用消费者组保证消息不丢失
3. **持久化**: Redis AOF 持久化
4. **监控**: 监控消息丢失率

**应急预案**:
- 如果 Redis Streams 不可靠，切换到 RabbitMQ
- 预留 3 天切换时间

**监控指标**:
- 消息丢失率: < 0.01%
- 压测吞吐量: > 10000 events/s

---

#### 风险 4: StateMachine 并发安全性难以保证

**描述**: 父子实例状态更新可能产生竞态条件

**影响**: 高
**概率**: 中 (30%)

**缓解措施**:
1. **Sprint 0 POC**: 验证并发场景下状态转换正确性
2. **乐观锁**: 使用 version 字段实现乐观锁
3. **事务**: PostgreSQL 事务保证原子性
4. **充分测试**: 编写并发测试用例

**应急预案**:
- 如果乐观锁不够，使用悲观锁 (SELECT FOR UPDATE)
- 增加状态一致性检查和修复工具

**监控指标**:
- 并发测试通过率: > 99%
- 状态不一致率: < 0.1%

---

#### 风险 5: v2.0 兼容性问题

**描述**: v2.0 API 兼容层可能存在遗漏或错误

**影响**: 中
**概率**: 中 (40%)

**缓解措施**:
1. **API 变更清单**: 详细列出所有 API 变更
2. **充分测试**: 编写 v2.0 兼容性测试
3. **灰度发布**: 先在新项目使用 v3.0
4. **回滚方案**: 保留 v2.0 快照，支持快速回滚

**应急预案**:
- 如果兼容性问题严重，推迟 v2.0 废弃时间
- 提供兼容性补丁

**监控指标**:
- 兼容性测试通过率: > 95%
- 迁移成功率: > 95%

---

### 5.2 项目风险 Top 5

#### 风险 6: 工作量估算偏乐观

**描述**: 实施工作量可能超出预期

**影响**: 高
**概率**: 中 (30%)

**缓解措施**:
1. **预留缓冲**: 每个 Sprint 预留 20% 缓冲时间
2. **优先级管理**: Must-have > Should-have > Nice-to-have
3. **每日站会**: 及时发现进度偏差
4. **风险上报**: 提前上报延期风险

**应急预案**:
- 削减非核心功能 (如 L1/L2 多实例)
- 延长 Sprint 6 时间

**监控指标**:
- Sprint 完成率: > 80%
- 任务延期率: < 20%

---

#### 风险 7: 团队技能不足

**描述**: 团队对 Redis Streams、Celery 等技术不熟悉

**影响**: 中
**概率**: 低 (20%)

**缓解措施**:
1. **技术培训**: Sprint 0 前进行技术培训
2. **技术文档**: 提供详细技术文档
3. **Code Review**: 加强代码审查
4. **技术分享**: 定期技术分享

**应急预案**:
- 引入外部顾问
- 调整技术选型

**监控指标**:
- 开发效率: > 预期 80%

---

#### 风险 8: 需求变更

**描述**: 实施过程中需求可能发生变化

**影响**: 中
**概率**: 中 (40%)

**缓解措施**:
1. **需求锁定**: Sprint 0 后锁定需求
2. **变更流程**: 需求变更需评审和评估
3. **优先级管理**: 变更影响优先级评估

**应急预案**:
- 延迟非核心需求到 v3.1
- 调整 Sprint 范围

**监控指标**:
- 需求变更率: < 10%

---

#### 风险 9: 测试时间不足

**描述**: 开发时间紧张，测试时间可能被压缩

**影响**: 高
**概率**: 中 (30%)

**缓解措施**:
1. **测试先行**: 开发前编写测试用例
2. **自动化测试**: 单元测试 + 集成测试自动化
3. **持续集成**: 每次 CI 运行测试
4. **预留测试时间**: 每个 Sprint 预留 2 天测试

**应急预案**:
- 延长 Sprint 6 测试时间
- 降低测试覆盖率目标 (但最低 > 70%)

**监控指标**:
- 测试覆盖率: > 80%
- 测试通过率: > 95%

---

#### 风险 10: 第三方依赖问题

**描述**: FastAPI、Redis、Celery 等依赖可能存在兼容性或性能问题

**影响**: 中
**概率**: 低 (20%)

**缓解措施**:
1. **版本锁定**: 锁定依赖版本
2. **Sprint 0 验证**: 提前验证关键依赖
3. **备用方案**: 准备备用技术栈
4. **监控**: 监控依赖的 Issue 和更新

**应急预案**:
- 升级到最新版本
- 切换到备用技术栈

**监控指标**:
- 依赖兼容性问题: 0

---

#### 风险 11: Sprint 雪崩风险 (R6 新增)

**描述**: 如果某个 Sprint 延期，可能导致后续所有 Sprint 雪崩式延期

**影响**: 高 (3-5 周总延期)
**概率**: 中 (30%)

**缓解措施**:
1. **Sprint 0-2 额外缓冲**: 前 3 个 Sprint 各预留 30% 缓冲 (而非 20%)
2. **周五进度 checkpoint**: 每周五评估进度偏差，提前识别风险
3. **Scope reduction protocol**: 如果 Sprint 2 延期 > 3 天，触发范围削减
   - 削减 Sprint 5 非核心功能 (L1/L2 多实例支持, 2 天)
   - 削减 Sprint 5 非核心功能 (分布式追踪, 3 天)
   - **Result**: 恢复 5 天缓冲

**应急预案**:
- **如果 Sprint 3 延期**: 合并 Sprint 4-5 部分 API 层工作
- **如果 Sprint 5 延期**: 延长 Sprint 6 至 3 周
- **如果连续 2 个 Sprint 延期**: 召开紧急评审，考虑削减 Nice-to-Have 功能

**监控指标**:
- Sprint 完成率: > 85% (Sprint 0-2), > 80% (Sprint 3-6)
- 累计延期周数: < 2 周 (触发范围削减)

---

### 5.3 风险矩阵 (含 R11 更新)

| 风险 | 影响 | 概率 | 风险等级 | 优先级 |
|------|------|------|----------|--------|
| R1: L3 并发控制复杂度 | 高 | 中 (40%) | 高 | P0 |
| R2: 聚合查询性能 | 高 | 中 (30%) | 高 | P0 |
| R3: Redis Streams 消息丢失 | 高 | 低 (20%) | 中 | P1 |
| R4: StateMachine 并发安全 | 高 | 中 (30%) | 高 | P0 |
| R5: v2.0 兼容性 | 中 | 中 (40%) | 中 | P1 |
| R6: 工作量估算偏乐观 | 高 | 中 (30%) | 高 | P0 |
| R7: 团队技能不足 | 中 | 低 (20%) | 低 | P2 |
| R8: 需求变更 | 中 | 中 (40%) | 中 | P1 |
| R9: 测试时间不足 | 高 | 中 (30%) | 高 | P0 |
| R10: 第三方依赖问题 | 中 | 低 (20%) | 低 | P2 |
| R11: **Sprint 雪崩风险** (R6 新增) | **高** | **中 (30%)** | **高** | **P0** |

**风险等级计算**: 影响 × 概率
- 高: 高 × 高/中
- 中: 高 × 低 或 中 × 中
- 低: 中 × 低 或 低 × 任何

**处理优先级**:
- P0 (必须处理): R1, R2, R4, R6, R9, R11 (Sprint 雪崩)
- P1 (高优先级): R3, R5, R8
- P2 (监控即可): R7, R10

---

## 6. 质量保证计划

### 6.1 代码质量标准

#### 6.1.1 代码规范

**Python 代码规范**:
- 遵循 PEP 8
- 使用 Black 格式化
- 使用 isort 排序 imports
- 使用 pylint 进行静态检查
- 类型注解覆盖率 > 80%

**文档规范**:
- 所有公共 API 有 docstring
- 使用 Google 风格 docstring
- 复杂逻辑有注释说明

**审查流程**:
- 所有代码必须经过 Code Review
- 至少 1 人 Approve 才能合并
- CI 检查必须通过

---

#### 6.1.2 TypeScript 编译检查

虽然本项目是 Python 项目，但如果涉及前端代码：
- 使用 TypeScript strict mode
- ESLint + Prettier
- 编译无错误和警告

---

### 6.2 测试策略

#### 6.2.1 测试金字塔

```
        /\
       /  \        E2E Tests (10%)
      /────\
     /      \     Integration Tests (20%)
    /────────\
   /          \  Unit Tests (70%)
  /____________\
```

**测试比例**:
- 单元测试: 70%
- 集成测试: 20%
- 端到端测试: 10%

**测试覆盖率目标**: > 80%

---

#### 6.2.2 单元测试

**框架**: pytest + pytest-asyncio

**覆盖范围**:
- 所有核心模块
- 所有状态转换逻辑
- 所有验证逻辑

**示例**:

```python
# tests/test_state_machine.py
import pytest
from orchestrator.state_machine import OrchestratorStateMachine, WorkflowStatus

@pytest.mark.asyncio
async def test_create_instance():
    """测试创建实例"""
    sm = OrchestratorStateMachine(storage=mock_storage)
    instance = await sm.create_instance(
        workflow_id="test_workflow",
        level=1,
        kind="project_master",
        project_id="proj-001",
        parameters={}
    )
    assert instance.id is not None
    assert instance.status == WorkflowStatus.INIT
    assert instance.level == 1

@pytest.mark.asyncio
async def test_pause_running_workflow():
    """测试暂停运行中的工作流"""
    sm = OrchestratorStateMachine(storage=mock_storage)
    instance = await sm.create_instance(...)
    await sm.update_status(instance.id, WorkflowStatus.RUNNING)

    success, error = await sm.pause_workflow(
        instance.id, "test", "test_user"
    )
    assert success
    assert (await sm.get_instance(instance.id)).paused == True

@pytest.mark.asyncio
async def test_invalid_state_transition():
    """测试无效状态转换"""
    sm = OrchestratorStateMachine(storage=mock_storage)
    instance = await sm.create_instance(...)
    await sm.update_status(instance.id, WorkflowStatus.COMPLETED)

    # COMPLETED 状态不能转换到 RUNNING
    success, error = await sm.update_status(
        instance.id, WorkflowStatus.RUNNING
    )
    assert not success
    assert "Invalid transition" in error
```

---

#### 6.2.3 集成测试

**框架**: pytest + docker-compose

**覆盖场景**:
- L1→L2 触发流程
- L2→L3 spawn 流程
- L3→L2 状态聚合
- 暂停/恢复流程
- Gate 决策流程

**示例**:

```python
# tests/integration/test_l1_l2_flow.py
import pytest
from orchestrator.core import OrchestratorCore

@pytest.mark.asyncio
async def test_l1_triggers_l2():
    """测试 L1 触发 L2"""
    core = OrchestratorCore(...)

    # 创建 L1 实例
    l1 = await core.create_workflow(
        workflow_id="project_master_workflow",
        level=1,
        parameters={"project_id": "proj-001"}
    )

    # 执行 L1 的 department_flow 步骤
    await core.run_step(l1.id, "trigger_qa_workflow")

    # 验证 L2 实例被创建
    l2_children = await core.get_children(l1.id)
    assert len(l2_children) == 1
    assert l2_children[0].level == 2
    assert l2_children[0].department == "qa"
```

---

#### 6.2.4 端到端测试

**框架**: pytest + 真实环境

**覆盖场景**:
- 完整三层流程执行 (L1→L2→L3)
- v2.0 数据迁移
- 完整工作流生命周期

**示例**:

```python
# tests/e2e/test_full_workflow.py
import pytest
from orchestrator.core import OrchestratorCore

@pytest.mark.e2e
async def test_full_three_level_workflow():
    """测试完整三层流程"""
    core = OrchestratorCore(...)

    # 1. 创建 L1 项目主流程
    l1 = await core.create_workflow(
        workflow_id="project_master_workflow",
        level=1,
        parameters={"project_id": "proj-001"}
    )

    # 2. 执行 L1 → 触发 L2
    await core.run_step(l1.id, "trigger_qa_workflow")
    l2_list = await core.get_children(l1.id)
    l2 = l2_list[0]

    # 3. 执行 L2 → spawn L3 任务
    await core.run_step(l2.id, "test_execution")

    # 模拟检测到 Bug
    await core.spawn_workflow(
        parent_id=l2.id,
        template_id="bug_fix",
        parameters={"bug_id": "BUG-001", "severity": "P0"}
    )

    l3_list = await core.get_children(l2.id)
    assert len(l3_list) == 1

    # 4. 完成 L3 → 触发 L2 聚合
    l3 = l3_list[0]
    await core.run_step(l3.id, "triage")
    await core.run_step(l3.id, "fix")

    # 验证 L2 聚合状态
    aggregate = await core.get_aggregate_state(l2.id)
    assert aggregate.by_status["COMPLETED"] == 1
```

---

### 6.3 性能测试

#### 6.3.1 性能目标

| 指标 | 目标值 | 测试方法 |
|------|--------|----------|
| API 响应时间 (P95) | < 100ms | Locust/k6 压测 |
| L3 spawn 延迟 (P95) | < 200ms | 单元测试 + 压测 |
| 状态查询延迟 (P95) | < 50ms | 压测 |
| L3 并发支持 | > 1000 实例 | 压测 |
| 事件吞吐量 | > 10000 events/s | Redis Streams 压测 |
| 聚合查询延迟 (P95) | < 100ms | 1000 L3 实例场景 |

---

#### 6.3.2 压测工具

**工具选择**:
- HTTP API 压测: Locust
- Redis 压测: redis-benchmark
- 数据库压测: pgbench

**压测场景**:
1. **场景 1**: 100 并发创建 L3 任务
2. **场景 2**: 1000 并发 L3 任务状态查询
3. **场景 3**: 10000 events/s 事件吞吐量
4. **场景 4**: 1000 L3 实例聚合查询

---

#### 6.3.3 性能监控

**监控指标**:
- API 响应时间 (P50, P95, P99)
- 数据库查询延迟
- Redis 命令延迟
- 事件队列长度
- L3 并发任务数

**告警规则**:
- API 响应时间 P95 > 100ms: Warning
- API 响应时间 P95 > 500ms: Critical
- 数据库查询延迟 > 100ms: Warning
- Redis 延迟 > 50ms: Warning

---

### 6.4 验收标准

#### 6.4.1 功能验收

**Must Have**:
- [x] 支持 L1/L2/L3 三层流程
- [x] 统一状态机管理
- [x] 模板驱动 L3 任务创建
- [x] 事件驱动架构
- [x] 实例级暂停/恢复
- [x] L3 并发限制和队列
- [x] 状态聚合 (L3→L2→L1)
- [x] Gate 决策流程
- [x] v2.0 数据迁移
- [x] RESTful API

**Should Have**:
- [ ] v2.0 API 兼容层
- [ ] 回滚方案
- [ ] 监控和告警

**Nice to Have**:
- [ ] L1/L2 多实例支持
- [ ] 分布式追踪 (OpenTelemetry)
- [ ] Web UI

---

#### 6.4.2 性能验收

**Must Have**:
- [x] API 响应时间 P95 < 100ms
- [x] L3 spawn 延迟 P95 < 200ms
- [x] 状态查询延迟 P95 < 50ms
- [x] L3 并发支持 > 1000 实例
- [x] 事件吞吐量 > 10000 events/s
- [x] 聚合查询延迟 P95 < 100ms

---

#### 6.4.3 质量验收

**Must Have**:
- [x] 单元测试覆盖率 > 80%
- [x] 所有测试用例通过
- [x] 代码审查通过
- [x] TypeScript 编译通过 (如有前端代码)
- [x] 无 Critical/Fixit 级别 Bug

---

## 7. 资源计划

### 7.1 团队角色和职责

#### 7.1.1 后端工程师 (2 人)

**职责**:
- 核心模块开发 (StateMachine, TemplateEngine, SpawnEngine, EventBus, AggregationEngine)
- API 开发 (FastAPI)
- 数据库设计和优化
- 单元测试和集成测试

**技能要求**:
- Python 3.10+
- FastAPI
- PostgreSQL (JSONB, 索引优化)
- Redis (Streams, Pub/Sub, 数据结构)
- Celery (可选)
- 异步编程 (asyncio)

**工作量**: 50-60 人天

---

#### 7.1.2 测试工程师 (1 人)

**职责**:
- 测试策略制定
- 单元测试编写
- 集成测试编写
- 端到端测试编写
- 性能测试

**技能要求**:
- pytest
- Locust/k6
- 性能测试经验
- 测试自动化

**工作量**: 10-15 人天

---

#### 7.1.3 DevOps 工程师 (0.5 人)

**职责**:
- CI/CD 流程搭建
- Docker 容器化
- 监控和告警搭建
- 发布流程

**技能要求**:
- Docker
- GitHub Actions
- Prometheus + Grafana
- Redis + PostgreSQL 运维

**工作量**: 5-8 人天

---

### 7.2 工作量分配 (R2 修订: 测试资源增加)

| 角色 | Sprint 0 | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 | Sprint 5 | Sprint 6 | 总计 |
|------|----------|----------|----------|----------|----------|----------|----------|------|
| 后端工程师 1 | 10 | 7 | 7 | 7 | 7 | 7 | 7 | 52 |
| 后端工程师 2 | 0 | 7 | 7 | 7 | 7 | 7 | 7 | 42 |
| 测试工程师 | 0 | 0 | 4 | 4 | 3 | 5 | 6 | **22** |
| DevOps 工程师 | 0 | 0 | 0 | 0 | 0 | 2 | 4 | 6 |
| **总计** | **10** | **14** | **18** | **18** | **17** | **21** | **24** | **122** |

**说明**:
- 后端工程师 1: 全职参与 (10 人天/Sprint × 7 = 70 人天，但 Sprint 0 后另一工程师加入)
- 后端工程师 2: Sprint 1 开始加入 (7 人天/Sprint × 6 = 42 人天)
- **测试工程师** (R2 修订): Sprint 2 开始参与，工作量大幅增加：
  - Sprint 2: 4 人天 (集成测试: Spawn, Events, Aggregation - 复杂度高)
  - Sprint 3: 4 人天 (集成测试: 聚合、性能测试)
  - Sprint 4: 3 人天 (API 集成测试)
  - Sprint 5: 5 人天 (E2E 测试 - 最复杂，三层流程)
  - Sprint 6: 6 人天 (回归测试 + 性能压测)
- DevOps 工程师: 兼职参与，Sprint 5-6 集中参与

**调整后总计**:
- 后端: 52 + 42 = 94 人天
- 测试: 12 人天
- DevOps: 6 人天
- **总计**: 112 人天 (包含缓冲)

---

### 7.3 技能要求和培训

#### 7.3.1 必需技能

| 技能 | 重要程度 | 用途 |
|------|----------|------|
| Python 3.10+ | 必须 | 核心开发语言 |
| FastAPI | 必须 | API 框架 |
| PostgreSQL | 必须 | 状态存储 |
| Redis | 必须 | 缓存和事件总线 |
| asyncio | 必须 | 异步编程 |
| pytest | 必须 | 测试框架 |

---

#### 7.3.2 加分技能

| 技能 | 重要程度 | 用途 |
|------|----------|------|
| Celery | 加分 | 任务队列 (备用) |
| Redis Streams | 加分 | 事件总线 |
| Jinja2 | 加分 | 模板引擎 |
| Locust/k6 | 加分 | 性能测试 |
| Docker | 加分 | 容器化 |

---

#### 7.3.3 培训计划 (R8 修订: 扩展至 2 周 / 20 小时)

**Sprint 0 前 (2 周, 20 小时)**:

##### Week 1: 基础培训 (10 小时)

| Day | 主题 | 时长 | 内容 |
|-----|------|------|------|
| Day 1 | FastAPI 深度培训 | 4h | - 异步路由设计 (2h)<br>- 依赖注入 (1h)<br>- WebSocket 支持 (1h) |
| Day 2 | PostgreSQL JSONB + 索引优化 | 4h | - JSONB 查询优化 (2h)<br>- GIN/GiST 索引 (1h)<br>- 部分索引策略 (1h) |
| Day 3 | Redis Streams + 消费者组 | 4h | - Streams 基础 (1h)<br>- 消费者组 (2h)<br>- 消息持久化 (1h) |
| Day 4 | asyncio 并发编程 | 4h | - Event Loop (1h)<br>- Tasks/Futures (1h)<br>- 并发安全 (2h) |
| Day 5 | 代码审查最佳实践 | 4h | - PR 审查流程 (1h)<br>- 常见反模式 (2h)<br>- 性能优化技巧 (1h) |

##### Week 2: 实践培训 (10 小时)

| Day | 主题 | 时长 | 内容 |
|-----|------|------|------|
| Day 6-7 | FastAPI mini-project | 8h | - CRUD API + Redis 缓存<br>- 异步任务处理<br>- JWT 认证<br>- **产出**: 可运行的示例 API |
| Day 8 | PostgreSQL JSONB mini-project | 6h | - 聚合查询优化<br>- 索引性能对比<br>- 大数据量测试<br>- **产出**: 性能优化报告 |
| Day 9 | Redis Streams mini-project | 4h | - 发布订阅实现<br>- 消费者组配置<br>- 消息丢失测试<br>- **产出**: 流式处理 demo |
| Day 10 | 技术审查与答疑 | 2h | - Sprint 0 POC 准备检查<br>- 技术栈 Q&A<br>- 团队协作规范 |

**培训材料准备** (新增):
- [ ] 培训 PPT (每次 session 20-30 页)
- [ ] 示例代码仓库 (所有 mini-project 代码)
- [ ] 实验手册 (step-by-step 指导)
- [ ] 环境配置文档 (开发环境 setup 指南)

**培训考核** (新增):
- [ ] Day 5: 基础知识小测验 (30 分钟)
- [ ] Day 10: mini-project 展示与评审 (1 小时)
- [ ] Sprint 0 开始前: 技术准备度 check (每人 30 分钟)

**讲师安排**:
- **理想**: 外部技术顾问 (FastAPI/Redis 专家)
- **备选**: Senior 后端工程师 (需提前 2 周准备材料)

---

### 7.4 开发环境

#### 7.4.1 本地开发环境

**硬件要求**:
- CPU: 4 核心以上
- 内存: 16GB 以上
- 硬盘: 50GB 以上

**软件要求**:
- OS: macOS / Linux / Windows (WSL2)
- Python: 3.10+
- PostgreSQL: 14+
- Redis: 7+
- Git: 2.30+

**开发工具**:
- IDE: VS Code / PyCharm
- Docker: 20.10+
- Docker Compose: 2.0+

---

#### 7.4.2 依赖服务

**本地开发**:
```bash
# 使用 docker-compose 启动依赖服务
docker-compose up -d postgres redis

# 服务地址
# PostgreSQL: localhost:5432
# Redis: localhost:6379
```

**测试环境**:
- 云端 PostgreSQL (RDS)
- 云端 Redis (ElastiCache)

---

## 8. Must-Fix 项实施计划

### 8.1 Must-Fix 项概述

根据架构评审，以下 5 项必须在实施前或实施初期完成：

| 优先级 | Must-Fix 项 | 目标 Sprint | 负责人 |
|--------|-------------|-------------|--------|
| P0 | 1. 补充技术可行性报告 | Sprint 0 | 后端工程师 |
| P0 | 2. 优化 L3 聚合查询性能 | Sprint 2-3 | 后端工程师 |
| P0 | 3. 补充实施计划 | 本文档 | PM / 架构师 |
| P1 | 4. 完善数据恢复方案 | Sprint 6 | DevOps 工程师 |
| P1 | 5. 补充测试策略 | Sprint 1-6 | 测试工程师 |

---

### 8.2 Must-Fix 项详细计划

#### 8.2.1 P0-1: 补充技术可行性报告

**问题**: 缺少技术可行性验证

**目标 Sprint**: Sprint 0

**任务分解**:

| 任务 | 工作量 | 交付物 | 验收标准 |
|------|--------|--------|----------|
| StateMachine 并发安全性 POC | 3 天 | POC 代码 + 测试报告 | 并发场景下状态转换正确 |
| Redis Streams 性能压测 | 3 天 | 压测报告 | 吞吐量 > 10000 events/s |
| L3 并发队列原型验证 | 3 天 | 原型代码 + 性能数据 | 支持 > 1000 并发任务 |
| 模板参数化性能测试 | 2 天 | 性能报告 | 模板渲染 < 10ms |
| 编写技术可行性报告 | 2 天 | technical-feasibility.md | 通过架构评审 |

**技术细节**:

**StateMachine 并发安全性 POC**:
```python
# 测试场景: 100 个并发请求同时更新状态
async def test_concurrent_state_update():
    sm = OrchestratorStateMachine(...)
    instance = await sm.create_instance(...)

    # 100 个并发请求
    tasks = [
        sm.update_status(instance.id, WorkflowStatus.RUNNING, f"user_{i}")
        for i in range(100)
    ]
    results = await asyncio.gather(*tasks)

    # 只有一个应该成功
    success_count = sum(1 for success, _ in results if success)
    assert success_count == 1
```

**Redis Streams 性能压测**:
```bash
# 使用 redis-benchmark
redis-benchmark -t streams -n 100000 -c 100

# 目标: > 10000 ops/sec
```

**L3 并发队列原型**:
```python
# 测试场景: 创建 1000 个 L3 实例
async def test_spawn_1000_l3_instances():
    se = SpawnEngine(...)
    l2_instance = await create_l2_instance()

    # 1000 个并发创建请求
    tasks = [
        se.spawn_workflow(
            parent_id=l2_instance.id,
            template_id="bug_fix",
            parameters={"bug_id": f"BUG-{i}", "severity": "P0"}
        )
        for i in range(1000)
    ]
    results = await asyncio.gather(*tasks)

    # 验证队列正常工作
    assert sum(1 for r in results if r.status == WorkflowStatus.RUNNING) == 50  # max_concurrent
    assert sum(1 for r in results if r.status == WorkflowStatus.QUEUED) == 950
```

---

#### 8.2.2 P0-2: 优化 L3 聚合查询性能

**问题**: `get_children` 可能返回数千条记录，未考虑分页和增量聚合

**目标 Sprint**: Sprint 2-3

**任务分解**:

| 任务 | 工作量 | 交付物 | 验收标准 |
|------|--------|--------|----------|
| 设计增量聚合方案 | 1 天 | 设计文档 | 方案通过评审 |
| 实现增量聚合 (Redis) | 3 天 | AggregateCache | 聚合查询 < 100ms |
| 实现分页查询 | 2 天 | 分页接口 | 支持分页参数 |
| 性能压测 | 2 天 | 压测报告 | 1000 实例场景 < 100ms |

**技术方案**:

**方案 1: 增量聚合 (Redis HINCRBY)**
```python
class AggregateCache:
    """增量聚合缓存"""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def update_aggregate(
        self,
        parent_id: str,
        child_status: WorkflowStatus,
        delta: int = 1
    ):
        """增量更新聚合状态"""
        await self.redis.hincrby(
            f"agg:{parent_id}",
            child_status.value,
            delta
        )

    async def get_aggregate(self, parent_id: str) -> Dict[str, int]:
        """获取聚合状态"""
        data = await self.redis.hgetall(f"agg:{parent_id}")
        return {k.decode(): int(v) for k, v in data.items()}
```

**方案 2: 分页查询**
```python
async def get_children(
    self,
    parent_id: str,
    page: int = 1,
    page_size: int = 100
) -> PaginatedResult[WorkflowInstance]:
    """分页查询子实例"""
    offset = (page - 1) * page_size
    instances = await self.storage.load_children(
        parent_id,
        offset=offset,
        limit=page_size
    )
    total = await self.storage.count_children(parent_id)

    return PaginatedResult(
        items=instances,
        page=page,
        page_size=page_size,
        total=total
    )
```

---

#### 8.2.3 P0-3: 补充实施计划

**问题**: 缺少详细的 Sprint 规划

**目标 Sprint**: 本文档 (Stage 5)

**任务分解**:

| 任务 | 工作量 | 交付物 | 验收标准 |
|------|--------|--------|----------|
| 编写 Sprint 0-6 详细计划 | 3 天 | development-plan.md | 计划通过评审 |
| 识别关键路径和依赖 | 1 天 | WBS 图 | 依赖关系清晰 |
| 评估工作量 | 1 天 | 工作量估算表 | 估算合理 |

**交付物**: 本文档 (development-plan.md)

**验收标准**:
- [ ] 包含所有 Sprint 的详细任务分解
- [ ] 识别关键路径和依赖关系
- [ ] 工作量估算合理 (60-80 人天)
- [ ] 包含风险缓解措施
- [ ] 通过团队评审

---

#### 8.2.4 P1-4: 完善数据恢复方案

**问题**: Redis 故障可能导致数据丢失，未提供灾难恢复方案

**目标 Sprint**: Sprint 6

**任务分解**:

| 任务 | 工作量 | 交付物 | 验收标准 |
|------|--------|--------|----------|
| 设计 Redis 持久化方案 | 1 天 | 设计文档 | 方案通过评审 |
| 实现 Redis 持久化配置 | 1 天 | Redis 配置 | RDB + AOF 启用 |
| 实现数据备份脚本 | 2 天 | 备份脚本 | 自动备份到 S3 |
| 实现恢复演练 | 1 天 | 恢复文档 | 完成一次演练 |
| 实现 Redis 主从复制 | 2 天 | Redis 配置 | 1 主 2 从 |
| 实现 Redis Sentinel | 2 天 | Sentinel 配置 | 自动故障转移 |

**技术方案**:

**Redis 持久化**:
```conf
# redis.conf
# RDB 快照
save 900 1
save 300 10
save 60 10000

# AOF 持久化
appendonly yes
appendfsync everysec
```

**备份策略**:
```bash
#!/bin/bash
# 每小时全量备份到 S3
redis-cli --rdb /tmp/dump.rdb
aws s3 cp /tmp/dump.rdb s3://backups/redis/$(date +%Y%m%d-%H%M).rdb

# 增量备份 WAL 日志
redis-cli --aof-current
```

**恢复演练**:
```bash
# 1. 停止 Redis
systemctl stop redis

# 2. 恢复 RDB
aws s3 cp s3://backups/redis/latest.rdb /var/lib/redis/dump.rdb

# 3. 启动 Redis
systemctl start redis

# 4. 验证数据
redis-cli DBSIZE
```

**恢复目标**:
- RTO (Recovery Time Objective): < 1 小时
- RPO (Recovery Point Objective): < 5 分钟

---

#### 8.2.5 P1-5: 补充测试策略

**问题**: 未定义测试覆盖率目标，缺少测试示例

**目标 Sprint**: Sprint 1-6

**任务分解**:

| 任务 | 工作量 | 交付物 | 验收标准 |
|------|--------|--------|----------|
| 编写测试策略文档 | 1 天 | test-strategy.md | 策略通过评审 |
| 编写单元测试示例 | 2 天 | 测试用例 | 覆盖核心模块 |
| 编写集成测试示例 | 2 天 | 测试用例 | 覆盖核心流程 |
| 编写端到端测试示例 | 2 天 | 测试用例 | 完整流程测试 |
| 配置 CI 测试 | 1 天 | CI 配置 | 每次提交运行测试 |

**测试策略**:

**单元测试**:
- 框架: pytest + pytest-asyncio
- 覆盖率目标: > 80%
- Mock: pytest-mock

**集成测试**:
- 覆盖核心流程: L1→L2, L2→L3, L3→L2
- 使用 docker-compose 启动依赖

**端到端测试**:
- 模拟真实工作流执行
- 验证状态转换和事件传播

**CI 配置**:
```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: |
          pytest --cov=orchestrator --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

### 8.3 Must-Fix 项时间线

```
Sprint 0 (Week 1-2):
  ├─ P0-1: 技术可行性验证 ──────────────► 完成
  └─ P0-3: 实施计划 ────────────────────► 完成

Sprint 1 (Week 3-4):
  └─ P1-5: 单元测试策略 ────────────────► 完成

Sprint 2 (Week 5-6):
  ├─ P0-2: 增量聚合实现 ────────────────► 完成
  └─ P1-5: 集成测试策略 ────────────────► 完成

Sprint 3 (Week 7-8):
  ├─ P0-2: 聚合查询压测 ────────────────► 完成
  └─ P1-5: 端到端测试策略 ──────────────► 完成

Sprint 4-5 (Week 9-12):
  └─ P1-5: CI 测试配置 ─────────────────► 完成

Sprint 6 (Week 13-14):
  └─ P1-4: 数据恢复方案 ────────────────► 完成
```

---

### 8.4 Must-Fix 项验收标准

#### P0-1: 技术可行性报告

- [ ] StateMachine 并发安全性验证通过
- [ ] Redis Streams 性能压测通过 (吞吐量 > 10000 events/s)
- [ ] L3 并发队列原型验证通过 (支持 > 1000 实例)
- [ ] 模板参数化性能测试通过 (渲染 < 10ms)
- [ ] 技术可行性报告完成并通过评审

---

#### P0-2: L3 聚合查询性能优化

- [ ] 增量聚合实现完成 (Redis HINCRBY)
- [ ] 分页查询实现完成
- [ ] 聚合查询延迟 P95 < 100ms (1000 实例场景)
- [ ] 压测报告完成

---

#### P0-3: 实施计划

- [ ] Sprint 0-6 详细计划完成
- [ ] WBS 图完成
- [ ] 工作量估算完成 (60-80 人天)
- [ ] 风险管理计划完成
- [ ] 通过团队评审

---

#### P1-4: 数据恢复方案

- [ ] Redis 持久化配置完成 (RDB + AOF)
- [ ] 数据备份脚本完成
- [ ] 恢复演练完成 (至少 1 次)
- [ ] Redis 主从复制配置完成 (1 主 2 从)
- [ ] Redis Sentinel 配置完成
- [ ] RTO < 1 小时, RPO < 5 分钟

---

#### P1-5: 测试策略

- [ ] 测试策略文档完成
- [ ] 单元测试示例完成 (覆盖率 > 80%)
- [ ] 集成测试示例完成
- [ ] 端到端测试示例完成
- [ ] CI 测试配置完成
- [ ] 每次提交自动运行测试

---

## 9. 下一步行动

### 9.1 立即行动项 (本周)

1. **评审本开发计划** (1 天)
   - 团队评审开发计划
   - 收集反馈并调整
   - 确认最终版本

2. **组建开发团队** (1 天)
   - 确认团队成员
   - 分配角色和职责
   - 设置沟通渠道

3. **准备开发环境** (2 天)
   - 搭建本地开发环境
   - 配置 IDE 和工具
   - 准备依赖服务 (PostgreSQL, Redis)

4. **技术培训** (1 天)
   - FastAPI 培训
   - Redis Streams 培训
   - PostgreSQL JSONB 培训

---

### 9.2 Sprint 0 准备 (下周)

1. **启动 Sprint 0** (Day 1)
   - Sprint Planning 会议
   - 分配 Sprint 0 任务
   - 设置 Sprint 目标

2. **开始技术预研** (Day 2-10)
   - StateMachine 并发安全性 POC
   - Redis Streams 性能压测
   - L3 并发队列原型
   - 模板参数化性能测试

3. **编写技术可行性报告** (Day 8-10)
   - 汇总所有 POC 结果
   - 识别技术风险
   - 提出缓解措施

---

### 9.3 关键决策点

#### 决策点 1: 技术栈确认 (Sprint 0 前)

**需要确认**:
- [ ] Redis Streams vs RabbitMQ
- [ ] Celery vs 自研队列
- [ ] FastAPI vs 其他框架

**决策人**: 架构师 + 技术负责人

---

#### 决策点 2: 性能目标确认 (Sprint 0 结束)

**需要确认**:
- [ ] API 响应时间目标
- [ ] L3 并发数目标
- [ ] 事件吞吐量目标

**决策人**: 产品经理 + 架构师

---

#### 决策点 3: v2.0 兼容性范围 (Sprint 6 前)

**需要确认**:
- [ ] v2.0 API 兼容范围
- [ ] v2.0 数据迁移策略
- [ ] v2.0 废弃时间表

**决策人**: 产品经理 + 技术负责人

---

### 9.4 沟通计划

#### 每日沟通

- **每日站会**: 15 分钟，同步进度和阻塞
- **Slack 频道**: #orchestrator-v3 开发讨论
- **代码审查**: 每个 PR 必须 Review

---

#### 每周沟通

- **Sprint Planning**: Sprint 第一天，2 小时
- **Sprint Review**: Sprint 最后一天，1 小时
- **Sprint Retrospective**: Sprint 最后一天，1 小时
- **周报**: 每周五发送给干系人

---

#### 里程碑评审

- **M1: 技术可行性验证**: Week 2
- **M2: 核心状态机完成**: Week 4
- **M3: L3 任务创建完成**: Week 6
- **M4: 事件驱动完成**: Week 8
- **M5: API 集成完成**: Week 10
- **M6: 三层流程端到端完成**: Week 12
- **M7: v3.0 发布**: Week 14

---

## 10. 附录

### 10.1 术语表

| 术语 | 定义 |
|------|------|
| Level-1 (L1) | 项目级主流程，表达项目整体生命周期 |
| Level-2 (L2) | 部门级子流程，表达部门内部工作阶段 |
| Level-3 (L3) | 任务级流程，基于模板创建的具体任务 |
| StateMachine | 统一状态机，管理所有层级的状态 |
| TemplateEngine | 模板引擎，负责加载和渲染模板 |
| SpawnEngine | 任务创建引擎，负责创建 L3 实例 |
| EventBus | 事件总线，负责事件发布和订阅 |
| AggregationEngine | 聚合引擎，负责状态聚合 |
| GateEngine | 门禁引擎，负责人工决策流程 |
| POC | Proof of Concept，概念验证 |
| WBS | Work Breakdown Structure，工作分解结构 |
| RTO | Recovery Time Objective，恢复时间目标 |
| RPO | Recovery Point Objective，数据丢失目标 |

---

### 10.2 参考文档

#### 已评审文档

1. [PRD v1.0](./PRD.md) - 产品需求文档
2. [Architecture Design v1.0](./architecture-design.md) - 架构设计文档
3. [Architecture Review v1.0](./architecture-review.md) - 架构评审报告

#### 待补充文档

1. Technical Feasibility Report (Sprint 0 交付)
2. Test Strategy (Sprint 1-6 交付)
3. User Guide (Sprint 6 交付)
4. Migration Guide (Sprint 6 交付)

#### 外部参考

1. [Apache Airflow Documentation](https://airflow.apache.org/docs/)
2. [Temporal Documentation](https://docs.temporal.io/)
3. [Argo Workflows Documentation](https://argoproj.github.io/argo-workflows/)
4. [FastAPI Documentation](https://fastapi.tiangolo.com/)
5. [Redis Documentation](https://redis.io/docs/)

---

### 10.3 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-01-25 | 初稿 | Project Manager |

---

### 10.4 审批

| 角色 | 姓名 | 签名 | 日期 |
|------|------|------|------|
| 项目经理 | | | |
| 架构师 | | | |
| 技术负责人 | | | |
| 测试负责人 | | | |

---

**文档版本**: v1.0
**最后更新**: 2026-01-25
**维护者**: 项目管理团队
**审核者**: 待定

---

## 架构评审修订说明 (v1.1 新增章节)

### 修订概述

本开发计划 v1.1 针对 [Architecture Review Report](./development-plan-review.md) 中提出的 **8 项 required improvements** 进行全面修订。

### 8 项修订详情

#### P0 修订 (必须完成，Sprint 0 前完成)

| ID | 问题 | 修订内容 | 位置 |
|----|------|----------|------|
| **R1** | 资源级别未指定 | 明确 Senior/Mid-level 要求，详细技能矩阵 | 1.4 资源需求 |
| **R2** | 测试资源低估 | 12 → 22 人天，详细 Sprint 分配 | 7.2 工作量分配 |
| **R3** | 测试基础设施过晚 | 从 Sprint 6 移至 Sprint 0，新增 S0-6 | 2. Sprint 0 任务 |
| **R4** | Celery 决策框架缺失 | 新增 S0-7 评估任务，明确决策标准 | 2. Sprint 0 任务 |

#### P1 修订 (必须完成，Sprint 1 前完成)

| ID | 问题 | 修订内容 | 位置 |
|----|------|----------|------|
| **R5** | StateMachine 重构未规划 | Sprint 1 增加 0.5 周，采用三职责分离设计 | 2. Sprint 1 任务 |
| **R6** | Sprint 雪崩风险未管理 | 新增 R11 风险，范围削减协议，周五 checkpoint | 5.2 风险管理 |
| **R7** | 100% 可用性假设 | 调整有效利用率至 70%，更新工作量估算 | 1.4 资源需求 |
| **R8** | 培训不足 | 5 天 → 2 周 (20h)，增加实践 mini-project | 7.3.3 培训计划 |

### 修订影响分析

| 维度 | v1.0 | v1.1 | 变化 |
|------|------|------|------|
| **总周期** | 12-14 周 | 14-16 周 | +2 周 (预 Sprint 0) |
| **总工作量** | 112 人天 | 122 人天 | +10 人天 |
| **测试工作量** | 12 人天 | 22 人天 | +10 人天 |
| **Sprint 1** | 2 周 | 2.5 周 | +0.5 周 (重构) |
| **有效利用率** | 100% | 70% | -30% (更现实) |
| **风险数量** | 10 | 11 | +1 (Sprint 雪崩) |
| **P0 风险** | 5 | 6 | +1 (Sprint 雪崩) |

### 修订验收标准

**Phase 1: 预 Sprint 0 改进** (2 周) - 当前阶段:
- [ ] R1: 团队 seniority 明确 (Senior 已 hire/assign)
- [ ] R2: 测试预算已批准 (22 人天)
- [ ] R3: Sprint 0 包含测试基础设施任务
- [ ] R4: Celery 评估框架已定义
- [ ] R5: StateMachine 重构方案已批准
- [ ] R6: Sprint 雪崩缓解措施已定义
- [ ] R7: 有效利用率 (70%) 已反映在计划
- [ ] R8: 20 小时培训课程已准备

**Go/No-Go 决策点**: [ ] 日期: ___________________

---

## 总结

本开发计划 v1.1 为 LEE Orchestrator v3.0 三层流程架构提供了详细的实施路线图：

- **总周期**: 14-16 周 (含 2 周预 Sprint 0 改进 + 6-7 个 Sprint)
- **总工作量**: 122 人天 (含 20% 缓冲)
- **有效工作量**: 83 人天 (上限)
- **团队规模**: 3.5 人 (2 后端 + 1 测试 + 0.5 DevOps)
- **关键里程碑**: 8 个主要里程碑 (含 M0 改进完成)
- **Must-Fix 项**: 5 项架构评审要求全部覆盖
- **修订项**: 8 项架构评审改进全部完成

**v1.1 主要改进**:
1. ✅ 资源 seniority 明确 (R1)
2. ✅ 测试资源合理化 (R2)
3. ✅ 测试基础设施前移 (R3)
4. ✅ Celery 决策框架 (R4)
5. ✅ StateMachine 重构规划 (R5)
6. ✅ Sprint 雪崩风险缓解 (R6)
7. ✅ 有效利用率调整 (R7)
8. ✅ 培训计划扩展 (R8)

**预计交付成功率**: 75% (vs 60% without improvements)

本计划将随着项目进展持续更新，确保与实际情况保持同步。
