---
id: TASK-FEAT-SRC-009-006-002
ssot_type: task
title: L3 Backend Development Workflow 模板实现
status: frozen
version: v1
parent_id: FEAT-SRC-009-006
derived_from_ids: []
source_refs:
- FEAT-SRC-009-006#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_006_002
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:50.508243'
---

# Objective

实现 L3 Backend Development 的 workflow 模板，支持 UTDD 循环执行

# Description

基于阶段规范实现可执行的 L3 workflow 模板，包含 UT 编写、实现、重构三阶段的编排逻辑，集成覆盖率检查门禁，输出代码、单元测试、覆盖率报告。

## Acceptance Mapping
- FEAT-SRC-009-006 / AC-006-001: Backend Development 阶段文档冻结
- FEAT-SRC-009-006 / AC-006-002: UTDD 循环定义完整性

## Prerequisites
- TASK-FEAT-SRC-009-006-001 completed

## Dependencies
- template.dev.feature_be_l3

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- template_path
- validation_result
```

## Evidence Requirements
```yaml
required_refs:
- TASK-FEAT-SRC-009-006-001
- template.dev.feature_be_l3
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/workflows/templates/l3-backend-development.yaml
preconditions:
- 确认无正在运行的 workflow instance
```

## Definition Of Done
- L3 Backend workflow 模板已创建
- UTDD 循环（UT → Impl → Refactor）编排正确
- 覆盖率门禁集成（≥80% 失败）
- 输出物规范正确（代码、UT、报告）
- 模板通过 schema 验证
