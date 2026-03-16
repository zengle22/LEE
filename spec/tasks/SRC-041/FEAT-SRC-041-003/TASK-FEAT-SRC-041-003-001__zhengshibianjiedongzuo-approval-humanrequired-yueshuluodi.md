---
id: TASK-FEAT-SRC-041-003-001
ssot_type: task
title: 正式边界动作 approval plus human_required 约束落地
status: draft
version: v1
workflow_instance_id: adr-017-gate-governance-impl
parent_id: FEAT-SRC-041-003
derived_from_ids:
- id: FEAT-SRC-041-003
  version: v1
  required: true
source_refs:
- FEAT-SRC-041-003#delivery
- ADR-017#Decision
owner: null
tags:
- gate
- approval
- policy
properties:
  contract_key: task_feat_src_041_003_001_boundary_approval_policy
  identity_kind: ssot
---

# Objective

对 `freeze`、`release`、`merge`、`risk_acceptance` 等正式边界动作实施 `purpose=approval` 且 `decision_mode=human_required` 的强约束，并阻断 `review` 语义绕过正式放行。

# Description

围绕 FEAT-SRC-041-016-003，冻结正式边界动作集合、违规组合阻断条件、`human_gate_context` 前置要求与审计分类规则，使 workflow 校验、runtime gate 构建和审批操作都以同一政策判断正式放行是否合法。

## Acceptance Mapping

- FEAT-SRC-041-003 / AC-FEAT-SRC-041-003-01: `freeze`、`release`、`merge`、`risk acceptance` 稳定映射为 `approval + human_required`，否则判定不合规。
- FEAT-SRC-041-003 / AC-FEAT-SRC-041-003-02: `review` 语义不得再表达正式放行动作，违规定义在规格审核与运行时消费链路中被拒绝。

## Prerequisites

- FEAT-SRC-041-001 已冻结
- FEAT-SRC-041-002 已冻结
- FEAT-SRC-041-003 已冻结

## Dependencies

- TASK-FEAT-SRC-041-001-001
- TASK-FEAT-SRC-041-002-001

## Inputs

- 双轴语义与 legacy 收敛规则
- `human_gate_context` 前置完整性规则
- ADR-017 中 `boundary_action`、审批策略与 fail-closed 约束

## Outputs

- 正式边界动作集合与 `approval + human_required` 绑定规则
- `review` 误用正式放行场景的阻断策略与错误说明
- workflow/runtime/audit 共用的边界动作合规判定点

## Definition Of Done

- 正式边界动作枚举和用途边界已冻结，不能按命令或场景自行扩写例外语义
- workflow lint、runtime validator、审批执行入口复用同一审批政策判断
- 缺少 `human_gate_context` 的正式边界动作在 pending 前即被阻断
- `review` 语义误用时返回明确违规原因与改写要求
- 审计链路记录 `boundary_action`、政策判定结果与阻断原因

## Observability

```yaml
execution_unit: task
log_scope: approval-boundary-policy-task
audit_fields:
- run_id
- task_id
- gate_id
- boundary_action
- purpose
- decision_mode
- policy_result
- context_ref
- evidence_refs
```

## Evidence Requirements

```yaml
required_refs:
- FEAT-SRC-041-003
- ADR-017
review_required: true
```

## Rollback Strategy

```yaml
mode: revert
restore_targets:
- spec/requirements/SRC-041/FEAT-SRC-041-003__zhengshibianjiedongzuode-approval-plus-human-requi.md
- spec/adr/ADR-017__gate-zhizeyujuecemoshifencengyurenjishenpipinshenjiaohu.md
- src/lee/orchestrator/execution/gate_operations.py
- src/lee/orchestrator/execution/gate_policy.py
preconditions:
- 保留当前正式边界动作样本与 review 误用案例，用于违规回放
```
