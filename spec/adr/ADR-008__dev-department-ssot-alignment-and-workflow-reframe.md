---
id: ADR-008
ssot_type: adr
title: Dev department SSOT alignment and workflow reframe
status: frozen
version: v1
parent_id:
derived_from_ids:
  - ADR-001
  - ADR-003
  - ADR-005
  - ADR-006
  - ADR-007
source_refs:
  - ADR-001#4-1-three-axis-model
  - ADR-001#5-3-object-duty-definitions
  - ADR-001#6-3-key-constraints
  - ADR-003#3-2-object-meaning
  - ADR-003#8-4-task-model
owner: dev
tags: [dev, ssot, workflow, governance]
properties:
  adr_kind: department_design
  decision_scope: dev_department_canonical_path
  frozen_at: 2026-03-11T00:00:00+08:00
---

# Dev 部门接入三轴 SSOT 的系统收口

## 1. Decision

Dev 部门后续的 canonical 设计调整为“三轴对齐、双入口收口、单链治理”。

从现在开始，Dev 部门不再把“实现模板”“Phase 子流程”“历史说明文档”并列视为多个平级主入口。

唯一允许继续前向演进的 Dev 主工作流族为：

- Feature 主入口：`template.dev.feature_delivery_l2`
- Bugfix 主入口：`template.dev.bugfix_delivery_l2`

其中：

- Feature 主入口服务于新能力交付
- Bugfix 主入口服务于测试发现后的缺陷修复
- 两条主入口都必须遵守三轴 SSOT 约束
- 两条主入口都必须产出正式证据收口对象

同时明确：

- `TECH` 是 Dev 将需求轴收敛成交付轴的正式桥接对象
- `API Contract` 是结构真相源，不替代 `TECH`
- `Evidence Pack` 是证据轴正式收口对象，不只是文件打包动作
- `phase-openspec-flow` 不再作为 Dev 当前 canonical 主流程
- 仓库中的 checked-in workflow 文件是 template，不是固定 runtime instance

本 ADR 冻结后，Dev 部门的所有 workflow、agent、contract、gate 调整都必须受本 ADR 约束。

## 2. Why

结合当前仓库状态，Dev 部门已经出现典型的“新旧并存但未收口”问题：

- Contract-First L2/L3 模板族已经形成较清晰主链
- `phase-openspec-flow` 试图表达另一套更重的 Phase 闭环
- README / WORKFLOWS 等文档仍传播不存在或失配的旧入口
- bugfix 模板与实际 agent / gate 命名已经发生漂移

如果继续在这种状态下演进，结果会是：

- AI 与人类都无法稳定判断哪条才是当前主路径
- 新 workflow 继续沿旧上下文生长
- 需求轴、交付轴、证据轴之间仍然缺桥
- Dev 部门对外只能表达“会写代码”，不能表达“如何从 FEAT 收敛到可审计交付”

因此，Dev 部门必须先冻结一份项目级正式决策，明确：

- 主入口只有哪两条
- 需求轴如何进入 Dev
- 交付轴对象由谁生成
- 证据轴如何正式收口
- 哪些旧资产降级为 draft / deprecated / broken

## 3. Dev In Three-Axis Model

### 3.1 Position

Dev 部门不是需求轴起点，也不是证据轴的唯一拥有者。

Dev 的正式职责是：

- 接收上游冻结后的需求轴对象
- 生成 Dev 自己负责的交付轴对象
- 执行实现与集成
- 产出能进入证据轴的正式验证与交付证据

### 3.2 Input / Output Boundary

Dev 的边界统一如下：

- 输入主源：`FEAT / TASK / acceptance brief / governing ADRs`
- 交付主产物：`TECH / API Contract / FE implementation / BE implementation / integration report`
- 证据主产物：`evidence pack / smoke gate result / verification summary`

### 3.3 Mandatory Rule

Dev workflow 的核心业务输入必须来自正式 SSOT 引用，而不能由自由文本 prompt 直接替代。

允许存在的辅助输入包括：

- repo path
- module
- env ref
- runtime config
- test account
- seed data

但这些只属于执行上下文，不属于业务真相源。

## 4. Canonical Object Mapping

Dev 侧对象边界统一如下：

| 对象 | 正式定位 | 轴 | 备注 |
|---|---|---|---|
| `FEAT` | 上游最小独立验收需求对象 | 需求轴 | 非 Dev 创建，但可作为 Dev 主输入 |
| `TASK` | 上游或 release 级实施任务对象 | 交付轴 | 可作为 Dev 开工边界输入 |
| `TECH` | Dev 的正式技术设计对象 | 交付轴 | Dev 收口需求到实现的第一锚点 |
| `API Contract` | 结构与接口真相源 | 交付轴 | 由 `TECH` 约束并冻结 |
| `FE_IMPL` | 前端实现工件引用 | 交付轴 | 不直接充当需求真源 |
| `BE_IMPL` | 后端实现工件引用 | 交付轴 | 不直接充当需求真源 |
| `INTEGRATION_REPORT` | 集成与联调正式结论 | 证据轴 / 交付边界证据 | 可触发 rollback |
| `DEV_EVIDENCE_PACK` | Dev 交付证据收口对象 | 证据轴 | 不是简单压缩包 |
| `SMOKE_GATE_RESULT` | Dev 最终守门结论 | 证据轴 | merge / delivery blocking input |
| `ADR` | 治理与约束对象 | 决策轴 | governs / constrains，不替代业务主源 |

### 4.1 TECH Rule

`TECH` 的默认关系为：

- `FEAT 1 -> 1 main TECH`

允许在复杂场景下扩展为：

- `FEAT 1 -> N TECH`

但不允许把一个无边界的 `TECH` 同时作为多个无关 `FEAT` 的前向主对象。

正式原则：

- `TECH` 是 Dev 对 `FEAT` 的正式交付翻译层
- 不允许从 `FEAT` 直接跳过 `TECH` 进入大规模实现
- `API Contract` 必须受 `TECH` 约束，而不是反向替代 `TECH`

### 4.2 Evidence Pack Rule

`DEV_EVIDENCE_PACK` 的职责不是“收集几个文件路径”，而是：

- 收敛 diff、test、review、gate、日志等证据
- 映射回 `FEAT / TECH / Contract / Acceptance`
- 生成“哪些验收项已覆盖、哪些仍缺证据”的正式结论
- 为 smoke gate 和下游交付判断提供唯一证据入口

因此：

- 没有 `DEV_EVIDENCE_PACK` 的 Dev 交付不能算完整证据闭环
- `runner output / screenshots / logs` 只是 Evidence Pack 的原材料，不替代它

## 5. Canonical Workflow Family

Dev 部门冻结后的 workflow 家族如下。

### 5.1 L2 Main Entry A: Feature Delivery

`template.dev.feature_delivery_l2`

这是 Dev 面向新功能交付的唯一推荐入口。

推荐阶段：

1. `tech_design`
2. `contract_design`
3. `frontend_dev`
4. `backend_dev`
5. `integration`
6. `evidence_pack`
7. `smoke_gate`

其职责不是直接改代码，而是：

- 串联 Dev 交付对象
- 保证 `TECH -> Contract -> FE/BE -> Integration -> Evidence` 顺序
- 阻止任何绕过 `TECH` 或绕过正式证据收口的路径

### 5.2 L2 Main Entry B: Bugfix Delivery

`template.dev.bugfix_delivery_l2`

这是 Dev 面向测试失败或执行反馈缺陷的唯一推荐入口。

推荐阶段：

1. `triage`
2. `root_cause`
3. `fix_design`
4. `fix_implementation`
5. `verification`
6. `evidence_pack`
7. `merge_or_reject`

### 5.3 L3 Workflow Set For Feature

Feature 主入口下的 canonical L3 为：

- `template.dev.tech_design_l3`
- `template.dev.feature_contract_l3`
- `template.dev.feature_fe_l3`
- `template.dev.feature_be_l3`
- `template.dev.feature_integration_l3`
- `template.dev.evidence_pack_l3`

### 5.4 L3 Workflow Set For Bugfix

Bugfix 主入口下的 canonical L3 为：

- `template.dev.bugfix_triage_l3`
- `template.dev.bugfix_root_cause_l3`
- `template.dev.bugfix_fix_design_l3`
- `template.dev.bugfix_fix_impl_l3`
- `template.dev.bugfix_verification_l3`
- `template.dev.bugfix_evidence_pack_l3`

## 6. Workflow Input / Output Rules

### 6.1 Shared Input Rule

所有现役 Dev workflow 至少应共享以下输入语义：

- `formal_ssot_id`
- `source_refs`
- `governing_adrs`
- `repo_context`

其中：

- `formal_ssot_id / source_refs` 用于正式可追溯
- `governing_adrs` 用于治理约束
- `repo_context` 用于执行上下文

### 6.2 Feature Input Rule

Feature 主链的业务主输入必须包括：

- `feat_ref`
- `task_refs` 或 `task_scope_ref`
- `acceptance_brief_ref`

其中：

- `TECH` 从这些正式对象派生
- `Contract` 从 `TECH` 派生
- `FE / BE / Integration` 继续消费 `TECH + Contract`

### 6.3 Feature Output Rule

Feature 主链的正式输出至少包括：

- `tech_spec_ref`
- `contract_freeze_ref`
- `fe_artifact_ref`
- `be_artifact_ref`
- `integration_report_ref`
- `dev_evidence_pack_ref`
- `smoke_gate_result_ref`

### 6.4 Integration Environment Rule

`feature_integration_l3` 允许两种模式：

1. contract / mock / fixture mode
2. environment-backed integration / E2E mode

若进入 environment-backed 模式，则必须显式输入：

- `env_ref`
- `base_url`
- `runtime_config_ref`
- `test_account_ref`（若需要）
- `seed_data_ref`（若需要）

但这些环境输入不替代正式业务输入。

### 6.5 Bugfix Input Rule

Bugfix 主链的核心输入必须围绕：

- `bug_refs`
- `test_case_refs`

必要时可加：

- `acceptance_brief_ref`
- `env_ref`
- `severity`
- `batch_mode`

### 6.6 Bugfix Output Rule

Bugfix 主链的正式输出至少包括：

- `bugfix_plan_ref`
- `root_cause_ref`
- `fix_diff_ref`
- `verification_report_ref`
- `bugfix_evidence_pack_ref`
- `merge_decision_ref`

## 7. Bugfix Granularity Decision

### 7.1 Default Rule

默认修复粒度为：

- `1 bug -> 1 bugfix workflow instance`

### 7.2 Controlled Batch Rule

只有满足以下条件时，才允许用一条 bugfix L2 处理一组 bug：

- 同一模块
- 同一根因类别
- 同一修复策略
- 同一验证面
- 同一发布窗口

若不满足上述条件，则必须拆为多个 workflow instance。

### 7.3 Why

该规则的目的不是降低效率，而是避免：

- 多根因混装
- 验证结果失真
- 回滚边界模糊
- 证据包无法准确闭合

因此，Dev 部门后续不允许把“批量修 bug”默认化为常态主路径。

## 8. Current-State Classification

结合当前仓库结构，Dev 资产应按以下方式重新分类。

### 8.1 Current

当前应继续演进的基础资产：

- `spec-global/departments/dev/AGENTS.md`
- `spec-global/departments/dev/workflows/templates/feature-l2-template.yaml`
- `spec-global/departments/dev/workflows/templates/feature-contract-l3-template.yaml`
- `spec-global/departments/dev/workflows/templates/feature-fe-l3-template.yaml`
- `spec-global/departments/dev/workflows/templates/feature-be-l3-template.yaml`
- `spec-global/departments/dev/workflows/templates/feature-integration-l3-template.yaml`
- `spec-global/departments/dev/gates/contract-freeze-gate/v1/gate.yaml`
- `spec-global/departments/dev/gates/smoke-gate/v1/gate.yaml`

其中：

- `feature-l2-template` 应后续演进为 `feature_delivery_l2`
- 其余模板作为收口基础继续整合

### 8.2 Draft

- `spec-global/departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml`

正式定位改为：

- draft workflow design
- 非当前 canonical Dev 主路径
- 不得作为新任务推荐入口

### 8.3 Deprecated

- `spec-global/departments/dev/README.md` 中传播旧主链或不存在路径的部分
- `spec-global/WORKFLOWS.md` 中仍把旧 Dev workflow 视为现役的部分
- `spec-global/departments/dev/rnd_l2_l3_spec.md` 作为历史设计说明继续保留，但不再承担可执行规范职责

### 8.4 Broken

- `spec-global/departments/dev/workflows/templates/bug-fix-l3-template.yaml`

正式判断：

- 该模板当前已与真实 agent / gate 目录命名脱节
- 不应再作为当前 Dev bugfix 主入口继续扩展
- 后续应由新的 bugfix workflow 家族替代

## 9. Mandatory Governance Rules

后续所有 Dev 规范维护必须遵守以下硬规则：

1. 不新建与 `dev` 平级的 `code` 部门承载重复 coding workflow
2. 不允许再引入第三个 Dev 主入口
3. 不允许继续把 `phase-openspec-flow` 当作当前现役主链扩展
4. 不允许让 `TECH` 缺位后直接从 `FEAT` 大规模进入实现
5. 不允许让 `Evidence Pack` 缺位后直接宣称“已完成交付”
6. 不允许在 bugfix 主链中默认混装无共同根因的一组 bug
7. 不允许让环境上下文字段替代正式 SSOT 主输入
8. 不允许把 checked-in workflow 当作 runtime instance 语义来描述

## 10. Migration Order

Dev 部门后续整改建议按以下顺序推进：

1. 先冻结 Dev workflow canonical family
2. 再更新 README / WORKFLOWS / governance docs，封旧入口
3. 再新增 `tech_design_l3`
4. 再新增 `evidence_pack_l3`
5. 再重写 `bugfix_delivery_l2 + bugfix L3 family`
6. 最后补齐 contract / gate / skill / CI validator

本 ADR 当前只冻结方向，不在此文中直接修改实现文件。

## 11. Conclusion

Dev 部门后续的核心竞争力不应再表述为“能快速写代码”，而应表述为：

> 能把需求轴稳定翻译成交付轴，并把实现结果稳定收口到证据轴。

因此，Dev 的正式主链不再只是“contract-first coding pipeline”，而是：

`FEAT / TASK -> TECH -> Contract -> FE / BE -> Integration -> Evidence -> Smoke`

同时，Dev 的正式第二入口为：

`BUG / Test Case -> Triage -> Root Cause -> Fix Design -> Fix -> Verification -> Evidence -> Merge Decision`

这两条链构成 Dev 部门冻结后的唯一现役方向。
