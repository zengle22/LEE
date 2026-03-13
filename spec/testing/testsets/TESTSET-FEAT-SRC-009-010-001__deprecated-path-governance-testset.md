---
id: TESTSET-FEAT-SRC-009-010-001
ssot_type: testset
title: Deprecated Path Governance TestSet
status: frozen
version: v1
parent_id: FEAT-SRC-009-010
derived_from_ids:
  - FEAT-SRC-009-010
  - ADR-008
source_refs:
  - FEAT-SRC-009-010#delivery
  - ADR-008#governance
owner: null
tags:
  - dev
  - governance
  - testset
properties:
  contract_key: testset_deprecated_path_governance
  identity_kind: ssot
---

# Deprecated Path Governance TestSet

## Coverage Matrix

| Case ID | Acceptance | Validation Target |
| --- | --- | --- |
| `TC-DEP-001` | AC-010-001 | governance spec exists and is frozen |
| `TC-DEP-002` | AC-010-002 | deprecated path inventory covers canonical legacy entries |
| `TC-DEP-003` | AC-010-003 | workflow header marks expose status, replacement, deadline |
| `TC-DEP-004` | AC-010-004 | migration guide points users to canonical L2 entries |
