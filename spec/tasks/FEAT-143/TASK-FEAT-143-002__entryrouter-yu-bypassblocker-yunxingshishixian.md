---
id: TASK-FEAT-143-002
ssot_type: task
title: EntryRouter 与 BypassBlocker 运行时实现
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_143_002
  identity_kind: ssot
---

# Objective

实现执行入口路由核心组件，包括 EntryRouter 接口和 BypassBlocker 旁路检测

# Description

实现 EntryRouter：接收 ExecutionRequest，协调 BypassBlocker 和 ChainValidator 进行校验，路由到合法执行路径或返回错误；实现 BypassBlocker：检测和阻断旁路执行请求，识别无 task_ref 的直接调用、task 不归属 TESTPLAN、TESTPLAN 不归属 RELEASE 等旁路场景。

## Acceptance Mapping
- FEAT-143 / AC-003-001: EntryRouter 仅接受包含有效 task_ref 且 task 归属 testplan 的执行请求
- FEAT-143 / AC-003-003: BypassBlocker 检测并阻断无 task_ref 的直接调用、task 不归属 TESTPLAN、TESTPLAN 不归属 RELEASE 的旁路请求

## Prerequisites
- TASK-FEAT-143-001

## Dependencies
- ArtifactManager
- SSOTService

## Observability
```yaml
execution_unit: task
log_scope: task-runtime-implementation
audit_fields:
- run_id
- task_id
- changed_files
- test_results
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- TECH-FEAT-143-009
- TASK-FEAT-143-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/execution/entry_router.py
- src/lee/orchestrator/execution/bypass_blocker.py
preconditions:
- 保留实现前的代码版本
```

## Definition Of Done
- TASK 文件已冻结
- EntryRouter 和 BypassBlocker 实现完成并通过单元测试
- 旁路检测规则 BYPASS-001/002/003 全部覆盖
