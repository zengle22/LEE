---
id: TASK-FEAT-172-001
ssot_type: task
title: Workflow 实例执行器上下文化与持久化
status: active
version: v1
parent_id: FEAT-172
derived_from_ids: []
source_refs:
- FEAT-172#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_172_001
  identity_kind: ssot
---

# Objective

让 workflow instance 稳定携带并持久化执行器上下文

# Description

<<<<<<< HEAD
基于 TECH-FEAT-172-001，将 `executor_override` 写入 workflow instance 数据，并在 create / continue / restart / resume 路径上保持一致，避免执行器信息只在 CLI 进程内短暂存在。
=======
基于 TECH-FEAT-172-001，将 `executor_override` 写入 workflow instance 数据，并在 create / continue / restart / resume 路径上保持一致，避免对话执行后端信息只在 CLI 进程内短暂存在，同时保证 code step 的真正 executor 不被 `qwen_chat` 误覆盖。
>>>>>>> codex/src011-qwen-implementation

## Acceptance Mapping
- FEAT-172 / AC-001: 实例携带执行器上下文

## Prerequisites
- TECH-FEAT-172-001 技术方案已冻结

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
- src/lee/cli/commands/run.py
- src/lee/orchestrator/execution/workflow_runner.py
```

## Definition Of Done
- 新建实例时可持久化执行器类型
- continue / restart / resume 路径保持执行器上下文正确
- `task_executions.executor_type` 可审计
- TASK 文件已冻结
<<<<<<< HEAD

=======
>>>>>>> codex/src011-qwen-implementation
