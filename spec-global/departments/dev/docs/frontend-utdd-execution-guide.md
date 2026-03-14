# Frontend UTDD Execution Guide

## Status

- State: frozen
- Canonical stage: `stage.dev.l3_frontend_development`
- Canonical workflow target: `template.dev.feature_fe_l3`

## Purpose

This guide defines the standard UTDD execution loop for frontend development in
the Dev department canonical workflow family.

## Canonical Loop

1. `write_ut`
   - add or update unit/component tests first
   - encode expected UI/state behavior before implementation changes
2. `implement_ui`
   - implement frontend code until tests pass
   - preserve `tech_spec_ref` and `contract_freeze_ref` boundaries
3. `refactor_ui`
   - improve code structure without breaking tests
   - keep contract field usage unchanged

## Completion Thresholds

- coverage threshold: `>=80%`
- code review check required before treating output as handoff-ready

## Review Checklist

- tests were updated before or together with implementation
- implementation uses only contract-defined fields
- generated or derived frontend types match frozen contract shape
- coverage report is attached and meets threshold
- handoff package is ready for integration and evidence collection
