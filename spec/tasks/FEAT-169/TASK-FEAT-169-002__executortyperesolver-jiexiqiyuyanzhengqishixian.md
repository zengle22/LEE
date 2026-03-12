---
id: TASK-FEAT-169-002
ssot_type: task
title: ExecutorTypeResolver 解析器与验证器实现
status: active
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
---

# Objective

实现四层优先级解析和配置验证逻辑

# Description

实现 ExecutorTypeResolver 实现 CLI > Env > Config > Default 四层优先级解析，实现 ExecutorTypeValidator 实现执行器类型验证和错误信息格式化，实现 ConfigValidationErrorHandler 实现错误处理

## Acceptance Mapping
- FEAT-169 / AC-001: CLI 指定 --executor=qwen 时配置层正确识别
- FEAT-169 / AC-002: 配置文件设置 executor: qwen 时配置层正确识别
- FEAT-169 / AC-003: 执行器来源优先级判定 CLI > 配置文件 > 默认设置
- FEAT-169 / AC-004: 配置错误时返回明确错误信息

## Prerequisites
- 执行器配置优先级与验证规则规范
- TASK-FEAT-169-001

## Dependencies
- TASK-FEAT-169-000
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
- FTA-FEAT-169-20260312
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/config/
```

## Definition Of Done
- ExecutorTypeResolver.resolve 实现四层优先级解析
- ExecutorTypeValidator.validate 实现验证逻辑
- ExecutorTypeValidator.format_error_message 实现错误格式化
- ConfigValidationErrorHandler 实现错误处理并阻止 workflow 启动
- 来源追踪功能正确记录 source_marker
- 单元测试覆盖所有 AC 场景
