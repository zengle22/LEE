---
id: SSFLOW-002
title: 三层工作流详细拆解 (L1/L2/L3 Workflow Deep Dive)
version: v1
created_at: 2026-03-17
owner: dev-governance
tags:
  - workflow
  - l1
  - l2
  - l3
  - handoff
---

# 三层工作流详细拆解 (L1/L2/L3 Workflow Deep Dive)

## 一、架构总览

### 1.1 三层模型定位

| 层级 | 名称 | 定位 | 负责角色 | 执行周期 |
|------|------|------|----------|----------|
| **L1** | Release Delivery | 版本交付主链 | Release Manager | 2-4 周/RELEASE |
| **L2** | Plan Management | 计划管理 | Tech Lead / QA Lead | 跟随 RELEASE 周期 |
| **L3** | Execution | 详细执行 | Developer / QA Engineer | 1-3 天/TASK |

### 1.2 完整层级关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         L1: Release Delivery                            │
│  输入：FEAT Bundle (frozen)                                             │
│  输出：RELEASE + DEVPLAN + TESTPLAN (全部 frozen)                       │
│  决策：Scope Freeze, Go/No-Go                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                ┌───────────────────┴───────────────────┐
                ▼                                       ▼
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│   L2: DEVPLAN Management        │     │   L2: TESTPLAN Management       │
│   输入：RELEASE + TASK Bundle   │     │   输入：RELEASE + FEAT.AC+TECH  │
│   输出：DEVPLAN (frozen)        │     │   输出：TESTPLAN (frozen)       │
│   决策：Dev Plan Freeze         │     │   决策：Test Plan Freeze        │
└─────────────────────────────────┘     └─────────────────────────────────┘
                │                                       │
                ▼                                       ▼
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│   L2: Feature Delivery (per TASK)│    │   L2: Test Plan Execution       │
│   输入：TASK + FEAT             │     │   输入：TESTPLAN + Test Set     │
│   输出：Evidence Pack           │     │   输出：Test Results            │
└─────────────────────────────────┘     └─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         L3: Detailed Execution                          │
│   - tech_design → contract_design → backend_dev → frontend_dev         │
│   - integration → evidence_pack → smoke_gate                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、L1: Release Delivery 工作流详解

### 2.1 工作流元数据

| 属性 | 值 |
|------|-----|
| **模板 ID** | `workflow.dev.release_delivery_l1` |
| **模板文件** | `spec-global/departments/dev/workflows/templates/release-delivery-l1-template.yaml` |
| **版本** | 1.0 |
| **负责部门** | Dev Governance |
| **负责角色** | Release Manager |

### 2.2 输入 Handoff

#### 上游工作流：Product Pipeline (Feat-to-Delivery-Prep)

```
上游工作流：workflow.product.feat_to_delivery_prep
触发条件：FEAT Bundle 完成冻结 + Delivery Prep 完成
Handoff 产物:
├── spec/requirements/FEAT-*.yaml (frozen)
├── spec/delivery-prep/{FEAT-ID}/ui.yaml (frozen)
├── spec/delivery-prep/{FEAT-ID}/tech.yaml (frozen)
└── spec/tasks/{FEAT-ID}/TASK-*.yaml (frozen)

Handoff 门禁：gate.product.delivery_prep_freeze_gate
审批人：product_owner, tech_lead
```

#### L1 输入参数

```yaml
input_params:
  feat_bundle_refs:
    type: array
    items: string
    required: true
    description: "FEAT IDs to include in this RELEASE"
    示例：["FEAT-001", "FEAT-002", "FEAT-003"]

  release_type:
    type: string
    enum: [major, minor, patch, hotfix]
    required: true
    description: "Release type for versioning"

  release_window:
    type: object
    required: true
    properties:
      start_date: "2026-03-17"
      end_date: "2026-03-31"
```

### 2.3 阶段详解

#### Stage 1: Scope Management

| 步骤 | ID | 类型 | 描述 | 输入 | 输出 | Gate |
|------|-----|------|------|------|------|------|
| **scope_init** | agent | 初始化 RELEASE 对象 | `feat_bundle_refs`, `release_window` | `spec/releases/release-{id}.yaml` | - |
| **scope_validate** | agent | 验证 FEAT Bundle | RELEASE 对象 | `dependency_graph.md`, `validation_result.json` | `gate.dev.scope_validate_gate` (auto) |
| **scope_freeze** | gate | 冻结 Scope | `validation_result` | `release-{id}.yaml` (scope_frozen) | `gate.dev.scope_freeze_gate` (human) |

**scope_freeze_gate 审批标准**:
```yaml
reviewers:
  - role: release_manager
  - role: product_owner
  - role: tech_lead

approval_criteria:
  - label: "FEAT Bundle 完整"
    criteria: "所有计划内的 FEAT 都已加入且 frozen"
    required: true
  - label: "依赖关系清晰"
    criteria: "dependency_graph 无环，关键路径明确"
    required: true
  - label: "风险可控"
    criteria: "已知风险已记录并有缓解方案"
    required: true
```

#### Stage 2: Plan Derivation

| 步骤 | ID | 类型 | 描述 | 输入 | 输出 | Gate |
|------|-----|------|------|------|------|------|
| **derive_devplan** | agent | 派生 DEVPLAN | RELEASE (scope_frozen) | `devplan-{id}.yaml` (draft) | - |
| **derive_testplan** | agent | 派生 TESTPLAN | RELEASE (scope_frozen) | `testplan-{id}.yaml` (draft) | - |
| **plan_validate** | agent | 验证覆盖度 | DEVPLAN, TESTPLAN | `validation_result.json` | `gate.dev.plan_validate_gate` (auto) |

**并行执行**: `derive_devplan` 和 `derive_testplan` 可并行执行

**plan_validate_gate 检查项**:
```json
{
  "devplan_coverage": 100,
  "testplan_coverage": 100,
  "milestones_validated": true,
  "errors": [],
  "warnings": []
}
```

#### Stage 3: Dev Execution

| 步骤 | ID | 类型 | 描述 | 输入 | 输出 |
|------|-----|------|------|------|------|
| **spawn_dev_l2** | skill | 生成 Dev L2 实例 | `plan_validate` 结果 | `.workflow/release-{id}/dev-instances/` |
| **track_dev_progress** | agent | 跟踪进度 | Dev L2 instances | `dev_progress_report.md` |

**Spawn 规则**:
```yaml
对 DEVPLAN 中每个 TASK:
  - 生成 Feature Delivery L2 instance
  - 绑定 FEAT 和 TASK
  - 执行 L2 流程 (tech_design → contract → be/fe → integration → evidence → smoke_gate)

L2 实例配置:
  template_id: template.dev.feature_delivery_l2
  context:
    formal_ssot_id: FEAT-XXX
    task_refs: [TASK-XXX-XXX]
    source_refs: [EPIC-XXX, SRC-XXX]
    governing_adrs: [ADR-026, ...]
```

#### Stage 4: QA Execution

| 步骤 | ID | 类型 | 描述 | 输入 | 输出 | 前置条件 |
|------|-----|------|------|------|------|----------|
| **spawn_qa_l2** | skill | 生成 QA L2 实例 | `track_dev_progress` | `.workflow/release-{id}/qa-instances/` | `dev_l2_complete_rate >= 100` |
| **track_qa_progress** | agent | 跟踪进度 | QA L2 instances | `qa_progress_report.md` | - |

**关键约束**: QA 执行必须在 Dev L2 完成后开始

#### Stage 5: Release Closure

| 步骤 | ID | 类型 | 描述 | 输入 | 输出 | Gate |
|------|-----|------|------|------|------|------|
| **coverage_check** | agent | 覆盖度检查 | `dev_progress`, `qa_progress` | `coverage_check_result.json` | - |
| **go_nogo_decision** | gate | 发布决策 | `coverage_check`, 进度报告 | `go_nogo_decision.yaml` (frozen) | `gate.dev.go_nogo_gate` (human) |
| **release_close** | agent | 关闭 RELEASE | `go_nogo_decision != No-Go` | `release_close_report.md`, RELEASE (closed) | - |

**Go/No-Go 决策矩阵**:

| 决策 | 条件 | 审批人 |
|------|------|--------|
| **Go** | 所有 FEAT 通过 L2 DoD, 无 P0 Bug, P1 Bug <= 3 | release_manager + product_owner |
| **Conditional Go** | 无 P0 Bug, P1 Bug <= 5, 有 workaround | release_manager + product_owner + tech_lead |
| **No-Go** | 任一 FEAT 未通过 L2 DoD, 或存在 P0 Bug | 任一关键干系人反对 |

### 2.4 输出 Handoff

#### 下游工作流：Deployment Pipeline

```
Handoff 触发：RELEASE.status = "closed"
Handoff 产物:
├── spec/releases/release-{id}.yaml (closed, frozen)
├── spec/releases/{release_id}/release_close_report.md
├── spec/devplans/devplan-{id}.yaml (frozen)
├── spec/testplans/testplan-{id}.yaml (frozen)
└── spec/evidence/{release_id}/evidence_pack/ (归档证据)

下游消费:
  - 部署流水线：执行生产部署
  - 监控告警：激活新版本监控规则
  - 用户通知：发送发布说明
```

---

## 三、L2: DEVPLAN Management 工作流详解

### 3.1 工作流元数据

| 属性 | 值 |
|------|-----|
| **模板 ID** | `workflow.dev.devplan_management_l2` |
| **模板文件** | `spec-global/departments/dev/workflows/templates/devplan-management-l2-template.yaml` |
| **版本** | 1.0 |
| **负责部门** | Development |
| **负责角色** | Tech Lead |

### 3.2 输入 Handoff

#### 上游：RELEASE L1 (scope_freeze 后)

```
触发条件：RELEASE.status = "scope_frozen"
输入 SSOT:
├── spec/releases/release-{id}.yaml (scope_frozen)
└── spec/tasks/{FEAT-ID}/TASK-*.yaml (来自 Delivery Prep, frozen)

关键约束:
  - TASK 在 Delivery Prep 阶段已生成，DEVPLAN 不派生 TASK
  - DEVPLAN 仅组织 TASK 执行顺序和分配责任人
```

### 3.3 阶段详解

#### Phase 1: Dev Plan Init

| 属性 | 值 |
|------|-----|
| **复杂度** | S (直接在 L2 内执行) |
| **输入** | `release-{id}.yaml` (scope_frozen) |
| **输出** | `devplan-{id}.yaml` (draft) |

**输出示例**:
```yaml
# spec/devplans/devplan-{release_id}.yaml
id: devplan-{release_id}
ssot_type: DEVPLAN
status: draft
release_ref: release-{release_id}
created_at: "2026-03-17T10:00:00Z"
task_refs: []  # Phase 2 填充
```

#### Phase 2: Task Organization

| 属性 | 值 |
|------|-----|
| **复杂度** | L ( spawns L3 ) |
| **输入** | `release-{id}.yaml`, `spec/tasks/{FEAT-ID}/TASK-*.yaml` |
| **输出** | `task_execution_order.yaml` |

**关键说明**: TASK 对象已在 Delivery Prep 生成，DEVPLAN 仅组织执行顺序

**输出示例**:
```yaml
# spec/devplans/{release_id}/task_execution_order.yaml
task_execution_order:
  - lane: backend
    priority: P0
    tasks:
      - task_id: TASK-FEAT-001-001
        depends_on: []
        estimated_effort: 4h
        assignee: dev-backend-001
      - task_id: TASK-FEAT-002-001
        depends_on: [TASK-FEAT-001-001]
        estimated_effort: 8h
        assignee: dev-backend-002
  - lane: frontend
    priority: P0
    tasks:
      - task_id: TASK-FEAT-001-002
        depends_on: [TASK-FEAT-001-001]
        estimated_effort: 4h
        assignee: dev-frontend-001
```

#### Phase 3: Task Validate

| 属性 | 值 |
|------|-----|
| **复杂度** | S |
| **Gate** | `gate.dev.task_validate_gate` (auto_check) |
| **输入** | `task_execution_order.yaml` |
| **输出** | `task_validation_result.json` |

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

#### Phase 4: Devplan Freeze

| 属性 | 值 |
|------|-----|
| **复杂度** | S |
| **Gate** | `gate.dev.devplan_freeze_gate` (human_approval) |
| **输入** | `task_validation_result.json` (passed) |
| **输出** | `devplan-{id}.yaml` (frozen) |

**审批标准**:
- ✅ 所有 FEAT 都有 TASK 覆盖
- ✅ TASK 执行顺序合理
- ✅ 责任人已确认

#### Phase 5: Spawn Dev L2

| 属性 | 值 |
|------|-----|
| **复杂度** | L |
| **Spawns** | Feature Delivery L2 (per TASK) |
| **模板** | `template.dev.feature_delivery_l2` |
| **输入** | `devplan-{id}.yaml` (frozen), `TASK-*.yaml` |
| **输出** | `.workflow/devplan-{id}/l2-instances/` |

**L2 实例生成规则**:
```yaml
对每个 TASK in DEVPLAN.task_refs:
  生成 L2 实例:
    id: feature-delivery-{task_id}
    template_id: template.dev.feature_delivery_l2
    context:
      formal_ssot_id: TASK.feat_ref
      source_refs: TASK.source_refs
      governing_adrs: [ADR-026, ADR-008, ...]
      repo_context: TASK.repo
      repo_frontend: TASK.repo_frontend
      repo_backend: TASK.repo_backend
      task_refs: [TASK.id]
```

#### Phase 6: Track Progress

| 属性 | 值 |
|------|-----|
| **复杂度** | S |
| **输入** | Dev L2 instances (running) |
| **输出** | `progress_report.md` |

**跟踪指标**:
- Dev L2 完成率
- 阻塞 TASK 数量
- 预计完成时间

#### Phase 7: Aggregate Results

| 属性 | 值 |
|------|-----|
| **复杂度** | S |
| **输入** | Dev L2 instances (completed) |
| **输出** | `dev_aggregate_report.md` |

**汇总内容**:
- 完成率统计
- Smoke Gate 通过率
- 证据包完整性
- 遗留问题清单

### 3.4 输出 Handoff

#### 下游：Feature Delivery L2 实例

```
Handoff 触发：DEVPLAN.status = "frozen"
Handoff 产物:
├── spec/devplans/devplan-{id}.yaml (frozen)
├── spec/devplans/{id}/task_execution_order.yaml
└── spec/tasks/{FEAT-ID}/TASK-*.yaml (传递给 L2 实例)

下游消费:
  - Feature Delivery L2 实例：执行详细开发流程
  - 进度跟踪系统：更新任务状态
```

---

## 四、L2: TESTPLAN Management 工作流详解

### 4.1 工作流元数据

| 属性 | 值 |
|------|-----|
| **模板 ID** | `workflow.qa.testplan_management_l2` |
| **模板文件** | `spec-global/departments/qa/workflows/templates/testplan-management-l2-template.yaml` |
| **版本** | 1.0 |
| **负责部门** | QA |
| **负责角色** | QA Lead |

### 4.2 输入 Handoff

#### 上游：RELEASE L1 (scope_freeze 后) + Delivery Prep

```
触发条件：RELEASE.status = "scope_frozen"
输入 SSOT:
├── spec/releases/release-{id}.yaml (scope_frozen)
├── spec/requirements/FEAT-*.yaml (frozen, 含 acceptance_criteria)
├── spec/delivery-prep/{FEAT-ID}/tech.yaml (frozen)
└── spec/tasks/{FEAT-ID}/TASK-*.yaml (frozen)
```

### 4.3 阶段详解

#### Phase 1: Test Plan Init

| 属性 | 值 |
|------|-----|
| **复杂度** | S |
| **输入** | `release-{id}.yaml` (scope_frozen) |
| **输出** | `testplan-{id}.yaml` (draft) |

**输出示例**:
```yaml
# spec/testplans/testplan-{release_id}.yaml
id: testplan-{release_id}
ssot_type: TESTPLAN
status: draft
release_ref: release-{release_id}
created_at: "2026-03-17T10:00:00Z"
test_strategy_ref: null  # Phase 2 填充
test_set_refs: []  # Phase 3 填充
```

#### Phase 2: Test Strategy Define

| 属性 | 值 |
|------|-----|
| **复杂度** | M |
| **输入** | `FEAT-*.yaml.AC`, `tech.yaml`, `TASK-*.yaml` |
| **输出** | `test_strategy.yaml` |

**输入消费**:
- `FEAT.acceptance_criteria`: 提取可测试特性
- `TECH specs`: 了解技术实现，识别风险区域
- `TASK`: 了解实施范围

**输出示例**:
```yaml
# spec/testplans/{release_id}/test_strategy.yaml
test_strategy:
  scope:
    smoke_tests:
      - target: "所有 FEAT 的核心功能"
        priority: P0
    regression_tests:
      - target: "所有 FEAT 的完整 AC"
        priority: P1
    automation_tests:
      - target: "可自动化的高频测试场景"
        priority: P2
  milestones:
    - name: "Smoke Complete"
      target_date: "2026-03-26"
    - name: "Regression Complete"
      target_date: "2026-03-28"
  risk_areas:
    - area: "验证码发送后端"
      risk_level: high
      test_focus: "API 容错、限流、备用方案"
```

#### Phase 3: Test Set Production

| 属性 | 值 |
|------|-----|
| **复杂度** | L |
| **Spawns** | Test Set Production L3 (per FEAT/module) |
| **模板** | `template.qa.test_set_production_l3` |
| **输入** | `test_strategy.yaml`, `FEAT-*.yaml.AC` |
| **输出** | `qa_specs_dir/test-sets/ts-{module}.yaml` |

**关键说明**: 此阶段生成 Test Set **设计资产**，用于覆盖度验证。实际执行在 TESTPLAN Freeze 之后。

**L3 阶段流程**:
```
Test Set Production L3:
  Stage 1: requirement_analysis
    → 分析 FEAT inputs，提取可测试特性

  Stage 2: strategy_design
    → 设计测试策略和风险区域

  Stage 3: test_set_generation
    → 生成标准化 Test Set YAML

  Stage 4: test_set_review
    → 审评完整性和可执行性

  Stage 5: output_validation
    → Schema 验证和 FEAT 追溯性检查
```

**L3 输出**:
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
    steps: [...]
    expected: "API 返回成功，用户收到验证码"
    trace_to:
      - FEAT-001.AC-001
```

#### Phase 4: Test Set Validate

| 属性 | 值 |
|------|-----|
| **复杂度** | S |
| **Gate** | `gate.qa.test_set_validate_gate` (auto_check) |
| **输入** | Test Set design assets |
| **输出** | `test_set_validation_result.json` |

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

| 属性 | 值 |
|------|-----|
| **复杂度** | S |
| **Gate** | `gate.qa.testplan_freeze_gate` (human_approval) |
| **输入** | `test_set_validation_result.json` (passed) |
| **输出** | `testplan-{id}.yaml` (frozen) |

**审批标准**:
- ✅ 所有 FEAT 都有 Test Set 覆盖
- ✅ Test Set 优先级分布合理
- ✅ 测试策略清晰
- ✅ 追溯性完整

#### Phase 6: Spawn Test Run L2

| 属性 | 值 |
|------|-----|
| **复杂度** | L |
| **Spawns** | Test Plan Execution L2 |
| **模板** | `template.qa.test_plan_l2` |
| **输入** | `testplan-{id}.yaml` (frozen), Test Set assets |
| **输出** | `.workflow/testplan-{id}/test-run-instances/` |

#### Phase 7-8: Track & Aggregate

| 属性 | 值 |
|------|-----|
| **复杂度** | S |
| **输入** | Test Run L2 instances |
| **输出** | `progress_report.md`, `test_aggregate_report.md` |

### 4.4 输出 Handoff

#### 下游：Test Plan Execution L2

```
Handoff 触发：TESTPLAN.status = "frozen"
Handoff 产物:
├── spec/testplans/testplan-{id}.yaml (frozen)
├── spec/testplans/{id}/test_strategy.yaml
└── qa_specs_dir/test-sets/ts-*.yaml (frozen)

下游消费:
  - Test Plan Execution L2：执行测试用例
  - Bug 跟踪系统：创建 Bug 工单
```

---

## 五、L3: Feature Delivery 工作流详解

### 5.1 工作流元数据

| 属性 | 值 |
|------|-----|
| **模板 ID** | `template.dev.feature_delivery_l2` |
| **模板文件** | `spec-global/departments/dev/workflows/templates/feature-delivery-l2-template.yaml` |
| **版本** | 3.0 |
| **负责部门** | Development |
| **执行角色** | Developer |

### 5.2 输入 Handoff

#### 上游：DEVPLAN Management L2

```
触发条件：Dev L2 instance spawned
输入 Contract:
├── formal_ssot_id: FEAT-ID
├── source_refs: [EPIC-ID, SRC-ID]
├── governing_adrs: [ADR-026, ADR-008, ...]
├── repo_context: path/to/repo
├── repo_frontend: path/to/frontend
├── repo_backend: path/to/backend
├── task_refs: [TASK-ID]
└── acceptance_brief_ref: spec/acceptance/{FEAT-ID}.md
```

### 5.3 阶段详解

#### Phase 1: Tech Design

| 属性 | 值 |
|------|-----|
| **复杂度** | L |
| **Spawns L3** | Yes |
| **L3 模板** | `template.dev.tech_design_l3` |
| **输入** | `FEAT-*.yaml` (frozen) |
| **输出** | `tech_spec.yaml` |

**L3 流程**:
```
Tech Design L3:
  - 读取 FEAT 需求
  - 分析技术影响
  - 设计技术方案
  - 输出 tech_spec.yaml
```

#### Phase 2: Contract Design

| 属性 | 值 |
|------|-----|
| **复杂度** | L |
| **Spawns L3** | Yes |
| **L3 模板** | `template.dev.feature_contract_l3` |
| **输入** | `tech_spec.yaml` |
| **输出** | `contract.yaml` (frozen) |
| **Gate** | `gate.dev.contract_freeze_gate` |

**Handoff**: `tech_spec` → `contract_design`

#### Phase 3-4: Backend/Frontend Dev

| 属性 | Backend Dev | Frontend Dev |
|------|-------------|--------------|
| **复杂度** | L | L |
| **Spawns L3** | Yes | Yes |
| **L3 模板** | `template.dev.feature_be_l3` | `template.dev.feature_fe_l3` |
| **输入** | `contract.yaml` (frozen) | `contract.yaml` (frozen) |
| **输出** | `be_artifacts/` | `fe_artifacts/` |
| **依赖** | `contract_design` | `contract_design` |

**并行执行**: Backend 和 Frontend 开发可并行

#### Phase 5: Integration

| 属性 | 值 |
|------|-----|
| **复杂度** | L |
| **Spawns L3** | Yes |
| **L3 模板** | `template.dev.feature_integration_l3` |
| **输入** | `be_artifacts/`, `fe_artifacts/` |
| **输出** | `integration_report.md` |
| **依赖** | `backend_dev`, `frontend_dev` |

#### Phase 6: Evidence Pack

| 属性 | 值 |
|------|-----|
| **复杂度** | L |
| **Spawns L3** | Yes |
| **L3 模板** | `template.dev.evidence_pack_l3` |
| **输入** | `integration_report.md` |
| **输出** | `evidence_pack.yaml` |

**Evidence Pack 内容**:
```yaml
evidence_pack:
  code_evidence:
    - source_files: [list of files]
    - test_files: [list of test files]
  test_evidence:
    - unit_test_results: {pass_rate: 100%}
    - coverage_report: {line_coverage: 85%}
    - smoke_test_results: {passed: true}
  review_evidence:
    - code_review_record: {reviewers: [...], status: approved}
  design_evidence:
    - tech_spec_ref: path/to/tech_spec.yaml
    - contract_ref: path/to/contract.yaml
```

#### Phase 7: Smoke Gate

| 属性 | 值 |
|------|-----|
| **复杂度** | S |
| **Spawns L3** | No |
| **Gate** | `gate.dev.smoke_gate` (blocking) |
| **输入** | `evidence_pack.yaml` |
| **输出** | smoke_gate_result (passed/failed) |

**Gate 检查项**:
- ✅ Evidence Pack 完整
- ✅ 单元测试通过
- ✅ 代码覆盖率达标
- ✅ Smoke Test 通过

### 5.4 输出 Handoff

#### 回传到 DEVPLAN Management

```
Handoff 触发：Feature Delivery L2 完成
Handoff 产物:
├── evidence_pack.yaml
├── smoke_gate_result (passed)
└── L2 实例状态：completed

SSOT 回流:
  - TASK.status → "completed"
  - TASK.evidence_pack_ref → path/to/evidence_pack.yaml
  - DEVPLAN 进度自动更新
```

---

## 六、L3: Test Set Production 工作流详解

### 6.1 工作流元数据

| 属性 | 值 |
|------|-----|
| **模板 ID** | `template.qa.test_set_production_l3` |
| **模板文件** | `spec-global/departments/qa/workflows/templates/test-set-production-l3-template.yaml` |
| **版本** | 1.2 |
| **负责部门** | QA |
| **执行角色** | QA Engineer |

### 6.2 输入 Handoff

#### 上游：TESTPLAN Management L2

```
触发条件：Test Set Production phase started
输入参数:
├── feat_freeze: spec/requirements/FEAT-*.yaml (preferred)
├── delivery_prep_bundle: spec/delivery-prep/{FEAT-ID}/
├── tech_design: spec/tech/{FEAT-ID}/tech.yaml (optional)
├── governing_adrs: [ADR-026, ...]
└── constraints: [architecture_constraints, process_constraints]
```

### 6.3 阶段详解

#### Stage 1: Requirement Analysis

| 属性 | 值 |
|------|-----|
| **Agent** | `agent.qa.requirement_analyzer` |
| **Gate** | `gate.qa.analysis_review` (human_review) |
| **输入** | `FEAT-*.yaml`, `delivery_prep_bundle` |
| **输出** | `analysis.md`, `ts-{module}.yaml` (draft) |

#### Stage 2: Strategy Design

| 属性 | 值 |
|------|-----|
| **Agent** | `agent.qa.test_strategist` |
| **Gate** | `gate.qa.strategy_review` (human_review) |
| **输入** | `FEAT.AC`, `tech.yaml` |
| **输出** | `strategy-draft.yaml` |

#### Stage 3: Test Set Generation

| 属性 | 值 |
|------|-----|
| **Agent** | `agent.qa.test_set_generator` |
| **输入** | `strategy-draft.yaml` |
| **输出** | `ts-{module}.yaml` (标准化 YAML) |

#### Stage 4: Test Set Review

| 属性 | 值 |
|------|-----|
| **Agent** | `agent.qa.test_set_reviewer` |
| **Gate** | `gate.qa.test_set_approval` (human_approval) |
| **输入** | `ts-{module}.yaml` |
| **输出** | `review-report.md` |

#### Stage 5: Output Validation

| 属性 | 值 |
|------|-----|
| **Agent** | `agent.qa.output_validator` |
| **Gate** | `gate.qa.output_validation` (auto_check) |
| **检查项** | file_existence, schema_validation, traceability |
| **输出** | `validation-report.json`, `validation_status` |

### 6.4 输出 Handoff

#### 回传到 TESTPLAN Management

```
Handoff 触发：Test Set Production L3 完成
Handoff 产物:
├── qa_specs_dir/test-sets/ts-{module}.yaml (frozen)
├── validation_status: "passed"
└── trace_to: FEAT-*.yaml.AC

下游消费:
  - TESTPLAN Freeze：验证覆盖度
  - Test Plan Execution：执行测试用例
```

---

## 七、跨层 Handoff 协议

### 7.1 L1 → L2 Handoff

```yaml
handoff_protocol:
  trigger_condition: "L1 stage completed + Gate passed"

  L1_scope_freeze_to_L2_plan_derivation:
    trigger: "RELEASE.status = scope_frozen"
    artifacts:
      - spec/releases/release-{id}.yaml (scope_frozen)
    consumers:
      - workflow.dev.devplan_management_l2
      - workflow.qa.testplan_management_l2

  L1_plan_validate_to_L2_execution:
    trigger: "gate.dev.plan_validate_gate passed"
    artifacts:
      - spec/releases/{id}/plan_validation_result.json
    consumers:
      - workflow.dev.devplan_management_l2 (spawn_dev_l2)
      - workflow.qa.testplan_management_l2 (spawn_test_run_l2)
```

### 7.2 L2 → L3 Handoff

```yaml
handoff_protocol:
  trigger_condition: "L2 phase started + complexity = L"

  L2_to_L3_spawn:
    trigger: "L2 phase entered with spawns_l3 = true"
    instance_generation:
      template_id: "from phase config"
      context_propagation:
        - formal_ssot_id
        - source_refs
        - governing_adrs
        - repo_context
        - task_refs/feat_ref

  L3_to_L2_return:
    trigger: "L3 instance completed"
    artifacts:
      - phase_id
      - status (completed/failed/blocked)
      - artifacts (phase outputs)
    state_update: "L2 phase status = completed"
```

### 7.3 SSOT 回流机制

```yaml
ssot_backpropagation:
  TASK_completion:
    trigger: "Feature Delivery L2 completed"
    updates:
      - TASK.status = "completed"
      - TASK.evidence_pack_ref = path/to/evidence_pack.yaml
      - TASK.actual_effort = recorded_hours
      - DEVPLAN.progress = auto_recalculated

  TestSet_completion:
    trigger: "Test Run L2 completed"
    updates:
      - TestSet.status = "passed/failed"
      - TestSet.pass_rate = recorded_rate
      - TestSet.bugs = list of found_bugs
      - TESTPLAN.progress = auto_recalculated

  RELEASE_aggregation:
    trigger: "DEVPLAN/TESTPLAN updated"
    updates:
      - RELEASE.dev_completion_rate = aggregated_from_devplan
      - RELEASE.qa_pass_rate = aggregated_from_testplan
      - RELEASE.bug_summary = aggregated_from_both
```

---

## 八、状态机总览

### 8.1 RELEASE 状态机

```
INIT → SCOPE_INIT → SCOPE_VALIDATE → SCOPE_FROZEN
                                              │
                                              ▼
                                         PLAN_DERIVE
                                              │
                                              ▼
                                         PLAN_VALIDATED
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
             DEV_EXECUTION           QA_EXECUTION              COVERAGE_CHECK
                    │                         │                         │
                    └─────────────────────────┴─────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
               RELEASED              CONDITIONAL_RELEASED           NOGO
                    │                         │                         │
                    ▼                         ▼                         ▼
                 CLOSED                    CLOSED                   FAILED
```

### 8.2 DEVPLAN/TESTPLAN 状态机

```
DRAFT → ORGANIZING/STRATEGY_DEFINE → VALIDATING → FROZEN → EXECUTING → COMPLETED
                                                                                │
                                                                                ▼
                                                                         AGGREGATED
```

### 8.3 Feature Delivery L2 状态机

```
Ready → In Progress → [Tech Design → Contract → BE/FE → Integration] → Evidence Pack → Smoke Gate → Closed
                                     │                                                      │
                                     └──────────────────── Failed ──────────────────────────┘
```

---

## 九、约束与门禁总览

### 9.1 硬约束 (Hard Constraints)

| 约束 ID | 描述 | 违反处理 |
|---------|------|----------|
| **C001** | RELEASE 必须绑定至少一个 frozen FEAT | 空 RELEASE 不允许创建 |
| **C002** | Scope Freeze 必须在 Plan Derivation 之前 | 禁止在 scope_freeze 之前执行 plan_derivation |
| **C003** | Dev 执行必须在 QA 执行之前完成 | QA 不允许在 Dev L2 未完成前开始 |
| **C004** | 所有 RELEASE 必须经过 Go/No-Go 决策 | 禁止跳过决策直接关闭 RELEASE |
| **C005** | 所有 TASK 必须通过 Smoke Gate | Smoke Gate 失败，TASK 标记为 failed |
| **C006** | Test Set 必须 trace 到 FEAT AC | 追溯性验证失败，Test Set 不允许冻结 |
| **C007** | Contract 必须在 Implementation 之前冻结 | 禁止在未冻结 contract 的情况下开始 BE/FE 开发 |

### 9.2 门禁总览

| Gate ID | 类型 | 位置 | 审批人 |
|---------|------|------|--------|
| `gate.dev.scope_freeze_gate` | human_approval | L1 Scope Management | RM, PO, TL |
| `gate.dev.scope_validate_gate` | auto_check | L1 Scope Management | - |
| `gate.dev.plan_validate_gate` | auto_check | L1 Plan Derivation | - |
| `gate.dev.go_nogo_gate` | human_approval | L1 Release Closure | RM, PO, TL |
| `gate.dev.task_validate_gate` | auto_check | L2 DEVPLAN Management | - |
| `gate.dev.devplan_freeze_gate` | human_approval | L2 DEVPLAN Management | TL, RM |
| `gate.dev.contract_freeze_gate` | human_approval | L2 Feature Delivery | TL |
| `gate.dev.smoke_gate` | blocking_gate | L2 Feature Delivery | - |
| `gate.qa.test_set_validate_gate` | auto_check | L2 TESTPLAN Management | - |
| `gate.qa.testplan_freeze_gate` | human_approval | L2 TESTPLAN Management | QA Lead, RM |
| `gate.qa.test_set_approval` | human_approval | L3 Test Set Production | QA Lead, PM |
