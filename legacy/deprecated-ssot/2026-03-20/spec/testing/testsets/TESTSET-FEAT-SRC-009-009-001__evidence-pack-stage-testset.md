---
id: TESTSET-FEAT-SRC-009-009-001
ssot_type: testset
title: Evidence Pack Stage TestSet
status: frozen
version: v1
parent_id: FEAT-SRC-009-009
derived_from_ids:
  - FEAT-SRC-009-009
  - ADR-008
source_refs:
  - FEAT-SRC-009-009#delivery
  - ADR-008#evidence-pack
owner: null
tags:
  - dev
  - evidence-pack
  - testset
properties:
  contract_key: testset_evidence_pack_stage
  identity_kind: ssot
---

# Evidence Pack Stage TestSet

## Coverage Matrix

| Case ID | Acceptance | Validation Target |
| --- | --- | --- |
| `TC-EVI-001` | AC-009-001 | stage definition exists and remains frozen |
| `TC-EVI-002` | AC-009-002 | workflow template covers collection, validation, packaging |
| `TC-EVI-003` | AC-009-003 | schema, validator, and audit declaration are enforced |
| `TC-EVI-004` | AC-009-004 | L2 closure and smoke-gate handoff refs are present |

## Test Targets

- `spec-global/departments/dev/stages/l3-evidence-pack.yaml`
- `spec-global/departments/dev/workflows/templates/evidence-pack-l3-template.yaml`
- `spec-global/departments/dev/contracts/evidence-pack/v1/schema.json`
- `src/lee/evidence/collector.py`
- `src/lee/evidence/validator.py`
- `src/lee/evidence/coverage_auditor.py`
