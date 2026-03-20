---
id: TASK-FEAT-172-002
ssot_type: task
title: 多执行器并发隔离与验证
status: active
version: v1
parent_id: FEAT-172
derived_from_ids: []
source_refs:
- FEAT-172#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_172_002
  identity_kind: ssot
---

# Objective

验证多执行器并存时的 workspace、evidence 与状态隔离

# Description

<<<<<<< HEAD
基于 TECH-FEAT-172-001，验证在同一仓库中并行存在 `qwen`、`claude_code`、`codex` 等执行器实例时，workflow state、evidence 路径和 workspace 临时产物互不污染。
=======
基于 TECH-FEAT-172-001，验证在同一仓库中并行存在 `qwen_chat`、`claude_code`、`codex`、`kimi` 等执行器实例时，workflow state、evidence 路径和 workspace 临时产物互不污染。
>>>>>>> codex/src011-qwen-implementation

## Acceptance Mapping
- FEAT-172 / AC-002: 多执行器隔离

## Prerequisites
- TECH-FEAT-172-001 技术方案已冻结
- TASK-FEAT-172-001 完成或接口已定义

## Dependencies
- TASK-FEAT-172-001

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- workflow_id
- run_id
- executor_type
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- TECH-FEAT-172-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/storage/sqlite_store.py
- src/lee/orchestrator/execution/tests/
```

## Definition Of Done
- 多执行器实例并行时 evidence 路径不冲突
- 不同执行器实例的状态与 workspace 互不干扰
- 并发 scope 的 continue / restart 行为有测试覆盖
- TASK 文件已冻结
<<<<<<< HEAD

=======
>>>>>>> codex/src011-qwen-implementation
