---
id: TASK-FEAT-SRC-009-012-003
ssot_type: task
title: 粒度合规检查清单设计
status: active
version: v1
parent_id: FEAT-SRC-009-012
derived_from_ids:
- FEAT-SRC-009-012
source_refs:
- FEAT-SRC-009-012
- ADR-008
owner: dev-qa-coordinator
tags:
- validation
- bugfix
- checklist
- ssot
properties:
  contract_key: task_granularity_checklist
  identity_kind: ssot
  materialized_from_workflow: wf_task_b16f6a2e
  priority: P1
  delivery_slice: validation
  lifecycle_status: draft
  workstream: dev-governance-validation
  responsible_role: dev-qa-coordinator
---

# 粒度合规检查清单设计

## Objective

创建粒度合规检查 checklist，确保每个 bugfix workflow instance 符合粒度控制要求。

## Description

基于五同原则和默认规则，创建可用于人工检查的 checklist，确保每个 bugfix workflow instance 符合粒度控制要求。

## Acceptance Criteria Mapping

| FEAT | AC | Description |
|------|-----|-------------|
| FEAT-SRC-009-012 | AC-012-001 | 粒度合规检查 checklist 可用 |

## Prerequisites

- TASK-FEAT-SRC-009-012-001 frozen

## Dependencies

- TASK-FEAT-SRC-009-012-001

## Definition of Done

- [ ] TASK 文件已创建并标记为 frozen
- [ ] Checklist 覆盖五同原则每个维度
- [ ] Checklist 覆盖默认规则判断
- [ ] Checklist 格式可执行、可记录

## Observability

- execution_unit: task
- log_scope: task-execution
- audit_fields: [run_id, changed_files, evidence_refs]

## Evidence Requirements

- required_refs:
  - TASK-FEAT-SRC-009-012-001
  - TECH-FEAT-SRC-009-012-001
- review_required: true

## Rollback Strategy

- mode: revert
- restore_targets:
  - spec/tasks/FEAT-SRC-009-012/TASK-FEAT-SRC-009-012-003
- preconditions:
  - 通知 dev-qa-coordinator

## SSOT

- identity_kind: ssot
- ssot_type: TASK
- parent: FEAT-SRC-009-012
- derived_from: FEAT-SRC-009-012#processing
