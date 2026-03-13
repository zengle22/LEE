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

## 维护规则

- 修改现役 Dev workflow 时，优先更新 canonical 模板，不要新建平级实现
- Phase 级执行路径必须走 runtime 可消费的 `l3_template_id`
- 证据轴 closure 必须通过 `evidence_pack` 与 `smoke_gate`
