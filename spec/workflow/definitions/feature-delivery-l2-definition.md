# Feature Delivery L2 Definition

## Status

- State: frozen
- Governing ADRs: `ADR-008`
- Business source: `FEAT-SRC-009-001`
- Checked-in workflow template remains a template, not a runtime instance

## Purpose

This document defines the project-level canonical structure for the Dev department Feature Delivery L2 workflow.

It acts as the project SSOT definition for:

- the shared input contract
- the L3 stage orchestration order
- the lifecycle state machine
- the upstream and downstream contract interfaces

This file is the formal definition layer. Runtime execution still comes from rendered workflow instances derived from checked-in templates.

## Canonical Scope

Feature Delivery L2 is the Dev department entry workflow for feature delivery from formal requirement input to evidence closure.

Its responsibility boundary is:

- receive frozen upstream feature input
- orchestrate Dev-owned L3 phases
- preserve contract-first and evidence-first governance
- produce auditable delivery evidence for downstream gates

Out of scope:

- direct implementation details of any L3 phase
- ad hoc prompt-driven feature execution without SSOT input
- treating this checked-in file as a fixed runtime workflow instance

## Shared Input Contract

The canonical input fields are:

| Field | Required | Meaning | Rule |
| --- | --- | --- | --- |
| `formal_ssot_id` | yes | formal upstream FEAT identifier | must reference a frozen FEAT object |
| `source_refs` | yes | trace refs back to requirement source | must preserve upstream traceability |
| `governing_adrs` | yes | governing decision constraints | ADRs constrain execution but do not replace business source |
| `repo_context` | yes | repository paths and branch/runtime context | must identify executable target repos/modules |

### Input Rules

1. `formal_ssot_id` is the primary business input anchor.
2. `source_refs` must point back to the upstream requirement chain.
3. `governing_adrs` are hard execution constraints.
4. `repo_context` is execution context, not business truth.
5. Free-form prompt text may supplement execution, but may not replace these four fields.

## Canonical L3 Orchestration

The target L3 orchestration order for Feature Delivery L2 is:

1. `contract_design`
2. `backend_dev`
3. `frontend_dev`
4. `integration`
5. `evidence_pack`

### Stage Semantics

- `contract_design`
  - freezes the structural truth source before implementation
- `backend_dev`
  - implements backend behavior against the frozen contract
- `frontend_dev`
  - implements frontend behavior against the frozen contract
- `integration`
  - verifies cross-phase structural and behavioral consistency
- `evidence_pack`
  - closes the evidence axis with a formal, reviewable evidence package

### Current Template Gap

The currently checked-in template at `spec-global/departments/dev/workflows/templates/feature-l2-template.yaml` is the active implementation template, but it does not yet fully match this target definition:

- it still models `frontend_dev` and `backend_dev` as parallel
- it ends with `smoke_test` rather than `evidence_pack`
- it still uses the template id `template.dev.feature`

This definition is therefore the canonical target contract for subsequent implementation tasks, especially:

- `TASK-FEAT-SRC-009-001-002`
- `TASK-FEAT-SRC-009-001-003`
- `TASK-FEAT-SRC-009-001-004`

## Lifecycle State Machine

The canonical lifecycle state machine is:

1. `Ready`
2. `In Progress`
3. `Evidence Pack Produced`
4. `Closed`

### Transition Rules

| From | To | Condition |
| --- | --- | --- |
| `Ready` | `In Progress` | formal input contract validated and execution started |
| `In Progress` | `Evidence Pack Produced` | contract, implementation, and integration outputs are complete and evidence pack is generated |
| `Evidence Pack Produced` | `Closed` | required review/gate checks pass and downstream closure criteria are satisfied |

### Invalid Transitions

- `Ready -> Evidence Pack Produced`
- `Ready -> Closed`
- `In Progress -> Closed`

## Interface Contracts

### Upstream Interface

Feature Delivery L2 consumes:

- frozen FEAT object referenced by `formal_ssot_id`
- upstream requirement trace carried by `source_refs`
- governance constraints from `governing_adrs`
- repository and module execution context from `repo_context`

### Downstream Interface

Feature Delivery L2 must produce or hand off references for:

- contract design outputs
- backend implementation outputs
- frontend implementation outputs
- integration report outputs
- formal evidence pack outputs

The downstream evidence closure object is the canonical handoff boundary for later smoke, acceptance, or release-style checks.

## Completion Conditions

This definition is satisfied when:

- the four shared input fields are explicitly defined
- the target L3 orchestration order is explicit
- the lifecycle state machine is explicit
- upstream and downstream interface contracts are explicit
- the template/runtime-instance boundary is explicit

## Traceability

- ADR: `ADR-008`
- FEAT: `FEAT-SRC-009-001`
- Follow-up implementation tasks:
  - `TASK-FEAT-SRC-009-001-002`
  - `TASK-FEAT-SRC-009-001-003`
  - `TASK-FEAT-SRC-009-001-004`
