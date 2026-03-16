---
id: TASK-FEAT-SRC-009-009-003
ssot_type: task
title: Evidence Pack 运行时收集器实现
status: draft
version: v1
parent_id: FEAT-SRC-009-009
derived_from_ids:
- TECH-FEAT-SRC-009-009-001
source_refs:
- TECH-FEAT-SRC-009-009-001#components
owner: dev-runtime-engineer
tags:
- task
- ssot
- evidence-pack
- runtime-implementation
properties:
  contract_key: task_evidence_pack_collector
  identity_kind: ssot
  workstream: runtime-implementation
  task_kind: implementation
  parent: FEAT-SRC-009-009
  derived_from: TECH-FEAT-SRC-009-009-001#components
  prerequisites:
  - TASK-FEAT-SRC-009-009-001
  - TASK-FEAT-SRC-009-009-002
  dependencies:
  - TECH-FEAT-SRC-009-009-001
  - TECH-FEAT-SRC-009-004-001
  priority: P1
  milestone: M3-Runtime
  estimated_effort: 1 day
---

# Evidence Pack 运行时收集器实现

## Objective

实现 EvidenceCollector 运行时组件，从各阶段收集证据并验证完整性。

## Description

基于 TECH 设计实现 EvidenceCollector 运行时组件，负责：
- 从 Integration 阶段、Test Set、Gate 结果等收集证据引用
- 去重后生成证据索引和 manifest
- 支持从 Git artifact、File System、Workflow Context 收集证据

## Acceptance Criteria Mapping

| FEAT | AC | Description |
|------|-----|-------------|
| FEAT-SRC-009-009 | AC-009-002 | 阶段任务清单覆盖证据收集任务 |

## Dependencies

- TASK-FEAT-SRC-009-009-001 (前置)
- TASK-FEAT-SRC-009-009-002 (前置)
- TECH-FEAT-SRC-009-009-001 (依赖)
- TECH-FEAT-SRC-009-004-001 (依赖)

## Definition Of Done

- [ ] EvidenceCollector 组件已实现
- [ ] 支持从 Git artifact、File System、Workflow Context 收集证据
- [ ] 实现证据去重和索引生成逻辑
- [ ] 单元测试覆盖率 >= 80%

## Observability

- execution_unit: task
- log_scope: task-runtime-collector
- audit_fields: [run_id, changed_files, test_coverage_report, component_id]

## Evidence Requirements

- required_refs: [TECH-FEAT-SRC-009-009-001, TASK-FEAT-SRC-009-009-001]
- review_required: true

## Rollback Strategy

- mode: revert
- restore_targets:
  - src/lee/evidence/collector.py
  - src/lee/evidence/manifest.py
