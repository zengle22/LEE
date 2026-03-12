---
id: TASK-FEAT-SRC-009-005-005
ssot_type: task
title: Contract Design 文档治理与入口更新
status: frozen
version: v1
parent_id: FEAT-SRC-009-005
derived_from_ids: []
source_refs:
- FEAT-SRC-009-005#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_005_005
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:49.376150'
---

# Objective

更新 README/WORKFLOWS 等文档，将 Contract Design L3 纳入 Dev 部门正式文档体系

# Description

基于 ADR-008 和已完成的 Contract Design 阶段定义，更新 Dev 部门文档资产，包括：(1) 更新 spec-global/departments/dev/README.md，添加 feature_contract_l3 入口说明；(2) 更新 WORKFLOWS.md，将 Contract Design L3 纳入 L3 工作流家族；(3) 更新 AGENTS.md，注册 feature_contract_l3 Agent；(4) 编写 Contract Design 阶段使用指南。确保文档与实现一致，不传播旧路径。

## Acceptance Mapping
- FEAT-SRC-009-005 / AC-005-001: 文档入口更新完成，Contract Design L3 可被发现
- FEAT-SRC-009-005 / AC-005-003: 文档明确定义与 Backend/Frontend 的交接规则

## Prerequisites
- TASK-FEAT-SRC-009-005-001 完成
- TASK-FEAT-SRC-009-005-002 完成

## Dependencies
- TASK-FEAT-SRC-009-005-001
- TASK-FEAT-SRC-009-005-002

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- doc_review_approval
```

## Evidence Requirements
```yaml
required_refs:
- spec-global/departments/dev/README.md
- spec-global/WORKFLOWS.md
- spec-global/departments/dev/AGENTS.md
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/README.md
- spec-global/WORKFLOWS.md
- spec-global/departments/dev/AGENTS.md
preconditions:
- 文档未正式发布前可回滚
```

## Definition Of Done
- spec-global/departments/dev/README.md 已更新，包含 feature_contract_l3 入口
- WORKFLOWS.md 已更新，Contract Design L3 纳入 L3 工作流家族
- AGENTS.md 已更新，feature_contract_l3 Agent 已注册
- Contract Design 阶段使用指南已编写
- 文档不传播旧路径或不存在的入口
- 文档通过评审并标记为 frozen 状态
