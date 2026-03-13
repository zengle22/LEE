---
id: TECH-FEAT-SRC-004
ssot_type: tech
title: tech_design
status: frozen
version: v1
parent_id: FEAT-SRC-009-002
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
frozen_at: '2026-03-13T00:38:12.829647'
---

kind: l2_workflow_template
version: '1.0'
id: template.dev.bugfix_delivery_l2
name: Bugfix Delivery L2 Template
phases:
- id: triage
  kind: l3_subflow
  l3_template_ref: template.dev.bugfix_triage_l3
- id: root_cause
  kind: l3_subflow
  l3_template_ref: template.dev.bugfix_root_cause_l3
- id: fix_design
  kind: l3_subflow
  l3_template_ref: template.dev.bugfix_fix_design_l3
- id: fix_implementation
  kind: l3_subflow
  l3_template_ref: template.dev.bugfix_fix_impl_l3
- id: verification
  kind: l3_subflow
  l3_template_ref: template.dev.bugfix_verification_l3
- id: evidence_pack
  kind: l3_subflow
  l3_template_ref: template.dev.bugfix_evidence_pack_l3
- id: merge_or_reject
  kind: gate
  gate_id: gate.dev.merge_decision
