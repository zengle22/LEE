# Structural Issue Routing Specification

## Status

- State: frozen
- Canonical stage: `stage.dev.l3_integration`
- Governing ADR: `ADR-008`

## Issue Classes

The router classifies integration failures into four canonical classes:

1. `structural_contract`
   - contract shape or field definition mismatch
   - rollback target: `contract_design`
2. `structural_tech`
   - TECH boundary or architecture mismatch
   - rollback target: `tech_design`
3. `structural_feat`
   - upstream FEAT scope or acceptance definition mismatch
   - rollback target: `formal_ssot_id`
4. `impl_bug`
   - implementation defect without structural boundary drift
   - rollback target: implementation phase only

## Escalation Rule

If the same issue class appears three consecutive times in the same feature
delivery chain, it must be escalated and treated as structural.

## Output Contract

The router must produce:

- `issue_class`
- `root_cause_summary`
- `rollback_target`
- `escalation_required`
- `routing_notes`

## Alignment Rules

- `structural_contract` aligns with `contract_freeze_ref`
- `structural_tech` aligns with `tech_spec_ref`
- `structural_feat` aligns with `formal_ssot_id`
- `impl_bug` must not bypass structural review if escalation threshold is hit
