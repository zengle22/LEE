---
id: TECH-FEAT-SRC-006
ssot_type: tech
title: tech_design
status: frozen
version: v1
parent_id: FEAT-SRC-009-005
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:49.316445'
workflow_instance_id: wf-tech-feat-src-006__tech-design-20260316
---

required_fields:
- rule: endpoint_has_method_path
  description: 每个端点必须有 Method + Path
- rule: dto_has_type
  description: 每个 DTO 字段必须有显式类型
- rule: field_naming_snake_case
  description: 字段命名必须使用 snake_case
forbidden_patterns:
- pattern: any
  description: 禁止使用模糊类型 'any'
- pattern: object_without_properties
  description: 禁止使用无结构的 'object'
versioning:
  rule: semver
  description: 版本必须遵循 SemVer (major.minor.patch)
