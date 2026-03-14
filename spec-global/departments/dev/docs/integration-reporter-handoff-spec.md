# Integration Reporter Handoff Specification

## Status

- State: frozen
- Canonical workflow target: `template.dev.feature_integration_l3`
- Downstream target: `template.dev.evidence_pack_l3`

## Reporter Output Contract

The reporter must publish:

- `integration_outputs`
- `verification_results`
- `integration_report_ref`
- `integration_test_result_ref`
- `issue_resolution_ref`
- `structural_issue_ref`

The report content must include:

- execution summary
- failed case details
- structural issue markers
- environment information
- traceability links to current FE/BE artifacts and contract

## Handoff Conditions

The Evidence Pack handoff is allowed only when:

- report review passed
- unresolved structural issue count is `0`
- threshold summary is present
- required integration outputs are attached

## Handoff Checklist

1. `integration_report_ref`
2. `integration_test_result_ref`
3. `issue_resolution_ref`
4. `structural_issue_ref`
5. `integration_outputs`
6. `verification_results`
