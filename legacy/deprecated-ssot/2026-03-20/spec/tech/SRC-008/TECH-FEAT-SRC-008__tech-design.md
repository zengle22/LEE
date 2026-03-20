---
id: TECH-FEAT-SRC-008
ssot_type: tech
title: tech_design
status: frozen
version: v1
parent_id: FEAT-SRC-009-010
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
frozen_at: '2026-03-13T00:47:10.067813'
workflow_instance_id: wf-tech-feat-src-008__tech-design-20260316
---

version: v1
updated_at: 2026-03-13
governing_adr: ADR-008
deprecated_paths:
- path: spec-global/departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml
  status: deprecated
  reason: 非当前 canonical Dev 主路径，已由 ADR-008 降级为 draft
  replacement: spec-global/departments/dev/workflows/templates/feature-l2-template.yaml
  deprecated_at: 2026-03-13
  migration_deadline: null
- path: spec-global/departments/dev/README.md
  status: partial_deprecated
  reason: 部分章节传播旧主链或不存在路径
  replacement_sections:
  - section: 主工作流入门
    new_path: spec-global/departments/dev/workflows/templates/README.md
- path: spec-global/WORKFLOWS.md
  status: partial_deprecated
  reason: 仍把旧 Dev workflow 视为现役
  affected_sections:
  - Dev 部门工作流
- path: spec-global/departments/dev/rnd_l2_l3_spec.md
  status: informational_only
  reason: 作为历史设计说明保留，不再承担可执行规范职责
  replacement: ADR-008 + feature-l2-template.yaml
- path: spec-global/departments/dev/workflows/templates/bug-fix-l3-template.yaml
  status: broken
  reason: 已与真实 agent/gate 目录命名脱节
  replacement: 待新增 bugfix_delivery_l2 + bugfix L3 family
