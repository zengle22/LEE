---
id: TASK-FEAT-169-000
ssot_type: task
title: 执行器配置优先级与验证规则规范
status: active
version: v1
parent_id: FEAT-169
derived_from_ids: []
source_refs:
- FEAT-169#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_169_000
  identity_kind: ssot
---

# Objective

冻结执行器类型选择、优先级判定、来源追踪与错误处理边界，作为实现任务的前置规范基线

# Description

在正式实现前冻结执行器配置规范，覆盖执行器类型白名单、CLI/环境变量/配置文件/默认值的优先级规则、来源追踪字段和错误信息模板，避免结构性规则散落在实现代码中。

## Acceptance Mapping
- FEAT-169 / AC-003: 最终生效值为 `qwen`，并记录来源为 `cli_override`
- FEAT-169 / AC-004: 返回包含非法值与可选值列表的明确错误信息，且不进入 workflow 执行阶段

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- evidence_refs
- review_refs
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-169
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec/tasks
- spec/contracts
- spec-global/departments/product/workflows
```

## Definition Of Done
- 结构性规则和契约边界文档已冻结
- 规范任务已覆盖相关结构性 Acceptance Checks
- 实现任务已明确引用该规范任务作为前置依赖
