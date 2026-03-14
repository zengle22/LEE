# TECH To Implementation Delivery Rules

## Status

- State: frozen
- Governing ADRs: `ADR-008`
- Upstream FEAT anchor: `FEAT-SRC-009-001`
- Contract anchor: `spec/contracts/tech-contract/v1/schema.json`

## Purpose

This document defines how a TECH bridge object is consumed by implementation
stages.

The goal is to make TECH the only formal translation layer between the
requirements axis and the implementation stages. No implementation phase may
bypass TECH and read free-form FEAT intent directly as its primary design input.

## Contract Dependencies

TECH depends on:

- frozen FEAT source
- source traceability refs
- governing ADR constraints

Implementation stages depend on TECH as follows:

- `contract_design`
  - consumes TECH to derive the structural truth source
- `backend_dev`
  - consumes TECH and frozen contract to define backend boundaries
- `frontend_dev`
  - consumes TECH and frozen contract to define frontend boundaries
- `integration`
  - consumes TECH, frozen contract, and implementation artifacts to verify closure

## Phase Requirements

### 1. Contract Design

Input contract:

- `tech_spec_ref`
- `formal_ssot_id`
- `source_refs`

Output artifacts:

- `contract_freeze_ref`
- `contract_trace_ref`
- `contract_hash`

Rule:

- Contract Design may not redefine scope outside the TECH bridge object.

### 2. Backend Development

Input contract:

- `tech_spec_ref`
- `contract_freeze_ref`
- `repo_context`

Output artifacts:

- `be_artifact_ref`
- `be_code_diff_ref`
- `be_selfcheck_ref`

Rule:

- Backend Development must translate TECH implementation rules into executable
  service behavior without mutating the frozen contract.

### 3. Frontend Development

Input contract:

- `tech_spec_ref`
- `contract_freeze_ref`
- `repo_context`

Output artifacts:

- `fe_artifact_ref`
- `fe_code_diff_ref`
- `fe_selfcheck_ref`

Rule:

- Frontend Development must consume the same TECH and contract boundary as the
  backend path. Frontend-specific adaptation may exist, but scope may not exceed
  the TECH object.

### 4. Integration

Input contract:

- `tech_spec_ref`
- `contract_freeze_ref`
- `fe_artifact_ref`
- `be_artifact_ref`

Output artifacts:

- `integration_report_ref`
- `structural_issue_ref`
- `rollback_request_ref`

Rule:

- Integration is the point where TECH is validated as an implementation-wide
  bridge object. Structural mismatches must route back through contract or TECH,
  not be patched ad hoc downstream.

## Global Rules

1. Implementation phases must not start before `tech_spec_ref` exists.
2. `contract_design` is the only stage allowed to create the structural truth source.
3. `backend_dev` and `frontend_dev` must preserve TECH traceability in outputs.
4. `integration` must report whether the observed implementation still matches TECH.

## Three-Axis Consistency

This delivery rule set must stay consistent with ADR-008:

- requirement axis:
  - FEAT remains the business source
- delivery axis:
  - TECH bridges FEAT into execution and contract stages
- evidence axis:
  - integration and later evidence packing prove that implementation still honors TECH
