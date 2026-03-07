# LEE Temporary Governance

## 1. Purpose

This document defines the temporary governance rules for LEE before the formal SSOT system fully covers all active work.

This governance layer exists to:

- prevent scope drift
- prevent completion-standard tampering
- prevent path and artifact disorder
- ensure completion claims are evidence-backed
- provide a minimum governance shell for AI and human collaboration

This is a temporary governance layer, not the final SSOT system.

## 2. Relationship to Existing LEE Systems

This temporary governance layer does not replace the mechanisms already implemented in LEE.

Current hard-governance sources remain:

- directory topology and placement: `.project/dirs.yaml`
- formal artifact identity and filename rules: SSOT identity layer
- formal SSOT output declaration: `spec-global/core/contracts/ssot-agent-output/v1/schema.json`
- formal SSOT materialization: artifact manager, placement policy, registry, runner integration

This temporary layer only governs work that is not yet fully represented by formal SSOT objects.

## 3. Governance Status

Current governance mode: `TEMPORARY_STRONG_CONSTRAINT`

This means:

- human review is mandatory for critical semantic changes
- AI may draft and implement within scope, but may not redefine truth
- governed outputs must either be formally registered or explicitly declared temporary
- completion claims must be evidence-backed

## 4. Global Red Lines

The following actions are forbidden unless explicitly approved by a human gate.

### 4.1 Truth / completion tampering

- changing acceptance criteria to make tasks pass
- weakening pass thresholds without approval
- deleting failing tests to claim success
- redefining incomplete work as complete

### 4.2 Path / artifact disorder

- writing governed outputs outside approved directories
- bypassing path manager or registry conventions in governed flows
- creating parallel unmanaged copies of the same governed artifact
- introducing hardcoded file paths where governed paths are required

### 4.3 Duplicate implementation

- creating a new module without checking for an existing similar implementation
- introducing overlapping components with unclear ownership
- replacing existing modules without an explicit migration note

### 4.4 False completion

- claiming "done" without evidence
- claiming "tested" without test result artifacts
- claiming "integrated" without integration evidence
- claiming "reviewed" without review notes

## 5. Minimum Truth Sources

Before formal SSOT is available for a task, every active task must have one temporary truth source:

- an Acceptance Brief
- a Module Contract
- or an approved task brief that explicitly states scope and acceptance criteria

If none exists, the task must not enter full implementation.

If a task already has a formal `EPIC / FEAT / UI / TECH / TASK / TESTSET / TC / BUG / REPORT / EVI` object, that formal SSOT object remains the primary truth source.

## 6. When to Use Acceptance Briefs

Acceptance Briefs are required for work that is not yet promoted into formal SSOT, such as:

- local refactors
- bugfixes
- infra adjustments
- module hardening
- temporary implementation tasks in LEE itself

Acceptance Briefs are not a replacement for formal SSOT objects. They are a temporary task anchor.

Each Acceptance Brief should declare its intended migration target:

- `none`
- `future_feat`
- `future_testset`
- `future_module_contract`

## 7. Required Evidence for Completion

A task cannot be marked complete unless it provides, where applicable:

- input reference
- changed files list
- output artifact path
- test evidence
- review notes
- unresolved risks or known gaps

If some evidence is unavailable, it must be explicitly declared as missing.

## 8. Human Gate Required Cases

Human review is required before completion for:

- acceptance criteria changes
- pass threshold changes
- contract or interface breaking changes
- module replacement
- new registry, path, gate, or workflow runtime semantics
- deletion of tests or governed artifacts
- any change that alters system truth interpretation

## 9. Temporary Allowed Mode

Before formal SSOT fully covers the work, LEE may continue in semi-automatic mode:

- AI may generate drafts
- AI may implement scoped code changes
- AI may generate tests
- AI may propose refactors

But AI may not:

- redefine requirements
- silently change truth source
- silently relax constraints
- silently ignore missing evidence

## 10. Completion Statement Format

Every completion output must include:

- Scope completed
- Changed files
- Evidence provided
- Tests executed
- Known limitations
- Whether human gate is still required

No bare "done" statement is allowed.

Use `.project/governance/COMPLETION_TEMPLATE.md` as the default format.

## 11. Module Contract Scope

Module Contracts in this directory are the minimum boundary cards for critical LEE infrastructure.

They do not replace formal contract schemas in `spec-global/`.
They exist to stop boundary drift while formal SSOT coverage is still incomplete.

## 12. Migration Principle

All temporary governance assets should be designed to migrate into future SSOT structures.

Temporary assets should be:

- traceable
- minimally structured
- non-contradictory
- replaceable by formal SSOT later

## 13. Current First-Wave Governed Modules

The first wave of temporary module contracts covers:

- artifact-registry
- path-manager
- workflow-runtime
- gate-flow
- agent-spec-maintainer
