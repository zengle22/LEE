---
id: TASK-FEAT-SRC-009-010-003
ssot_type: task
title: 旧路径 workflow 文件头部标记实现
status: frozen
version: v1
parent_id: FEAT-SRC-009-010
derived_from_ids: []
source_refs:
- FEAT-SRC-009-010#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_010_003
  identity_kind: ssot
frozen_at: '2026-03-13T00:47:10.208669'
---

# Objective

在 phase-openspec-flow 等旧 workflow 文件头部添加 deprecated 标记

# Description

修改 spec-global/departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml，在文件头部添加正式的 deprecated 状态标记，包含 replacement 指向 feature-l2-template.yaml，添加 migration_deadline 字段

## Acceptance Mapping
- FEAT-SRC-009-010 / AC-010-003: 标记规范覆盖 workflow 文件头部
- FEAT-SRC-009-010 / AC-010-002: Deprecated 路径清单完整

## Prerequisites
- TASK-FEAT-SRC-009-010-001 已完成

## Dependencies
- TASK-FEAT-SRC-009-010-001

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- yaml_diff
```

## Evidence Requirements
```yaml
required_refs:
- TASK-FEAT-SRC-009-010-001
- ADR-008#8-2-Draft
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml
preconditions:
- 确保原始 workflow 文件已版本控制
```

## Definition Of Done
- TASK 文件已冻结
- workflow.yaml 头部已添加 deprecated 状态标记
- replacement 字段正确指向 feature-l2-template.yaml
