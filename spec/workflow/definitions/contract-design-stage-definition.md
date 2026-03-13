# Contract Design Stage Definition

## Status

- State: frozen
- Governing ADRs: `ADR-008`
- Business source: `FEAT-SRC-009-005`
- Canonical runtime template: `template.dev.feature_contract_l3`

## Purpose

This document defines the canonical Dev department Contract Design stage.

It is the SSOT definition for:

- the stage input contract
- the required contract-design task family
- the stage outputs and review records
- the completion criteria
- the handoff contract into backend and frontend implementation

This file defines the stage semantics. Runtime execution remains the responsibility
of checked-in workflow templates and rendered workflow instances.

## Canonical Scope

Contract Design is the structural convergence stage between `tech_design` and
implementation stages inside `template.dev.feature_delivery_l2`.

Its responsibility boundary is:

- consume the frozen TECH bridge object
- derive and review API, data, and event contracts
- produce a freeze-ready structural truth source
- define handoff artifacts for backend and frontend implementation

Out of scope:

- direct backend or frontend code implementation
- changing upstream TECH scope without explicit rollback
- bypassing review or freeze controls with ad hoc contract output

## Shared Input Contract

The canonical input fields are:

| Field | Required | Meaning | Rule |
| --- | --- | --- | --- |
| `formal_ssot_id` | yes | formal feature or task anchor driving this stage | must reference a frozen upstream SSOT object |
| `source_refs` | yes | upstream trace into FEAT, EPIC, SRC, and TECH | must preserve full traceability |
| `governing_adrs` | yes | architecture and governance constraints | ADRs constrain execution and review |
| `tech_spec_ref` | yes | frozen TECH bridge object | is the primary structural source for contract design |

### Optional Inputs

| Field | Meaning | Rule |
| --- | --- | --- |
| `existing_contract_refs` | prior compatible contract versions | may inform migration, but cannot replace `tech_spec_ref` |
| `review_context` | repo/module ownership and reviewer routing | execution context only |
| `decision_constraints` | temporary implementation limits or migration constraints | must not change contract ownership boundary |

### Input Rules

1. `tech_spec_ref` is the structural source of truth for this stage.
2. `formal_ssot_id` and `source_refs` preserve business lineage and auditability.
3. `governing_adrs` may constrain contract shape, but do not replace the upstream TECH object.
4. Existing contracts may only be used for compatibility or migration analysis.
5. Free-form prompts may supplement explanation, but may not replace the canonical input fields above.

## Required Task Family

Contract Design must explicitly cover these three task classes:

1. `api_contract_design`
   - define endpoints, methods, payloads, error codes, and versioning rules
2. `data_contract_design`
   - define entities, field schemas, storage-facing DTO boundaries, and compatibility rules
3. `event_contract_design`
   - define emitted/consumed events, event payloads, ordering assumptions, and idempotency rules

### Task Coverage Rules

- All three task classes are mandatory for stage completion.
- A stage review must call out omissions explicitly; silent omission is invalid.
- If one task class is intentionally not applicable, the review record must state the reason and the compensating boundary rule.

## Canonical Outputs

Contract Design must produce the following outputs:

| Output | Required | Meaning |
| --- | --- | --- |
| `api_contract_ref` | yes | canonical API contract artifact |
| `data_contract_ref` | yes | canonical data contract artifact |
| `event_contract_ref` | yes | canonical event contract artifact |
| `contract_review_ref` | yes | review record covering all three contract classes |
| `contract_freeze_ref` | yes | frozen structural truth source after gate approval |
| `contract_hash` | yes | stable freeze fingerprint for downstream verification |

### Output Rules

1. The review record must describe coverage across API, data, and event contracts.
2. `contract_freeze_ref` is the only downstream handoff object treated as structural truth.
3. Pre-freeze working artifacts may exist, but backend and frontend stages must not consume them as canonical inputs.

## Handoff Rules

### Backend Handoff

Backend implementation consumes:

- `tech_spec_ref`
- `contract_freeze_ref`
- `contract_hash`

Backend implementation must not:

- extend DTO structure outside the frozen contract
- invent storage or error-code fields not represented in the contract package

### Frontend Handoff

Frontend implementation consumes:

- `tech_spec_ref`
- `contract_freeze_ref`
- `contract_hash`

Frontend implementation must not:

- invent request or response fields outside the frozen contract
- treat pre-freeze drafts as current truth

## Completion Criteria

This stage is complete only when:

1. canonical inputs are present and valid
2. API, data, and event contract tasks are all covered
3. required output artifacts are produced
4. the review record explicitly confirms coverage and quality
5. the freeze gate approves the contract package
6. the downstream backend/frontend handoff boundary is explicit

## Traceability

- ADR: `ADR-008`
- FEAT: `FEAT-SRC-009-005`
- Follow-up tasks:
  - `TASK-FEAT-SRC-009-005-002`
  - `TASK-FEAT-SRC-009-005-003`
  - `TASK-FEAT-SRC-009-005-004`
  - `TASK-FEAT-SRC-009-005-005`
