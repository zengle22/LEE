---
id: TASK-FEAT-SRC-009-012-001
ssot_type: task
title: Bugfix 粒度控制规范定义
status: active
version: v1
parent_id: FEAT-SRC-009-012
derived_from_ids:
- FEAT-SRC-009-012
source_refs:
- FEAT-SRC-009-012
- ADR-008
- EPIC-SRC-009#scope
owner: dev-architecture-owner
tags:
- governance
- bugfix
- granularity
- ssot
properties:
  contract_key: task_granularity_spec
  identity_kind: ssot
  materialized_from_workflow: wf_task_b16f6a2e
  priority: P0
  delivery_slice: governance-spec
  lifecycle_status: draft
  workstream: dev-governance-spec
  responsible_role: dev-architecture-owner
---

# Bugfix 粒度控制规范定义

## Objective

定义 Bugfix 粒度控制的默认规则和五同原则，确保 1 bug → 1 workflow instance 成为默认标准，同时为 batch 场景提供清晰的判断依据。

## Description

基于 FEAT-SRC-009-012 和 ADR-008，定义 1 bug → 1 workflow instance 默认规则，以及五同原则（同模块、同根因、同修复方案、同测试范围、同风险等级）的完整规范。

## Acceptance Criteria Mapping

| FEAT | AC | Description |
|------|-----|-------------|
| FEAT-SRC-009-012 | AC-012-001 | Bugfix 粒度控制规则文档已冻结 |
| FEAT-SRC-009-012 | AC-012-002 | 默认规则明确为 1 bug → 1 bugfix workflow instance |
| FEAT-SRC-009-012 | AC-012-003 | 五同原则完整定义（同模块、同根因、同修复方案、同测试范围、同风险等级） |

## Prerequisites

- FEAT-SRC-009-012 frozen
- TECH-FEAT-SRC-009-012-001 active
- ADR-008 frozen

## Dependencies

- FEAT-SRC-009-002

## Definition of Done

- [ ] TASK 文件已创建并标记为 frozen
- [ ] 默认规则章节完整定义
- [ ] 五同原则每个维度有清晰判断标准
- [ ] 规范文档通过评审

## Observability

- execution_unit: task
- log_scope: task-execution
- audit_fields: [run_id, changed_files, evidence_refs]

## Evidence Requirements

- required_refs:
  - TECH-FEAT-SRC-009-012-001
  - ADR-008
  - FEAT-SRC-009-012
- review_required: true

## Rollback Strategy

- mode: revert
- restore_targets:
  - spec/requirements/features/FEAT-SRC-009-012
  - spec/tech/TECH-FEAT-SRC-009-012-001
- preconditions:
  - 通知 EPIC-SRC-009 owner
  - 更新依赖此 TASK 的 downstream 任务

## SSOT

- identity_kind: ssot
- ssot_type: TASK
- parent: FEAT-SRC-009-012
- derived_from: FEAT-SRC-009-012#processing
