---
id: SSFLOW-001
title: RELEASE/DEVPLAN/TESTPLAN 工作流链 (SSOT Delivery Workflow Chain)
version: v1
created_at: 2026-03-17
owner: dev-governance
tags:
  - workflow
  - ssot
  - release
  - devplan
  - testplan
---

# RELEASE/DEVPLAN/TESTPLAN 工作流链

## 一、完整 SSOT 交付链路总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Product Pipeline ( upstream )                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  RAW → SRC → EPIC → FEAT → Delivery Prep (UI/TECH/TASK 冻结)           │
│                              │                                          │
│                              ▼                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Dev Governance ( Delivery Axis )                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  L1: RELEASE Delivery                                                  │
│      FEAT Bundle → RELEASE → DEVPLAN → TASK                            │
│                          │                                              │
│                          ▼                                              │
│  L2: DEVPLAN Management                                                │
│      RELEASE + TASK → Dev Execution → Evidence                         │
│                                                                         │
│  L2: TESTPLAN Management                                               │
│      RELEASE + FEAT.AC + TECH → Test Strategy → Test Set               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、L1: RELEASE 生成工作流 (Scope Management)

### 2.1 工作流定位

| 属性 | 值 |
|------|-----|
| **工作流 ID** | `workflow.dev.release_delivery_l1` |
| **模板文件** | `spec-global/departments/dev/workflows/templates/release-delivery-l1-template.yaml` |
| **负责角色** | Release Manager |
| **上游输入** | FEAT Bundle (来自 Delivery Prep) |
| **下游输出** | RELEASE (frozen) + DEVPLAN + TESTPLAN |

### 2.2 输入 SSOT

| SSOT 类型 | 位置 | 状态要求 | 用途 |
|-----------|------|----------|------|
| **FEAT Bundle** | `spec/requirements/FEAT-*.yaml` | frozen | RELEASE 范围定义 |
| **Delivery Prep Bundle** | `spec/delivery-prep/` | frozen | UI/TECH/TASK 引用 |
| **EPIC** | `spec/requirements/EPIC-*.yaml` | frozen | 追溯链 |
| **SRC** | `spec/requirements/SRC-*.yaml` | frozen | 追溯链 |

### 2.3 工作流阶段

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    L1: RELEASE Delivery DAG                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐                                                    │
│  │ 1. Scope        │                                                    │
│  │    Management   │                                                    │
│  │                 │                                                    │
│  │  - scope_init   │──┐                                                 │
│  │  - scope_validate│  │                                                │
│  │  - scope_freeze │◄─┘ (human gate)                                   │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 2. Plan         │                                                    │
│  │    Derivation   │                                                    │
│  │                 │                                                    │
│  │  - derive_devplan  │──┐                                              │
│  │  - derive_testplan │◄─┘ (parallel)                                  │
│  │  - plan_validate   │                                                 │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐     ┌─────────────────┐                           │
│  │ 3. Dev          │     │ 4. QA           │                           │
│  │    Execution    │     │    Execution    │                           │
│  │                 │     │                 │                           │
│  │  - spawn_dev_l2 │     │  - spawn_qa_l2  │                           │
│  │  - track_dev    │     │  - track_qa     │                           │
│  └─────────────────┘     └─────────────────┘                           │
│           │                     │                                       │
│           └──────────┬──────────┘                                       │
│                      ▼                                                  │
│  ┌─────────────────────────┐                                            │
│  │ 5. Release Closure      │                                            │
│  │                         │                                            │
│  │  - coverage_check       │                                            │
│  │  - go_nogo_decision     │◄── (human gate)                           │
│  │  - release_close        │                                            │
│  └─────────────────────────┘                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.4 详细阶段说明

#### Stage 1: Scope Management

| 步骤 | ID | 类型 | 输入 | 输出 | Gate |
|------|-----|------|------|------|------|
| **scope_init** | agent | `feat_bundle_refs`, `release_window`, `release_type` | `spec/releases/release-{id}.yaml` | - |
| **scope_validate** | agent | RELEASE 对象 | `dependency_graph.md`, `scope_validation_result` | `gate.dev.scope_validate_gate` (auto) |
| **scope_freeze** | gate | `scope_validation_result` | `spec/releases/release-{id}.yaml` (frozen) | `gate.dev.scope_freeze_gate` (human) |

**scope_init 输出示例**:
```yaml
# spec/releases/release-{release_id}.yaml
id: release-{release_id}
ssot_type: RELEASE
status: open
feat_refs: [FEAT-001, FEAT-002, ...]
release_window:
  start_date: "2026-03-17"
  end_date: "2026-03-31"
release_type: major  # major/minor/patch/hotfix
```

**scope_freeze Gate 审批标准**:
- ✅ FEAT Bundle 完整：所有计划内的 FEAT 都已加入且 frozen
- ✅ 依赖关系清晰：dependency_graph 无环，关键路径明确
- ✅ 风险可控：已知风险已记录并有缓解方案

**审批人角色**: `release_manager`, `product_owner`, `tech_lead`

#### Stage 2: Plan Derivation

| 步骤 | ID | 类型 | 输入 | 输出 | Gate |
|------|-----|------|------|------|------|
| **derive_devplan** | agent | RELEASE (scope_frozen) | `spec/devplans/devplan-{id}.yaml` | - |
| **derive_testplan** | agent | RELEASE (scope_frozen) | `spec/testplans/testplan-{id}.yaml` | - |
| **plan_validate** | agent | DEVPLAN, TESTPLAN | `plan_validation_result.json` | `gate.dev.plan_validate_gate` (auto) |

**DEVPLAN 输出示例**:
```yaml
# spec/devplans/devplan-{release_id}.yaml
id: devplan-{release_id}
ssot_type: DEVPLAN
status: draft
release_ref: release-{release_id}
task_refs: [TASK-FEAT-001-001, TASK-FEAT-001-002, ...]
task_execution_order:
  - lane: frontend
    tasks: [TASK-FEAT-001-002, ...]
  - lane: backend
    tasks: [TASK-FEAT-001-001, ...]
milestones:
  - name: "Dev Complete"
    target_date: "2026-03-25"
assignees:
  - role: developer
    task_refs: [...]
```

**TESTPLAN 输出示例**:
```yaml
# spec/testplans/testplan-{release_id}.yaml
id: testplan-{release_id}
ssot_type: TESTPLAN
status: draft
release_ref: release-{release_id}
test_strategy:
  smoke_tests: [ts-smoke-001, ...]
  regression_tests: [ts-reg-001, ...]
  automation_tests: [ts-auto-001, ...]
milestones:
  - name: "Test Complete"
    target_date: "2026-03-28"
assignees:
  - role: qa_engineer
    test_set_refs: [...]
```

**plan_validate Gate 检查项**:
```json
{
  "devplan_coverage": 100,
  "testplan_coverage": 100,
  "milestones_validated": true
}
```

### 2.5 输出 SSOT

| SSOT 类型 | 位置 | 状态 | 用途 |
|-----------|------|------|------|
| **RELEASE** | `spec/releases/release-{id}.yaml` | scope_frozen → closed | 版本交付主对象 |
| **DEVPLAN** | `spec/devplans/devplan-{id}.yaml` | draft → frozen | 开发计划 |
| **TESTPLAN** | `spec/testplans/testplan-{id}.yaml` | draft → frozen | 测试计划 |

---

## 三、L2: DEVPLAN 派生工作流 (Plan Derivation)

### 3.1 工作流定位

| 属性 | 值 |
|------|-----|
| **工作流 ID** | `workflow.dev.devplan_management_l2` |
| **模板文件** | `spec-global/departments/dev/workflows/templates/devplan-management-l2-template.yaml` |
| **负责角色** | Tech Lead / Development Team |
| **上游输入** | RELEASE (scope_frozen) + TASK (来自 Delivery Prep) |
| **下游输出** | DEVPLAN (frozen) + Feature Delivery L2 Instances |

### 3.2 输入 SSOT

| SSOT 类型 | 位置 | 状态要求 | 用途 |
|-----------|------|----------|------|
| **RELEASE** | `spec/releases/` | scope_frozen | 派生源 |
| **TASK Bundle** | `spec/tasks/FEAT-*/TASK-*.yaml` | frozen (来自 Delivery Prep) | 组织执行顺序 |
| **TECH** | `spec/tech/` | frozen (来自 Delivery Prep) | 技术实现参考 |

### 3.3 工作流阶段

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  L2: DEVPLAN Management                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐                                                    │
│  │ 1. Dev Plan     │                                                    │
│  │    Init         │                                                    │
│  │                 │                                                    │
│  │  → devplan.yaml │                                                    │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 2. Task         │                                                    │
│  │    Organization │                                                    │
│  │                 │                                                    │
│  │  - Read TASKs   │                                                    │
│  │  - Define order │                                                    │
│  │  - Define lanes │                                                    │
│  │                 │                                                    │
│  │  → task_execution_order.yaml │                                       │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 3. Task         │                                                    │
│  │    Validate     │                                                    │
│  │                 │                                                    │
│  │  - Coverage check│                                                   │
│  │  - Role check   │                                                    │
│  │                 │                                                    │
│  │  → validation_result.json │                                          │
│  │  [gate.dev.task_validate_gate] │                                     │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 4. DEVPLAN      │                                                    │
│  │    Freeze       │                                                    │
│  │                 │                                                    │
│  │  → devplan.yaml (frozen) │                                           │
│  │  [gate.dev.devplan_freeze_gate] │                                    │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 5. Spawn Dev L2 │                                                    │
│  │                 │                                                    │
│  │  - Per TASK:    │                                                    │
│  │    Feature Delivery L2 │                                             │
│  │                 │                                                    │
│  │  → l2-instances/ │                                                   │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 6. Track        │                                                    │
│  │    Progress     │                                                    │
│  │                 │                                                    │
│  │  → progress_report.md │                                              │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 7. Aggregate    │                                                    │
│  │    Results      │                                                    │
│  │                 │                                                    │
│  │  → dev_aggregate_report.md │                                         │
│  └─────────────────┘                                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.4 详细阶段说明

#### Phase 1: Dev Plan Init

**输出**:
```yaml
# spec/devplans/devplan-{release_id}.yaml (draft)
id: devplan-{release_id}
ssot_type: DEVPLAN
status: draft
release_ref: release-{release_id}
created_at: "2026-03-17T10:00:00Z"
```

#### Phase 2: Task Organization

**关键说明**: TASK 对象已在 Delivery Prep 阶段生成，DEVPLAN 不派生 TASK，仅组织执行顺序。

**输出**:
```yaml
# spec/devplans/{release_id}/task_execution_order.yaml
task_execution_order:
  - lane: backend
    priority: P0
    tasks:
      - task_id: TASK-FEAT-001-001
        depends_on: []
        estimated_effort: 4h
      - task_id: TASK-FEAT-002-001
        depends_on: [TASK-FEAT-001-001]
        estimated_effort: 8h
  - lane: frontend
    priority: P0
    tasks:
      - task_id: TASK-FEAT-001-002
        depends_on: [TASK-FEAT-001-001]
        estimated_effort: 4h
```

#### Phase 3: Task Validate

**Gate**: `gate.dev.task_validate_gate` (auto_check)

**检查项**:
```json
{
  "all_feats_covered": true,
  "all_tasks_have_assignee": true,
  "all_dependencies_clear": true,
  "validation_errors": [],
  "validation_warnings": []
}
```

#### Phase 4: DEVPLAN Freeze

**Gate**: `gate.dev.devplan_freeze_gate` (human_approval)

**审批标准**:
- ✅ 所有 FEAT 都有 TASK 覆盖
- ✅ TASK 执行顺序合理
- ✅ 责任人已确认

**输出**:
```yaml
# spec/devplans/devplan-{release_id}.yaml (frozen)
id: devplan-{release_id}
ssot_type: DEVPLAN
status: frozen
release_ref: release-{release_id}
frozen_at: "2026-03-17T14:00:00Z"
task_refs: [TASK-FEAT-001-001, TASK-FEAT-001-002, ...]
```

#### Phase 5: Spawn Dev L2

对每个 TASK 生成 Feature Delivery L2 实例：

```
TASK-FEAT-001-001 ──→ Feature Delivery L2 Instance #1
TASK-FEAT-001-002 ──→ Feature Delivery L2 Instance #2
...
```

每个 L2 实例绑定：
- `formal_ssot_id`: FEAT-ID
- `task_refs`: [TASK-ID]
- `source_refs`: EPIC/SRC refs
- `governing_adrs`: [ADR-026, ...]

### 3.5 输出 SSOT

| SSOT 类型 | 位置 | 状态 | 用途 |
|-----------|------|------|------|
| **DEVPLAN** | `spec/devplans/devplan-{id}.yaml` | frozen | 开发计划冻结 |
| **Feature Delivery L2 Instances** | `.workflow/release-{id}/dev-instances/` | running → completed | 执行实例 |

---

## 四、L2: TESTPLAN 派生工作流 (Plan Derivation)

### 4.1 工作流定位

| 属性 | 值 |
|------|-----|
| **工作流 ID** | `workflow.qa.testplan_management_l2` |
| **模板文件** | `spec-global/departments/qa/workflows/templates/testplan-management-l2-template.yaml` |
| **负责角色** | QA Lead / QA Team |
| **上游输入** | RELEASE (scope_frozen) + FEAT.AC + TECH + TASK |
| **下游输出** | TESTPLAN (frozen) + Test Set 设计资产 |

### 4.2 输入 SSOT

| SSOT 类型 | 位置 | 状态要求 | 用途 |
|-----------|------|----------|------|
| **RELEASE** | `spec/releases/` | scope_frozen | 派生源 |
| **FEAT.acceptance_criteria** | `spec/requirements/FEAT-*.yaml` | frozen | 测试策略依据 |
| **TECH specs** | `spec/tech/` | frozen (来自 Delivery Prep) | 技术实现参考 |
| **TASK Bundle** | `spec/tasks/` | frozen (来自 Delivery Prep) | 实施范围参考 |

### 4.3 工作流阶段

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  L2: TESTPLAN Management                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐                                                    │
│  │ 1. Test Plan    │                                                    │
│  │    Init         │                                                    │
│  │                 │                                                    │
│  │  → testplan.yaml│                                                    │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 2. Test Strategy│                                                    │
│  │    Define       │                                                    │
│  │                 │                                                    │
│  │  - Read FEAT.AC │                                                    │
│  │  - Read TECH    │                                                    │
│  │  - Read TASK    │                                                    │
│  │  - Define scope │                                                    │
│  │                 │                                                    │
│  │  → test_strategy.yaml │                                              │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 3. Test Set     │                                                    │
│  │    Production   │◄── Spawns L3 per FEAT/module                      │
│  │                 │                                                    │
│  │  - Per FEAT:    │                                                    │
│  │    Test Set Production L3 │                                          │
│  │                 │                                                    │
│  │  → test-sets/ts-{module}.yaml │                                      │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 4. Test Set     │                                                    │
│  │    Validate     │                                                    │
│  │                 │                                                    │
│  │  - Coverage check│                                                   │
│  │  - Priority check│                                                   │
│  │  - Traceability │                                                    │
│  │                 │                                                    │
│  │  → validation_result.json │                                          │
│  │  [gate.qa.test_set_validate_gate] │                                  │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 5. TESTPLAN     │                                                    │
│  │    Freeze       │                                                    │
│  │                 │                                                    │
│  │  → testplan.yaml (frozen) │                                          │
│  │  [gate.qa.testplan_freeze_gate] │                                    │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 6. Spawn Test   │                                                    │
│  │    Run L2       │                                                    │
│  │                 │                                                    │
│  │  → test-run-instances/ │                                             │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 7. Track        │                                                    │
│  │    Progress     │                                                    │
│  │                 │                                                    │
│  │  → progress_report.md │                                              │
│  └─────────────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 8. Aggregate    │                                                    │
│  │    Results      │                                                    │
│  │                 │                                                    │
│  │  → test_aggregate_report.md │                                        │
│  └─────────────────┘                                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.4 详细阶段说明

#### Phase 1: Test Plan Init

**输出**:
```yaml
# spec/testplans/testplan-{release_id}.yaml (draft)
id: testplan-{release_id}
ssot_type: TESTPLAN
status: draft
release_ref: release-{release_id}
created_at: "2026-03-17T10:00:00Z"
test_strategy_ref: null  # Phase 2 填充
test_sets: []  # Phase 3 填充
```

#### Phase 2: Test Strategy Define

**输入消费**:
- `FEAT.acceptance_criteria`: 提取可测试特性
- `TECH specs`: 了解技术实现，识别风险区域
- `TASK`: 了解实施范围

**输出**:
```yaml
# spec/testplans/{release_id}/test_strategy.yaml
test_strategy:
  scope:
    smoke_tests:
      - target: "所有 FEAT 的核心功能"
      - priority: P0
    regression_tests:
      - target: "所有 FEAT 的完整 AC"
      - priority: P1
    automation_tests:
      - target: "可自动化的高频测试场景"
      - priority: P2
  milestones:
    - name: "Smoke Complete"
      target_date: "2026-03-26"
    - name: "Regression Complete"
      target_date: "2026-03-28"
  risk_areas:
    - area: "验证码发送后端"
      risk_level: high
      test_focus: "API 容错、限流、备用方案"
    - area: "双登录方式切换"
      risk_level: medium
      test_focus: "状态一致性、切换流畅性"
```

#### Phase 3: Test Set Production

**关键说明**: 此阶段生成 Test Set **设计资产**，用于覆盖度验证。实际执行在 TESTPLAN Freeze 之后。

**L3 模板**: `template.qa.test_set_production_l3`

**L3 阶段**:
1. `requirement_analysis` → 分析 FEAT inputs
2. `strategy_design` → 设计测试策略
3. `test_set_generation` → 生成标准化 YAML
4. `test_set_review` → 审评完整性
5. `output_validation` → Schema 验证

**输出示例**:
```yaml
# qa_specs_dir/test-sets/ts-{module}.yaml
id: ts-{module}
ssot_type: TESTSET
status: frozen
feat_ref: FEAT-001
test_cases:
  - id: tc-001
    type: smoke
    priority: P0
    description: "验证码发送 API 正常调用"
    steps:
      - step: "调用 /api/send-code"
      - step: "验证返回 200"
      - step: "验证短信送达"
    expected: "API 返回成功，用户收到验证码"
    trace_to:
      - FEAT-001.AC-001
  - id: tc-002
    type: regression
    priority: P1
    description: "验证码发送失败备用方案"
    steps: [...]
    expected: "主方案失败时自动切换备用方案"
    trace_to:
      - FEAT-001.AC-002
```

#### Phase 4: Test Set Validate

**Gate**: `gate.qa.test_set_validate_gate` (auto_check)

**检查项**:
```json
{
  "all_feats_covered": true,
  "priority_distribution_valid": true,
  "traceability_complete": true,
  "validation_errors": [],
  "validation_warnings": []
}
```

#### Phase 5: TESTPLAN Freeze

**Gate**: `gate.qa.testplan_freeze_gate` (human_approval)

**审批标准**:
- ✅ 所有 FEAT 都有 Test Set 覆盖
- ✅ Test Set 优先级分布合理
- ✅ 测试策略清晰
- ✅ 追溯性完整

**输出**:
```yaml
# spec/testplans/testplan-{release_id}.yaml (frozen)
id: testplan-{release_id}
ssot_type: TESTPLAN
status: frozen
release_ref: release-{release_id}
frozen_at: "2026-03-17T16:00:00Z"
test_strategy_ref: "spec/testplans/{release_id}/test_strategy.yaml"
test_set_refs:
  - ts-module-001
  - ts-module-002
```

### 4.5 输出 SSOT

| SSOT 类型 | 位置 | 状态 | 用途 |
|-----------|------|------|------|
| **TESTPLAN** | `spec/testplans/testplan-{id}.yaml` | frozen | 测试计划冻结 |
| **Test Set 设计资产** | `qa_specs_dir/test-sets/ts-*.yaml` | frozen | 测试执行依据 |
| **Test Run L2 Instances** | `.workflow/testplan-{id}/test-run-instances/` | running → completed | 执行实例 |

---

## 五、上下游输入输出链路

### 5.1 完整数据流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SSOT Data Flow                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Product Pipeline:                                                      │
│  ┌──────┐    ┌──────┐    ┌──────┐    ┌─────────────┐                   │
│  │ RAW  │───→│ SRC  │───→│ EPIC │───→│ FEAT Bundle │                   │
│  └──────┘    └──────┘    └──────┘    │ + Delivery  │                   │
│                                       │   Prep      │                   │
│                                       └──────┬──────┘                   │
│                                              │                          │
│                                              ▼                          │
│  Dev Governance (L1):                         │                          │
│  ┌────────────────────────────────────────────┴───┐                      │
│  │              RELEASE (scope_frozen)            │                      │
│  │              ↓                                 │                      │
│  │         ┌────┴────┐                            │                      │
│  │         ↓         ↓                            │                      │
│  │    DEVPLAN    TESTPLAN                         │                      │
│  │    (draft)    (draft)                          │                      │
│  └────────┬─────────┬─────────────────────────────┘                      │
│           │         │                                                    │
│           │         ▼                                                    │
│           │    ┌────────────────────────────┐                           │
│           │    │ Test Set Production L3     │                           │
│           │    │ (生成设计资产)              │                           │
│           │    └────────────────────────────┘                           │
│           │                                                             │
│           ▼                                                             │
│  ┌────────────────────────────────────────┐                             │
│  │ Feature Delivery L2 (per TASK)         │                             │
│  │  → tech_design → contract → be/fe →    │                             │
│  │  → integration → evidence → smoke_gate │                             │
│  └────────────────────────────────────────┘                             │
│           │                                                             │
│           ▼                                                             │
│  ┌────────────────────────────────────────┐                             │
│  │ Test Plan Execution L2                 │                             │
│  │  → env_provision → test_execution →    │                             │
│  │  → report → exit_eval                  │                             │
│  └────────────────────────────────────────┘                             │
│                                                                         │
│  SSOT 回流：                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  TASK 完成 → DEVPLAN 更新 (完成率、证据)                        │   │
│  │  Test Set 完成 → TESTPLAN 更新 (通过率、Bug)                     │   │
│  │  DEVPLAN/TESTPLAN 汇总 → RELEASE 更新 (决策支持)                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 SSOT 对象状态机

#### RELEASE 状态机

```
INIT ──→ SCOPE_INIT ──→ SCOPE_VALIDATE ──→ SCOPE_FROZEN
                                                    │
                                                    ▼
                                           PLAN_DERIVE
                                                    │
                                                    ▼
                                           PLAN_VALIDATED
                                                    │
                                                    ▼
                            ┌───────────────────┬───┴───┬───────────────────┐
                            ▼                   ▼       ▼                   ▼
                     DEV_EXECUTION       QA_EXECUTION   COVERAGE_CHECK    GO_NOGO
                            │                   │       │                   │
                            └───────────────────┴───────┴───────────────────┘
                                                    │
                     ┌──────────────────────────────┼──────────────────────────────┐
                     ▼                              ▼                              ▼
                RELEASED                    CONDITIONAL_RELEASED              NOGO
                     │                              │                              │
                     ▼                              ▼                              ▼
                  CLOSED                         CLOSED                        FAILED
```

#### DEVPLAN 状态机

```
DRAFT ──→ ORGANIZING ──→ VALIDATING ──→ FROZEN ──→ EXECUTING ──→ COMPLETED
                              │                                    │
                              ▼                                    ▼
                          FAILED                               AGGREGATED
```

#### TESTPLAN 状态机

```
DRAFT ──→ STRATEGY_DEFINE ──→ TESTSET_PRODUCTION ──→ VALIDATING
                                                             │
                                                             ▼
                                                         FROZEN
                                                             │
                                                             ▼
                                                         EXECUTING
                                                             │
                                                             ▼
                                                         COMPLETED/AGGREGATED
```

### 5.3 关键约束

| 约束 ID | 约束内容 | 违反处理 |
|---------|----------|----------|
| **C001** | RELEASE 必须绑定至少一个 frozen FEAT | 空 RELEASE 不允许创建 |
| **C002** | 必须先冻结 Scope 才能派生 DEVPLAN/TESTPLAN | 禁止在 scope_freeze 之前执行 plan_derivation |
| **C003** | Dev 执行必须在 QA 执行之前完成 | QA 不允许在 Dev L2 未完成前开始 |
| **C004** | 所有 RELEASE 必须经过 Go/No-Go 决策 | 禁止跳过决策直接关闭 RELEASE |
| **C005** | 所有 TASK 必须通过 Smoke Gate | Smoke Gate 失败，TASK 标记为 failed |
| **C006** | Test Set 必须 trace 到 FEAT AC | 追溯性验证失败，Test Set 不允许冻结 |

---

## 六、现有实现状态

### 6.1 已完成的工作流模板

| 模板 ID | 文件路径 | 状态 |
|---------|----------|------|
| `workflow.dev.release_delivery_l1` | `spec-global/departments/dev/workflows/templates/release-delivery-l1-template.yaml` | ✅ 完整 |
| `workflow.dev.devplan_management_l2` | `spec-global/departments/dev/workflows/templates/devplan-management-l2-template.yaml` | ✅ 完整 |
| `workflow.qa.testplan_management_l2` | `spec-global/departments/qa/workflows/templates/testplan-management-l2-template.yaml` | ✅ 完整 |
| `template.dev.feature_delivery_l2` | `spec-global/departments/dev/workflows/templates/feature-delivery-l2-template.yaml` | ✅ 完整 |
| `template.qa.test_set_production_l3` | `spec-global/departments/qa/workflows/templates/test-set-production-l3-template.yaml` | ✅ 完整 |

### 6.2 已完成的 SSOT 规范

| 规范 ID | 文件路径 | 状态 |
|---------|----------|------|
| `FEAT-SRC-046-001` | `spec/requirements/SRC-046/FEAT-SRC-046-001__...md` | ✅ Frozen |
| `FEAT-SRC-046-002` | `spec/requirements/SRC-046/FEAT-SRC-046-002__...md` | ✅ Frozen |
| `FEAT-SRC-046-003` | `spec/requirements/SRC-046/FEAT-SRC-046-003__...md` | ✅ Frozen |
| `FEAT-SRC-046-004` | `spec/requirements/SRC-046/FEAT-SRC-046-004__...md` | ✅ Frozen |

### 6.3 缺失环节

| 缺失项 | 描述 | 优先级 |
|--------|------|--------|
| **RELEASE 实例** | 尚无正式的 RELEASE YAML 实例 | P0 |
| **DEVPLAN 实例** | 尚无正式的 DEVPLAN YAML 实例 | P0 |
| **TESTPLAN 实例** | 尚无正式的 TESTPLAN YAML 实例 | P0 |
| **Go/No-Go 决策实现** | Gate 实现尚未完成 | P1 |
| **SSOT 回流机制** | 自动回流尚未实现 | P1 |

---

## 七、后续行动

### 7.1 立即行动 (本周)

- [ ] 创建首个 RELEASE 实例 (release-001)
- [ ] 执行 Scope Management 工作流
- [ ] 派生首个 DEVPLAN 和 TESTPLAN

### 7.2 短期行动 (2-4 周)

- [ ] 实现 Go/No-Go Gate 审批服务
- [ ] 实现 SSOT 回流机制
- [ ] 创建完整的 SSOT 实例链

### 7.3 中期行动 (1-3 月)

- [ ] 集成 CI/CD 部署流程
- [ ] 实现自动覆盖度检查
- [ ] 完善度量指标收集

---

## 附录 A: 工作流模板索引

| 层级 | 工作流 | 模板文件 | 负责角色 |
|------|--------|----------|----------|
| L1 | RELEASE Delivery | `release-delivery-l1-template.yaml` | Release Manager |
| L2 | DEVPLAN Management | `devplan-management-l2-template.yaml` | Tech Lead |
| L2 | TESTPLAN Management | `testplan-management-l2-template.yaml` | QA Lead |
| L3 | Feature Delivery | `feature-delivery-l2-template.yaml` | Developer |
| L3 | Test Set Production | `test-set-production-l3-template.yaml` | QA Engineer |

## 附录 B: SSOT 对象字段索引

| SSOT 类型 | 核心字段 | 引用字段 |
|-----------|----------|----------|
| RELEASE | `id`, `status`, `feat_refs`, `release_window` | `parent_epic_ref` |
| DEVPLAN | `id`, `status`, `release_ref`, `task_refs` | `task_execution_order` |
| TESTPLAN | `id`, `status`, `release_ref`, `test_set_refs` | `test_strategy_ref` |
| TESTSET | `id`, `status`, `feat_ref`, `test_cases` | `trace_to` (FEAT AC) |
