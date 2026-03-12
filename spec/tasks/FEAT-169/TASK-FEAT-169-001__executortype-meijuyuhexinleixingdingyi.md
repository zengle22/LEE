---
id: TASK-FEAT-169-001
ssot_type: task
title: ExecutorType 枚举与核心类型定义
status: active
version: v1
parent_id: FEAT-169
derived_from_ids: []
source_refs:
- FEAT-169#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_169_001
  identity_kind: ssot
---

# Objective

实现 ExecutorType 枚举和大小写不敏感解析方法

# Description

在 src/lee/orchestrator/config/ 下创建 ExecutorType 枚举，定义允许的执行器类型(qwen, claude_code, auto)，实现 from_string 大小写不敏感解析方法

## Acceptance Mapping
- FEAT-169 / AC-001: CLI 指定 --executor=qwen 时配置层正确识别
- FEAT-169 / AC-002: 配置文件设置 executor: qwen 时配置层正确识别

## Prerequisites
- 执行器配置优先级与验证规则规范

## Dependencies
- TASK-FEAT-169-000

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
- ExecutorType 枚举定义完成
- from_string 大小写不敏感解析实现
- allowed_values 类方法返回允许值列表
- 单元测试覆盖边界情况(大小写混合、无效值)
