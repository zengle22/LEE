---
id: TASK-FEAT-143-002
ssot_type: task
title: EntryValidator 与 BypassBlocker 运行时实现
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

实现执行入口验证器和旁路阻断器，确保所有执行请求必须通过标准入口且旁路请求被有效阻断

# Description

基于 TASK-FEAT-143-001 定义的规范，实现 EntryValidator 核心组件：解析入口参数 (task_ref, plan_ref, release_ref)、检测旁路执行尝试、执行参数有效性预校验。实现 BypassBlocker 的旁路检测逻辑和阻断响应机制，返回规范错误码 ERR-BYPASS-001。

## Acceptance Mapping
- FEAT-143 / AC-003-001: 实现入口唯一性验证逻辑：检查 task_ref 存在性及其归属 testplan
- FEAT-143 / AC-003-003: 实现旁路检测和阻断：识别无 task_ref 的直接调用并拒绝执行

## Prerequisites
- TASK-FEAT-143-001

## Dependencies
- {'task_id': 'TASK-FEAT-143-001', 'relationship': 'implements'}

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- test_results
- coverage_report
```

## Evidence Requirements
```yaml
required_refs:
- TASK-FEAT-143-001
- FTA-FEAT-143-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/execution/entry/validator.py
- src/lee/orchestrator/execution/entry/bypass_blocker.py
preconditions:
- 确保有回滚前的代码版本
```

## Definition Of Done
- EntryValidator 核心逻辑实现完成
- BypassBlocker 旁路检测实现完成
- 入口合法性校验通过单元测试
- 旁路阻断场景通过单元测试
- 错误代码 ERR-ENTRY-001/002/003、ERR-BYPASS-001 正确返回
- 代码通过静态分析和类型检查
