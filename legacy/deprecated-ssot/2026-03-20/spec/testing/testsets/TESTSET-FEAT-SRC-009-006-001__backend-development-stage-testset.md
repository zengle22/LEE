---
id: TESTSET-FEAT-SRC-009-006-001
ssot_type: testset
title: Backend Development Stage TestSet
status: frozen
version: v1
parent_id: FEAT-SRC-009-006
derived_from_ids:
  - FEAT-SRC-009-006
  - ADR-008
source_refs:
  - FEAT-SRC-009-006#delivery
  - ADR-008#backend-development
owner: null
tags:
  - dev
  - backend
  - testset
properties:
  contract_key: testset_backend_development_stage
  identity_kind: ssot
---

# Backend Development Stage TestSet

## Coverage Matrix

| Case ID | Acceptance | Validation Target |
| --- | --- | --- |
| `TC-BE-001` | AC-006-001 | Stage definition exists and remains frozen |
| `TC-BE-002` | AC-006-002 | UTDD loop is explicit in stage definition and workflow template |
| `TC-BE-003` | AC-006-003 | Coverage threshold is fixed at `>=80%` and runtime guard exists |
| `TC-BE-004` | AC-006-004 | Backend handoff rules into frontend/integration are explicit |

## Test Cases

### TC-BE-001 Stage Freeze Validation

- Target: `spec-global/departments/dev/stages/l3-backend-development.yaml`
- Pass criteria:
  - file exists
  - `status: frozen`

### TC-BE-002 UTDD Loop Validation

- Targets:
  - `spec-global/departments/dev/stages/l3-backend-development.yaml`
  - `spec-global/departments/dev/workflows/templates/feature-be-l3-template.yaml`
- Pass criteria:
  - `write_ut`
  - `implement_logic` / `implement_backend`
  - `refactor`

### TC-BE-003 Coverage Guard Validation

- Targets:
  - `spec-global/departments/dev/stages/l3-backend-development.yaml`
  - `spec-global/departments/dev/workflows/templates/feature-be-l3-template.yaml`
  - `src/lee/orchestrator/execution/runners/llm_runner.py`
- Pass criteria:
  - threshold is `>=80%`
  - template declares coverage gate
  - runtime evaluates coverage and requests retry

### TC-BE-004 Handoff Validation

- Target: `spec-global/departments/dev/stages/l3-backend-development.yaml`
- Pass criteria:
  - frontend receives `contract_freeze_ref`, `contract_hash`, `be_artifact_ref`
  - integration receives `tech_spec_ref`, `contract_freeze_ref`, `be_artifact_ref`, `unit_test_ref`, `coverage_report_ref`
