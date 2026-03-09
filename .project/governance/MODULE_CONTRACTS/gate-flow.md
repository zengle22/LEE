# Module Contract: gate-flow

## Responsibility

Control human and AI validation checkpoints before critical transitions.

## In Scope

- gate requirement definition
- gate decision visibility
- approval, rejection, or pending semantics
- completion gating rules for critical changes

## Out of Scope

- producing implementation artifacts
- redefining business truth
- changing acceptance rules autonomously

## Inputs

- review request
- evidence bundle
- reviewer decision
- temporary governance classification

## Outputs

- gate result
- gate notes
- next-state permission

## Invariants

- critical transitions require explicit gate result
- rejected items may not be treated as approved
- missing evidence must remain visible
- "pending review" must not be presented as "done"

## Forbidden Changes Without Human Review

- bypassing mandatory gates
- silently changing gate requirements
- auto-promoting pending items to approved
- weakening required evidence for critical transitions

## Acceptance Conditions

- gate can be requested
- decision can be recorded
- blocked items remain blocked

## Known Temporary Limitations

- gate logic is still distributed across workflow conventions, reviews, and manual practice
- full gate-state formalization is not yet complete

## Related Files

- `.project/governance/TEMP_GOVERNANCE.md`
- `.project/governance/REVIEW_CHECKLIST.md`
- `src/lee/orchestrator/execution/workflow_runner.py`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
