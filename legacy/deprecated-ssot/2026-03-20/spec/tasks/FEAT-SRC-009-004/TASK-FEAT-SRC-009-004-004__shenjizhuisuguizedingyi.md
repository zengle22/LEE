---
id: TASK-FEAT-SRC-009-004-004
ssot_type: task
title: 审计追溯规则定义
status: frozen
version: v1
parent_id: FEAT-SRC-009-004
derived_from_ids: []
source_refs:
- FEAT-SRC-009-004#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_004_004
  identity_kind: ssot
frozen_at: '2026-03-13T00:47:10.167123'
---

# Objective

定义从 Evidence Pack 到上游 FEAT/TECH 的完整追溯路径和审计规则

# Description

设计 Evidence Pack 的审计追溯机制，明确如何从证据反向追溯到需求、技术设计、实现变更，确保交付可审计、可追踪

## Acceptance Mapping
- FEAT-SRC-009-004 / AC-004-004: 审计追溯规则文档化，定义从 Evidence Pack 到上游 FEAT/TECH 的追溯路径
- FEAT-SRC-009-004 / AC-004-006: 不干预 Evidence Pack 审计逻辑

## Prerequisites
- TASK-FEAT-SRC-009-004-001 Schema 冻结

## Observability
```yaml
execution_unit: task
log_scope: evidence-pack-audit-rules
audit_fields:
- run_id
- changed_files
- trace_refs
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-SRC-009-004
- ADR-008
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/contracts/evidence-pack/v1/audit-trace-rules.md
```

## Definition Of Done
- 审计追溯规则文档已创建于 spec-global/departments/dev/contracts/evidence-pack/v1/audit-trace-rules.md
- 文档定义从 Evidence Pack 到 FEAT 的追溯路径（通过 formal_ssot_id 和 source_refs）
- 文档定义从 Evidence Pack 到 TECH 的追溯路径
- 文档定义从 Evidence Pack 到实现变更的追溯路径（通过 code-diff 引用）
- 文档明确本机制不干预审计逻辑，仅定义追溯规则
- 审计规则评审通过
