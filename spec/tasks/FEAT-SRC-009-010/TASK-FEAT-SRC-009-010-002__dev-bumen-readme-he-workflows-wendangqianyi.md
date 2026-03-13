---
id: TASK-FEAT-SRC-009-010-002
ssot_type: task
title: Dev 部门 README 和 WORKFLOWS 文档迁移
status: frozen
version: v1
parent_id: FEAT-SRC-009-010
derived_from_ids: []
source_refs:
- FEAT-SRC-009-010#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_010_002
  identity_kind: ssot
frozen_at: '2026-03-13T00:47:10.093885'
---

# Objective

更新 Dev 部门入口文档，封禁旧路径，指向新 L2 主入口

# Description

修改 spec-global/departments/dev/README.md 和 spec-global/WORKFLOWS.md，将旧主链引用替换为 Feature Delivery L2 和 Bugfix Delivery L2 入口，添加 deprecated 标记和迁移指南链接

## Acceptance Mapping
- FEAT-SRC-009-010 / AC-010-004: 迁移指南包含从旧路径到新 L2 入口的清晰映射关系
- FEAT-SRC-009-010 / AC-010-001: 新入口 README/WORKFLOWS 已更新

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
- diff_summary
```

## Evidence Requirements
```yaml
required_refs:
- TASK-FEAT-SRC-009-010-001
- ADR-008#8-Current-State-Classification
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/README.md
- spec-global/WORKFLOWS.md
preconditions:
- 确保原始文档已版本控制
```

## Definition Of Done
- TASK 文件已冻结
- README.md 已更新并标记旧路径为 deprecated
- WORKFLOWS.md 已更新并移除旧 Dev workflow 现役描述
