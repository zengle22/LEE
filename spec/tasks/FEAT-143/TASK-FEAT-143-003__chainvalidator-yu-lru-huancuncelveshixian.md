---
id: TASK-FEAT-143-003
ssot_type: task
title: ChainValidator 与 LRU 缓存策略实现
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_143_003
  identity_kind: ssot
---

# Objective

实现 RELEASE->PLAN->TASK 执行路径完整性校验组件

# Description

实现 ChainValidator：验证 RELEASE->TESTPLAN->TASK 执行路径的完整性，按渐进式顺序 (task->plan->release) 逐级校验并提供清晰错误定位；实现 LRU 缓存策略 (60 秒 TTL) 平衡一致性与性能，减少重复 SSOT 对象查询。

## Acceptance Mapping
- FEAT-143 / AC-003-002: ChainValidator 验证 release_ref->testplan_ref->task_ref 链路完整且有效，按渐进式顺序校验

## Prerequisites
- TASK-FEAT-143-001

## Dependencies
- ArtifactManager
- SSOTService
- TASK-FEAT-143-002

## Observability
```yaml
execution_unit: task
log_scope: task-runtime-implementation
audit_fields:
- run_id
- task_id
- changed_files
- test_results
- cache_metrics
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
- src/lee/orchestrator/execution/chain_validator.py
- src/lee/orchestrator/execution/cache/
preconditions:
- 保留实现前的代码版本
```

## Definition Of Done
- TASK 文件已冻结
- ChainValidator 实现完成并通过单元测试
- 校验规则 CHAIN-001/002/003 全部覆盖
- LRU 缓存 TTL 60 秒策略生效
