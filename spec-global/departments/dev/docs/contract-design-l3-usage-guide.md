# Contract Design L3 Usage Guide

## Status

- State: frozen
- Canonical workflow: `template.dev.feature_contract_l3`
- Governing ADR: `ADR-008`

## When To Use

Use this workflow only for the `contract_design` phase inside
`template.dev.feature_delivery_l2`.

It is the single canonical path for converting a frozen TECH object into the
frozen contract package consumed by backend and frontend implementation.

## Required Inputs

- `formal_ssot_id`
- `source_refs`
- `governing_adrs`
- `tech_spec_ref`

Optional:

- `existing_contract_refs`
- `review_context`
- `decision_constraints`

## Step Sequence

1. `api_contract_design`
2. `data_contract_design`
3. `event_contract_design`
4. `contract_self_review`
5. `contract_freeze`

## Output Package

The workflow must produce:

- `api_contract_ref`
- `data_contract_ref`
- `event_contract_ref`
- `contract_review_ref`
- `contract_freeze_ref`
- `contract_hash`

## Downstream Rule

`backend_dev` and `frontend_dev` may consume only:

- `tech_spec_ref`
- `contract_freeze_ref`
- `contract_hash`

Pre-freeze drafts must not be treated as canonical input.
