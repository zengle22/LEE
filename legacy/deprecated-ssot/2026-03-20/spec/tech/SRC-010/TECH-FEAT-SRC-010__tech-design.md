---
id: TECH-FEAT-SRC-010
ssot_type: tech
title: tech_design
status: frozen
version: v1
parent_id: FEAT-SRC-009-009
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:53.025948'
workflow_instance_id: wf-tech-feat-src-010__tech-design-20260316
---

module: evidence_pack_core
location: spec-global/departments/dev/evidence/
canonical_form: schema.json + collector.py
components:
- name: EvidenceSchema
  type: data_class
  responsibility: 定义证据包的正式结构
  implementation: JSON Schema + Python dataclass
- name: EvidenceCollector
  type: service
  responsibility: 从各阶段收集证据并验证完整性
  dependencies:
  - Git API (code diff)
  - File System (artifact paths)
  - Workflow Context (phase outputs)
- name: EvidenceValidator
  type: validator
  responsibility: 验证证据格式与合规性
  dependencies:
  - JSON Schema Validator
  - Custom validation rules
- name: EvidencePackager
  type: service
  responsibility: 打包证据并生成审计声明
  dependencies:
  - EvidenceSchema
  - EvidenceValidator
  - Hash generator (SHA-256)
