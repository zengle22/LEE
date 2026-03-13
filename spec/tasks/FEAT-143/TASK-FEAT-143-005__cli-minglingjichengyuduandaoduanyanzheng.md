---
id: TASK-FEAT-143-005
ssot_type: task
title: CLI 命令集成与端到端验证
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_143_005
  identity_kind: ssot
---

# Objective

实现 lee qa execute 命令并完成端到端集成验证

# Description

实现 lee qa execute CLI 命令，集成 EntryRouter/BypassBlocker/ChainValidator/AuditLogger 组件。实现 5 阶段反馈模型、状态图标系统、错误码显示。完成端到端测试验证所有 AC。

## Acceptance Mapping
- FEAT-143 / AC-003-001: lee qa execute 命令仅接受有效 task_ref 参数
- FEAT-143 / AC-003-003: 旁路执行请求被阻断并显示 ERR-BYPASS 错误码
- FEAT-143 / AC-003-004: lee qa audit log 命令可查询审计日志

## Prerequisites
- TASK-FEAT-143-002
- TASK-FEAT-143-003
- TASK-FEAT-143-004

## Dependencies
- {'task_id': 'TASK-FEAT-143-001', 'relation': 'requires_specification'}
- {'task_id': 'TASK-FEAT-143-002', 'relation': 'requires_entry_router'}
- {'task_id': 'TASK-FEAT-143-003', 'relation': 'requires_chain_validator'}
- {'task_id': 'TASK-FEAT-143-004', 'relation': 'requires_audit_logger'}

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
- TASK-FEAT-143-002
- TASK-FEAT-143-003
- TASK-FEAT-143-004
- UI-FEAT-143-018
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/cli/commands/qa_execute.py
- src/lee/cli/commands/qa_audit.py
- src/lee/cli/output_formatter.py
```

## Definition Of Done
- src/lee/cli/commands/qa_execute.py 实现完成
- 5 阶段反馈模型已实现
- 状态图标系统已配置
- 错误码显示已集成
- 端到端测试覆盖所有 AC 场景
- lee qa audit log 命令已实现
- TASK 文件已冻结
