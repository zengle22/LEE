---
id: ADR-027
title: 渐进式工作流落地设计 (Incremental Workflow Implementation)
version: v1
workflow_instance_id: wf-adr-027-20260317
source_refs: []
owner: dev-governance
tags:
  - workflow
  - incremental-design
  - l2-l3-first
status: draft
ssot_type: adr
properties:
  design_kind: architecture_decision_record
  supersedes: []
---

# ADR-027: 渐进式工作流落地设计

## 1. 决策背景

### 1.1 问题陈述

ADR-026 定义了完整的 L1/L2/L3 三层工作流架构，但 L1 实现复杂度高（需要状态机、决策门禁、跨部门协调），短期内难以落地验证核心价值。

### 1.2 核心洞察

交付轴的核心价值在于：
1. **FEAT → DEVPLAN/TESTPLAN 的派生链路**（可追溯性）
2. **DEVPLAN/TESTPLAN → 执行工作流的驱动**（可执行性）
3. **执行结果 → SSOT 的回流**（可度量性）

L1 的 Scope Management 和 Go/No-Go 决策是治理需求，而非交付核心路径。

### 1.3 决策

**先实现 L2+L3 核心链路，L1 作为后续规划**。

---

## 2. 设计方案

### 2.1 阶段一：L2+L3 核心链路（MVP）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    L2: Feature-to-Plan Orchestration                    │
│  workflow.core.feat2plan                                                │
│  输入：FEAT Bundle (frozen)                                             │
│  输出：DEVPLAN (frozen) + TESTPLAN (frozen)                             │
└─────────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌───────────┐       ┌───────────┐       ┌───────────┐
    │  L3 #1    │       │  L3 #2    │       │  L3 #3    │
    │ FEAT2     │       │ RELEASE2  │       │ RELEASE2  │
    │ RELEASE   │       │ DEVPLAN   │       │ TESTPLAN  │
    │           │       │           │       │           │
    │ 输入：    │       │ 输入：    │       │ 输入：    │
    │ - FEAT    │       │ - RELEASE │       │ - RELEASE │
    │ 输出：    │       │ - TASK    │       │ - FEAT.AC │
    │ - RELEASE │       │ 输出：    │       │ - TECH    │
    │           │       │ - DEVPLAN │       │ 输出：    │
    │           │       │           │       │ - TESTPLAN│
    └───────────┘       └───────────┘       └───────────┘
                            │                   │
                            ▼                   ▼
                    ┌───────────────┐   ┌───────────────┐
                    │ Dev Execution │   │ QA Execution  │
                    │ (现有工作流)   │   │ (现有工作流)   │
                    └───────────────┘   └───────────────┘
```

### 2.2 L3 工作流定义

#### L3-1: FEAT2RELEASE

| 属性 | 值 |
|------|-----|
| **模板 ID** | `template.core.feat2release` |
| **输入** | FEAT Bundle (frozen) |
| **输出** | RELEASE (draft) |
| **职责** | 生成 RELEASE 对象，绑定 FEAT refs |

**阶段流程**:
```
1. release_init
   → 生成 RELEASE-{id}.yaml
   → 绑定 feat_refs: [FEAT-001, FEAT-002, ...]
   → 设置 release_type, release_window

2. release_validate
   → 验证 FEAT Bundle 非空
   → 验证所有 FEAT 为 frozen 状态
   → 生成 dependency_graph.md

3. release_output
   → 输出 RELEASE (draft) 到下游 L3
```

**输出示例**:
```yaml
# spec/releases/release-{id}.yaml
id: release-{id}
ssot_type: RELEASE
status: draft  # 注意：不是 frozen，因为还未经历 Scope Freeze
feat_refs: [FEAT-001, FEAT-002, FEAT-003]
release_window:
  start_date: "2026-03-17"
  end_date: "2026-03-31"
release_type: minor
derived_from:
  - FEAT-001
  - FEAT-002
  - FEAT-003
```

---

#### L3-2: RELEASE2DEVPLAN

| 属性 | 值 |
|------|-----|
| **模板 ID** | `template.core.release2devplan` |
| **输入** | RELEASE (draft) + TASK Bundle (来自 Delivery Prep) |
| **输出** | DEVPLAN (frozen) |
| **职责** | 从 RELEASE 派生 DEVPLAN，组织 TASK 执行顺序 |

**关键说明**: TASK 对象已在 Delivery Prep 阶段生成，本 L3 不派生 TASK，仅组织执行顺序

**阶段流程**:
```
1. devplan_init
   → 生成 DEVPLAN-{release_id}.yaml (draft)
   → 绑定 release_ref

2. task_organization
   → 读取 spec/tasks/{FEAT-ID}/TASK-*.yaml
   → 定义 task_execution_order (按依赖关系排序)
   → 定义 workstream 分组 (backend/frontend/integration)
   → 分配责任人 (assignees)

3. task_validate
   → 验证所有 FEAT 都有 TASK 覆盖
   → 验证 TASK 依赖关系清晰
   → 验证责任人已确认
   → Gate: gate.dev.task_validate_gate (auto_check)

4. devplan_freeze
   → 锁定 task_refs，禁止增删
   → 标记 DEVPLAN.status = "frozen"
   → Gate: gate.dev.devplan_freeze_gate (human_approval)
   → 审批人：tech_lead, release_manager
```

**输入 Contract**:
```yaml
l3_input_schema:
  required_fields:
    - release_ref: "release-{id}"
    - task_bundle: "spec/tasks/{FEAT-ID}/TASK-*.yaml"
    - feat_bundle_refs: ["FEAT-001", "FEAT-002"]
```

**输出 Contract**:
```yaml
l3_output_schema:
  required_fields:
    - devplan_freeze: "spec/devplans/devplan-{id}.yaml"
    - task_execution_order: "spec/devplans/{id}/task_execution_order.yaml"
    - validation_result: "{all_feats_covered: bool, errors: []}"
```

**输出示例**:
```yaml
# spec/devplans/devplan-{release_id}.yaml
id: devplan-{release_id}
ssot_type: DEVPLAN
status: frozen
release_ref: release-{release_id}
frozen_at: "2026-03-17T14:00:00Z"
task_refs:
  - TASK-FEAT-001-001
  - TASK-FEAT-001-002
  - TASK-FEAT-002-001

# spec/devplans/{release_id}/task_execution_order.yaml
task_execution_order:
  - lane: backend
    priority: P0
    tasks:
      - task_id: TASK-FEAT-001-001
        depends_on: []
        assignee: dev-backend-001
        estimated_effort: 4h
      - task_id: TASK-FEAT-002-001
        depends_on: [TASK-FEAT-001-001]
        assignee: dev-backend-002
        estimated_effort: 8h
  - lane: frontend
    priority: P0
    tasks:
      - task_id: TASK-FEAT-001-002
        depends_on: [TASK-FEAT-001-001]
        assignee: dev-frontend-001
        estimated_effort: 4h
```

---

#### L3-3: RELEASE2TESTPLAN

| 属性 | 值 |
|------|-----|
| **模板 ID** | `template.core.release2testplan` |
| **输入** | RELEASE (draft) + FEAT.AC + TECH + TASK |
| **输出** | TESTPLAN (frozen) + Test Set 设计资产 |
| **职责** | 从 RELEASE 派生 TESTPLAN，生产 Test Set 设计资产 |

**阶段流程**:
```
1. testplan_init
   → 生成 TESTPLAN-{release_id}.yaml (draft)
   → 绑定 release_ref

2. test_strategy_define
   → 读取 FEAT.acceptance_criteria
   → 读取 TECH specs (了解技术实现)
   → 定义测试策略 (smoke/regression/automation)
   → 识别风险区域
   → 生成 test_strategy.yaml

3. test_set_production
   → 对每个 FEAT/module 生成 Test Set 设计资产
   → 定义测试用例 (steps, expected, priority)
   → 建立追溯性 (trace_to FEAT AC)
   → 输出 qa_specs_dir/test-sets/ts-{module}.yaml

4. test_set_validate
   → 验证所有 FEAT 都有 Test Set 覆盖
   → 验证追溯性完整
   → 验证优先级分布合理
   → Gate: gate.qa.test_set_validate_gate (auto_check)

5. testplan_freeze
   → 锁定 test_set_refs，禁止增删
   → 标记 TESTPLAN.status = "frozen"
   → Gate: gate.qa.testplan_freeze_gate (human_approval)
   → 审批人：qa_lead, release_manager
```

**输入 Contract**:
```yaml
l3_input_schema:
  required_fields:
    - release_ref: "release-{id}"
    - feat_acceptance_criteria: "spec/requirements/FEAT-*.yaml#.acceptance_criteria"
    - tech_specs: "spec/tech/{FEAT-ID}/tech.yaml"
    - task_bundle: "spec/tasks/{FEAT-ID}/TASK-*.yaml"
```

**输出 Contract**:
```yaml
l3_output_schema:
  required_fields:
    - testplan_freeze: "spec/testplans/testplan-{id}.yaml"
    - test_strategy: "spec/testplans/{id}/test_strategy.yaml"
    - test_set_assets: "qa_specs_dir/test-sets/ts-*.yaml"
    - validation_result: "{all_feats_covered: bool, traceability_complete: bool}"
```

**输出示例**:
```yaml
# spec/testplans/testplan-{release_id}.yaml
id: testplan-{release_id}
ssot_type: TESTPLAN
status: frozen
release_ref: release-{release_id}
frozen_at: "2026-03-17T16:00:00Z"
test_strategy_ref: "spec/testplans/{id}/test_strategy.yaml"
test_set_refs:
  - ts-module-001
  - ts-module-002

# qa_specs_dir/test-sets/ts-module-001.yaml
id: ts-module-001
ssot_type: TESTSET
status: frozen
feat_ref: FEAT-001
test_cases:
  - id: tc-001
    type: smoke
    priority: P0
    description: "验证码发送 API 正常调用"
    steps:
      - step: "调用 POST /api/send-code"
      - step: "验证返回状态码 200"
      - step: "验证用户收到短信"
    expected: "API 返回成功，用户收到验证码"
    trace_to:
      - FEAT-001.AC-001
  - id: tc-002
    type: regression
    priority: P1
    description: "主方案失败时自动切换备用方案"
    steps: [...]
    expected: "备用方案启动，用户仍能收到验证码"
    trace_to:
      - FEAT-001.AC-002
```

---

### 2.3 L2 工作流定义

#### L2: FEAT2PLAN

| 属性 | 值 |
|------|-----|
| **模板 ID** | `workflow.core.feat2plan` |
| **模板文件** | `spec-global/workflows/core/feat2plan-l2-template.yaml` |
| **输入** | FEAT Bundle (frozen) |
| **输出** | DEVPLAN (frozen) + TESTPLAN (frozen) |
| **负责角色** | Tech Lead + QA Lead |

**编排逻辑**:
```yaml
stages:
  - id: generate_release
    name: "Generate RELEASE"
    steps:
      - id: run_feat2release
        kind: skill
        skill_id: skill.orchestrator.run_l3
        l3_template: template.core.feat2release
        outputs:
          - release_draft

  - id: derive_plans
    name: "Derive DEVPLAN and TESTPLAN"
    steps:
      - id: run_release2devplan
        kind: skill
        skill_id: skill.orchestrator.run_l3
        l3_template: template.core.release2devplan
        depends_on: [run_feat2release]
        inputs:
          - release_draft
          - task_bundle  # 来自 Delivery Prep
        outputs:
          - devplan_freeze

      - id: run_release2testplan
        kind: skill
        skill_id: skill.orchestrator.run_l3
        l3_template: template.core.release2testplan
        depends_on: [run_feat2release]
        parallel_with: [run_release2devplan]
        inputs:
          - release_draft
          - feat_acceptance_criteria
          - tech_specs
        outputs:
          - testplan_freeze

  - id: output_contract
    name: "Output Contract"
    steps:
      - id: validate_outputs
        kind: agent
        description: "验证 DEVPLAN 和 TESTPLAN 都已冻结"
        depends_on: [run_release2devplan, run_release2testplan]
```

**执行策略**:
- `run_release2devplan` 和 `run_release2testplan` **可并行执行**
- 两者都依赖 `run_feat2release` 的输出 (RELEASE draft)

---

### 2.4 与现有工作流的集成

#### 驱动 Dev 执行工作流

```
L2 FEAT2PLAN 完成后:
  输出：DEVPLAN (frozen) + task_execution_order.yaml

触发下游:
  workflow.dev.feature_delivery_l2 (已有)
  输入：
    - formal_ssot_id: FEAT-ID
    - task_refs: [TASK-ID] (来自 DEVPLAN)
    - source_refs: [EPIC-ID, SRC-ID]
    - governing_adrs: [ADR-026, ...]
  执行：tech_design → contract → be/fe → integration → evidence → smoke_gate
```

#### 驱动 QA 执行工作流

```
L2 FEAT2PLAN 完成后:
  输出：TESTPLAN (frozen) + test_strategy.yaml + Test Set 设计资产

触发下游:
  workflow.qa.test_plan_execution (已有)
  输入:
    - testplan_ref: testplan-{id}
    - test_set_refs: [ts-001, ts-002]
    - test_environment: qa/staging
  执行：env_provision → test_set_execution → report → exit_eval
```

---

## 3. 与 ADR-026 的关系

### 3.1 架构对比

| 维度 | ADR-026 (完整版) | ADR-027 (渐进版) |
|------|------------------|------------------|
| **L1** | 完整的 Release Delivery DAG | 暂不实现，留待后续 |
| **L2** | DEVPLAN/TESTPLAN Management | FEAT2PLAN (简化编排) |
| **L3** | Feature Delivery + Test Set Production | FEAT2RELEASE + RELEASE2DEVPLAN + RELEASE2TESTPLAN |
| **门禁** | 4 个 Gate (scope_freeze, plan_validate, go_nogo, release_close) | 2 个 Gate (task_validate, devplan_freeze, test_set_validate, testplan_freeze) |
| **状态机** | RELEASE 14 状态 | RELEASE 3 状态 (draft → frozen → closed) |

### 3.2 演进路径

```
Phase 1 (ADR-027 MVP):
  L2: FEAT2PLAN
  L3: FEAT2RELEASE + RELEASE2DEVPLAN + RELEASE2TESTPLAN
  输出：DEVPLAN + TESTPLAN (frozen)
  驱动：现有 Dev/QA 执行工作流

Phase 2 (ADR-026 核心):
  L1: Scope Management (简化版)
  - scope_init → scope_validate → scope_freeze
  L2: 保持 ADR-027 设计
  新增：RELEASE 状态管理

Phase 3 (ADR-026 完整):
  L1: 完整 Release Delivery DAG
  - Dev Execution + QA Execution + Release Closure
  - Go/No-Go 决策门禁
  - 完整状态机
```

---

## 4. 实施计划

### 4.1 Phase 1: L3 模板实现（1-2 周）

| 任务 | 描述 | 优先级 |
|------|------|--------|
| **T1** | 实现 `template.core.feat2release` | P0 |
| **T2** | 实现 `template.core.release2devplan` | P0 |
| **T3** | 实现 `template.core.release2testplan` | P0 |
| **T4** | 实现 Gate: `task_validate_gate`, `devplan_freeze_gate` | P0 |
| **T5** | 实现 Gate: `test_set_validate_gate`, `testplan_freeze_gate` | P0 |

### 4.2 Phase 2: L2 编排实现（1 周）

| 任务 | 描述 | 优先级 |
|------|------|--------|
| **T6** | 实现 `workflow.core.feat2plan` 编排逻辑 | P0 |
| **T7** | 实现 L3 调用和并行执行 | P0 |
| **T8** | 实现输出验证 | P1 |

### 4.3 Phase 3: 端到端验证（1 周）

| 任务 | 描述 | 优先级 |
|------|------|--------|
| **T9** | 创建测试 FEAT Bundle | P0 |
| **T10** | 执行 FEAT2PLAN 完整流程 | P0 |
| **T11** | 验证 DEVPLAN 驱动 Dev 工作流 | P0 |
| **T12** | 验证 TESTPLAN 驱动 QA 工作流 | P0 |
| **T13** | 验证 SSOT 回流机制 | P1 |

---

## 5. 关键设计决策

### 5.1 RELEASE 对象定位

**决策**: 在渐进版中，RELEASE 是 L3 生成的**中间产物**，而非治理对象

| 属性 | 完整版 (ADR-026) | 渐进版 (ADR-027) |
|------|------------------|------------------|
| **创建时机** | L1 Scope Init (人类创建) | L3 FEAT2RELEASE (自动生成) |
| **状态** | 14 状态机 | 3 状态 (draft → frozen → closed) |
| **职责** | 交付主链起点 | FEAT → DEVPLAN/TESTPLAN 的中间载体 |
| **冻结时机** | Scope Freeze Gate (人类审批) | DEVPLAN/TESTPLAN Freeze 时连带冻结 |

### 5.2 Task 组织 vs Task 派生

**决策**: DEVPLAN 不派生 TASK，仅组织已有 TASK 的执行顺序

**理由**:
1. TASK 在 Delivery Prep 阶段已生成并冻结
2. 避免重复生成和状态不一致
3. 符合"单一事实来源"原则

**实现**:
```yaml
# Delivery Prep 输出
spec/tasks/FEAT-001/
  ├── TASK-FEAT-001-001.yaml
  └── TASK-FEAT-001-002.yaml

# DEVPLAN 组织 (非派生)
spec/devplans/{release_id}/task_execution_order.yaml
  → 引用已有 TASK，定义执行顺序和责任人
```

### 5.3 Test Set 两阶段生命周期

**决策**: Test Set 设计资产在 TESTPLAN Freeze 前生产，实际执行在 Freeze 后

**理由**:
1. 设计资产用于验证 TESTPLAN 覆盖度
2. Freeze 前验证，避免冻结后发现遗漏
3. 执行阶段可能修改测试用例（如环境适配），但不影响设计资产

**实现**:
```yaml
Phase 1: Test Set Production (L3)
  → qa_specs_dir/test-sets/ts-*.yaml (设计资产，frozen)
  → 用于覆盖度验证

Phase 2: Test Set Execution (下游 QA 工作流)
  → 执行实际测试
  → 可能调整测试数据/环境，但不修改设计资产
```

---

## 6. 验收标准

### 6.1 功能验收

- [ ] FEAT Bundle 输入后，自动生成 RELEASE 对象
- [ ] RELEASE 可正确派生 DEVPLAN 和 TESTPLAN
- [ ] DEVPLAN 包含所有 FEAT 的 TASK，执行顺序合理
- [ ] TESTPLAN 包含所有 FEAT 的 Test Set，追溯性完整
- [ ] DEVPLAN/TESTPLAN 可驱动现有 Dev/QA 工作流
- [ ] 执行结果可回传到 SSOT

### 6.2 质量验收

- [ ] 所有 Gate 正确执行（自动检查 + 人类审批）
- [ ] 错误场景正确处理（如 FEAT 未冻结、TASK 缺失）
- [ ] 输出 YAML Schema 验证通过
- [ ] 端到端执行成功率 >= 95%

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| RELEASE 对象被误用 | 中 | 明确标记 status=draft，不可直接用于发布 |
| TASK 组织逻辑复杂 | 中 | 优先支持简单依赖（DAG），复杂依赖后续优化 |
| Test Set 追溯性验证失败 | 高 | 强制执行 trace_to FEAT AC 验证 |
| 与现有工作流集成失败 | 高 | 优先复用现有输入输出 Contract |

---

## 8. 后续演进

### 8.1 L1  Scope Management（Phase 2）

```yaml
新增工作流：
  workflow.dev.scope_management
  步骤:
    - scope_init: 人类创建 RELEASE 对象
    - scope_validate: 验证 FEAT Bundle
    - scope_freeze: 人类审批，锁定 scope

修改:
  template.core.feat2release → 改为从 scope_frozen 的 RELEASE 开始
```

### 8.2 L1 Release Closure（Phase 3）

```yaml
新增工作流：
  workflow.dev.release_closure
  步骤:
    - coverage_check: 验证 Dev/QA 完成率
    - go_nogo_decision: 人类决策门禁
    - release_close: 关闭 RELEASE，归档证据

新增状态:
  RELEASE.status: closed / conditional_released / no_go
```

### 8.3 完整 L1 DAG（Phase 4）

```yaml
整合为完整 DAG:
  Scope Management → Plan Derivation → Dev Execution → QA Execution → Release Closure
```

---

## 9. 结论

渐进式设计优先实现 L2+L3 核心链路，快速验证 SSOT 派生和执行驱动的价值。L1 作为后续规划，在核心链路稳定后逐步引入治理门禁和状态机。

**核心优势**:
- ✅ 快速落地：2-4 周可完成 MVP
- ✅ 风险可控：失败不影响现有流程
- ✅ 价值明确：直接解决"FEAT 如何到执行"的核心问题
- ✅ 演进清晰：Phase 2/3/4 路径明确
