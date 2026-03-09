# Module Contract: agent-spec-maintainer

## Responsibility

Maintain agent specifications so that they preserve boundary clarity, contract layering, and migration discipline.

## In Scope

- agent spec updates
- output contract layering guidance
- SSOT adoption guidance for agents that emit formal objects
- example payload guidance for transitional envelope output

## Out of Scope

- direct runtime execution authority
- completion truth ownership for arbitrary tasks
- replacing formal contract schemas with prose

## Inputs

- existing agent specs
- target contract references
- migration requirements

## Outputs

- updated agent specs
- explicit contract references
- SSOT output examples where required

## Invariants

- `output_schema` remains the business-content contract
- `ssot_output_schema` remains the governance contract for formal objects
- agents that emit formal SSOT objects must say so explicitly
- transitional envelope structure must remain explicit when both layers are present

## Forbidden Changes Without Human Review

- collapsing business contract and SSOT governance into one ambiguous payload
- removing SSOT declaration requirements from formal-object-producing agents
- changing agent boundary semantics without migration notes

## Acceptance Conditions

- agent specs remain parseable
- contract references stay explicit
- formal-object-producing agents declare SSOT output expectations

## Known Temporary Limitations

- only a subset of agent specs currently participate in formal SSOT output materialization
- migration examples still coexist with older agent output conventions

## Related Files

- `spec-global/core/agents/agent-spec-maintainer/v1/agent.yaml`
- `spec-global/departments/prd/agents/prd-writer/v1/agent.yaml`
- `spec-global/departments/ui/agents/ui-designer/v1/agent.yaml`
- `spec-global/departments/qa/agents/test-set-generator/v1/agent.yaml`
- `docs/features/ssot/SSOT_AGENT_CONTRACT.md`
