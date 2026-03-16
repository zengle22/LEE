---
id: TASK-FEAT-012-001-002
ssot_type: task
title: 执行器选择优先级规范与路由决策实现
status: frozen
version: v1
parent_id: FEAT-012-001
derived_from_ids: []
source_refs:
- FEAT-012-001#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_012_001_002
  identity_kind: ssot
frozen_at: '2026-03-12T22:38:48.183700'
---

# Objective

定义并实现执行器选择优先级规则（CLI 参数 > 默认配置 > 系统预设），确保与现有 qwen 执行器实现一致性

# Description

制定执行器选择优先级策略规范，实现 executor router 层的决策逻辑：CLI 显式参数覆盖默认配置，默认配置覆盖系统预设。确保 kimi/qwen 执行器复用同一路由逻辑，无代码重复。

## Acceptance Mapping
- FEAT-012-001 / AC-012-001-02: 执行器选择优先级规则实现：CLI 参数优先级高于默认配置
- FEAT-012-001 / AC-012-001-04: 与现有 qwen 执行器实现一致性，复用相同路由逻辑

## Prerequisites
- TASK-FEAT-012-001-001

## Dependencies
- TASK-FEAT-012-001-001

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- evidence_refs
- test_results
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-012-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/executor/router.py
- src/executor/selector.py
```

## Definition Of Done
- 执行器选择优先级规范文档完成
- executor router 层优先级决策逻辑实现
- kimi/qwen 执行器复用同一路由链路验证
- 集成测试验证优先级规则（CLI > config > preset）
- TASK 文件已冻结
