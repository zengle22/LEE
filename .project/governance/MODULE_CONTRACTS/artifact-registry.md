# Module Contract: artifact-registry

## Responsibility

Maintain discoverable, queryable, and traceable records of generated artifacts.

## In Scope

- artifact metadata registration
- artifact lookup
- artifact status tracking
- artifact dependency references
- parent and related-object indexing for governed artifacts

## Out of Scope

- business content generation
- direct file content editing
- final business truth ownership

## Inputs

- artifact metadata
- artifact path
- producing run or task context

## Outputs

- registry entries
- lookup results
- artifact trace links

## Invariants

- every governed artifact must have a registry record or explicit temporary exemption
- registry path and actual file path must stay consistent
- artifact identity must remain stable within the recorded context
- SSOT parent and relation metadata must remain queryable

## Forbidden Changes Without Human Review

- changing artifact identity rules
- deleting registry records to hide failures
- silently changing registry storage semantics
- weakening traceability fields to accommodate broken flows

## Acceptance Conditions

- can register an artifact
- can query an artifact
- can verify artifact path consistency
- can trace producer information

## Known Temporary Limitations

- partial schema coverage
- incomplete cross-run impact analysis

## Related Files

- `src/lee/orchestrator/execution/artifacts/registry.py`
- `src/lee/orchestrator/execution/artifacts/models.py`
- `src/lee/orchestrator/execution/artifacts/manager.py`
