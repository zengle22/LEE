---
id: TASK-FEAT-SRC-009-006-005
ssot_type: task
title: L3 Backend 文档迁移与旧入口封禁
status: frozen
version: v1
parent_id: FEAT-SRC-009-006
derived_from_ids: []
source_refs:
- FEAT-SRC-009-006#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_006_005
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:50.543156'
---

# Objective

更新 README/WORKFLOWS 文档，将 L3 Backend Development 纳入标准路径，封禁旧入口

# Description

执行 ADR-008 第 8 章资产分类要求，更新 README 和 WORKFLOWS 文档，将 L3 Backend Development 阶段纳入推荐路径，降级或封禁旧的 backend workflow 入口。

## Acceptance Mapping
- FEAT-SRC-009-006 / AC-006-001: Backend Development 阶段文档冻结

## Prerequisites
- TASK-FEAT-SRC-009-006-001 completed
- TASK-FEAT-SRC-009-006-002 completed

## Dependencies
- ADR-008
- spec-global/departments/dev/README.md
- spec-global/WORKFLOWS.md

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- deprecated_paths
```

## Evidence Requirements
```yaml
required_refs:
- ADR-008
- FEAT-SRC-009-006
review_required: false
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/README.md
- spec-global/WORKFLOWS.md
preconditions:
- 备份原文档
```

## Definition Of Done
- README.md 已更新，包含 L3 Backend Development 标准路径
- WORKFLOWS.md 已更新，封禁旧 backend workflow 入口
- 旧入口已标记为 deprecated/draft
- CI 校验 workflow 引用来源
