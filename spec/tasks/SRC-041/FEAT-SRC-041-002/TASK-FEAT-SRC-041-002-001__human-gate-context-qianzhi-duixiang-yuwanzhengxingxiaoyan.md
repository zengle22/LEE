---
id: TASK-FEAT-SRC-041-002-001
ssot_type: task
title: human_gate_context 前置对象与完整性校验接线
status: draft
version: v1
workflow_instance_id: adr-017-gate-governance-impl
parent_id: FEAT-SRC-041-002
derived_from_ids:
- id: FEAT-SRC-041-002
  version: v1
  required: true
source_refs:
- FEAT-SRC-041-002#delivery
- TECH-FEAT-SRC-041-001
- ADR-017#Human Gate Context Contract
owner: null
tags:
- gate
- runtime
- human-approval
properties:
  contract_key: task_feat_src_041_002_001_human_gate_context
  identity_kind: ssot
---

# Objective

把 `human_gate_context` 物化为所有 `decision_mode=human_required` 与自动升级到人工决策场景的统一前置对象，并在 gate 进入待审批前执行完整性校验。

# Description

围绕 FEAT-SRC-041-016-002，定义 `subject`、`subject_refs`、`why_now`、`evidence_refs`、`risk_summary`、`next_action`、`escalation_reason` 的最小字段结构、必填性、缺失处理与共享消费方式，确保 runtime、CLI、trace 与审计使用同一个上下文对象，而不是各自产生局部字段集合。

## Acceptance Mapping

- FEAT-SRC-041-002 / AC-FEAT-SRC-041-002-01: 所有 `decision_mode=human_required` 的 gate 在进入待审批状态前具备完整 `human_gate_context`。
- FEAT-SRC-041-002 / AC-FEAT-SRC-041-002-02: 自动检查升级到人工决策时补齐 `human_gate_context`，并记录 `escalation_reason` 与可追溯引用。

## Prerequisites

- FEAT-SRC-041-001 双轴语义已冻结
- FEAT-SRC-041-002 已冻结
- ADR-017 已冻结

## Dependencies

- TASK-FEAT-SRC-041-001-001

## Inputs

- TASK-FEAT-SRC-041-001-001 冻结的 `purpose` / `decision_mode` 语义
- TECH-FEAT-SRC-041-016 中的 `human_gate_context` 字段边界与校验时机
- decision_mode=human_required gate 清单与自动升级场景触发条件

## Outputs

- `human_gate_context` 最小字段结构与必填规则
- gate 进入 pending 前的上下文完整性校验点
- 自动升级到人工决策时的上下文补齐与错误阻断规则

## Definition Of Done

- `human_gate_context` 字段、必填性、缺失处理和引用追溯规则已冻结
- 所有人工决策 gate 在进入待审批前经过统一 completeness validator
- 自动升级场景可以稳定补齐 `escalation_reason`、`subject_refs`、`evidence_refs`
- CLI、runtime、trace、audit 复用同一上下文对象标识，不再维护平行字段集合
- 缺少上下文字段时的阻断结果、日志字段与人工补救动作已明确

## Observability

```yaml
execution_unit: task
log_scope: human-gate-context-task
audit_fields:
- run_id
- task_id
- gate_id
- gate_definition_id
- context_ref
- escalation_reason
- missing_fields
- evidence_refs
```

## Evidence Requirements

```yaml
required_refs:
- FEAT-SRC-041-002
- TECH-FEAT-SRC-041-016
- ADR-017
review_required: true
```

## Rollback Strategy

```yaml
mode: revert
restore_targets:
- spec/requirements/SRC-041/FEAT-SRC-041-002__human-gate-context-rengongjueceqianzhishangxiawenq.md
- spec/tech/TECH-FEAT-SRC-041-016__adr-017-gate-shuangzhou-yurenjueshenpi-frozen-jishujiagou.md
- src/lee/orchestrator/execution/gate_context_builder.py
- src/lee/orchestrator/execution/gate_api.py
- src/lee/orchestrator/execution/human_approval.py
preconditions:
- 保留当前人工审批 pending 入口与异常样本，便于回放验证
```
