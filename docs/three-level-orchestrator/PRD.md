# LEE Orchestrator 三层流程架构 PRD

> **版本**: v1.0
> **状态**: Draft
> **创建日期**: 2026-01-25
> **目标版本**: LEE Orchestrator v3.0

---

## 目录

1. [需求概述](#1-需求概述)
2. [用户故事](#2-用户故事)
3. [功能详细说明](#3-功能详细说明)
4. [数据模型](#4-数据模型)
5. [API 设计](#5-api-设计)
6. [YAML Schema 扩展](#6-yaml-schema-扩展)
7. [验收标准](#7-验收标准)
8. [不确定决策点](#8-不确定决策点)
9. [风险评估](#9-风险评估)
10. [数据埋点建议](#10-数据埋点建议)

---

## 核心设计原则

> **设计原则声明**：本系统中，三层嵌套 workflow 的状态机转换（创建/执行/完成/暂停/恢复），**全部由 Orchestrator 统一管理**，任何 AI/Executor/人类工具都必须通过 Orchestrator 的 API 间接操作。

### 谁拥有「状态机」？

- **只有 Orchestrator** 拥有状态机
- Orchestrator 维护所有 workflow instance（L1/L2/L3）的状态表和依赖关系
- 状态机是单一事实来源（Single Source of Truth）

### 谁可以读状态？

- **PM Agent、Gate 会话、日志系统**都只能通过 Orchestrator 提供的 API/工具来读
- 不允许直接访问底层状态存储
- 所有读取操作必须通过统一的查询接口

### 谁可以改状态？

- **只有 Orchestrator 自己**可以修改状态：
  - 执行完一个 step → 根据结果修改该 step 和 workflow 的状态
  - spawn 子 workflow → 在自己这边记一条新的 instance
  - 子 workflow 完成 → 触发上层 workflow 的某个 step "完成"
- **不允许外部直接改状态**

### Executor / LLM / Skill / MCP 的职责边界

- **永远只接收一个 `StepExecutionRequest`**
- **干一件事，返回结果**
- **不直接碰状态机**
- Executor 只关注任务执行，不关心流程状态

---

## 落地原则（Implementation Checklist）

### 原则 1: 统一状态模型

```
所有 workflow（不管 L1/L2/L3）用同一套 StateModel 管理

统一字段：
- id, level, status, steps[], paused
- 区别只是：level: project/department/task
- 和少量特有字段（如 department 名）
```

### 原则 2: 事件驱动的层级触发

```
上层 触发 下层，只是"事件 + 条件"，不写死逻辑

- L1 → L2：kind: department_flow + department_workflow: qa_main
- L2 → L3：on_event: new_bug_logged → spawn: bug_fix

具体怎么 spawn / 等待完成，统统在 orchestrator 内部用统一机制做
不在 spec 之外硬编码
```

### 原则 3: 状态变更也是事件

```
暂停 / 恢复 / Gate 决策也当成"状态机事件"

- pause_workflow / resume_workflow / gate_approve 都走 orchestrator 的 API
- 不允许外部直接改某个 instance 的 status 字段
- 所有状态变更必须通过 Orchestrator 验证和执行
```

### 原则 4: 窄工具接口（Narrow API）

```
PM、Gate、其它 AI 只通过「窄工具」和 orchestrator 对话

PM 工具：
- orchestrator_get_state(level, instance_id)
- orchestrator_run_step(instance_id, step_id)

Gate 工具：
- gate_show(instance_id, gate_id)
- gate_decide(instance_id, gate_id, decision)

没有"跳级"操作，所有调用都经过 Orchestrator 验证
```

---

## 1. 需求概述

### 1.1 背景与目标

#### 当前问题

LEE Orchestrator v2.0 在处理复杂工作流时存在以下限制：

1. **单一工作流概念**：无法区分项目级、部门级、任务级的流程
2. **并发模型不清晰**：容易导致状态管理混乱
3. **暂停/恢复粒度不明确**：缺乏细粒度的流程控制
4. **模板复用缺失**：无法基于模板快速创建大量相似任务实例

#### 目标

引入**三层流程架构**，支持：

- **清晰的责任分层**：项目、部门、任务三级流程
- **明确的并发模型**：每层有独立的并发规则
- **细粒度暂停/恢复**：精确到单个流程实例
- **模板复用机制**：支持 Level-3 工作流模板化

### 1.2 核心价值主张

| 维度 | 现状 (v2.0) | 目标 (v3.0) | 业务价值 |
|------|-------------|-------------|----------|
| 流程层级 | 单一工作流 | 三层分层架构 | 职责清晰，易于管理 |
| 并发控制 | 不明确 | 每层独立规则 | 避免状态冲突 |
| 模板复用 | 无 | Level-3 模板库 | 快速创建任务实例 |
| 暂停粒度 | 全局 | 实例级别 | 精确控制流程 |
| PM 关注点 | 所有流程 | 仅 Level-1 | 聚焦战略决策 |

### 1.3 用户画像

#### 用户 1: PM（产品经理）

**角色**：项目负责人
**关注点**：
- 项目整体进度
- 跨部门协作
- 里程碑达成

**使用场景**：
- 创建和管理 Level-1 主流程
- 监控各部门 Level-2 子流程状态
- 处理跨部门阻塞和决策

#### 用户 2: 部门负责人

**角色**：QA Lead、Dev Lead、Design Lead 等
**关注点**：
- 本部门工作流执行
- 任务分配和调度
- 质量把关

**使用场景**：
- 管理 Level-2 部门子流程
- 触发 Level-3 任务实例
- 审批本部门工作流中的关键节点

#### 用户 3: 执行者（AI Agent + 人类开发者）

**角色**：实际执行任务的角色
**关注点**：
- 明确的任务目标
- 完成所需的资源
- 任务依赖关系

**使用场景**：
- 执行 Level-3 任务流程
- 报告任务进度
- 请求暂停/恢复

### 1.4 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     Level-1: 公司级主流程                          │
│                   Project Master Workflow                         │
│                  (每项目仅 1 实例，阶段串行)                         │
│  需求 → 设计 → 开发 → 测试 → 上线 → 运营                              │
└─────────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Level-2     │    │  Level-2     │    │  Level-2     │
│  PRD 部门    │    │  Dev 部门    │    │  QA 部门     │
│  子流程      │    │  子流程      │    │  子流程      │
│ (每部门1实例) │    │ (每部门1实例) │    │ (每部门1实例) │
│ 阶段串行      │    │ 阶段串行      │    │ 阶段串行      │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
  可挂 N 个 Level-3    可挂 N 个 Level-3    可挂 N 个 Level-3
  ┌─────────┐         ┌─────────┐         ┌─────────┐
  │ Bug Fix │         │ Feature │         │ Test    │
  │ Task #1 │         │ Task #1 │         │ Task #1 │
  └─────────┘         └─────────┘         └─────────┘
  ┌─────────┐         ┌─────────┐         ┌─────────┐
  │ Bug Fix │         │ Feature │         │ Test    │
  │ Task #2 │  ...    │ Task #2 │  ...    │ Task #2 │  ...
  └─────────┘         └─────────┘         └─────────┘
  (基于模板创建)       (基于模板创建)       (基于模板创建)
  (允许大量并发)       (允许大量并发)       (允许大量并发)
```

---

## 2. 用户故事

### US-1: PM 创建项目主流程

**作为** PM
**我想要** 为新项目创建 Level-1 主流程
**以便** 明确项目的整体阶段和里程碑

**验收标准**：
- [ ] 可以定义项目的所有阶段（需求、设计、开发、测试、上线、运营）
- [ ] 可以为每个阶段指定负责的部门
- [ ] 可以查看所有 Level-2 子流程的聚合状态
- [ ] 当所有部门完成当前阶段后，自动进入下一阶段

### US-2: 部门负责人管理子流程

**作为** QA Lead
**我想要** 在 Level-2 测试子流程中触发多个 Level-3 Bug 修复任务
**以便** 并行处理多个缺陷

**验收标准**：
- [ ] 可以基于 `bug_fix.yaml` 模板创建多个任务实例
- [ ] 每个任务实例有独立的状态（NEW → TRIAGED → FIXING → VERIFIED → CLOSED）
- [ ] 可以查看所有 Bug 任务的整体进度
- [ ] 当所有 P0/P1 Bug 关闭后，可以继续测试流程

### US-3: 执行者处理任务

**作为** 开发者
**我想要** 暂停我正在处理的 Bug 修复任务
**以便** 等待额外的需求澄清

**验收标准**：
- [ ] 可以暂停我的任务实例（不影响其他任务）
- [ ] 暂停后任务状态变更为 `PAUSED`
- [ ] 收到需求澄清后，可以恢复任务
- [ ] 恢复后任务从中断点继续执行

### US-4: PM 监控跨部门协作

**作为** PM
**我想要** 查看哪些 Level-2 子流程被阻塞
**以便** 协调解决跨部门依赖问题

**验收标准**：
- [ ] 可以看到每个 Level-2 子流程的状态（运行中/阻塞/完成）
- [ ] 可以看到阻塞原因（如：等待其他部门输出）
- [ ] 可以查看阻塞的持续时间
- [ ] 可以收到阻塞超时的告警

### US-5: 复用任务模板

**作为** QA Lead
**我想要** 使用预定义的 Bug 处理模板
**以便** 快速创建标准化的 Bug 修复流程

**验收标准**：
- [ ] 可以从模板库中选择 `bug_fix.yaml` 模板
- [ ] 创建时传入参数（bug_id、severity、description）
- [ ] 生成的任务实例自动包含标准流程步骤
- [ ] 可以覆盖模板中的默认配置

---

## 3. 功能详细说明

### 3.1 三层流程架构

#### 3.1.1 Level-1: 公司级主流程（Project Master Workflow）

**定义**：表达项目从立项到运营的整体生命周期

**特征**：
- **唯一性**：每个项目仅 1 个实例
- **串行阶段**：阶段按顺序执行（需求 → 设计 → 开发 → 测试 → 上线 → 运营）
- **部门触发**：每个阶段通过 `department_flow` 类型的步骤触发 Level-2 子流程
- **PM 关注**：PM Agent 只关注这一层，不深入部门内部细节

**YAML 示例**：

```yaml
id: project_master_workflow
level: 1
kind: project_master
version: v1

metadata:
  name: "Texas Hold'em Platform Development"
  project_id: "proj-001"
  owner: "pm_agent@v1"

phases:
  - id: phase_requirements
    name: "需求阶段"
    department: prd
    steps:
      - id: trigger_prd_workflow
        type: department_flow
        target_level: 2
        target_department: prd
        wait_for_completion: true

  - id: phase_design
    name: "设计阶段"
    department: design
    depends_on: [phase_requirements]
    steps:
      - id: trigger_design_workflow
        type: department_flow
        target_level: 2
        target_department: design

  # ... 更多阶段
```

**状态机**：

```
INIT → REQUIREMENTS → DESIGN → DEVELOPMENT → TESTING → DEPLOYMENT → OPERATIONS → COMPLETED
       ↓              ↓           ↓              ↓            ↓             ↓
     [L2-PRD]      [L2-Design] [L2-Dev]      [L2-QA]     [L2-Ops]      [L2-Maintenance]
```

#### 3.1.2 Level-2: 部门级子流程（Department Workflow）

**定义**：每个部门在项目中的主子流程，表达部门内部的工作阶段

**特征**：
- **单实例**：每个部门每项目仅 1 个主子流程实例
- **两种模式**：
  - `mono-department`：单部门内部流程（如 QA 的测试主流程）
  - `cross-department`：跨部门协作流程（如 PRD → Design）
- **串行阶段**：阶段按顺序执行
- **可挂 L3 任务**：每个阶段可以挂载多个 Level-3 任务，允许并发执行

**YAML 示例**：

```yaml
id: qa_department_workflow
level: 2
kind: department
version: v1

metadata:
  name: "QA 测试主流程"
  project_id: "proj-001"
  department: qa
  mode: mono-department
  owner: "qa_lead"

phases:
  - id: phase_test_planning
    name: "测试规划"
    steps:
      - id: create_test_plan
        run: agent.qa.planner
        outputs:
          - path: "qa/test-plan.md"

  - id: phase_test_execution
    name: "测试执行"
    depends_on: [phase_test_planning]
    spawn_tasks:
      - template: bug_fix
        trigger_on: bug_detected
        max_concurrent: 10

  # ... 更多阶段
```

**状态机**：

```
INIT → PLANNING → EXECUTION → DEFECT_CONVERGENCE → REPORTING → COMPLETED
                  ↓
              [挂载 L3 任务]
               ┌────┴────┐
         [Bug #1]  [Bug #2]  ...  [Bug #N]
```

#### 3.1.3 Level-3: 任务级流程（Task Workflow）

**定义**：基于可复用模板创建的具体任务实例

**特征**：
- **模板驱动**：从 `ai-spec/workflows/templates/` 加载模板
- **多实例**：同一模板可以创建大量并发实例
- **参数化**：支持传入参数（如 `{{ bug_id }}`、`{{ severity }}`）
- **独立状态**：每个实例有独立的生命周期

**模板示例**：`ai-spec/workflows/templates/bug_fix.yaml`

```yaml
id: bug_fix_template
level: 3
kind: template
version: v1

metadata:
  name: "Bug 修复流程模板"
  category: bug_lifecycle

parameters:
  - name: bug_id
    type: string
    required: true
  - name: severity
    type: enum
    values: [P0, P1, P2, P3]
    required: true
  - name: description
    type: string
    required: true

stages:
  - id: triage
    name: "分流"
    run: agent.qa.bug_triager
    inputs:
      - bug_id: "{{ bug_id }}"
    outputs:
      - path: "bugs/{{ bug_id }}/triage.yaml"

  - id: fix
    name: "修复"
    depends_on: [triage]
    run: agent.dev.bug_fixer
    condition: "{{ severity }} IN [P0, P1]"

  # ... 更多阶段
```

**实例化示例**：

```yaml
# Spawn 参数
template: bug_fix
parameters:
  bug_id: "BUG-2026-0001"
  severity: "P0"
  description: "用户无法登录"
```

**状态机**：

```
NEW → TRIAGED → ASSIGNED → FIXING → FIXED → VERIFYING → VERIFIED → CLOSED
```

### 3.2 并发模型

#### 3.2.1 Level-1 并发规则

```
规则：
- 每个项目 1 个实例
- 阶段串行执行（不可并行）
- 不同项目的主流程可以并行

状态约束：
- 同时只能有 1 个 phase 处于 active 状态
- 当前 phase 完成后才能进入下一 phase
```

**示例**：

```
Project A: [需求 ✓] → [设计 →] → [开发] → [测试] → [上线]
                         ↑
                    当前阶段

Project B: [需求 ✓] → [设计 ✓] → [开发 →] → [测试] → [上线]
                                   ↑
                              当前阶段
```

#### 3.2.2 Level-2 并发规则

```
规则：
- 每个部门每项目 1 个实例
- 阶段串行执行
- 同一阶段内可挂载多个 L3 任务（允许并行）

状态约束：
- 同时只能有 1 个 phase 处于 active 状态
- 同一 phase 内的 L3 任务可以并行执行
- 不同部门的 L2 可以并行
```

**示例**：

```
QA Department L2:
[规划 ✓] → [执行 →] → [收敛] → [报告]
            ↑
        当前阶段

挂载的 L3 任务:
[Bug #1: TRIAGED]  [Bug #2: FIXING]  [Bug #3: VERIFYING]
     并行执行
```

#### 3.2.3 Level-3 并发规则

```
规则：
- 基于模板创建多个实例
- 允许大量并发（100+ 实例）
- 每个实例独立状态机

状态约束：
- 实例之间无依赖（除非显式定义）
- 并发数量可配置（默认 50）
- 超过并发限制时排队
```

**示例**：

```
Bug Fix 实例:
[Bug #1: FIXING]  [Bug #2: VERIFYING]  [Bug #3: TRIAGED]
[Bug #4: NEW]     [Bug #5: ASSIGNED]   [Bug #6: FIXED]
     ↑              ↑                 ↑
  并行执行中

排队等待:
[Bug #7]  [Bug #8]  ...  [Bug #100]
```

### 3.3 暂停/恢复机制

#### 3.3.1 设计原则

```
粒度：
- 暂停某个 workflow 实例（不是整个系统）
- 每个实例有 paused: bool 字段

实现方式：
- 通过 Gate 实现暂停/恢复
- 不是 PM Agent 直接改 state

权限控制：
- Level-1: 项目 owner / 高级 PM
- Level-2: 项目 PM + 部门负责人
- Level-3: 任务 owner（AI + 人类）
```

#### 3.3.2 暂停操作

**触发方式**：

1. **人工暂停**：
   ```bash
   # CLI 命令
   lee workflow pause \
     --level 3 \
     --instance-id "bug-fix-BUG-2026-0001" \
     --reason "等待需求澄清"
   ```

2. **自动暂停**（通过 Gate）：
   ```yaml
   gates:
     - id: wait_for_requirement_clarification
       type: pause
       condition: "category == requirement"
       action: pause_instance
   ```

**暂停后的行为**：

```
暂停时状态转换：
- BEFORE: [FIXING]
- PAUSE →   [FIXING_PAUSED]
- 效果:
  - 停止执行下一步
  - 保留当前状态
  - 可以被恢复

不允许暂停的状态：
- COMPLETED
- FAILED
- CANCELLED
```

#### 3.3.3 恢复操作

**触发方式**：

1. **人工恢复**：
   ```bash
   lee workflow resume \
     --level 3 \
     --instance-id "bug-fix-BUG-2026-0001" \
     --note "已收到需求澄清，继续修复"
   ```

2. **事件触发恢复**：
   ```yaml
   on_event:
     - event: requirement_clarified
       action: resume_instance
   ```

**恢复后的行为**：

```
恢复时状态转换：
- BEFORE: [FIXING_PAUSED]
- RESUME → [FIXING]
- 效果:
  - 从暂停点继续执行
  - 检查依赖是否仍然满足
  - 如果依赖不满足，保持暂停
```

#### 3.3.4 权限矩阵

| 操作 | Level-1 | Level-2 | Level-3 |
|------|---------|---------|---------|
| 暂停 | 项目 owner, 高级 PM | 项目 PM, 部门 lead | 任务 owner |
| 恢复 | 项目 owner, 高级 PM | 项目 PM, 部门 lead | 任务 owner |
| 查看状态 | PM, 部门 lead, 任务 owner | PM, 部门 lead, 任务 owner | 任务 owner |
| 取消 | 项目 owner | 项目 PM | - |

### 3.4 层级交互

#### 3.4.1 L1 → L2 触发机制

**触发方式**：`department_flow` 类型的步骤

```yaml
# Level-1 workflow.yaml
steps:
  - id: trigger_qa_workflow
    type: department_flow
    target_level: 2
    target_department: qa
    inputs:
      - release_manifest: "$output.dev.release_manifest"
    wait_for_completion: true
    on_completion:
      emit_event: qa_workflow_completed
```

**交互流程**：

```
Level-1                          Level-2 (QA)
   │                                 │
   ├─► 触发 department_flow ────────►│
   │                                 │
   ├─► 等待完成  ◄──────────────────┤───── 发送完成事件
   │                                 │
   ├─► 收到 completion event         │
   │                                 │
   ├─► 进入下一阶段                   │
```

#### 3.4.2 L2 → L3 Spawn 机制

**触发方式**：`spawn_tasks` 配置 + `on_event`

```yaml
# Level-2 workflow.yaml
phases:
  - id: test_execution
    spawn_tasks:
      - template: bug_fix
        trigger_on: bug_detected
        max_concurrent: 10
        queue_when_full: true

# 或通过事件触发
on_event:
  - event: bug_detected
    action: spawn
    template: bug_fix
    parameters:
      bug_id: "$event.bug_id"
      severity: "$event.severity"
```

**Spawn 流程**：

```
Level-2 (QA)                    Level-3 (Bug Fix)
   │                                │
   ├─► 检测到事件 (bug_detected)    │
   │                                │
   ├─► 加载模板 (bug_fix.yaml) ────►│
   │                                │
   ├─► 传入参数                     │
   │   ├─ bug_id: "BUG-001"         │
   │   ├─ severity: "P0"            │
   │   └─ description: "..."        │
   │                                │
   ├─► 创建实例 ◄───────────────────┤───── 实例创建完成
   │                                │
   ├─► 监控实例状态                 │
   │                                │
   ├─► 收集实例输出                 │
```

#### 3.4.3 状态聚合（L3 → L2 → L1）

**聚合规则**：

```
Level-3 → Level-2:
- 当所有 L3 任务完成时，L2 phase 可进入下一阶段
- 可配置完成条件（如：所有 P0/P1 完成）

Level-2 → Level-1:
- 当所有 L2 子流程完成时，L1 phase 可进入下一阶段
- 可配置完成条件（如：至少 3 个部门通过）
```

**配置示例**：

```yaml
# Level-2: 定义 L3 完成条件
phases:
  - id: test_execution
    completion_criteria:
      all: false  # 不需要所有 L3 完成
      rules:
        - name: "P0/P1 必须完成"
          condition: "count(l3_tasks.where(status == COMPLETED && severity IN [P0, P1])) == count(l3_tasks.where(severity IN [P0, P1]))"
        - name: "P2/P3 可部分完成"
          condition: "percentage(l3_tasks.where(status == COMPLETED && severity IN [P2, P3])) >= 80"

# Level-1: 定义 L2 完成条件
phases:
  - id: development
    completion_criteria:
      all: true  # 所有 L2 必须完成
      allowed_to_skip: []
```

### 3.5 模板系统

#### 3.5.1 模板定义

**位置**：`ai-spec/workflows/templates/`

**目录结构**：

```
ai-spec/workflows/templates/
├── bug_fix.yaml               # Bug 修复模板
├── feature_development.yaml   # 功能开发模板
├── test_execution.yaml        # 测试执行模板
├── code_review.yaml           # Code Review 模板
└── deployment.yaml            # 部署模板
```

**模板 Schema**：

```yaml
id: "{{ template_id }}"
level: 3
kind: template
version: v1

metadata:
  name: "模板名称"
  category: "类别"
  description: "描述"
  author: "作者"
  created_at: "2026-01-25"

# 参数定义
parameters:
  - name: "参数名"
    type: "string | number | enum | boolean"
    required: true | false
    default: "默认值"
    description: "参数描述"

# 阶段定义
stages:
  - id: "stage_id"
    name: "阶段名称"
    run: "agent_id@version"
    depends_on: ["previous_stage"]
    condition: "{{ 参数名 }} == 'value'"
    inputs:
      - name: "输入名"
        value: "{{ 参数名 }}"
    outputs:
      - path: "output/{{ 参数名 }}.yaml"
        required: true

# 事件定义
on_event:
  - event: "event_name"
    action: "spawn | pause | resume | complete"
    target: "target_stage"

# 完成条件
completion:
  required_outputs:
    - "output/final.yaml"
  success_criteria:
    - "status == VERIFIED"
```

#### 3.5.2 参数化

**支持的表达式**：

```yaml
# 简单变量
{{ bug_id }}

# 嵌套属性
{{ event.bug.severity }}

# 条件表达式
{{ severity == 'P0' ? 'urgent' : 'normal' }}

# 默认值
{{ description | default('No description') }}

# 列表操作
{{ tags | join(',') }}

# 时间戳
{{ now() }}
{{ now() | date_format('%Y-%m-%d') }}
```

**示例**：

```yaml
# 模板
parameters:
  - name: bug_id
    type: string
  - name: severity
    type: enum

stages:
  - id: triage
    inputs:
      - bug_id: "{{ bug_id }}"
      - priority: "{{ severity == 'P0' ? 'urgent' : 'normal' }}"
    outputs:
      - path: "bugs/{{ bug_id }}/triage-{{ now() | date_format('%Y%m%d') }}.yaml"
```

#### 3.5.3 模板库管理

**版本控制**：

```yaml
# bug_fix.yaml
metadata:
  version: v2  # 模板版本
  deprecated_by: v3  # 如果被废弃

changelog:
  - version: v3
    date: 2026-01-25
    changes:
      - "添加 severity 参数"
      - "增加 debug_agent 诊断步骤"
```

**模板继承**：

```yaml
# bug_fix_p0.yaml (继承自 bug_fix.yaml)
extends: bug_fix.yaml

parameters:
  - name: bug_id
  - name: severity
    default: "P0"  # 覆盖默认值

stages:
  - id: debug_analysis  # 额外步骤
    name: "P0 Bug 必须诊断"
    run: agent.qa.debug_agent
```

---

## 4. 数据模型

### 4.1 统一状态模型（Core State Machine）

> **设计约束**：所有层级（L1/L2/L3）使用同一套状态模型，通过 `level` 字段区分。

```python
@dataclass
class WorkflowInstance:
    """统一的工作流实例模型"""

    # === 通用字段（所有层级共享） ===
    id: str                              # 实例 ID（全局唯一）
    workflow_id: str                     # 工作流定义 ID
    level: Literal[1, 2, 3]              # 层级标识
    kind: Literal["project_master", "department", "task"]
    project_id: str                      # 所属项目
    parent_id: Optional[str]             # 父实例 ID（L2->L3）
    status: WorkflowStatus               # 统一状态枚举
    paused: bool                         # 是否暂停
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # === 步骤和阶段 ===
    current_stage: Optional[str]         # 当前阶段/步骤
    stage_history: List[StageHistory]   # 阶段历史
    steps: Dict[str, StepState]         # 步骤状态表

    # === 输出和日志 ===
    outputs: List[OutputArtifact]
    logs: List[EventLog]

    # === 层级特有字段（通过 Union 类型或 Optional 实现） ===
    # Level-1 专属
    phases: Optional[List[PhaseDef]] = None
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
```

### 4.2 状态枚举（统一）

```python
class WorkflowStatus(Enum):
    """统一的工作流状态枚举"""
    INIT = "init"                    # 初始化
    RUNNING = "running"              # 运行中
    PAUSED = "paused"                # 已暂停（由其他状态 + paused=true 组合）
    COMPLETED = "completed"          # 已完成
    FAILED = "failed"                # 已失败
    CANCELLED = "cancelled"          # 已取消

class StepStatus(Enum):
    """步骤状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    GATE_PENDING = "gate_pending"    # 等待人工门禁
```

### 4.3 状态转换规则（由 Orchestrator 强制执行）

```python
# 状态转换矩阵
# 只有 Orchestrator 可以执行这些转换
ALLOWED_TRANSITIONS = {
    WorkflowStatus.INIT: [WorkflowStatus.RUNNING],
    WorkflowStatus.RUNNING: [WorkflowStatus.PAUSED, WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED],
    WorkflowStatus.PAUSED: [WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED],
    # COMPLETED, FAILED, CANCELLED 是终态
}

# 暂停是修饰符，不是独立状态
# 实际状态 = status + paused
# 例如：RUNNING + paused=true = "运行中但已暂停"
```

### 4.4 Orchestrator 核心接口设计

```python
class OrchestratorCore:
    """Orchestrator 核心接口

    这是唯一可以修改状态机的组件。
    所有外部调用必须通过这些窄接口。
    """

    # === 状态查询（只读） ===
    def get_state(self, instance_id: str) -> WorkflowInstance:
        """查询实例状态"""
        pass

    def get_children(self, instance_id: str) -> List[WorkflowInstance]:
        """查询子实例"""
        pass

    def get_aggregate_state(self, instance_id: str) -> AggregateState:
        """查询聚合状态（L2->L3, L1->L2）"""
        pass

    # === 步骤执行 ===
    def run_step(self, instance_id: str, step_id: str, executor: str) -> StepResult:
        """执行单个步骤

        这是执行步骤的唯一入口点：
        1. 验证实例状态和步骤依赖
        2. 更新步骤状态为 IN_PROGRESS
        3. 调用 executor 执行
        4. 根据结果更新步骤和实例状态
        5. 触发后续步骤或子工作流
        """
        pass

    # === 工作流生命周期 ===
    def create_workflow(self, workflow_id: str, level: int,
                       parameters: Dict, parent_id: Optional[str]) -> WorkflowInstance:
        """创建工作流实例

        只有 Orchestrator 可以创建实例：
        - L1 实例：由 PM 通过 orchestrator_run_step 间接触发
        - L2 实例：由 L1 的 department_flow 步骤自动触发
        - L3 实例：由 L2 的 spawn 事件触发
        """
        pass

    def spawn_workflow(self, parent_id: str, template_id: str,
                      parameters: Dict) -> WorkflowInstance:
        """Spawn 子工作流

        这是创建 L3 实例的唯一方式：
        - 验证父实例状态
        - 加载模板
        - 渲染参数
        - 创建实例
        - 建立父子关联
        """
        pass

    # === 状态变更事件 ===
    def pause_workflow(self, instance_id: str, reason: str, operator: str) -> bool:
        """暂停工作流

        通过 Gate 决策触发：
        - 验证权限
        - 设置 paused=true
        - 记录暂停原因和时间
        - 如果配置了级联暂停，则暂停所有子实例
        """
        pass

    def resume_workflow(self, instance_id: str, note: str, operator: str) -> bool:
        """恢复工作流

        通过 Gate 决策或事件触发：
        - 验证权限
        - 设置 paused=false
        - 检查依赖是否仍然满足
        - 如果依赖不满足，保持暂停
        """
        pass

    def complete_step(self, instance_id: str, step_id: str,
                      outputs: List[Artifact]) -> bool:
        """完成步骤

        由 Executor 调用（通过 Orchestrator 提供的工具）：
        - 验证步骤状态
        - 更新步骤状态为 COMPLETED
        - 触发步骤验证
        - 如果有门禁，进入 GATE_PENDING
        - 如果步骤完成，检查是否触发下一步骤
        - 如果是最后一步，检查工作流是否完成
        """
        pass

    def gate_decision(self, instance_id: str, gate_id: str,
                     decision: GateDecision, operator: str) -> bool:
        """门禁决策

        通过 Gate 会话调用：
        - 验证门禁状态
        - 记录决策
        - 根据决策更新工作流状态
        - 如果是 APPROVE，触发下一步骤
        - 如果是 REJECT，工作流可能失败或回退
        """
        pass

    # === 内部状态机（不对外暴露） ===
    def _update_status(self, instance_id: str, new_status: WorkflowStatus):
        """内部方法：更新状态"""
        pass

    def _trigger_next_step(self, instance_id: str):
        """内部方法：触发下一步骤"""
        pass

    def _check_workflow_completion(self, instance_id: str) -> bool:
        """内部方法：检查工作流是否完成"""
        pass

    def _propagate_completion_to_parent(self, instance_id: str):
        """内部方法：向父实例传播完成事件"""
        pass
```

### 4.5 WorkflowTemplate（模板）

```yaml
id: string                           # 模板 ID
name: string
category: string
description: string
version: string
author: string
created_at: timestamp
updated_at: timestamp
deprecated: boolean
deprecated_by: string | null         # 废弃后的替代版本

# 参数定义
parameters: array[ParameterDefinition]

# 阶段定义
stages: array[StageDefinition]

# 事件处理
on_event: array[EventHandler]

# 完成条件
completion: CompletionCriteria

# 继承
extends: string | null               # 继承的模板 ID
overrides: object                    # 覆盖的字段
```

### 4.3 层级关联关系

```
Project (proj-001)
  └─ Level-1 Instance (l1-proj-001)
      ├─ Phase: requirements
      │   └─ Level-2 Instance (l2-prd-proj-001)
      │       └─ Spawned Tasks: []
      ├─ Phase: design
      │   └─ Level-2 Instance (l2-design-proj-001)
      │       ├─ Spawned Tasks:
      │       │   ├─ Level-3 Instance (l3-feature-001)
      │       │   └─ Level-3 Instance (l3-feature-002)
      ├─ Phase: development
      │   └─ Level-2 Instance (l2-dev-proj-001)
      │       └─ Spawned Tasks: []
      └─ Phase: testing
          └─ Level-2 Instance (l2-qa-proj-001)
              ├─ Spawned Tasks:
              │   ├─ Level-3 Instance (l3-bug-001) [template: bug_fix]
              │   ├─ Level-3 Instance (l3-bug-002) [template: bug_fix]
              │   └─ Level-3 Instance (l3-bug-003) [template: bug_fix]
              └─ Completion Criteria:
                  - All P0/P1 bugs completed
                  - 80% P2/P3 bugs completed
```

---

## 5. API 设计

### 5.1 Workflow 管理

```
# 创建工作流实例
POST /api/v3/workflows
Body:
{
  "workflow_id": "bug_fix",
  "level": 3,
  "template_id": "bug_fix",
  "parameters": {
    "bug_id": "BUG-001",
    "severity": "P0"
  },
  "parent_id": "l2-qa-proj-001"
}

# 查询工作流状态
GET /api/v3/workflows/{instance_id}

# 暂停工作流
POST /api/v3/workflows/{instance_id}/pause
Body:
{
  "reason": "等待需求澄清"
}

# 恢复工作流
POST /api/v3/workflows/{instance_id}/resume
Body:
{
  "note": "已收到澄清，继续"
}

# 取消工作流
POST /api/v3/workflows/{instance_id}/cancel
Body:
{
  "reason": "不再需要"
}
```

### 5.2 模板管理

```
# 列出所有模板
GET /api/v3/templates

# 获取模板详情
GET /api/v3/templates/{template_id}

# 创建模板
POST /api/v3/templates
Body:
{
  "id": "bug_fix",
  "name": "Bug 修复流程",
  "category": "bug_lifecycle",
  "parameters": [...],
  "stages": [...]
}

# 更新模板
PUT /api/v3/templates/{template_id}

# 删除模板
DELETE /api/v3/templates/{template_id}
```

### 5.3 层级查询

```
# 获取项目所有 Level-1 实例
GET /api/v3/projects/{project_id}/level1

# 获取 Level-1 的所有 Level-2 子流程
GET /api/v3/workflows/{l1_instance_id}/children

# 获取 Level-2 的所有 Level-3 任务
GET /api/v3/workflows/{l2_instance_id}/tasks

# 获取层级树
GET /api/v3/projects/{project_id}/tree
Response:
{
  "level1": {
    "id": "l1-proj-001",
    "status": "RUNNING",
    "current_phase": "testing",
    "children": [
      {
        "id": "l2-qa-proj-001",
        "department": "qa",
        "status": "RUNNING",
        "tasks": [
          {
            "id": "l3-bug-001",
            "template": "bug_fix",
            "status": "FIXING"
          }
        ]
      }
    ]
  }
}
```

### 5.4 状态聚合

```
# 获取 Level-2 聚合状态
GET /api/v3/workflows/{l2_instance_id}/aggregate
Response:
{
  "total_tasks": 100,
  "by_status": {
    "COMPLETED": 80,
    "RUNNING": 15,
    "PAUSED": 3,
    "FAILED": 2
  },
  "by_severity": {
    "P0": {"total": 10, "completed": 10},
    "P1": {"total": 20, "completed": 18},
    "P2": {"total": 70, "completed": 52}
  },
  "completion_criteria_met": true
}

# 获取 Level-1 聚合状态
GET /api/v3/workflows/{l1_instance_id}/aggregate
Response:
{
  "current_phase": "testing",
  "phases": [
    {"id": "requirements", "status": "COMPLETED"},
    {"id": "design", "status": "COMPLETED"},
    {"id": "development", "status": "COMPLETED"},
    {"id": "testing", "status": "RUNNING"}
  ],
  "department_status": {
    "prd": "COMPLETED",
    "design": "COMPLETED",
    "dev": "COMPLETED",
    "qa": "RUNNING"
  }
}
```

---

## 6. YAML Schema 扩展

### 6.1 Level-1 新增字段

```yaml
# Level-1 workflow.yaml
id: project_master_workflow
level: 1  # 新增：标识层级
kind: project_master  # 新增：标识类型

# 新增：阶段定义
phases:
  - id: phase_id
    name: "阶段名称"
    department: "负责部门"
    depends_on: ["prev_phase_id"]  # 阶段依赖

    steps:
      - id: step_id
        type: department_flow  # 新增：触发 L2
        target_level: 2  # 新增：目标层级
        target_department: "qa"  # 新增：目标部门
        wait_for_completion: true  # 新增：等待完成

        inputs:
          - release_manifest: "$output.dev.release_manifest"

        on_completion:  # 新增：完成回调
          emit_event: "qa_workflow_completed"
          next_phase: "deployment"

# 新增：完成条件
completion:
  all_phases_required: true
  allowed_to_skip: []
```

### 6.2 Level-2 新增字段

```yaml
# Level-2 workflow.yaml
id: qa_department_workflow
level: 2  # 新增：标识层级
kind: department  # 新增：标识类型

# 新增：部门信息
metadata:
  department: qa  # 新增
  mode: mono-department  # 新增：mono-department | cross-department
  parent_project: proj-001  # 新增：所属项目

# 新增：阶段定义（类似 L1）
phases:
  - id: phase_id
    name: "阶段名称"
    depends_on: ["prev_phase_id"]

    # 新增：Spawn 配置
    spawn_tasks:
      - template: bug_fix  # 模板 ID
        trigger_on: bug_detected  # 触发事件
        max_concurrent: 10  # 最大并发数
        queue_when_full: true  # 排队等待
        parameters:
          bug_id: "$event.bug_id"
          severity: "$event.severity"

    steps:
      - id: step_id
        run: agent_id
        # ... 正常步骤定义

# 新增：事件触发
on_event:
  - event: bug_detected
    action: spawn  # spawn | pause | resume | complete
    template: bug_fix
    target_phase: test_execution

# 新增：完成条件（基于 L3 聚合）
completion:
  criteria:
    - name: "P0/P1 必须完成"
      condition: |
        count(l3_tasks.where(status == COMPLETED && severity IN [P0, P1])) ==
        count(l3_tasks.where(severity IN [P0, P1]))
    - name: "P2/P3 可部分完成"
      condition: |
        percentage(l3_tasks.where(status == COMPLETED && severity IN [P2, P3])) >= 80
```

### 6.3 Level-3 新增字段

```yaml
# Level-3 workflow.yaml (模板定义)
id: bug_fix_template
level: 3  # 新增：标识层级
kind: template  # 新增：标识类型

# 新增：模板元数据
metadata:
  category: bug_lifecycle  # 新增
  author: qa_team  # 新增
  version: v1  # 新增
  deprecated: false  # 新增

# 新增：参数定义
parameters:
  - name: bug_id  # 新增
    type: string
    required: true
    description: "Bug ID"
  - name: severity
    type: enum
    values: [P0, P1, P2, P3]
    required: true
    default: P2

# 新增：继承
extends: base_bug_fix  # 可选：继承基础模板
overrides:  # 覆盖的字段
  parameters:
    - name: severity
      default: P0

# 现有 stages 定义
stages:
  - id: triage
    name: "分流"
    run: agent.qa.bug_triager
    condition: "{{ severity }} IN [P0, P1]"  # 新增：支持参数表达式
    inputs:
      - bug_id: "{{ bug_id }}"  # 新增：支持参数插值
    outputs:
      - path: "bugs/{{ bug_id }}/triage.yaml"

# 新增：事件处理
on_event:
  - event: requirement_clarified
    action: resume  # resume | pause | complete
    target_stage: fix

# 新增：暂停配置
pause:
  allowed_stages: [triage, fix]  # 允许暂停的阶段
  auto_pause_on:  # 自动暂停条件
    - condition: "{{ category }} == requirement"
      reason: "等待需求澄清"
```

### 6.4 通用新增字段

```yaml
# 所有层级通用
metadata:
  paused: false  # 新增：是否暂停
  pause_reason: ""  # 新增：暂停原因
  paused_at: null  # 新增：暂停时间
  paused_by: ""  # 新增：暂停操作人

# 新增：权限配置
permissions:
  pause:
    roles: [project_owner, department_lead, task_owner]
  resume:
    roles: [project_owner, department_lead, task_owner]
  cancel:
    roles: [project_owner, department_lead]

# 新增：SLA 配置
sla:
  phase_timeout: 7d  # 阶段超时
  task_timeout: 24h  # 任务超时
  escalation:
    - after: 4h
      notify: [department_lead]
    - after: 8h
      notify: [pm, tech_lead]

# 新增：监控配置
monitoring:
  metrics:
    - name: cycle_time
      unit: hours
    - name: paused_duration
      unit: hours
  alerts:
    - condition: paused_duration > 24h
      severity: warning
      notify: [department_lead]
```

---

## 7. 验收标准

### AC-1: 层级隔离

**Given** 一个项目
**When** 创建 Level-1 主流程
**Then**
- [ ] 生成唯一的 Level-1 实例 ID
- [ ] 实例的 `level` 字段为 1
- [ ] 实例的 `kind` 字段为 `project_master`
- [ ] 可以查询该实例的所有子流程

### AC-2: L1 → L2 触发

**Given** 一个 Level-1 主流程处于"需求"阶段
**When** 该阶段完成
**Then**
- [ ] 自动触发 Level-2 "设计"部门子流程
- [ ] Level-2 实例正确关联到 Level-1（parent_id）
- [ ] Level-1 进入"设计"阶段并等待 L2 完成
- [ ] Level-1 状态保持为 `RUNNING`

### AC-3: L2 → L3 Spawn

**Given** 一个 Level-2 QA 子流程处于"测试执行"阶段
**When** 检测到 3 个 Bug（bug_detected 事件）
**Then**
- [ ] 基于 `bug_fix` 模板创建 3 个 Level-3 实例
- [ ] 每个实例的 `parent_id` 指向 L2 实例
- [ ] 每个实例传入正确的参数（bug_id, severity）
- [ ] L2 实例的 `spawned_tasks` 包含 3 个任务 ID

### AC-4: 暂停/恢复 L3 任务

**Given** 一个 Level-3 Bug 修复任务处于 `FIXING` 状态
**When** 任务 owner 发起暂停
**Then**
- [ ] 任务状态变更为 `FIXING_PAUSED`
- [ ] `paused` 字段为 `true`
- [ ] 记录暂停原因和时间
**When** 收到需求澄清后恢复
**Then**
- [ ] 任务状态恢复为 `FIXING`
- [ ] `paused` 字段为 `false`
- [ ] 记录恢复操作和时间

### AC-5: 并发限制

**Given** Level-2 配置 `max_concurrent: 10`
**When** 触发 15 个 Level-3 任务
**Then**
- [ ] 前 10 个任务立即创建，状态为 `RUNNING`
- [ ] 后 5 个任务进入队列，状态为 `QUEUED`
- [ ] 当任一 RUNNING 任务完成时，从队列取 1 个任务启动
- [ ] 最终所有 15 个任务都完成

### AC-6: 状态聚合

**Given** Level-2 有 10 个 Level-3 任务（3 个 P0，7 个 P2）
**When** 3 个 P0 全部完成，5 个 P2 完成（2 个 P2 未完成）
**Then**
- [ ] 聚合状态显示 P0 完成率 100%
- [ ] 聚合状态显示 P2 完成率 71%
- [ ] 如果完成条件是"所有 P0 完成"，则条件满足
- [ ] Level-2 可以进入下一阶段

### AC-7: 模板参数化

**Given** `bug_fix.yaml` 模板定义了 `bug_id` 和 `severity` 参数
**When** 使用 `bug_id: "BUG-001"`, `severity: "P0"` 创建实例
**Then**
- [ ] 实例的 `parameters` 字段包含传入的值
- [ ] 阶段中的 `{{ bug_id }}` 被替换为 `BUG-001`
- [ ] 输出路径 `bugs/{{ bug_id }}/triage.yaml` 变为 `bugs/BUG-001/triage.yaml`
- [ ] 条件 `{{ severity }} IN [P0, P1]` 计算结果为 `true`

### AC-8: 权限控制

**Given** 一个 Level-3 任务，owner 是 `dev_agent@v1`
**When** `dev_agent@v1` 尝试暂停任务
**Then**
- [ ] 暂停操作成功
**When** 其他非 owner 尝试暂停任务
**Then**
- [ ] 返回权限错误
- [ ] 任务状态不变

---

## 8. 决策点（已确认）

### ✅ 决策点 1: L3 并发限制策略

**决策**：采用 **A. 队列等待** 策略

**配置**：
- 队列最大长度：1000
- 队列超时：24小时（超时后标记为 FAILED）
- 队列优先级：按 severity（P0 > P1 > P2 > P3）和时间戳排序

**问题**：当超过 `max_concurrent` 限制时，如何处理？

**选项**：
- **A. 队列等待**：新任务进入队列，等待有空位时启动
- **B. 立即拒绝**：返回错误，不创建任务
- **C. 降级创建**：创建但标记为 `WAITING`，由外部触发启动

---

### ✅ 决策点 2: L1 Phase 切换策略

**决策**：采用 **A. 全部完成**，支持配置例外

**配置**：
- 默认：所有 L2 子流程必须完成当前阶段
- 例外机制：通过 `allowed_to_skip` 配置可跳过的部门
- 跳过审批：需要 PM + 项目 owner 双重审批

**问题**：Level-1 何时进入下一阶段？

**选项**：
- **A. 全部完成**：所有 L2 子流程必须完成当前阶段
- **B. 多数完成**：至少 N% 的 L2 完成（可配置）
- **C. 关键路径完成**：关键部门完成，非关键部门可并行

---

### ✅ 决策点 3: 暂停传播机制

**决策**：采用 **B. 仅阻塞新任务**

**配置**：
- 已运行的 L3 任务继续执行
- 新 L3 任务进入队列等待
- L2 恢复后，队列中的任务自动启动
- 支持手动配置级联暂停行为

**问题**：当 L2 被暂停时，其 L3 任务如何处理？

**选项**：
- **A. 级联暂停**：自动暂停所有 RUNNING 的 L3
- **B. 仅阻塞新任务**：已运行的 L3 继续运行，新 L3 无法启动
- **C. 不影响**：L3 独立运行，不受 L2 暂停影响

---

### ✅ 决策点 4: 模板版本管理

**决策**：采用 **A. 固定版本**

**配置**：
- 实例创建时绑定模板版本
- 模板更新不影响已创建的实例
- 提供 `template migrate` 命令迁移旧实例

**问题**：模板更新后，已创建的 L3 实例如何处理？

**选项**：
- **A. 固定版本**：实例创建时绑定模板版本，不受更新影响
- **B. 自动升级**：实例自动使用最新模板
- **C. 可选升级**：提供升级命令，由用户决定

---

### ✅ 决策点 5: 跨项目模板共享

**决策**：采用 **C. 混合模式**

**配置**：
- 全局模板位置：`ai-spec/workflows/templates/`
- 项目覆盖模板：`{project}/.project/templates/`
- 命名冲突：项目模板覆盖全局模板，需显式声明

---

### ✅ 决策点 6: L3 失败处理

**决策**：采用 **C. 阈值控制**

**配置**：
- 失败阈值：默认 20% 可失败
- P0/P1 失败单独统计（不允许失败）
- 可选任务标记：`optional: true` 失败不影响 L2

---

### ✅ 决策点 7: 实例删除策略

**决策**：采用 **C. 归档策略**

**配置**：
- 归档时间阈值：90 天
- 归档格式：JSON 压缩 + 索引
- 归档位置：`.project/archive/`

**问题**：模板是项目级还是全局级？

**选项**：
- **A. 项目级**：每个项目有自己的模板库
- **B. 全局级**：所有项目共享同一模板库
- **C. 混合模式**：有全局模板和项目覆盖模板

**推荐**：C（混合模式）
**理由**：标准化 + 灵活性

**需要确认**：
- [ ] 全局模板的位置？
- [ ] 项目如何覆盖全局模板？
- [ ] 模板命名冲突如何解决？

---

### ⚠️ 决策点 6: L3 失败处理

**问题**：当 L3 任务失败时，L2 如何处理？

**选项**：
- **A. 立即阻塞**：L2 立即暂停，等待人工介入
- **B. 继续执行**：L2 继续执行，记录失败
- **C. 阈值控制**：失败率超过阈值时才阻塞

**推荐**：C（阈值控制）
**理由**：避免因个别失败影响整体进度

**需要确认**：
- [ ] 失败阈值如何配置（百分比/绝对数量）？
- [ ] 不同 severity 的 L3 是否有不同阈值？
- [ ] 如何标记 L3 为"可选任务"（失败不影响 L2）？

---

### ⚠️ 决策点 7: 实例删除策略

**问题**：已完成的实例是否保留？保留多久？

**选项**：
- **A. 永久保留**：所有实例永久保留
- **B. 定期清理**：超过 N 天的已完成实例自动删除
- **C. 归档策略**：超过 N 天的实例归档到冷存储

**推荐**：C（归档策略）
**理由**：平衡存储成本和审计需求

**需要确认**：
- [ ] 归档时间阈值（如 90 天）？
- [ ] 归档格式和位置？
- [ ] 是否支持恢复归档实例？

---

## 9. 风险评估

### 9.1 技术风险

#### 风险 1: 状态一致性

**描述**：三层流程之间的状态同步可能出现不一致

**影响**：高
**概率**：中

**缓解措施**：
- 使用事务保证原子性
- 定期状态一致性检查
- 实现状态修复工具

**监控指标**：
- 状态不一致率 < 0.1%
- 状态修复成功率 > 99%

---

#### 风险 2: 性能瓶颈

**描述**：大量 L3 任务并发可能导致性能问题

**影响**：高
**概率**：中

**缓解措施**：
- 实现任务队列和并发限制
- 使用连接池和缓存
- 优化数据库查询

**监控指标**：
- 任务创建延迟 < 100ms
- 状态查询延迟 < 50ms
- 并发任务数支持 > 1000

---

#### 风险 3: 模板兼容性

**描述**：模板更新可能导致旧实例无法运行

**影响**：中
**概率**：低

**缓解措施**：
- 模板版本绑定
- 向后兼容性检查
- 模板迁移工具

**监控指标**：
- 模板兼容性冲突 = 0
- 迁移成功率 > 95%

---

### 9.2 产品风险

#### 风险 4: 学习曲线

**描述**：三层架构增加用户理解成本

**影响**：中
**概率**：高

**缓解措施**：
- 提供完整文档和示例
- 设计友好的 CLI 和 UI
- 提供交互式向导

**监控指标**：
- 用户上手时间 < 2 小时
- 文档完整性评分 > 4.5/5.0

---

#### 风险 5: 过度设计

**描述**：三层架构可能对小项目过于复杂

**影响**：中
**概率**：中

**缓解措施**：
- 提供简化模式（单层）
- 提供项目模板
- 自动生成配置

**监控指标**：
- 简化模式使用率 > 30%
- 项目模板采用率 > 50%

---

### 9.3 兼容性风险

#### 风险 6: v2.0 向后兼容

**描述**：现有 v2.0 工作流如何迁移到 v3.0

**影响**：高
**概率**：高

**缓解措施**：
- 提供迁移工具
- 支持 v2.0 兼容模式
- 分阶段迁移

**监控指标**：
- 迁移成功率 > 95%
- 迁移时间 < 1 小时/项目

---

#### 风险 7: Agent 集成

**描述**：现有 Agent 可能不支持新的事件和状态

**影响**：中
**概率**：中

**缓解措施**：
- 提供 Agent 升级指南
- 支持事件适配器
- 提供测试工具

**监控指标**：
- Agent 兼容性 > 90%
- 适配器覆盖率 = 100%

---

## 10. 数据埋点建议

### 10.1 核心指标

#### 流程执行指标

```yaml
# Level-1 指标
metrics:
  - name: l1_phase_duration
    type: histogram
    description: "Level-1 各阶段持续时间"
    labels: [project_id, phase_id]
    buckets: [1h, 4h, 24h, 72h, 168h]

  - name: l1_total_duration
    type: histogram
    description: "Level-1 总持续时间"
    labels: [project_id]
    buckets: [1d, 7d, 30d, 90d]

  - name: l1_phase_transitions
    type: counter
    description: "Level-1 阶段转换次数"
    labels: [project_id, from_phase, to_phase]

# Level-2 指标
  - name: l2_phase_duration
    type: histogram
    description: "Level-2 各阶段持续时间"
    labels: [project_id, department, phase_id]
    buckets: [30m, 2h, 8h, 24h]

  - name: l2_spawn_count
    type: counter
    description: "Level-2 Spawn 的 L3 任务数量"
    labels: [project_id, department, template_id]

# Level-3 指标
  - name: l3_task_duration
    type: histogram
    description: "Level-3 任务持续时间"
    labels: [project_id, template_id, severity]
    buckets: [10m, 1h, 4h, 24h]

  - name: l3_task_completion_rate
    type: gauge
    description: "Level-3 任务完成率"
    labels: [project_id, department, template_id]
```

#### 暂停/恢复指标

```yaml
metrics:
  - name: workflow_pause_count
    type: counter
    description: "工作流暂停次数"
    labels: [level, department, template_id, reason]

  - name: workflow_pause_duration
    type: histogram
    description: "工作流暂停持续时间"
    labels: [level, department, template_id]
    buckets: [10m, 1h, 4h, 24h, 72h]

  - name: workflow_resume_count
    type: counter
    description: "工作流恢复次数"
    labels: [level, department, template_id]
```

#### 并发指标

```yaml
metrics:
  - name: l3_concurrent_tasks
    type: gauge
    description: "当前并发的 L3 任务数"
    labels: [project_id, department]

  - name: l3_queue_length
    type: gauge
    description: "L3 任务队列长度"
    labels: [project_id, department]

  - name: l3_queue_wait_duration
    type: histogram
    description: "L3 任务队列等待时间"
    labels: [project_id, department]
    buckets: [1s, 10s, 1m, 10m, 1h]
```

### 10.2 业务指标

```yaml
metrics:
  - name: project_cycle_time
    type: histogram
    description: "项目从需求到上线的时间"
    labels: [project_id]
    buckets: [1d, 7d, 30d, 90d, 180d]

  - name: department_handoff_delay
    type: histogram
    description: "部门间交接延迟"
    labels: [from_department, to_department]
    buckets: [1h, 4h, 24h, 72h]

  - name: bug_fix_time_by_severity
    type: histogram
    description: "Bug 修复时间（按严重级别）"
    labels: [severity]
    buckets: [1h, 4h, 24h, 72h, 168h]

  - name: template_usage
    type: counter
    description: "模板使用次数"
    labels: [template_id, category]
```

### 10.3 质量指标

```yaml
metrics:
  - name: workflow_failure_rate
    type: gauge
    description: "工作流失败率"
    labels: [level, department, template_id]

  - name: state_inconsistency_count
    type: counter
    description: "状态不一致次数"
    labels: [level, instance_id]

  - name: permission_denied_count
    type: counter
    description: "权限拒绝次数"
    labels: [operation, role]

  - name: template_validation_error_count
    type: counter
    description: "模板验证错误次数"
    labels: [template_id, error_type]
```

### 10.4 告警规则

```yaml
alerts:
  - name: HighLevel3FailureRate
    condition: l3_task_completion_rate < 0.8
    duration: 1h
    severity: warning
    message: "Level-3 任务完成率低于 80%"

  - name: LongRunningWorkflow
    condition: l1_phase_duration{phase_id="development"} > 168h
    duration: 0s
    severity: info
    message: "开发阶段超过 7 天"

  - name: ExcessivePausedWorkflows
    condition: workflow_pause_duration > 72h
    duration: 0s
    severity: warning
    message: "工作流暂停超过 72 小时"

  - name: LongQueueWait
    condition: l3_queue_wait_duration > 4h
    duration: 30m
    severity: warning
    message: "L3 任务队列等待超过 4 小时"

  - name: StateInconsistencyDetected
    condition: state_inconsistency_count > 0
    duration: 0s
    severity: critical
    message: "检测到状态不一致"
```

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| Level-1 | 公司级主流程，表达项目整体生命周期 |
| Level-2 | 部门级子流程，表达部门内部工作阶段 |
| Level-3 | 任务级流程，基于模板创建的具体任务 |
| Workflow Instance | 工作流实例，运行中的工作流 |
| Workflow Template | 工作流模板，可复用的流程定义 |
| Spawn | 创建 Level-3 任务实例的操作 |
| Phase | 阶段，工作流中的大阶段 |
| Stage | 步骤，工作流中的具体执行步骤 |
| Pause/Resume | 暂停/恢复，控制工作流执行的操作 |
| Aggregation | 聚合，从 L3 收集状态到 L2，从 L2 到 L1 |

### B. 参考文档

1. **现有文档**：
   - [Orchestrator PRD v2.0](./Orchestrator-PRD.md)
   - [Orchestrator Architecture v2.0](./architecture.md)

2. **相关项目**：
   - Apache Airflow: DAG 编排
   - Temporal: 工作流引擎
   - Argo Workflows: Kubernetes 工作流

3. **设计模式**：
   - Composite Pattern: 树形层级结构
   - Template Method Pattern: 模板复用
   - Observer Pattern: 事件驱动

### C. 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-01-25 | 初稿 | PM Agent |

---

**文档版本**: v1.0
**最后更新**: 2026-01-25
**维护者**: LEE 产品团队
**审核者**: 待定
