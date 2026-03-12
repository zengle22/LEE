---
id: TECH-FEAT-SRC-002
ssot_type: tech
title: tech_design
status: frozen
version: v1
parent_id: FEAT-SRC-009-001
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
frozen_at: '2026-03-13T00:06:13.702854'
---

validation_rules:
  formal_ssot_id:
  - type: string
  - pattern: ^FEAT-[A-Z]+-[0-9]+-[0-9]+$
  - must_resolve: true
  - status_check: frozen
  source_refs:
  - type: array
  - min_items: 1
  - item_pattern: ^[A-Z]+-[A-Z]+-[0-9]+(#.*)?$
  governing_adrs:
  - type: array
  - min_items: 1
  - item_pattern: ^ADR-[0-9]+$
  - must_exist_in: spec/adr/
  repo_context:
    required_fields:
    - repo_path: string
    - branch_rules: object
    - module_scope: string
