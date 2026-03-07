# Module Contract: path-manager

## Responsibility

Provide governed path resolution for project artifacts, runtime data, and outputs.

## In Scope

- path generation
- path normalization
- governed directory mapping
- directory topology loading from `.project/dirs.yaml`
- placement resolution for formal SSOT main files

## Out of Scope

- registry persistence
- artifact metadata management
- business logic storage decisions
- final filename ownership for formal SSOT objects

## Inputs

- project root
- artifact type or placement context
- runtime context

## Outputs

- resolved governed paths
- directory-family decisions

## Invariants

- no hardcoded unmanaged output paths in governed flows
- the same input context should resolve deterministically
- directory conventions must be documented and stable
- `dirs.yaml` owns placement only, not formal SSOT filenames

## Forbidden Changes Without Human Review

- changing base directory semantics
- introducing unmanaged parallel output roots
- changing path rules that break existing governed artifacts
- moving filename ownership from SSOT identity back into directory config

## Acceptance Conditions

- resolves expected paths correctly
- prevents invalid output locations
- supports governed storage conventions

## Known Temporary Limitations

- some legacy modules may still bypass path config
- transition code still coexists with older output-path helpers

## Related Files

- `src/lee/orchestrator/core/project_config.py`
- `src/lee/orchestrator/core/path_config.py`
- `src/lee/orchestrator/execution/artifacts/placement.py`
- `.project/dirs.yaml`
