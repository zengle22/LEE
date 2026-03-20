---
id: TASK-FEAT-SRC-009-010-001
ssot_type: task
title: 旧路径降级治理规范定义
status: frozen
version: v1
parent_id: FEAT-SRC-009-010
derived_from_ids: []
source_refs:
- FEAT-SRC-009-010#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_010_001
  identity_kind: ssot
frozen_at: '2026-03-13T00:47:10.081041'
---

# Objective

定义旧路径降级的结构规范和标记标准

# Description

创建旧路径降级治理的正式规范文档，定义 deprecated_paths 清单结构、标记规范（README 标记、代码注释标记、workflow 文件头部标记）、迁移指南结构和活跃度监控机制

## Acceptance Mapping
- FEAT-SRC-009-010 / AC-010-001: 旧路径治理文档已冻结
- FEAT-SRC-009-010 / AC-010-002: Deprecated 路径清单完整
- FEAT-SRC-009-010 / AC-010-003: 标记规范覆盖 README、代码注释、workflow 文件头部

## Prerequisites
- ADR-008 已冻结

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- ADR-008
- FEAT-SRC-009-010
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/workflows/
preconditions:
- 确保原始规范文档备份
```

## Definition Of Done
- TASK 文件已冻结
- 规范文档通过评审
- deprecated_paths 清单完整覆盖 phase-openspec-flow 等旧路径
