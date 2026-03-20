---
id: TASK-FEAT-SRC-009-010-005
ssot_type: task
title: 旧路径降级验证测试设计
status: frozen
version: v1
parent_id: FEAT-SRC-009-010
derived_from_ids: []
source_refs:
- FEAT-SRC-009-010#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_010_005
  identity_kind: ssot
frozen_at: '2026-03-13T00:47:10.236819'
---

# Objective

设计验证测试用例，确认旧路径降级治理的有效性

# Description

创建 Test Set 验证旧路径降级治理效果，包括：验证 deprecated_paths 清单完整性、验证标记规范可执行性、验证迁移指南可执行性、验证新入口文档正确指向新 L2 入口

## Acceptance Mapping
- FEAT-SRC-009-010 / AC-010-002: Deprecated 路径清单完整性
- FEAT-SRC-009-010 / AC-010-003: 标记规范可执行性
- FEAT-SRC-009-010 / AC-010-004: 迁移指南完整性

## Prerequisites
- TASK-FEAT-SRC-009-010-001 已完成
- TASK-FEAT-SRC-009-010-002 已完成
- TASK-FEAT-SRC-009-010-003 已完成

## Dependencies
- TASK-FEAT-SRC-009-010-001
- TASK-FEAT-SRC-009-010-002
- TASK-FEAT-SRC-009-010-003

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- test_cases_count
- coverage_summary
```

## Evidence Requirements
```yaml
required_refs:
- TASK-FEAT-SRC-009-010-001
- TASK-FEAT-SRC-009-010-002
- TASK-FEAT-SRC-009-010-003
- FEAT-SRC-009-010#Acceptance
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec/tasks/FEAT-SRC-009-010/testset_deprecated_paths_validation.yaml
preconditions:
- 确保原始 Test Set 已版本控制
```

## Definition Of Done
- TASK 文件已冻结
- Test Set 设计完成并通过评审
- 测试用例覆盖所有 AC 验证场景
