---
id: TASK-FEAT-SRC-041-005-001
ssot_type: task
title: 人工 gate_result 统一输出与审计追溯绑定
status: draft
version: v1
workflow_instance_id: adr-017-gate-governance-impl
parent_id: FEAT-SRC-041-005
derived_from_ids:
- id: FEAT-SRC-041-005
  version: v1
  required: true
source_refs:
- FEAT-SRC-041-005#delivery
- ADR-017#Decision
owner: null
tags:
- gate
- audit
- result
properties:
  contract_key: task_feat_src_041_005_001_gate_result_audit
  identity_kind: ssot
---

# Objective

将所有人工 gate 的决策结果统一收口为 `gate_result`，并把 `subject_refs`、`evidence_refs`、`next_action`、`approver_identity` 与 trace/audit 建立稳定追溯关系。

# Description

围绕 FEAT-SRC-041-016-005，冻结人工决策结果的统一结构、受控 `decision_outcome` / `next_action` 边界、结果对象与 `human_gate_context` / `gate_definition_id` 的关联方式，以及 CLI、runtime、审计对 `result_ref` 的共同消费路径，避免不同决策分支继续输出互不兼容的私有结果结构。

## Acceptance Mapping

- FEAT-SRC-041-005 / AC-FEAT-SRC-041-005-01: 所有人工 gate 审批结论统一输出为 `gate_result`，而不是特定 gate 私有结构。
- FEAT-SRC-041-005 / AC-FEAT-SRC-041-005-02: `gate_result` 稳定包含 `subject_refs`、`evidence_refs` 与 `next_action`，并可追溯到审批对象与证据。

## Prerequisites

- FEAT-SRC-041-001 已冻结
- FEAT-SRC-041-002 已冻结
- FEAT-SRC-041-005 已冻结

## Dependencies

- TASK-FEAT-SRC-041-001-001
- TASK-FEAT-SRC-041-002-001
- TASK-FEAT-SRC-041-003-001

## Inputs

- 双轴语义与正式边界动作审批政策
- `human_gate_context` 最小字段与引用边界
- ADR-017 中 `gate_result` 对象、`result_ref` 与 trace/audit 接线约束

## Outputs

- 统一的 `gate_result` 结构与受控结果取值边界
- `subject_refs`、`evidence_refs`、`next_action` 的必填规则与追溯链
- runtime、CLI、audit 共用的 `result_ref` 物化与回放约束

## Definition Of Done

- 所有人工决策分支共用单一 `gate_result` 对象，不再维护平行结果载体
- `subject_refs`、`evidence_refs`、`next_action`、`approver_identity` 成为统一结果最小治理边界
- `decision_outcome` 与 `next_action` 的合法组合已明确，非法组合会阻断提交
- `gate_result` 可追溯到 `gate_definition_id`、`human_gate_context` 与 trace/audit 记录
- 结果对象支持重放、审计和 CLI 展示，而不依赖私有 gate 类型解释

## Observability

```yaml
execution_unit: task
log_scope: gate-result-audit-task
audit_fields:
- run_id
- task_id
- gate_id
- result_ref
- decision_outcome
- next_action
- approver_identity
- subject_refs
- evidence_refs
```

## Evidence Requirements

```yaml
required_refs:
- FEAT-SRC-041-005
- ADR-017
review_required: true
```

## Rollback Strategy

```yaml
mode: revert
restore_targets:
- spec/requirements/SRC-041/FEAT-SRC-041-005__rengong-gate-juecejieguodetongyi-gate-result-shuch.md
- spec/adr/ADR-017__gate-zhizeyujuecemoshifencengyurenjishenpipinshenjiaohu.md
- src/lee/orchestrator/execution/gate_operations.py
- src/lee/orchestrator/execution/trace.py
- src/lee/orchestrator/execution/gate_result.py
preconditions:
- 备份现有人工审批结果输出样本与 trace 记录，用于对比回放
```
