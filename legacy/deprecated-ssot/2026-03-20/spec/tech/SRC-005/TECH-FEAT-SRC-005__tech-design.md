---
id: TECH-FEAT-SRC-005
ssot_type: tech
title: tech_design
status: frozen
version: v1
parent_id: FEAT-SRC-009-012
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:55.340302'
workflow_instance_id: wf-tech-feat-src-005__tech-design-20260316
---

module: five_same_evaluator
version: v1.0
state: frozen
evaluation_criteria:
  same_module:
    method: extract_module_from_bug_report()
    tolerance: exact_match
  same_root_cause:
    method: root_cause_category_tagging()
    tolerance: same_category_family
  same_fix_approach:
    method: fix_pattern_matching()
    tolerance: same_pattern_class
  same_test_scope:
    method: test_coverage_overlap_analysis()
    tolerance: overlap_ratio >= 0.8
  same_risk_level:
    method: risk_assessment_matrix()
    tolerance: same_risk_band
output:
- five_same_result:
    pass: bool
    details:
      '...': null
- confidence_score: 0.0-1.0
