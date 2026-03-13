# Frontend Output Specification

## Status

- State: frozen
- Canonical workflow: `template.dev.feature_fe_l3`
- Governing ADR: `ADR-008`

## Required Outputs

| Output | Meaning | Required |
| --- | --- | --- |
| `fe_artifact_ref` | frontend implementation artifact or diff package | yes |
| `unit_test_ref` | unit/component test artifact | yes |
| `coverage_report_ref` | frontend coverage report | yes |
| `contract_usage_verification_ref` | verification record that contract field usage is aligned | yes |

## Evidence Requirements

Frontend Development must hand the following evidence to `template.dev.evidence_pack_l3`:

- `fe_artifact_ref`
- `unit_test_ref`
- `coverage_report_ref`
- `contract_usage_verification_ref`

Optional:

- `refactor_report_ref`
- `fe_handoff_package_ref`
- `handoff_notes`

## Format Rules

- coverage reports must include a numeric coverage value
- contract verification must explicitly call out contract field usage compliance
- frontend artifact must be traceable to the current `formal_ssot_id`
