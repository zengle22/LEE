---
id: TASK-FEAT-143-004
ssot_type: task
title: AuditLogger 与审计存储层实现
status: frozen
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_143_004
  identity_kind: ssot
frozen_at: '2026-03-13T13:08:01.898838'
---

# Objective

实现审计日志记录器和双写存储机制

# Description

实现 AuditLogger 组件，包含 SQLite+WAL 审计存储、内存队列 + 后台异步写入双写机制、审计查询接口。支持按 execution_id/task_ref/plan_ref/release_ref/operator/time_range 多维度查询。

## Acceptance Mapping
- FEAT-143 / AC-003-004: 审计日志包含入口来源、路径链、时间戳、操作用户，可追溯查询

## Prerequisites
- TASK-FEAT-143-001

## Dependencies
- {'task_id': 'TASK-FEAT-143-001', 'relation': 'requires_specification'}
- {'task_id': 'TASK-FEAT-143-002', 'relation': 'requires_entry_router'}

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
- TASK-FEAT-143-001
- TECH-FEAT-143-016
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/qa/audit_logger.py
- src/lee/qa/audit_schemas.py
- data/audit/audit_log.db
```

## Definition Of Done
- src/lee/qa/audit_logger.py 实现完成
- SQLite+WAL 存储层已配置
- 双写机制（队列 + 异步写入）已实现
- 审计查询 API 已实现
- entry_source 枚举值已注册
- 错误码 QA-ENTRY-012 已实现
- TASK 文件已冻结
