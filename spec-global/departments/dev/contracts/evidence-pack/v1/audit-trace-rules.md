# Evidence Pack Audit Trace Rules

## Purpose

This document defines how an Evidence Pack can be traced back to upstream SSOT
objects and implementation artifacts.

This mechanism defines trace rules only. It does not implement or override any
audit decision logic.

## Trace Rule 1: Evidence Pack To FEAT

Required fields:

- `formal_ssot_id`
- `source_refs`

Rule:

- `formal_ssot_id` must point to the owning workflow, feature, or bug execution root
- `source_refs` must preserve links back to the requirement axis

Expected result:

- reviewers can trace an evidence pack to its parent FEAT or BUG source

## Trace Rule 2: Evidence Pack To TECH

Required refs:

- `source_refs`
- `delivery_outputs[*].ref`

Rule:

- if the upstream chain contains a TECH bridge object, the evidence pack must preserve a trace path from
  implementation evidence back to the TECH ref through delivery outputs or source refs

Expected result:

- reviewers can determine whether the final evidence still honors the TECH bridge object

## Trace Rule 3: Evidence Pack To Implementation Changes

Required refs:

- `delivery_outputs`
- `verification_results`

Rule:

- code-diff or implementation artifact refs must remain reachable from the evidence pack
- test, review, and integration outputs must point to or name the corresponding implementation refs

Expected result:

- reviewers can follow the chain from evidence pack -> code diff -> verification -> review

## Non-Interference Rule

This specification does not:

- decide whether an audit passes or fails
- redefine review thresholds
- replace smoke, review, or release gates

It only defines the minimum trace links that must exist for auditability.
