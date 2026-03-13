---
id: TASK-FEAT-169-002
ssot_type: task
title: 执行器配置解析器与验证器实现
status: frozen
version: v1
parent_id: FEAT-169
derived_from_ids: []
source_refs:
- FEAT-169#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_169_002
  identity_kind: ssot
frozen_at: '2026-03-13T01:36:39.456198'
---

# Objective

实现 ConfigResolver 类完成四层优先级解析和验证逻辑

# Description

在 src/lee/orchestrator/config/resolver.py 创建 ConfigResolver 类，实现 resolve 方法按 CLI > Env > Config > Default 优先级解析执行器配置，实现 validate_executor_type 方法验证执行器类型合法性，实现 get_valid_executor_types 方法从 ExecutorFactory 动态获取合法类型列表，错误信息格式包含非法值和可选值列表

## Acceptance Mapping
- FEAT-169 / AC-001: CLI 指定 --executor=qwen 时配置层正确识别
- FEAT-169 / AC-002: 配置文件设置 executor: qwen 时配置层正确识别
- FEAT-169 / AC-003: 执行器来源优先级判定 CLI > 配置文件 > 默认设置
- FEAT-169 / AC-004: 配置错误时返回明确错误信息

## Prerequisites
- TASK-FEAT-169-001

## Dependencies
- TASK-FEAT-169-001

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
- FTA-FEAT-169-20260313
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/config/resolver.py
```

## Definition Of Done
- ConfigResolver.resolve 方法实现四层优先级解析逻辑
- ConfigResolver.validate_executor_type 方法实现验证逻辑
- ConfigResolver.get_valid_executor_types 方法从 ExecutorFactory 动态获取类型
- 错误信息格式为 '错误：非法的执行器类型 X\n可选值：[列表]'
- 解析结果正确设置 source_marker 用于追溯
- 单元测试覆盖所有优先级场景和边界情况
