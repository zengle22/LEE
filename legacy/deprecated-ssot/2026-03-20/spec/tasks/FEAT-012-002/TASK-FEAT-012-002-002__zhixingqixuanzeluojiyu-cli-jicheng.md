---
id: TASK-FEAT-012-002-002
ssot_type: task
title: 执行器选择逻辑与 CLI 集成
status: frozen
version: v1
parent_id: FEAT-012-002
derived_from_ids: []
source_refs:
- FEAT-012-002#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_012_002_002
  identity_kind: ssot
frozen_at: '2026-03-12T22:48:20.438019'
---

# Objective

实现执行器选择逻辑，集成 CLI 参数优先级处理

# Description

在 CLI 启动流程中集成配置加载，实现执行器选择逻辑：CLI 参数 > 配置文件 > 系统默认，支持配置变更在下次执行时生效

## Acceptance Mapping
- FEAT-012-002 / AC-012-002-01: 配置项读取与生效：未指定 --executor 时使用配置默认值
- FEAT-012-002 / AC-012-002-02: 配置与 CLI 参数的优先级：CLI 参数优先于配置文件
- FEAT-012-002 / AC-012-002-03: 配置变更后生效：下次 CLI 执行时读取最新配置

## Prerequisites
- TASK-FEAT-012-002-001

## Dependencies
- TASK-FEAT-012-002-001

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- evidence_refs
- integration_test_results
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-012-002
- TECH-FEAT-012-002
- TASK-FEAT-012-002-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/cli/
- src/orchestrator/executor_selection.py
- spec/tasks/FEAT-012-002/TASK-FEAT-012-002-002.md
```

## Definition Of Done
- CLI 启动时配置加载集成完成
- 执行器选择优先级逻辑实现（--executor > config > default）
- 配置变更检测与重载机制实现
- 集成测试验证完整配置生命周期
- TASK 文件已冻结
