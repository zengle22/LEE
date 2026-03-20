---
id: TESTSET-FEAT-SRC-009-011-001
ssot_type: testset
title: Shared Input Schema TestSet
status: frozen
version: v1
parent_id: FEAT-SRC-009-011
derived_from_ids:
  - FEAT-SRC-009-011
  - ADR-008
source_refs:
  - FEAT-SRC-009-011#delivery
  - ADR-008#shared-input
owner: null
tags:
  - dev
  - contract
  - testset
properties:
  contract_key: testset_shared_input_schema
  identity_kind: ssot
---

# Shared Input Schema TestSet

## Coverage Matrix

| Case ID | Acceptance | Validation Target |
| --- | --- | --- |
| `TC-SIS-001` | AC-011-001 | schema and shared input doc exist and are frozen |
| `TC-SIS-002` | AC-011-002 | `formal_ssot_id` format rule is enforced |
| `TC-SIS-003` | AC-011-003 | `source_refs` and `governing_adrs` rules are enforced |
| `TC-SIS-004` | AC-011-004 | validation checklist is present and executable |

## Execution Assets

- `tests/unit/test_shared_input_schema_validation.py`
- `tests/unit/test_shared_input_checklist.py`
