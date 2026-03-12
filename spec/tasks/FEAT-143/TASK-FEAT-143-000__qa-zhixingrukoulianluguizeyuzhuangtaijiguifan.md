---
id: TASK-FEAT-143-000
ssot_type: task
title: QA 执行入口链路规则与状态机规范
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_143_000
  identity_kind: ssot
---

# Objective

定义 RELEASE -> PLAN -> TASK 链路校验规则、状态机边界和错误码映射，作为实现任务的先决规范

# Description

在正式实现前冻结执行入口规则集，覆盖 RULE-001~RULE-006、路径校验边界、状态转换约束、错误码映射和审计字段契约，避免结构性规则直接埋入实现代码。

## Acceptance Mapping
- FEAT-143 / AC-003-001: 仅当请求包含有效的 task_ref 且 task 归属 testplan 时才被接受
- FEAT-143 / AC-003-002: 系统验证 release_ref -> testplan_ref -> task_ref 链路完整且有效
- FEAT-143 / AC-003-004: 日志中包含每次执行的入口来源、路径链、时间戳、操作用户

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
- FEAT-143
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
- 链路规则和状态机规范文档已冻结
- 错误码与规则映射表已定义
- 实现任务已明确引用该规范任务作为前置依赖
