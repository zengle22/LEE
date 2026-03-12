---
id: SRC-010
ssot_type: src
title: SRC
status: active
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: src
  identity_kind: ssot
---

product_entity: 需求链一致性测试系统
core_function:
- Verification
- Reporting
input_contract: Standardized src/epic/feat/task document set
output_contract: Structured scorecard.json & exception_list.md
success_metrics:
- name: Trace Completeness
  target: -> 100%
- name: Semantic Alignment Score
  target: Trend Up
- name: Replay Stability Score
  target: Variance < Threshold
- name: Overlap Rate
  target: -> 0%
- name: Executability Rate
  target: Significant Increase
constraints:
- Read-only operation on requirements
- No replacement of PO value judgment
- Non-blocking gate in Phase 1-2
- 'Cost control: Programmatic rules > LLM'
phase_roadmap:
- 'Phase 1: Structure & Trace'
- 'Phase 2: Semantics & Overlap'
- 'Phase 3: Stability & Regression'
