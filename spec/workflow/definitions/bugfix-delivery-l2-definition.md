# Bugfix Delivery L2 Definition

## Status

- State: frozen
- Governing ADRs: `ADR-008`
- Business source: `FEAT-SRC-009-002`
- Technical source: `TECH-FEAT-SRC-009-002-001`
- Checked-in workflow template remains a template, not a runtime instance

## Purpose

This document defines the canonical Dev department Bugfix Delivery L2 workflow.

It is the formal SSOT definition layer for:

- the bugfix shared input contract
- the L3 stage orchestration order
- the lifecycle state machine
- the bugfix granularity control rules
- the upstream and downstream interface contracts

This file defines the canonical bugfix path. Runtime execution must be derived
from checked-in workflow templates, not from ad hoc prompts.

## Canonical Scope

Bugfix Delivery L2 is the Dev department entry workflow for defect remediation
from formal bug source to evidence closure.

Its responsibility boundary is:

- receive a formal bug source and reproducible evidence
- route the bug through triage and root-cause analysis
- constrain the fix path before implementation
- require verification and evidence closure before merge or closure

Out of scope:

- direct code implementation details of any L3 phase
- redefining the upstream bug creation process
- mixing unrelated bugs into one execution unit without an approved batch rule

## Shared Input Contract

The canonical bugfix input fields are:

| Field | Required | Meaning | Rule |
| --- | --- | --- | --- |
| `bug_ssot_id` | yes | formal upstream BUG identifier | must reference a frozen bug object |
| `severity` | yes | severity classification | must be one of `P0`, `P1`, `P2` |
| `reproduction_evidence` | yes | logs, screenshots, and replayable steps | must be sufficient to reproduce or verify the defect |

Optional execution context:

| Field | Required | Meaning | Rule |
| --- | --- | --- | --- |
| `source_refs` | no | upstream requirement or bug trace links | should preserve root traceability |
| `repo_context` | no | repository/runtime context | execution context only |
| `test_case_refs` | no | linked verification artifacts | required when a formal testcase already exists |
| `batch_context` | no | candidate multi-bug grouping metadata | valid only when five-same rule passes |

### Input Rules

1. `bug_ssot_id` is the primary business input anchor.
2. `severity` determines response urgency and review strictness.
3. `reproduction_evidence` must be concrete enough to verify the defect path.
4. Free-form prompt text may supplement execution, but may not replace the required fields.

## Canonical L3 Orchestration

The target L3 orchestration order for Bugfix Delivery L2 is:

1. `triage`
2. `root_cause`
3. `fix_design`
4. `fix_implementation`
5. `verification`
6. `evidence_pack`

### Stage Semantics

- `triage`
  - validates the bug input and decides single-bug vs batch eligibility
- `root_cause`
  - identifies the actual defect source and affected scope
- `fix_design`
  - constrains the remediation boundary before coding
- `fix_implementation`
  - applies the code or configuration fix
- `verification`
  - proves the fix and checks regressions
- `evidence_pack`
  - packages closure evidence for merge or downstream review

## Lifecycle State Machine

The canonical lifecycle state machine is:

1. `Ready`
2. `Triaged`
3. `Fix In Progress`
4. `Verification Passed`
5. `Evidence Pack Produced`
6. `Closed`

### Transition Rules

| From | To | Condition |
| --- | --- | --- |
| `Ready` | `Triaged` | required input contract validated and routing decision made |
| `Triaged` | `Fix In Progress` | root cause and fix design are accepted |
| `Fix In Progress` | `Verification Passed` | implementation completed and verification succeeds |
| `Verification Passed` | `Evidence Pack Produced` | evidence pack and review package are generated |
| `Evidence Pack Produced` | `Closed` | merge or closure decision passes |

### Invalid Transitions

- `Ready -> Fix In Progress`
- `Triaged -> Closed`
- `Fix In Progress -> Closed`
- `Verification Passed -> Closed`

## Granularity Control

Default rule:

- one `bug_ssot_id` maps to one Bugfix Delivery L2 run

Batch exception:

- multi-bug execution is allowed only when the five-same rule passes:
  - same module
  - same root-cause class
  - same remediation strategy
  - same verification surface
  - same release window

If any of the five-same conditions fail, the batch must be rejected and split
back into single-bug execution units.

## Interface Contracts

### Upstream Interface

Bugfix Delivery L2 consumes:

- a frozen bug object referenced by `bug_ssot_id`
- reproduction evidence referenced by `reproduction_evidence`
- severity classification from `severity`
- optional trace and testcase context from `source_refs` and `test_case_refs`

### Downstream Interface

Bugfix Delivery L2 must produce or hand off references for:

- triage decision
- root-cause report
- fix design brief
- fix implementation diff or artifact
- verification report
- evidence pack

The downstream closure boundary is the evidence pack plus the merge or closure
decision bound to the bugfix run.

## Completion Conditions

This definition is satisfied when:

- the three required input fields are explicitly defined
- the six-stage orchestration order is explicit
- the lifecycle state machine is explicit
- the default single-bug rule and five-same batch exception are explicit
- upstream and downstream interface contracts are explicit

## Traceability

- ADR: `ADR-008`
- FEAT: `FEAT-SRC-009-002`
- TECH: `TECH-FEAT-SRC-009-002-001`
- Follow-up implementation tasks:
  - `TASK-FEAT-SRC-009-002-002`
  - `TASK-FEAT-SRC-009-002-003`
  - `TASK-FEAT-SRC-009-002-004`
  - `TASK-FEAT-SRC-009-002-005`
