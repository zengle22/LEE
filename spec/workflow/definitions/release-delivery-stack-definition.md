# Release Delivery Stack Definition

## Status

- State: draft
- Governing ADRs: `ADR-001`
- Canonical scope: delivery axis
- Checked-in workflow definitions remain templates, not runtime instances

## Purpose

This document defines the project-level canonical workflow stack that makes the
delivery axis executable.

It is the formal definition layer for:

- the L1 release-delivery orchestration workflow
- the three delivery-axis management L2 workflows
- the full L3 stage catalog under those L2 workflows
- the requirement-axis binding rules into delivery-axis objects
- the downstream handoff rules into Dev execution, QA execution, and release gate

This file defines the workflow semantics and object boundaries. Runtime
execution still comes from rendered workflow instances derived from checked-in
templates.

## Canonical Scope

The delivery-axis workflow stack owns:

- creating and freezing `RELEASE`
- deriving and committing `DEVPLAN`
- deriving and committing `TESTPLAN`
- expanding plan slices into auditable task packs
- aggregating plan coverage, execution evidence, and release readiness
- closing the release only after evidence-axis checks pass

Out of scope:

- direct backend or frontend code implementation
- direct test execution details inside specific test sets
- replacing requirement truth owned by `FEAT / TECH / TESTSET`
- replacing evidence truth owned by `REPORT / EVI / BUG`

## Canonical Stack Overview

### L1: `release_delivery_l1`

The L1 workflow is the orchestration shell for one release delivery cycle.

Its canonical L2 order is:

1. `release_management_l2`
2. `devplan_management_l2`
3. `testplan_management_l2`
4. `delivery_execution_handoff`
5. `release_readiness_gate`
6. `release_closeout`

### L2 Catalog

The delivery axis must provide these three management L2 workflows:

1. `release_management_l2`
2. `devplan_management_l2`
3. `testplan_management_l2`

These three workflows are mandatory. Without them, `RELEASE / DEVPLAN /
TESTPLAN` remain static objects rather than executable delivery governance.

## Requirement-Axis Binding Rules

All delivery-axis workflows must bind back to the requirement axis explicitly.

### `release_management_l2`

Required upstream binding:

- `derived_from_ids = FEAT@version`
- `source_refs` back to requirement and governance anchors

### `devplan_management_l2`

Required upstream binding:

- `parent_id = RELEASE`
- `derived_from_ids` contains the release-pinned `FEAT@version`
- `derived_from_ids` may also include `TECH`

### `testplan_management_l2`

Required upstream binding:

- `parent_id = RELEASE`
- `derived_from_ids` contains the release-pinned `FEAT@version`
- `derived_from_ids` contains corresponding `TESTSET`

### `TASK`

Required downstream binding:

- `TASK.parent_id` must be `DEVPLAN` or `TESTPLAN`
- `TASK.implements` points to `FEAT / TECH`
- `TASK.verifies` points to `FEAT / TESTSET / TC`
- `TASK.properties.slice_key` binds the task to a delivery slice

## L1 Definition

## `release_delivery_l1`

### Responsibility

`release_delivery_l1` is the single orchestration shell for the delivery axis.

It must:

- receive frozen requirement-axis inputs
- establish release scope
- derive Dev and QA commitments
- hand off formal task packs to execution workflows
- aggregate release readiness from evidence-axis outputs
- close or abort the release

### Canonical L1 Inputs

| Field | Required | Meaning | Rule |
| --- | --- | --- | --- |
| `release_version` | yes | target release semver | becomes `REL-x.y.z` |
| `release_title` | yes | human-readable release title | used for summary and review |
| `release_scope_refs` | yes | pinned `FEAT@version` list | must all be frozen |
| `governing_adrs` | yes | delivery governance constraints | must include `ADR-001` |
| `repo_context` | yes | execution repo/workspace context | execution context only |

### Canonical L1 Outputs

| Output | Required | Meaning |
| --- | --- | --- |
| `release_ref` | yes | canonical `RELEASE` object |
| `devplan_ref` | yes | canonical `DEVPLAN` object |
| `testplan_ref` | yes | canonical `TESTPLAN` object |
| `task_pack_refs` | yes | downstream task pack references |
| `release_gate_report_ref` | yes | aggregated release gate report |
| `release_close_ref` | yes | final release closure record |

## L2 Definitions

## `release_management_l2`

### Purpose

Manage release scope from initial cut to final release close.

### Canonical L3 Order

1. `release_scope_init_l3`
2. `release_scope_validate_l3`
3. `release_scope_freeze_l3`
4. `release_recut_audit_l3`
5. `release_gate_aggregate_l3`
6. `go_no_go_decision_l3`
7. `release_closeout_l3`

## `devplan_management_l2`

### Purpose

Translate release scope into Dev commitments and executable development task
packs.

### Canonical L3 Order

1. `devplan_scope_bind_l3`
2. `devplan_slice_design_l3`
3. `devplan_dependency_plan_l3`
4. `devplan_task_pack_l3`
5. `devplan_coverage_check_l3`
6. `devplan_commit_gate_l3`

## `testplan_management_l2`

### Purpose

Translate release scope into QA commitments, testset bindings, and executable
test task packs.

### Canonical L3 Order

1. `testplan_scope_bind_l3`
2. `testplan_testset_bind_l3`
3. `testplan_env_matrix_l3`
4. `testplan_entry_gate_design_l3`
5. `testplan_task_pack_l3`
6. `testplan_coverage_check_l3`
7. `testplan_commit_gate_l3`

## L3 Catalog

Each L3 below is a canonical stage definition. Every L3 must be represented in
templates as a checked-in reusable unit, not a fixed runtime instance.

### `release_scope_init_l3`

Purpose:

- create the formal `RELEASE` object
- normalize release title, semver, scope refs, and owner

Required inputs:

- `release_version`
- `release_title`
- `release_scope_refs`
- `governing_adrs`

Required outputs:

- `release_ref`
- `normalized_scope_refs`
- `release_init_report_ref`

Entry gate:

- all scope refs exist

Completion rule:

- `RELEASE` is created with valid `derived_from_ids`

### `release_scope_validate_l3`

Purpose:

- verify that every scope object is frozen and version-pinned
- reject non-frozen or unresolved scope members

Required inputs:

- `release_ref`
- `normalized_scope_refs`

Required outputs:

- `scope_validation_report_ref`
- `scope_validation_status`

Blocking conditions:

- scope contains unresolved `FEAT`
- scope contains non-frozen `FEAT / TECH / TESTSET`

Completion rule:

- validation report explicitly says scope is fit for freeze

### `release_scope_freeze_l3`

Purpose:

- transition `RELEASE` into frozen scope state
- stamp scope freeze metadata and rollback baseline

Required inputs:

- `release_ref`
- `scope_validation_report_ref`
- `rollback_plan`

Required outputs:

- `scope_freeze_ref`
- `release_scope_frozen_at`

Gate:

- scope validation must pass

Completion rule:

- `RELEASE` is ready to derive `DEVPLAN / TESTPLAN`

### `release_recut_audit_l3`

Purpose:

- manage approved scope recuts after freeze
- record old refs, new refs, approval, and affected slices

Required inputs:

- `release_ref`
- `recut_request`
- `old_scope_refs`
- `new_scope_refs`

Required outputs:

- `recut_audit_ref`
- `release_recut_entry`
- `affected_plan_refs`

Gate:

- explicit approval is required

Completion rule:

- recut is fully auditable and downstream recheck targets are identified

### `release_gate_aggregate_l3`

Purpose:

- aggregate `DEVPLAN / TESTPLAN / REPORT / EVI / BUG`
- produce the formal release readiness snapshot

Required inputs:

- `release_ref`
- `devplan_ref`
- `testplan_ref`
- `evidence_refs`
- `bug_refs`
- `report_refs`

Required outputs:

- `release_gate_report_ref`
- `release_gate_summary`

Blocking conditions:

- release scope not fully covered
- required report kinds missing
- blocker bug not closed or waived

Completion rule:

- release readiness state is explicit and reviewable

### `go_no_go_decision_l3`

Purpose:

- make the formal go/no-go decision from aggregated release evidence

Required inputs:

- `release_ref`
- `release_gate_report_ref`
- `waiver_records`

Required outputs:

- `go_no_go_report_ref`
- `decision_status`

Gate:

- human release approval is mandatory

Completion rule:

- release decision is explicit: `go`, `conditional_go`, or `no_go`

### `release_closeout_l3`

Purpose:

- finalize release closure and produce release report

Required inputs:

- `release_ref`
- `go_no_go_report_ref`
- `deploy_evidence_refs`

Required outputs:

- `release_report_ref`
- `release_close_ref`

Gate:

- `go_no_go_decision_l3` must resolve to `go` or approved `conditional_go`

Completion rule:

- release is either closed as `released` or retained for remediation

### `devplan_scope_bind_l3`

Purpose:

- create `DEVPLAN`
- bind release scope to development responsibility

Required inputs:

- `release_ref`
- release-pinned `FEAT@version`
- related `TECH` refs when available

Required outputs:

- `devplan_ref`
- `devplan_scope_map`

Completion rule:

- every in-scope feature is represented in the Dev planning map

### `devplan_slice_design_l3`

Purpose:

- design the delivery slices that Dev will execute

Required inputs:

- `devplan_ref`
- `devplan_scope_map`
- `TECH` refs

Required outputs:

- `devplan_slices`

Slice fields must include:

- `slice_key`
- `feat_id`
- `feat_version`
- `required`
- `dependencies`

Completion rule:

- slices are unique, complete, and traceable back to `FEAT@version`

### `devplan_dependency_plan_l3`

Purpose:

- define cross-slice order and blocking dependencies

Required inputs:

- `devplan_ref`
- `devplan_slices`

Required outputs:

- `devplan_dependency_graph_ref`

Completion rule:

- no circular dependencies exist

### `devplan_task_pack_l3`

Purpose:

- expand development slices into executable `TASK` packs

Required inputs:

- `devplan_ref`
- `devplan_slices`
- `devplan_dependency_graph_ref`

Required outputs:

- `dev_task_refs`
- `dev_task_pack_ref`

Each task must include:

- `parent_id = DEVPLAN`
- `implements = FEAT / TECH`
- `slice_key`
- owner
- done definition

Completion rule:

- each required slice has at least one executable Dev task

### `devplan_coverage_check_l3`

Purpose:

- verify that Dev plan fully covers release scope

Required inputs:

- `release_ref`
- `devplan_ref`
- `dev_task_refs`

Required outputs:

- `devplan_coverage_report_ref`

Blocking conditions:

- any release feature is not covered
- any required slice has no task

Completion rule:

- coverage report explicitly marks Dev plan complete or incomplete

### `devplan_commit_gate_l3`

Purpose:

- transition `DEVPLAN` from draft to committed

Required inputs:

- `devplan_ref`
- `devplan_coverage_report_ref`

Required outputs:

- `devplan_commit_ref`

Gate:

- coverage must pass

Completion rule:

- `DEVPLAN` is execution-ready

### `testplan_scope_bind_l3`

Purpose:

- create `TESTPLAN`
- bind release scope to QA validation responsibility

Required inputs:

- `release_ref`
- release-pinned `FEAT@version`

Required outputs:

- `testplan_ref`
- `testplan_scope_map`

Completion rule:

- every in-scope feature is represented in the QA planning map

### `testplan_testset_bind_l3`

Purpose:

- resolve each release feature to its canonical `TESTSET`

Required inputs:

- `testplan_ref`
- `testplan_scope_map`
- `TESTSET` refs

Required outputs:

- `testplan_testset_map`

Blocking conditions:

- any required feature has no bound `TESTSET`

Completion rule:

- all required features are bound to at least one validation source

### `testplan_env_matrix_l3`

Purpose:

- define test environments, build baseline, and environment matrix

Required inputs:

- `testplan_ref`
- `release_ref`
- `repo_context`

Required outputs:

- `environment_matrix_ref`
- `environment_matrix`

Completion rule:

- environment matrix is explicit and usable by downstream QA execution

### `testplan_entry_gate_design_l3`

Purpose:

- define QA entry rules and blocking conditions for test execution

Required inputs:

- `testplan_ref`
- `testplan_testset_map`
- `environment_matrix`

Required outputs:

- `test_entry_gate_ref`

Rules must include:

- test entry prerequisites
- env readiness conditions
- blocker bug handling
- bypass policy

Completion rule:

- QA execution can be blocked or allowed through a formal gate

### `testplan_task_pack_l3`

Purpose:

- expand validation slices into executable test tasks

Required inputs:

- `testplan_ref`
- `testplan_testset_map`
- `test_entry_gate_ref`

Required outputs:

- `test_task_refs`
- `test_task_pack_ref`

Each task must include:

- `parent_id = TESTPLAN`
- `verifies = FEAT / TESTSET / TC`
- `slice_key`
- entry criteria
- owner

Completion rule:

- each required slice has at least one executable QA task

### `testplan_coverage_check_l3`

Purpose:

- verify that the test plan fully covers release scope and test sets

Required inputs:

- `release_ref`
- `testplan_ref`
- `test_task_refs`

Required outputs:

- `testplan_coverage_report_ref`

Blocking conditions:

- any release feature is not covered by QA
- any required testset is not mapped into execution

Completion rule:

- test coverage is explicit, reviewable, and adequate for commit

### `testplan_commit_gate_l3`

Purpose:

- transition `TESTPLAN` from draft to committed

Required inputs:

- `testplan_ref`
- `testplan_coverage_report_ref`
- `environment_matrix_ref`

Required outputs:

- `testplan_commit_ref`

Gate:

- coverage and environment readiness must pass

Completion rule:

- `TESTPLAN` is execution-ready

## Downstream Handoff Rules

### Dev Execution Handoff

`devplan_management_l2` must hand off `dev_task_refs` to the Dev execution
workflow family, including the existing feature-delivery stack.

Downstream Dev execution must consume:

- task refs
- release ref
- devplan ref
- slice metadata
- upstream `FEAT / TECH` bindings

### QA Execution Handoff

`testplan_management_l2` must hand off `test_task_refs` to the QA execution
entry.

Downstream QA execution must consume:

- task ref
- testplan ref
- release ref
- environment matrix
- target testset bindings

## Completion Criteria

This workflow stack is complete only when:

1. `release_delivery_l1` exists as the canonical orchestration shell
2. the three delivery-axis L2 workflows are explicit
3. every L2 has an explicit ordered L3 catalog
4. every L3 has purpose, inputs, outputs, gate, and completion rule
5. requirement-axis bindings are explicit
6. downstream Dev and QA handoff boundaries are explicit
7. release closure is evidence-driven rather than status-text-driven

## Traceability

- ADR: `ADR-001`
- Existing Dev execution reference: `template.dev.feature_delivery_l2`
- Existing QA execution reference: `template.qa.test_plan_l2`
