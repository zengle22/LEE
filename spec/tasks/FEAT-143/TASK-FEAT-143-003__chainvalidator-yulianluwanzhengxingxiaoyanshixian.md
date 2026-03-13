---
id: TASK-FEAT-143-003
ssot_type: task
title: ChainValidator 与链路完整性校验实现
status: frozen
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
frozen_at: '2026-03-13T13:08:01.881607'
---

# Objective

实现 RELEASE→PLAN→TASK 链路完整性校验器

# Description

实现 ChainValidator 组件，按渐进式顺序 (task→plan→release) 逐级校验执行路径完整性。包含 LRU 缓存策略 (60s TTL)、错误定位提示、Registry 不一致时降级策略。

## Acceptance Mapping
- FEAT-143 / AC-003-002: ChainValidator 验证 release_ref→testplan_ref→task_ref 链路完整且有效

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
- src/lee/qa/chain_validator.py
- src/lee/qa/cache.py
```

## Definition Of Done
- src/lee/qa/chain_validator.py 实现完成
- 渐进式校验 (task→plan→release) 已实现
- LRU 缓存策略已配置 (60s TTL)
- Registry 降级策略已实现
- 错误码 QA-ENTRY-003~010 已注册
- TASK 文件已冻结
