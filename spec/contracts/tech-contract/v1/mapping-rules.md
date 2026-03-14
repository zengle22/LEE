# FEAT To TECH Mapping Rules

## Status

- State: frozen
- Governing ADRs: `ADR-008`
- Parent FEAT family: `FEAT-SRC-009-*`
- Contract anchor: `spec/contracts/tech-contract/v1/schema.json`

## Purpose

This document defines the canonical translation path from FEAT objects to TECH
bridge objects.

It exists to prevent TECH generation from degrading into free-form design prose.
Each TECH object must preserve traceability back to the FEAT requirement surface.

## Mapped Fields

| FEAT Field | TECH Field | Mapping Rule |
| --- | --- | --- |
| `goal` | `architecture_decisions[*].decision` | Translate business goal into technical design decision and why it exists |
| `inputs` | `implementation_rules.required_inputs` | Convert FEAT inputs into executable input dependencies |
| `processing` | `architecture_decisions[*].impact` and `core_components` | Translate product processing into technical components and interaction boundaries |
| `outputs` | `implementation_rules.required_outputs` | Convert expected outputs into delivery-facing artifacts or interfaces |
| `acceptance_checks` | `feat_mapping.acceptance_mapping` | Every acceptance check must map to an implementation unit and evidence path |
| `dependencies` | `delivery_handoffs` | Translate dependency relationships into explicit technical handoff edges |
| `non_goals` | `implementation_rules.forbidden_shortcuts` | Preserve boundaries by recording what TECH must not solve ad hoc |

## Translation Rules

1. A FEAT clause may not disappear when translated into TECH.
2. Every FEAT acceptance check must produce at least one TECH implementation unit.
3. TECH must introduce no parallel business scope that is absent from FEAT.
4. FEAT business wording may be normalized, but traceability must remain explicit.

## Traceability Matrix

Each TECH object must carry a `traceability_matrix` equivalent using
`feat_mapping.goal_mapping` and `feat_mapping.acceptance_mapping`.

Minimum coverage rule:

- every FEAT `goal` contributes at least one `goal_mapping`
- every FEAT `acceptance_checks[*].id` contributes at least one `acceptance_mapping`
- every `acceptance_mapping` points to a concrete implementation unit

## Example Mapping

Example FEAT source:

- FEAT: `FEAT-SRC-009-003`
- Goal: define TECH as the formal bridge from requirements axis to delivery axis
- Acceptance hint: all bridge fields must be structurally defined and traceable

Example TECH translation:

- `architecture_decisions`
  - define a dedicated TECH bridge contract instead of free-form implementation notes
- `implementation_rules.required_inputs`
  - `formal_ssot_id`
  - `source_refs`
  - `governing_adrs`
- `implementation_rules.required_outputs`
  - `tech_spec_ref`
  - `delivery_handoff_refs`
- `feat_mapping.acceptance_mapping`
  - `AC-003-001 -> tech-contract-schema`
  - `AC-003-002 -> validation-rules`
  - `AC-003-003 -> mapping-rules`

## Review Checklist

- Are all FEAT inputs visible in TECH implementation rules?
- Does every acceptance check map to a concrete implementation unit?
- Are non-goals preserved as forbidden shortcuts?
- Is the resulting TECH object still within the FEAT scope boundary?
