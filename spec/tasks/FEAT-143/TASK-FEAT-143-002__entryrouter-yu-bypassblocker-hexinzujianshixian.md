---
id: TASK-FEAT-143-002
ssot_type: task
title: EntryRouter 与 BypassBlocker 核心组件实现
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

实现执行入口路由器和旁路阻断器核心组件

# Description

实现 EntryRouter 作为执行入口的核心接口，集成 BypassBlocker 检测并阻断旁路执行请求。包含 BYPASS-001~004 场景识别、ERR-BYPASS-*错误码返回、异步审计记录。

## Acceptance Mapping
- FEAT-143 / AC-003-001: EntryRouter 仅接受包含有效 task_ref 的执行请求
- FEAT-143 / AC-003-003: BypassBlocker 检测并阻断旁路执行尝试，返回规范错误码

## Prerequisites
- TASK-FEAT-143-001

## Dependencies
- {'task_id': 'TASK-FEAT-143-001', 'relation': 'requires_specification'}

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
- src/lee/qa/entry_router.py
- src/lee/qa/bypass_blocker.py
```

## Definition Of Done
- src/lee/qa/entry_router.py 实现完成
- src/lee/qa/bypass_blocker.py 实现完成
- 旁路检测规则 BYPASS-001~004 已实现
- 单元测试覆盖所有旁路场景
- TASK 文件已冻结
