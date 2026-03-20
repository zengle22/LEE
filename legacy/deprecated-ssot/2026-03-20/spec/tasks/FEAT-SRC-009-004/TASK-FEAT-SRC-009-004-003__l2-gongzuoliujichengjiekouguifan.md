---
id: TASK-FEAT-SRC-009-004-003
ssot_type: task
title: L2 工作流集成接口规范
status: frozen
version: v1
parent_id: FEAT-SRC-009-004
derived_from_ids: []
source_refs:
- FEAT-SRC-009-004#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_004_003
  identity_kind: ssot
frozen_at: '2026-03-13T00:47:10.153185'
---

# Objective

定义 Evidence Pack 与 Feature/Bugfix Delivery L2 工作流的集成接口

# Description

明确定义 Evidence Pack 如何从 L2 工作流接收输入、如何触发证据收集、如何输出正式收口对象，确保交付链完整闭合

## Acceptance Mapping
- FEAT-SRC-009-004 / AC-004-003: L2 工作流集成接口规范完整

## Prerequisites
- FEAT-SRC-009-001 L2 工作流定义冻结
- TASK-FEAT-SRC-009-004-001 Schema 冻结

## Observability
```yaml
execution_unit: task
log_scope: evidence-pack-integration
audit_fields:
- run_id
- changed_files
- integration_refs
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-SRC-009-004
- FEAT-SRC-009-001
- FEAT-SRC-009-002
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/contracts/evidence-pack/v1/integration-spec.md
```

## Definition Of Done
- L2→Evidence Pack 集成接口文档已创建于 spec-global/departments/dev/contracts/evidence-pack/v1/integration-spec.md
- 文档明确定义与 Feature Delivery L2 的集成点（在 Evidence Pack 阶段触发）
- 文档明确定义与 Bugfix Delivery L2 的集成点（在 bugfix_evidence_pack 阶段触发）
- 定义输入契约（integration_outputs、verification_results）
- 定义输出契约（evidence_pack_ref、smoke_gate_input）
- 集成规范评审通过
