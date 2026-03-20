---
id: TASK-FEAT-SRC-009-008-003
ssot_type: task
title: StructuralIssueRouter 与回滚边界定义
status: frozen
version: v1
parent_id: FEAT-SRC-009-008
derived_from_ids: []
source_refs:
- FEAT-SRC-009-008#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_008_003
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:51.840417'
---

# Objective

定义结构性问题识别和回滚路由机制

# Description

基于 Frozen 技术架构，定义 StructuralIssueRouter 的问题分类机制（structural_contract、structural_tech、structural_feat、impl_bug）、根因分析逻辑、回滚边界标识、升级路径（连续 3 次同类失败自动升级为 structural）

## Acceptance Mapping
- FEAT-SRC-009-008 / AC-008-002: 阶段任务清单 - 问题修复机制定义
- FEAT-SRC-009-008 / AC-008-004: 交接规则 - 结构性问题解决状态

## Prerequisites
- TASK-FEAT-SRC-009-008-001

## Dependencies
- FROZEN-ARCH-FEAT-SRC-009-008
- ADR-008

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- evidence_refs
- rollback_routing_refs
```

## Evidence Requirements
```yaml
required_refs:
- FROZEN-ARCH-FEAT-SRC-009-008
- ADR-008
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec/tasks/FEAT-SRC-009-008/TASK-FEAT-SRC-009-008-003.md
```

## Definition Of Done
- StructuralIssueRouter 规范已冻结
- 问题分类表清晰定义（4 类别）
- 回滚边界和升级路径文档化
- 与 TECH/CONTRACT/FEAT 回滚点对齐
