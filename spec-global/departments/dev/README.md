# Development Specification System
# 研发部门规范体系

本目录描述 Dev 部门当前的 canonical 工作流、模板、Gate 与 Agent 定义。

## 当前主入口

Dev 部门当前只保留两个主入口：

1. `template.dev.feature_delivery_l2`
   作用：新功能从 `FEAT -> TECH -> CONTRACT -> FE/BE -> INTEGRATION -> EVIDENCE -> SMOKE`
2. `template.dev.bugfix_delivery_l2`
   作用：缺陷修复与验证闭环

其中，**Feature 主入口的 canonical 模板** 为：
`workflows/templates/feature-delivery-l2-template.yaml`

**Bugfix 主入口的 canonical 模板** 为：
`workflows/templates/bugfix-delivery-l2-template.yaml`

## Feature Delivery L2

当前现役阶段顺序为：

1. `tech_design`
2. `contract_design`
3. `backend_dev`
4. `frontend_dev`
5. `integration`
6. `evidence_pack`
7. `smoke_gate`

治理规则：

- `formal_ssot_id`、`source_refs`、`governing_adrs`、`repo_context` 是共享输入契约
- `contract_design` 绑定 `gate.dev.contract_freeze_gate`
- `smoke_gate` 绑定 `gate.dev.smoke_gate`
- 生命周期状态按 `Ready -> In Progress -> Evidence Pack Produced -> Closed` 收口

共享输入规范说明见：
`docs/shared-input-spec.md`

## 现役 L3 模板

- `template.dev.tech_design_l3`
- `template.dev.feature_contract_l3`
- `template.dev.feature_fe_l3`
- `template.dev.feature_be_l3`
- `template.dev.feature_integration_l3`
- `template.dev.evidence_pack_l3`
- `template.dev.bugfix_triage_l3`
- `template.dev.bugfix_root_cause_l3`
- `template.dev.bugfix_fix_design_l3`
- `template.dev.bugfix_fix_impl_l3`
- `template.dev.bugfix_verification_l3`
- `template.dev.bugfix_evidence_pack_l3`

### Contract Design L3

`template.dev.feature_contract_l3` 是 `contract_design` 阶段的唯一现役 L3 模板。

它的 canonical 约束是：

- 输入锚点必须包含 `formal_ssot_id`、`source_refs`、`governing_adrs`、`tech_spec_ref`
- 任务族必须覆盖 `api_contract_design`、`data_contract_design`、`event_contract_design`
- 评审产物必须输出 `contract_review_ref`
- 冻结阶段必须通过 `gate.dev.contract_freeze_gate`
- 下游 Backend/Frontend 只允许消费 `contract_freeze_ref`，不得消费草稿契约

使用说明见：
`docs/contract-design-l3-usage-guide.md`

### Backend Development L3

`template.dev.feature_be_l3` 是 `backend_dev` 阶段的唯一现役 L3 模板。

它的 canonical 约束是：

- 输入锚点必须包含 `tech_spec_ref`、`contract_freeze_ref`、`repo_backend`
- 执行顺序必须是 `write_ut -> implement_backend -> refactor_backend -> coverage_gate -> publish_backend`
- `coverage_gate` 的最低阈值固定为 `80%`
- 低于阈值时运行时必须回退到 `write_ut`
- Frontend / Integration 只能消费发布后的 backend handoff 产物

旧的“DTO Implementation / API Handler Implementation / Self-Check / Code Diff Output”阶段叙事已被 canonical UTDD 模板取代，不再作为推荐入口说明。

### Frontend Development L3

`template.dev.feature_fe_l3` 是 `frontend_dev` 阶段的唯一现役 L3 模板。

它的 canonical 约束是：

- 输入锚点必须包含 `tech_spec_ref`、`contract_freeze_ref`、`repo_frontend`
- 执行顺序必须是 `write_ut -> implement_ui -> refactor_ui -> coverage_gate -> publish_frontend`
- 运行时可以携带 `env_ref`、`base_url`、`runtime_config_ref`
- Evidence handoff 至少包含 `fe_artifact_ref`、`unit_test_ref`、`coverage_report_ref`、`contract_usage_verification_ref`

旧的“Type Generation / UI Implementation / Self-Check / Code Diff Output”阶段叙事已被 canonical UTDD 模板取代，不再作为推荐入口说明。

## Bugfix Delivery L2

当前现役阶段顺序为：

1. `triage`
2. `root_cause`
3. `fix_design`
4. `fix_implementation`
5. `verification`
6. `evidence_pack`
7. `merge_or_reject`

治理规则：

- `bug_ssot_id`、`severity`、`reproduction_evidence` 是共享输入契约
- 默认 `1 bug -> 1 workflow instance`
- 只有满足五同原则时才允许 `batch_mode`
- `merge_or_reject` 前必须完成 `evidence_pack`

## Deprecated / Draft

以下资产不再作为新任务入口：

- `workflows/phase-openspec-flow/v1/workflow.yaml`
  状态：`deprecated`
  说明：保留为历史参考，不再作为 Dev 部门 canonical 主路径

- 旧 `feature-l2-template.yaml`
  状态：`compat`
  说明：保留兼容窗口，但新功能统一收口到 `feature-delivery-l2-template.yaml`

- 旧 `bug-fix-l3-template.yaml`
  状态：`deprecated`
  说明：保留历史参考，不再作为 Bugfix 主入口；Bugfix 统一收口到 `bugfix-delivery-l2-template.yaml`

迁移指南：
`docs/deprecated-path-migration-guide.md`

## 维护规则

- 修改现役 Dev workflow 时，优先更新 canonical 模板，不要新建平级实现
- Phase 级执行路径必须走 runtime 可消费的 `l3_template_id`
- 证据轴 closure 必须通过 `evidence_pack` 与 `smoke_gate`
