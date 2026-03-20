---
id: TASK-FEAT-SRC-009-011-003
ssot_type: task
title: Workflow 目录共享规范集成
status: active
version: v1
parent_id: FEAT-SRC-009-011
derived_from_ids: []
source_refs:
- FEAT-SRC-009-011#delivery
- TECH-FEAT-SRC-009-011-001
owner: null
tags: []
properties:
  contract_key: task_workflow_runtime_integration
  identity_kind: ssot
  materialized_from_workflow: wf_task_4a3a7a74
---

# Objective

将共享输入规范集成到 workflow 模板

# Description

更新所有 Dev workflow 模板以引用共享输入规范，确保跨工作流的一致性和可集成性

## Acceptance Mapping
- FEAT-SRC-009-011 / AC-011-001: 共享输入规范文档已冻结

## Prerequisites
- TASK-FEAT-SRC-009-011-001 已完成
- TASK-FEAT-SRC-009-011-002 已完成

## Dependencies
- 无

## Definition Of Done
- workflow_catalog 覆盖所有 Dev workflow
- feature_delivery_l2 模板引用共享输入规范
- bugfix_delivery_l2 模板引用共享输入规范
- L3 阶段模板引用共享输入规范
- 集成验证通过

## Observability
- execution_unit: task
- log_scope: task-execution
- audit_fields: [run_id, changed_files, evidence_refs]

## Evidence Requirements
- required_refs: [TECH-FEAT-SRC-009-011-001]
- review_required: true

## Rollback Strategy
- mode: revert
- restore_targets: [spec-global/departments/dev/workflows/templates/]
