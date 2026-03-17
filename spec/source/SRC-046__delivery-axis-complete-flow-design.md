---
id: SRC-046
ssot_type: src
title: 交付轴完整流程设计 (SRC-046 补充方案)
status: draft
version: v1
workflow_instance_id: wf-src-046-20260317
source_refs: []
owner: dev-governance
tags:
  - delivery-axis
  - release-management
  - workflow-design
properties:
  design_kind: workflow_architecture
  governed_by_adrs:
    - ADR-001
---

# 交付轴完整流程设计 (SRC-046 补充方案)

## 一、问题陈述

### 1.1 当前断裂点

**Product Main Pipeline 只生成了 TASK，缺少交付轴核心 SSOT 对象：**

```
当前流程 (断裂):
Product Main Pipeline:
  Raw → SRC → EPIC → FEAT → Delivery Prep (UI/TECH/TASK) → Handoff
                                              ❌ 缺少 RELEASE
                                              ❌ 缺少 DEVPLAN
                                              ❌ 缺少 TESTPLAN
                                              ❌ 直接跳到 TASK 执行

问题影响:
- 版本交付没有正式 RELEASE 对象作为入口
- Dev 执行没有 DEVPLAN 作为计划依据
- QA 执行没有 TESTPLAN 作为测试依据
- 交付覆盖度无法统计
- 发布决策没有数据支撑
```

### 1.2 目标流程 (完整)

```
应然的交付轴:
Product Pipeline (L1) → Release Delivery (L1) → Dev/QA Execution (L2)

FEAT → RELEASE → DEVPLAN → TESTPLAN → TASK
              ↓          ↓
         (Dev 消费)   (QA 消费)
```

---

## 二、交付轴三层 Workflow 架构 (补充后)

```
┌─────────────────────────────────────────────────────────────────┐
│                     L1: Release Delivery DAG                    │
│  (版本交付主链：从 RELEASE 创建到发布关闭)                         │
│                                                                 │
│  Stage 1: Scope Management                                      │
│    - scope_init: 初始化 RELEASE，绑定 FEAT Bundle               │
│    - scope_validate: 验证 FEAT Bundle 完整性                     │
│    - scope_freeze: 冻结 RELEASE Scope (人类门禁)                │
│                                                                 │
│  Stage 2: Plan Derivation                                       │
│    - derive_devplan: 派生 DEVPLAN                               │
│    - derive_testplan: 派生 TESTPLAN                             │
│    - plan_validate: 验证 DEVPLAN/TESTPLAN 覆盖度                 │
│                                                                 │
│  Stage 3: Dev Execution                                         │
│    - spawn_dev_l2: 生成 Dev L2 实例                              │
│    - track_dev_progress: 跟踪 Dev 进度                           │
│                                                                 │
│  Stage 4: QA Execution                                          │
│    - spawn_qa_l2: 生成 QA L2 实例                                │
│    - track_qa_progress: 跟踪 QA 进度                             │
│                                                                 │
│  Stage 5: Release Closure                                       │
│    - coverage_check: 验证交付覆盖度                             │
│    - go_nogo_decision: 发布决策 (人类门禁)                       │
│    - release_close: 关闭 RELEASE                                │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  L2: DEVPLAN │    │  L2: DEVPLAN │    │ L2: TESTPLAN │
│  Scope Init  │    │  Execution   │    │  Management  │
│  (派生 TASK)  │    │  (spawn L2)  │    │  (派生测试)  │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  TASK SSOT   │    │ L3: Feature  │    │ L2: Test     │
│  对象落盘     │    │  Dev L2      │    │  Plan Exec   │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 三、SSOT 线 (形式规格链) 补充

### 3.1 完整 SSOT 衍生链

```
┌─────────────────────────────────────────────────────────────────┐
│                    SSOT Delivery Chain                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Product 部门 (Delivery Prep):                                  │
│  RAW → SRC → EPIC → FEAT → UI/TECH/TASK (冻结)                 │
│                              │                                  │
│                              ▼                                  │
│  Dev Governance (Release Center):                               │
│                    FEAT Bundle → RELEASE                        │
│                                 │                               │
│           ┌─────────────────────┼─────────────────────┐        │
│           │                     │                     │        │
│           ▼                     ▼                     ▼        │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  │ DEVPLAN         │   │ TESTPLAN        │   │ (已有 TASK)     │
│  │ (消费 TECH/TASK) │   │ (消费 AC/TECH)  │   │ (消费 TECH)     │
│  │ 组织任务执行     │   │ 定义测试策略     │   │ 执行实施        │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘
│           │                     │                                  │
│           │                     ▼                                  │
│           │            ┌─────────────────┐                        │
│           │            │ Test Set 生产     │ ◄── 执行层            │
│           │            │ (基于 TESTPLAN)  │                        │
│           │            └─────────────────┘                        │
│           │                     │                                  │
│           ▼                     ▼                                  │
│  ┌─────────────────────────────────────────┐                     │
│  │      Dev + QA Execution (消费 TECH)      │                     │
│  └─────────────────────────────────────────┘                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

关键说明：
- TECH/TASK 在 Delivery Prep 阶段已生成并冻结
- DEVPLAN 不派生 TASK，而是组织/分配已有 TASK
- TESTPLAN 定义测试策略，Test Set 是执行层产物
- Test Set 基于 TESTPLAN 指令 + FEAT.AC + TECH 生成
```

### 3.2 SSOT 对象定义

| SSOT 类型 | 全称 | 负责部门 | 输入 | 输出 | 冻结时机 |
|-----------|------|----------|------|------|----------|
| **FEAT** | Feature | Product | EPIC | UI/TECH/TASK | Delivery Prep 完成 |
| **RELEASE** | Release | Dev Governance | FEAT Bundle | DEVPLAN, TESTPLAN | Scope Freeze |
| **DEVPLAN** | Development Plan | Dev Governance | RELEASE + TECH + TASK | 执行任务分配 | Plan Derive 完成 |
| **TESTPLAN** | Test Plan | QA | RELEASE + FEAT(AC) + TECH + TASK | Test Set 派生指令 | Plan Derive 完成 |
| **Test Set** | Test Set | QA | TESTPLAN + FEAT(AC) + TECH | 测试用例细节 | Test Set 生产完成 |
| **TASK** | Task | Dev/QA | DEVPLAN/TESTPLAN + TECH | 执行结果 | 执行完成 |

### 3.3 SSOT 追溯关系

```yaml
# 关键依赖关系说明：
# - DEVPLAN 依赖 Delivery Prep 中的 TECH 和 TASK
# - TESTPLAN 依赖 FEAT 的 AC + TECH + TASK (用于测试策略)
# - Test Set 是 TESTPLAN 冻结后的产物，不是 TESTPLAN 的输入

# RELEASE SSOT 示例
ssot_type: RELEASE
id: RELEASE-001
status: scope_frozen  # planning → scope_frozen → in_execution → released → closed
feat_bundle_refs:  # ← 绑定的 FEAT Bundle
  - FEAT-001
  - FEAT-002
  - FEAT-003
delivery_prep_refs:  # ← 绑定的 Delivery Prep (含 TECH/TASK)
  - FEAT-001/delivery-prep-freeze
  - FEAT-002/delivery-prep-freeze
  - FEAT-003/delivery-prep-freeze
devplan_ref: "spec/devplans/devplan-001.yaml"  # ← 派生的 DEVPLAN
testplan_ref: "spec/testplans/testplan-001.yaml"  # ← 派生的 TESTPLAN
release_window:
  start_date: "2026-03-20"
  end_date: "2026-03-27"
release_type: minor

# DEVPLAN SSOT 示例
ssot_type: DEVPLAN
id: DEVPLAN-001
status: frozen
release_ref: "RELEASE-001"
tech_refs:  # ← 消费 Delivery Prep 中的 TECH
  - FEAT-001/tech-spec
  - FEAT-002/tech-spec
task_refs:  # ← 消费 Delivery Prep 中的 TASK，不是派生
  - TASK-FEAT-001-001
  - TASK-FEAT-001-002
  - TASK-FEAT-002-001
milestones:
  - name: "Backend Complete"
    target_date: "2026-03-23"
  - name: "Frontend Complete"
    target_date: "2026-03-24"
  - name: "Integration Complete"
    target_date: "2026-03-25"

# TESTPLAN SSOT 示例
ssot_type: TESTPLAN
id: TESTPLAN-001
status: frozen
release_ref: "RELEASE-001"
feat_ac_refs:  # ← 消费 FEAT 的验收标准
  - FEAT-001.acceptance_criteria
  - FEAT-002.acceptance_criteria
tech_refs:  # ← 消费 TECH 了解实现细节
  - FEAT-001/tech-spec
  - FEAT-002/tech-spec
test_strategy:  # ← 测试策略定义
  smoke_scope: "核心链路 + 高风险变更"
  regression_scope: "全量功能"
  automation_ratio_target: 0.8
test_set_instruction_refs:  # ← 派生 Test Set 的指令 (不是 Test Set 本身)
  - instruction: "为每个 FEAT 生成 Smoke Test Set"
  - instruction: "为关键链路生成 Regression Test Set"
milestones:
  - name: "Smoke Test Complete"
    target_date: "2026-03-25"
  - name: "Regression Test Complete"
    target_date: "2026-03-26"
  - name: "Test Report Complete"
    target_date: "2026-03-27"
```

---

## 四、Workflow 用户故事线 (补充后)

### 4.1 完整用户故事线

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    Complete Workflow Execution Chain                     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Product Main Pipeline (L1)                                       │    │
│  │ RAW → SRC → EPIC → FEAT → Delivery Prep                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Release Delivery (L1) ← 新增                                     │    │
│  │ FEAT Bundle → RELEASE → DEVPLAN → TESTPLAN                      │    │
│  │                                                                  │    │
│  │ Stages:                                                          │    │
│  │   1. Scope Management (init → validate → freeze)                │    │
│  │   2. Plan Derivation (derive_devplan → derive_testplan)         │    │
│  │   3. Dev Execution (spawn L2 → track)                           │    │
│  │   4. QA Execution (spawn L2 → track)                            │    │
│  │   5. Release Closure (coverage → go/nogo → close)               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│           ┌───────────────────────┼───────────────────────┐             │
│           ▼                       ▼                       ▼             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │ DEVPLAN Mgmt    │    │ Feature Dev     │    │ TESTPLAN Mgmt   │     │
│  │ (L2 - Dev)      │    │ (L2 - Dev)      │    │ (L2 - QA)       │     │
│  │                 │    │                 │    │                 │     │
│  │ - Init          │    │ - Tech Design   │    │ - Init          │     │
│  │ - Derive TASK   │    │ - Contract      │    │ - Derive Test   │     │
│  │ - Validate      │    │ - BE Dev        │    │ - Validate      │     │
│  │ - Freeze        │    │ - FE Dev        │    │ - Freeze        │     │
│  │ - Spawn L2      │    │ - Integration   │    │ - Spawn L2      │     │
│  │ - Track         │    │ - Evidence      │    │ - Track         │     │
│  │ - Aggregate     │    │ - Smoke Gate    │    │ - Aggregate     │     │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘     │
│           │                       │                       │             │
│           │                       │                       ▼             │
│           │                       │              ┌─────────────────┐   │
│           │                       │              │ Test Run        │   │
│           │                       │              │ (L2 - QA)       │   │
│           │                       │              │                 │   │
│           │                       │              │ - Env Provision │   │
│           │                       │              │ - Test Set Exec │   │
│           │                       │              │ - Report        │   │
│           │                       │              │ - Exit Eval     │   │
│           │                       │              └─────────────────┘   │
│           │                       │                                     │
│           ▼                       ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Release Closure ← 新增                                          │    │
│  │ - Coverage Check (Dev + QA 完成率)                              │    │
│  │ - Go/No-Go Decision (人类门禁)                                  │    │
│  │ - Release Close                                                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.2 关键门禁点

```yaml
gates:
  # Release L1 门禁
  release_gates:
    - id: gate.dev.scope_freeze_gate
      type: human_approval
      stage: scope_management
      reviewers: [release_manager, product_owner, tech_lead]
      criteria:
        - "FEAT Bundle 完整"
        - "依赖关系清晰"
        - "风险可控"

    - id: gate.dev.scope_validate_gate
      type: auto_check
      stage: scope_management
      checks:
        - "所有 FEAT 都是 frozen 状态"
        - "FEAT 依赖关系无环"
        - "FEAT outputs 完备"

    - id: gate.dev.plan_validate_gate
      type: auto_check
      stage: plan_derivation
      checks:
        - "DEVPLAN 覆盖率 = 100%"
        - "TESTPLAN 覆盖率 = 100%"
        - "里程碑时间合理"

    - id: gate.dev.go_nogo_gate
      type: human_approval
      stage: release_closure
      reviewers: [release_manager, product_owner, tech_lead]
      options:
        - Go: 允许发布
        - Conditional Go: 带已知问题发布
        - No-Go: 打回修复

  # DEVPLAN L2 门禁
  devplan_gates:
    - id: gate.dev.task_validate_gate
      type: auto_check
      checks:
        - "所有 FEAT 都有 TASK"
        - "TASK 责任角色明确"

    - id: gate.dev.devplan_freeze_gate
      type: human_approval
      reviewers: [release_manager, dev_lead]

  # TESTPLAN L2 门禁
  testplan_gates:
    - id: gate.qa.test_set_validate_gate
      type: auto_check
      checks:
        - "所有 FEAT 都有 Test Set"
        - "Test Case 与 FEAT AC 可追溯"

    - id: gate.qa.testplan_freeze_gate
      type: human_approval
      reviewers: [release_manager, qa_lead]
```

---

## 五、交付轴执行流程详解

### 5.1 Phase 1: Scope Management

```
┌─────────────────────────────────────────────────────────────────┐
│ Scope Management                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: scope_init                                             │
│    Agent: agent.dev.release_manager                             │
│    Input: feat_bundle_refs: [FEAT-001, FEAT-002, ...]          │
│    Output: spec/releases/release-{release_id}.yaml             │
│    Action:                                                      │
│      - 生成 RELEASE 对象                                        │
│      - 绑定 FEAT Bundle                                         │
│      - 定义 release_window                                      │
│                                                                 │
│  Step 2: scope_validate                                         │
│    Agent: agent.dev.scope_validator                             │
│    Input: RELEASE.feat_refs                                     │
│    Output: scope_validation_result.json                         │
│    Checks:                                                      │
│      - ✓ 所有 FEAT 都是 frozen 状态                              │
│      - ✓ FEAT 依赖关系无环                                      │
│      - ✓ FEAT outputs 完备                                      │
│    Gate: auto_check (失败则阻塞)                                │
│                                                                 │
│  Step 3: scope_freeze                                           │
│    Gate: human_approval                                         │
│    Reviewers: release_manager, product_owner, tech_lead         │
│    Action:                                                      │
│      - 锁定 feat_refs，禁止增删                                 │
│      - 标记 status = "scope_frozen"                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Phase 2: Plan Derivation

```
┌─────────────────────────────────────────────────────────────────┐
│ Plan Derivation                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Pre-condition:                                                 │
│    - RELEASE.status = "scope_frozen"                            │
│    - 所有 FEAT 的 Delivery Prep 已完成 (TECH/TASK 冻结)            │
│                                                                 │
│  Step 1: derive_devplan (并行)                                  │
│    Agent: agent.dev.plan_deriver                                │
│    Input:                                                       │
│      - RELEASE (scope_frozen)                                   │
│      - TECH specs (来自 Delivery Prep)                          │
│      - TASK specs (来自 Delivery Prep)                          │
│    Output: spec/devplans/devplan-{release_id}.yaml             │
│    Action:                                                      │
│      - 读取 RELEASE.feat_refs                                   │
│      - 消费 TECH 了解技术实现细节                                 │
│      - 组织/分配已有 TASK (不是派生新 TASK)                       │
│      - 定义 milestones, assignees, workstreams                  │
│                                                                 │
│  Step 2: derive_testplan (并行)                                 │
│    Agent: agent.qa.plan_deriver                                 │
│    Input:                                                       │
│      - RELEASE (scope_frozen)                                   │
│      - FEAT.acceptance_criteria                                 │
│      - TECH specs (了解实现细节)                                │
│      - TASK specs (了解实施范围)                                │
│    Output: spec/testplans/testplan-{release_id}.yaml           │
│    Action:                                                      │
│      - 定义 test_strategy (smoke/regression/automation 比例)     │
│      - 定义 test_scope (基于 FEAT.AC 和 TECH)                     │
│      - 定义 test milestones, test types                         │
│      - 生成 Test Set 生产指令 (不是 Test Set 本身)                │
│                                                                 │
│  Step 3: plan_validate                                          │
│    Agent: agent.dev.plan_validator                              │
│    Input: DEVPLAN, TESTPLAN                                     │
│    Output: plan_validation_result.json                          │
│    Checks:                                                      │
│      - ✓ 所有 FEAT 都有 DEVPLAN 条目                             │
│      - ✓ 所有 FEAT 都有 TESTPLAN 条目                            │
│      - ✓ 里程碑时间合理                                         │
│    Gate: auto_check (失败则阻塞)                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Phase 3: Dev Execution

```
┌─────────────────────────────────────────────────────────────────┐
│ Dev Execution                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: spawn_dev_l2                                           │
│    Skill: skill.orchestrator.spawn_l2                           │
│    Input: DEVPLAN.task_refs                                     │
│    Output: .workflow/release-{id}/dev-instances/                │
│    Action:                                                      │
│      - 对每个 TASK 生成 Feature Delivery L2 实例                  │
│      - 绑定 FEAT 和 TASK                                         │
│      - 执行 L2 流程：                                             │
│          tech_design → contract → be/fe → integration          │
│          → evidence_pack → smoke_gate                           │
│                                                                 │
│  Step 2: track_dev_progress                                     │
│    Agent: agent.dev.progress_tracker                            │
│    Input: Dev L2 instances                                      │
│    Output: dev_progress_report.md                               │
│    Metrics:                                                     │
│      - Dev L2 完成率                                             │
│      - 阻塞风险识别                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.4 Phase 4: QA Execution

```
┌─────────────────────────────────────────────────────────────────┐
│ QA Execution                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Pre-condition: dev_progress.dev_l2_complete_rate >= 100%      │
│                                                                 │
│  Step 1: spawn_qa_l2                                            │
│    Skill: skill.orchestrator.spawn_l2                           │
│    Input: TESTPLAN.test_set_refs                                │
│    Output: .workflow/release-{id}/qa-instances/                 │
│    Action:                                                      │
│      - 生成 Test Plan L2 实例                                    │
│      - 绑定 RELEASE 和 TESTPLAN                                   │
│      - 执行 L2 流程：                                             │
│          env_provision → test_set_execution → report           │
│          → exit_evaluation                                      │
│                                                                 │
│  Step 2: track_qa_progress                                      │
│    Agent: agent.qa.progress_tracker                             │
│    Input: QA L2 instances                                       │
│    Output: qa_progress_report.md                                │
│    Metrics:                                                     │
│      - Test Set 完成率                                           │
│      - Pass/Fail率                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.5 Phase 5: Release Closure

```
┌─────────────────────────────────────────────────────────────────┐
│ Release Closure                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: coverage_check                                         │
│    Agent: agent.dev.coverage_checker                            │
│    Input: dev_progress_report, qa_progress_report               │
│    Output: coverage_check_result.json                           │
│    Checks:                                                      │
│      - ✓ Dev L2 完成率 = 100%                                   │
│      - ✓ QA Test Set 完成率 = 100%                              │
│      - ✓ QA Pass Rate >= 100% (或条件通过)                      │
│      - ✓ 所有 Smoke Gate 通过                                   │
│                                                                 │
│  Step 2: go_nogo_decision                                       │
│    Gate: human_approval                                         │
│    Reviewers: release_manager, product_owner, tech_lead         │
│    Options:                                                     │
│      - Go: 允许发布                                             │
│      - Conditional Go: 带已知问题发布                           │
│      - No-Go: 打回修复                                          │
│                                                                 │
│  Step 3: release_close                                          │
│    Agent: agent.dev.release_closer                              │
│    Pre-condition: go_nogo_decision != 'No-Go'                   │
│    Output:                                                      │
│      - release_close_report.md                                  │
│      - release_archive/ (归档证据)                              │
│      - RELEASE.status = "closed"                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、职责分层矩阵 (补充后)

| 职责 | Product | Dev Governance | Dev | QA |
|------|---------|----------------|-----|-----|
| **FEAT 生产** | 负责 | - | 消费 | 消费 |
| **RELEASE 创建** | - | 负责 | - | - |
| **DEVPLAN 派生** | - | 负责 | 消费 | - |
| **TESTPLAN 派生** | - | - | - | 负责 |
| **TASK 执行** | - | - | 执行 (Dev L2) | - |
| **Test Set 生产** | - | - | - | 负责 |
| **Test Run 执行** | - | - | - | 执行 (QA L2) |
| **Scope Freeze** | 参与评审 | 负责 | - | - |
| **Go/No-Go 决策** | 参与决策 | 负责 | - | 提供数据 |

---

## 七、关键设计原则

### 7.1 RELEASE 中心原则

```yaml
principle: "RELEASE 是交付轴的唯一入口"
rationale: |
  - 所有 FEAT 必须通过 RELEASE 组织才能进入执行
  - 禁止绕过 RELEASE 直接执行 TASK
  - RELEASE 是统计交付覆盖度的基础单元

implementation:
  - RELEASE 必须绑定至少一个 frozen FEAT
  - RELEASE 必须先 scope_freeze 才能派生计划
  - RELEASE 必须经过 Go/No-Go 决策才能关闭
```

### 7.2 计划派生原则

```yaml
principle: "DEVPLAN 和 TESTPLAN 必须从 RELEASE 派生"
rationale: |
  - DEVPLAN/TESTPLAN 必须共享同一个 RELEASE 上下文
  - 禁止脱离 RELEASE 独立创建计划
  - 计划覆盖度验证必须在派生后立即执行

implementation:
  - derive_devplan 和 derive_testplan 并行执行
  - plan_validate 验证覆盖率必须达到 100%
  - DEVPLAN/TESTPLAN 都必须 freeze 后才能执行
```

### 7.3 Dev 先于 QA 原则

```yaml
principle: "QA 执行必须在 Dev 执行完成后开始"
rationale: |
  - QA 测试需要被测代码已部署
  - Dev Smoke 必须先通过才能 QA 测试
  - 避免 QA 在未完成代码上浪费时间

implementation:
  - spawn_qa_l2 的 pre_condition: dev_l2_complete_rate >= 100
  - QA L2 可以读取 Dev L2 的 evidence_pack 作为参考
```

### 7.4 覆盖度验证原则

```yaml
principle: "交付覆盖度必须验证通过才能进入 Go/No-Go 决策"
rationale: |
  - 未经验证的覆盖率数据可能导致错误发布
  - 必须同时验证 Dev 和 QA 的完成情况

implementation:
  - coverage_check 是 release_closure 的第一步
  - 覆盖率数据来自 Dev/QA progress_tracker
  - coverage_check 失败不阻塞流程，但影响决策
```

---

## 八、实施计划

### 8.1 Phase 1: RELEASE L1 模板创建

- [ ] 创建 `release-delivery-l1-template.yaml`
- [ ] 创建 `agent.dev.release_manager`
- [ ] 创建 `agent.dev.scope_validator`
- [ ] 创建 `agent.dev.release_closer`
- [ ] 创建 `gate.dev.scope_freeze_gate`
- [ ] 创建 `gate.dev.go_nogo_gate`

### 8.2 Phase 2: DEVPLAN/TESTPLAN L2 模板创建

- [ ] 创建 `devplan-management-l2-template.yaml`
- [ ] 创建 `testplan-management-l2-template.yaml`
- [ ] 创建 `agent.dev.plan_deriver`
- [ ] 创建 `agent.qa.plan_deriver`
- [ ] 创建 `agent.dev.plan_validator`

### 8.3 Phase 3: Product Pipeline 集成

- [ ] 修改 `product-main-pipeline` 输出为 RELEASE 输入
- [ ] 添加 `release_delivery` 阶段到 Product Pipeline
- [ ] 更新 handoff 配置

### 8.4 Phase 4: 试点运行

- [ ] 选择一个小型 FEAT Bundle 试点
- [ ] 执行完整 RELEASE L1 流程
- [ ] 收集反馈并优化

---

## 九、与现有流程的兼容

### 9.1 向后兼容

```yaml
compatibility:
  # 现有 TASK 对象仍然有效
  existing_tasks:
    status: "still valid"
    action: "migrate to new flow gradually"

  # 现有 QA Test Run 仍然可以执行
  existing_test_runs:
    status: "still valid"
    action: "bind to RELEASE retrospectively"

  # 现有 Bug Fix 流程
  existing_bugfix:
    status: "still valid"
    action: "evidence must flow back to RELEASE"
```

### 9.2 迁移路径

```
迁移路径:
1. 新 FEAT 必须通过 RELEASE 流程
2. 进行中的 FEAT 可以选择加入 RELEASE
3. 已完成的 FEAT 可以 retrospective 绑定到 RELEASE
```

---

## 十、验收标准

### 10.1 RELEASE L1 验收

- [ ] 能够创建 RELEASE 对象并绑定 FEAT Bundle
- [ ] Scope Freeze 门禁正常工作
- [ ] DEVPLAN/TESTPLAN 正确派生
- [ ] Dev/QA 执行进度可跟踪
- [ ] Go/No-Go 决策门禁正常工作
- [ ] RELEASE Close 正常归档

### 10.2 DEVPLAN/TESTPLAN L2 验收

- [ ] TASK/Test Set 正确派生
- [ ] 覆盖度验证正常工作
- [ ] L2 实例正确生成
- [ ] 进度跟踪数据准确

### 10.3 端到端验收

- [ ] 从 FEAT Bundle 到 RELEASE Close 全流程通畅
- [ ] 交付覆盖度统计准确
- [ ] 发布决策有数据支撑
