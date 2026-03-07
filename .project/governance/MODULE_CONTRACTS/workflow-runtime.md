# Module Contract: workflow-runtime

## Responsibility

Drive workflow execution state transitions and runtime coordination.

## In Scope

- step and stage execution state
- runtime status persistence
- workflow progress tracking
- output validation flow
- SSOT contract materialization trigger path

## Out of Scope

- business decision truth ownership
- final acceptance authority
- SSOT content authorship

## Inputs

- workflow definition
- runtime context
- execution state updates
- structured agent output

## Outputs

- workflow state
- execution logs
- runtime artifacts
- materialized formal outputs when declared by contract

## Invariants

- workflow state must be externally inspectable
- failed steps must not be marked completed without evidence
- runtime transitions must remain consistent
- if an agent declares `ssot_output_schema`, structured output handling must remain explicit and inspectable

## Forbidden Changes Without Human Review

- silent auto-complete of failed stages
- hidden state-transition changes
- changing completion semantics
- bypassing SSOT contract validation on declared SSOT-producing agents

## Acceptance Conditions

- state transitions are correct
- failures remain visible
- outputs are traceable to runtime state
- structured output validation and SSOT materialization remain observable

## Known Temporary Limitations

- not every workflow step is yet formal-SSOT-aware
- some agent outputs still rely on transitional envelope conventions

## Related Files

- `src/lee/orchestrator/execution/workflow_runner.py`
- `src/lee/orchestrator/execution/runners/base.py`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `src/lee/orchestrator/execution/validators/schema_validator.py`
