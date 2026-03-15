---
id: EPIC-009
ssot_type: epic
title: QA Department SSOT Alignment and Workflow Reframe
status: archived
version: v1
parent_id: null
derived_from_ids:
- SRC-007
source_refs:
- SRC-007#scope
owner: null
tags: []
properties:
  manual_materialization: true
  materialized_from_workflow: wf_task_734ed71c
  superseded_by: EPIC-011
  superseded_reason: Replaced by canonical frozen EPIC with formal source linkage.
---

# QA Department SSOT Alignment and Workflow Reframe

epic_id: EPIC-SRC-007
title: QA Department SSOT Alignment and Workflow Reframe
goal: Establish a three-axis SSOT model (requirements axis, delivery axis, evidence
  axis) that unifies 8 core QA objects with clear parent-child relationships and mandatory
  traceability rules. Transform QA department from fragmented traceability and informal
  execution channels into a formally integrated SSOT decision chain where QA artifacts
  serve as binding inputs to release gates.
scope:
- 'Define and freeze SSOT object boundaries for 8 core QA objects: TESTSET, TESTPLAN,
  TASK, REPORT, BUG, TSE, TC, EVI with canonical parent relationships'
- Elevate TESTPLAN from 'planning document' to formal SSOT object with mandatory RELEASE
  parent binding and coverage declaration capabilities
- Establish TASK as the unified QA execution entry point, eliminating direct FEAT
  execution and free-text initiation paths
- 'Implement mandatory traceability chain: TESTSET→FEAT, TESTPLAN→RELEASE, TASK→TESTPLAN,
  REPORT→TASK/RELEASE, BUG→REPORT/FEAT, TSE→TASK+TESTPLAN+RELEASE'
- 'Reframe QA workflow taxonomy from single ''test execution'' to 5 categories: Test
  Set Production, Release Test Planning, Test Task Execution, Bug Triage & Regression,
  Go/No-Go Assessment'
- Enable REPORT(go_no_go) as formal RELEASE determination input for release gate decisions
- Ensure BUG objects maintain mandatory references to source_report_id and found_in_release
  for audit compliance
- Define contract schemas for test-plan, test-set-execution, and go-no-go-assessment
  supporting Agent tool development
non_goals:
- EPIC-level design decisions for downstream FEAT implementations
- Technical architecture selection and tooling decisions
- R&D scheduling and resource allocation planning
- Implementation of specific validator/CLI/CI enforcement tools (covered in migration
  step 5)
- Legacy data migration strategy for existing unstructured QA artifacts
success_metrics:
- 'Requirements Axis Completeness: FEAT→TESTSET→TC full mapping achieved with 100%
  TESTSET parented to exactly one FEAT@version'
- 'Delivery Axis Completeness: RELEASE→TESTPLAN→TASK full mapping achieved with 100%
  TESTPLAN parented to RELEASE'
- 'Evidence Axis Completeness: TASK/TSE→BUG/REPORT/EVI full mapping with mandatory
  traceability references'
- 'TESTPLAN Schema Elevation: TESTPLAN objects include parent_id→RELEASE, derived_from_ids
  coverage declaration, and go_no_go binding capability'
- 'Unified Execution Entry: 100% of QA executions initiated via TASK-TESTPLAN-* pattern
  with zero direct FEAT execution exceptions'
- 'End-to-End Traceability: 100% of BUG objects reference source_report_id + found_in_release;
  100% of REPORT(test_execution) traceable to TASK'
- 'Workflow Taxonomy Adoption: All QA workflows categorized into one of 5 canonical
  types with corresponding workflow templates'
- 'Audit Compliance: Complete traceability chain verifiable for compliance auditors
  across TESTSET→FEAT, TESTPLAN→RELEASE, BUG→REPORT→TASK'
priority: P0
feat_split_principles:
- 'Boundary-First: Freeze QA object boundaries (TESTSET/TESTPLAN/TASK/REPORT/BUG/TSE
  parent relationships) before contract upgrades'
- 'Axis-Oriented: Split FEATs by SSOT axis - Requirements Axis (FEAT→TESTSET), Delivery
  Axis (RELEASE→TESTPLAN→TASK), Evidence Axis (BUG/REPORT/TSE traceability)'
- 'Object-Centric: Each core object upgrade constitutes independent FEAT: TESTSET
  formalization, TESTPLAN elevation, TASK unification, REPORT categorization, BUG
  traceability'
- 'Workflow-Category: Split 5 workflow categories into separate FEATs: Test Set Production,
  Release Test Planning, Test Task Execution, Bug Triage & Regression, Go/No-Go Assessment'
- 'Migration-Ordered: FEAT sequence follows migration order - Object boundaries →
  Contract schemas → Workflow templates → Project samples → Validator/CLI/CI integration'
- 'Contract-Driven: Each FEAT delivers frozen contract schema enabling Agent development
  against standardized interfaces'
- 'Dependency-Respecting: TESTPLAN elevation (parent→RELEASE) is critical path dependency
  for TASK formalization; TESTSET formalization prerequisite for TESTPLAN coverage
  declaration'
source_refs:
- SRC-007
- PD-SRC-007
ssot:
  identity_kind: ssot
  ssot_type: EPIC
  parent: null
  derived_from: SRC-007
