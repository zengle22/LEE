---
id: TASK-FEAT-SRC-009-006-003
ssot_type: task
title: TDD 覆盖率门禁运行时集成
status: frozen
version: v1
parent_id: FEAT-SRC-009-006
derived_from_ids: []
source_refs:
- FEAT-SRC-009-006#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_006_003
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:50.520139'
---

# Objective

将 TDD 覆盖率门禁（≥80%）集成到 L2/L3 运行时中

# Description

在 L2 Feature Delivery Workflow 和 L3 Backend Development Workflow 中集成覆盖率门禁检查，确保低于 80% 覆盖率时自动失败并回退至 UT 编写阶段。此 TASK 覆盖 RISK-004 缓解策略的运行时实现。

## Acceptance Mapping
- FEAT-SRC-009-006 / AC-006-003: 完成标准可量化

## Prerequisites
- TASK-FEAT-SRC-009-006-002 completed

## Dependencies
- template.dev.feature_delivery_l2
- template.dev.l3_backend_development

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- coverage_threshold
- coverage_actual
- gate_result
```

## Evidence Requirements
```yaml
required_refs:
- TASK-FEAT-SRC-009-006-002
- RISK-004
review_required: false
```

## Rollback Strategy
```yaml
mode: replay
restore_targets:
- spec-global/departments/dev/workflows/templates/feature_delivery_l2.yaml
- spec-global/departments/dev/workflows/templates/l3-backend-development.yaml
preconditions:
- 备份当前 workflow 配置
```

## Definition Of Done
- 覆盖率检查集成到 L3 Backend workflow
- 覆盖率<80% 时自动失败
- 失败时回退至 UT 编写阶段
- 覆盖率报告正确生成
- 集成测试通过
