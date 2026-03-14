# TECH Review Checklist

## Purpose

This checklist is used before a TECH object is frozen.

It verifies that TECH is structurally complete, traceable to FEAT, and
actionable for downstream implementation phases.

## 1. Schema Completeness

- [ ] `id` exists and follows the TECH ID pattern
- [ ] `ssot_type` is explicitly `tech`
- [ ] `parent_id` points to the correct FEAT
- [ ] `source_refs` are present and non-empty
- [ ] `architecture_decisions` are present and structured
- [ ] `feat_mapping` is present and structured
- [ ] `implementation_rules` are present and structured
- [ ] `delivery_handoffs` are present and structured
- [ ] `validation_rules` are present and structured

## 2. FEAT Mapping Accuracy

- [ ] FEAT goal clauses are translated into technical decisions
- [ ] FEAT inputs are translated into implementation required inputs
- [ ] FEAT outputs are translated into required outputs or interfaces
- [ ] every FEAT acceptance check has at least one TECH mapping
- [ ] TECH introduces no scope outside the parent FEAT

## 3. Implementation Rule Executability

- [ ] Contract Design input and output boundaries are explicit
- [ ] Backend Development input and output boundaries are explicit
- [ ] Frontend Development input and output boundaries are explicit
- [ ] Integration input and output boundaries are explicit
- [ ] forbidden shortcuts are explicit and actionable

## 4. Risk Coverage

- [ ] architectural risks are identified
- [ ] delivery handoff risks are identified
- [ ] rollback or re-entry boundaries are visible
- [ ] evidence expectations are present for downstream verification

## 5. Freeze Readiness

- [ ] TECH is understandable without re-reading the whole FEAT prose
- [ ] downstream teams can implement from TECH without guessing missing structure
- [ ] reviewer can explain how TECH enforces FEAT scope discipline

## Example Use

Review candidate:

- FEAT: `FEAT-SRC-009-003`
- TECH: `TECH-FEAT-SRC-009-003-001`

Expected outcome:

- all schema sections present
- all FEAT acceptance checks mapped
- all four implementation stages have explicit handoff rules
