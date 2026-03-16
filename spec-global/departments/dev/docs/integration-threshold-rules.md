# Integration Threshold Rules

## Status

- State: frozen
- Canonical stage: `stage.dev.l3_integration`

## Quantified Completion Rules

- critical path pass rate: `100%`
- normal flow pass rate: `>=95%`
- exception flow pass rate: `>=80%`
- unresolved structural issue count: `0`

## Enforcement Rules

- missing threshold summary is a failure
- any unresolved structural issue blocks Evidence Pack handoff
- threshold evaluation must be emitted by the verifier output

## Alignment Rule

The threshold summary must align with:

- `integration_test_result_ref`
- `integration_report_ref`
- `structural_issue_ref`
