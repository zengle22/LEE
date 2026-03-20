---
id: TASK-FEAT-002-005
ssot_type: task
title: FEAT 规格视图文档迁移与入门指南
status: frozen
version: v1
parent_id: FEAT-002
derived_from_ids: []
source_refs:
- FEAT-002#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_002_005
  identity_kind: ssot
frozen_at: '2026-03-13T00:29:17.574416'
---

# Objective

更新 README 和 WORKFLOWS 文档，封旧入口，建立新规格视图的文档入口

# Description

完成 FEAT 规格视图的文档治理：
- 更新 spec-global/WORKFLOWS.md，将 FEAT 规格视图纳入主入口文档
- 更新 spec-global/departments/dev/README.md，移除旧路径引用
- 创建 FEAT 规格视图的使用指南和示例
- 标记 phase-openspec-flow 等旧路径为 deprecated

## Acceptance Mapping
- FEAT-002 / AC-002-001: FEAT 规格视图文档完成并发布

## Prerequisites
- TASK-FEAT-002-001
- TASK-FEAT-002-002
- TASK-FEAT-002-003

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- deprecation_notices
```

## Evidence Requirements
```yaml
required_refs:
- TASK-FEAT-002-001
- TASK-FEAT-002-002
review_required: false
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/WORKFLOWS.md
- spec-global/departments/dev/README.md
```

## Definition Of Done
- TASK 文件已冻结
- WORKFLOWS.md 和 README.md 更新完成
- 旧路径标记为 deprecated
