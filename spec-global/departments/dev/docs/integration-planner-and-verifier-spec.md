# Integration Planner And Verifier Specification

## Status

- State: frozen
- Canonical stage: `stage.dev.l3_integration`
- Canonical workflow target: `template.dev.feature_integration_l3`

## IntegrationPlanner

The planner is responsible for:

- resolving `fe_artifact_ref` and `be_artifact_ref`
- confirming `contract_freeze_ref` exists and is frozen
- generating the integration test matrix
- selecting execution mode

### Planner Inputs

- `tech_spec_ref`
- `contract_freeze_ref`
- `fe_artifact_ref`
- `be_artifact_ref`
- optional environment inputs: `env_ref`, `base_url`, `runtime_config_ref`

### Planner Output

- `integration_plan_ref`
- `integration_matrix_ref`
- `execution_mode`

## IntegrationVerifier

The verifier supports two canonical modes:

1. `contract_mock_mode`
   - validates integration behavior against frozen contract and mocks/fixtures
2. `environment_backed_mode`
   - validates behavior against a real dev/test environment

### Verifier Threshold Rules

- critical path pass rate: `100%`
- normal flow pass rate: `>=95%`
- exception flow pass rate: `>=80%`

### Verifier Outputs

- `integration_test_result_ref`
- `integration_report_ref`
- `threshold_summary_ref`
- `structural_issue_ref`

## Execution Matrix Rules

- the matrix must cover critical, normal, and exception paths
- each case must be traceable back to the frozen contract and current FE/BE artifacts
- missing matrix coverage is a verifier failure
