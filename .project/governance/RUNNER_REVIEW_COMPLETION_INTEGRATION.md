# Runner, Review, Completion Integration Plan

## Purpose

This document describes how `.project/governance/` should be connected to runtime behavior.

The governance files are not intended to be passive documentation only.
They should influence:

- runner preflight behavior
- review behavior
- completion output behavior

## 1. Runner Integration

### Goal

Block or warn on implementation work that has neither:

- a formal SSOT truth source
- nor a temporary Acceptance Brief or Module Contract

### Recommended Preflight

For implementation-facing steps:

1. Determine whether the step already has a formal SSOT target
   - examples: `EPIC`, `FEAT`, `TESTSET`, `TC`
   - sources: explicit workflow context, input payload, `ssot_output_schema`, registry references
2. If no formal SSOT target exists, check for temporary governance anchors
   - matching Acceptance Brief in `.project/governance/ACCEPTANCE_BRIEFS/`
   - relevant module contract in `.project/governance/MODULE_CONTRACTS/`
3. If neither exists:
   - allow analysis / planning / draft output
   - do not allow the step to be treated as full implementation complete
   - emit explicit warning or block, depending on strictness

### Suggested Hook Points

- `src/lee/orchestrator/execution/runners/base.py`
  - add governance path helpers and step classification helpers
- `src/lee/orchestrator/execution/runners/llm_runner.py`
  - run governance preflight before completion-state output is finalized
- `src/lee/orchestrator/execution/workflow_runner.py`
  - surface governance paths in workflow context for downstream steps

### Suggested Result Shape

```json
{
  "governance_preflight": {
    "formal_ssot_present": false,
    "acceptance_brief_found": true,
    "module_contract_found": false,
    "allow_full_completion": false,
    "warnings": ["No formal SSOT target; running under temporary governance."]
  }
}
```

## 2. Review Integration

### Goal

Make review use the same governance baseline every time.

### Recommended Rule

When reviewing implementation-facing work:

- first check for formal SSOT truth source
- if absent, require Acceptance Brief or Module Contract
- require evidence language to match `REVIEW_CHECKLIST.md`

### Current Best Entry

- `spec-global/core/agents/spec-review/v1/agent.yaml`

This review agent should check:

- truth source present or explicitly absent
- governance refs declared when needed
- completion semantics not weakened
- gate requirements not silently removed

## 3. Completion Integration

### Goal

Ban bare "done" outputs.

### Recommended Rule

Any completion-facing agent or runner-composed completion summary should use:

- `.project/governance/COMPLETION_TEMPLATE.md`

Required fields:

- scope completed
- changed files
- evidence
- tests executed
- known limitations
- human gate required

### Suggested Hook Points

- completion-oriented agents
- workflow handoff steps
- final runner summary composition

### Suggested Enforcement Levels

- soft mode:
  - missing fields produce warnings
- strict mode:
  - completion output without required fields cannot be marked final

## 4. Recommended Rollout Order

### Phase 1

- update spec-maintainer and spec-review agents to understand governance refs
- require new implementation-facing specs to carry governance references

### Phase 2

- add runner governance preflight in warning mode
- expose governance findings in step outputs

### Phase 3

- enforce completion template for completion-facing agents
- optionally block final completion without evidence fields

## 5. Boundaries

This integration must preserve the existing division:

- formal SSOT remains the primary truth source when it exists
- temporary governance only fills the gap when formal SSOT is absent
- temporary governance must not become a shadow SSOT

## 6. Current Spec Governance L3 Runtime

The current governed spec workflow is:

- `core.spec-governance`
- template: `spec-global/core/workflows/templates/spec-governance-l3-template.yaml`

Current runtime behavior:

1. `spec_maintenance` writes the maintained target spec back to `params.target_path`
2. the runner generates an exact unified diff at `docs/reports/governance/spec-review/{request_id}-spec.diff`
3. `spec_review` reads the target spec, diff, and generation summary as review context
4. `review_gate` auto-checks blocker/major thresholds
5. failed auto-checks enter a human gate branch when `human_gate_required=true`
6. human `revise` rewinds to `spec_maintenance`

This means spec governance is no longer just generate -> review -> report.
It is now a true:

- writeback flow
- mandatory review gate
- human re-review branch
- revise loop

See:

- `.project/governance/SPEC_GOVERNANCE_L3_USAGE.md`
