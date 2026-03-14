# Evidence Pack Integration Specification

## Purpose

This document defines how Evidence Pack integrates with Dev department L2 workflows.

It covers:

- Feature Delivery L2 integration
- Bugfix Delivery L2 integration
- input contract handoff
- output contract handoff

## Feature Delivery L2 Integration

Trigger point:

- phase: `evidence_pack`
- condition: `integration` phase has produced its final report and upstream delivery artifacts exist

Required inputs:

- `formal_ssot_id`
- `source_refs`
- `governing_adrs`
- `delivery_outputs`
- `verification_results`
- `integration_report_ref`

Expected outputs:

- `evidence_pack_ref`
- `delivery_candidate_ref`
- `smoke_gate_input`

Handoff rule:

- Evidence Pack is the final pre-gate closure phase for Feature Delivery L2.
- `smoke_gate` may not execute before `evidence_pack_ref` exists.

## Bugfix Delivery L2 Integration

Trigger point:

- phase: `evidence_pack`
- condition: `verification` phase has produced verification outputs and closure artifacts exist

Required inputs:

- `bug_ssot_id`
- `severity`
- `reproduction_evidence`
- `delivery_outputs`
- `verification_results`
- `verification_report_ref`

Expected outputs:

- `evidence_pack_ref`
- `closure_summary_ref`
- `merge_or_reject_input`

Handoff rule:

- Bugfix Delivery L2 must not enter `merge_or_reject` before the bugfix evidence pack exists.

## Shared Interface Rules

1. `delivery_outputs` must point to upstream implementation or contract artifacts.
2. `verification_results` must point to test, review, integration, or deployment evidence.
3. Evidence Pack emits only references, not opaque free-form summaries.
4. All emitted refs must remain traceable to `formal_ssot_id` or `bug_ssot_id`.
