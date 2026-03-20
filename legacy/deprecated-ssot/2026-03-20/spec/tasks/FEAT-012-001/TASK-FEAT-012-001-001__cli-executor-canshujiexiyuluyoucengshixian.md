---
id: TASK-FEAT-012-001-001
ssot_type: task
title: CLI executor 参数解析与路由层实现
status: frozen
version: v1
parent_id: FEAT-012-001
derived_from_ids: []
source_refs:
- FEAT-012-001#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_012_001_001
  identity_kind: ssot
frozen_at: '2026-03-12T22:38:48.172582'
---

# Objective

实现 CLI --executor 参数解析、验证及向 executor router 层的路由传递

# Description

在 CLI 入口层添加 --executor 参数解析逻辑，实现执行器名称有效性校验，并将解析结果传递至 executor router。包含参数提取、可用执行器列表校验、无效参数错误提示。

## Acceptance Mapping
- FEAT-012-001 / AC-012-001-01: CLI 参数 --executor <name> 被正确解析并传递至执行器路由层
- FEAT-012-001 / AC-012-001-03: 无效执行器名称返回清晰错误提示，列出可用执行器列表

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
- src/cli/argument_parser.py
- src/cli/executor_validator.py
```

## Definition Of Done
- CLI 参数解析器支持 --executor 参数
- 执行器名称有效性校验逻辑实现
- 无效参数错误提示包含可用执行器列表
- 单元测试覆盖参数解析和校验场景
- TASK 文件已冻结
