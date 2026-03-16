---
id: TASK-FEAT-SRC-041-001-001
ssot_type: task
title: Gate 双轴语义与 legacy 收敛治理定义
status: frozen
version: v1
workflow_instance_id: adr-017-gate-governance-impl
parent_id: FEAT-SRC-041-001
derived_from_ids:
- id: FEAT-SRC-041-001
  version: v1
  required: true
source_refs:
- FEAT-SRC-041-001#delivery
- ADR-017#Allowed Combinations
owner: null
tags:
- gate
- governance
- semantics
properties:
  contract_key: task_feat_src_041_001_001_semantics_governance
  identity_kind: ssot
frozen_at: '2026-03-16T11:38:58.441429'
---

# Objective

冻结 `purpose` / `decision_mode` 双轴模型、允许组合、禁止组合与 legacy 映射，作为 workflow、runtime、CLI 与审计共同消费的唯一 gate 语义真相源。

# Description

围绕 FEAT-SRC-041-016-001，将 gate 语义从历史分类收口到双轴模型，明确 `auto_check`、`human_review`、`human_approval`、`human_gate`、`Auto Gate`、`Review Gate`、`Approval Gate` 的兼容映射规则、缺失信息时的 fail-closed 策略，以及下游不得引入第三分类轴的治理门禁。该任务同时补齐字段级 trace 锚点，使后续 workflow 模板、runtime 归一化、CLI 投影与 TESTSET 可直接派生。

## Acceptance Mapping

- FEAT-SRC-041-001 / AC-FEAT-SRC-041-001-01: 新增或收敛后的 gate 定义以 `purpose` 与 `decision_mode` 作为唯一正式语义，并具备允许/禁止组合与缺失字段阻断规则。
- FEAT-SRC-041-001 / AC-FEAT-SRC-041-001-02: 所有 legacy gate 分类仅作为兼容映射入口消费，不得继续发布为正式治理语义。

## Prerequisites

- EPIC-SRC-041-016 已冻结
- FEAT-SRC-041-001 已冻结
- ADR-017 已冻结

## Dependencies

- 无

## Inputs

- FEAT-SRC-041-001 冻结的目标语义与 acceptance
- ADR-017 中的 `gate_definition`、允许组合与 legacy 映射边界
- ADR-017 关于 allowed combinations、legacy 兼容与人工审批前置语义的硬约束

## Outputs

- `gate_definition` 双轴字段与合法组合清单
- legacy 分类到双轴模型的完整映射与 fail-closed 规则
- 下游 workflow/runtime/CLI/TESTSET 的 trace anchors 与校验点清单

## Definition Of Done

- `purpose`、`decision_mode`、`boundary_action` 的正式字段边界已冻结到 canonical spec 与 TECH 锚点
- 第一阶段允许组合与禁止组合清单完整，可直接驱动 lint、runtime validator 与 review checklist
- `human_gate`、`Review Gate` 等歧义 legacy 输入的拒绝条件与补充信息要求已明确
- 禁止新增第三分类轴的治理规则已写入规格消费约束与审查要点
- acceptance trace 已从抽象标签细化到对象字段、消费链路、校验点与派生产物

## Observability

```yaml
execution_unit: task
log_scope: gate-semantics-task
audit_fields:
- run_id
- task_id
- feat_id
- gate_definition_id
- purpose
- decision_mode
- legacy_gate_type
- evidence_refs
```

## Evidence Requirements

```yaml
required_refs:
- FEAT-SRC-041-001
- ADR-017
review_required: true
```

## Rollback Strategy

```yaml
mode: revert
restore_targets:
- spec/requirements/SRC-041/FEAT-SRC-041-016-001__gate-purpose-yu-decision-mode-mubiaoyuyidongjie.md
- spec/adr/ADR-017__gate-zhizeyujuecemoshifencengyurenjishenpipinshenjiaohu.md
- src/lee/orchestrator/execution/gate_semantics.py
preconditions:
- 先备份当前 legacy gate 映射消费点与 validator 入口
```
