---
id: EPIC-SSOT-REV-001
ssot_type: epic
title: Reverse Workflow SSOT Chain Compliance & Alignment
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: epic
  identity_kind: ssot
frozen_at: '2026-03-13T11:30:57.178379'
---

epic_id: EPIC-SSOT-REV-001
title: Reverse Workflow SSOT Chain Compliance & Alignment
goal: Enable the reverse workflow to fully undertake and align with the current SSOT
  document chain standards without expanding scope.
scope:
- Define mapping rules for SRC/EPIC/FEAT objects within reverse workflow
- Implement validation logic for canonical SSOT directory paths
- Enforce artifact generation limits to seed/view/handoff/index only
- Ensure formal object materialization is restricted to SRC/EPIC/FEAT
non_goals:
- Create new parallel workflow keys
- Materialize formal objects outside SRC/EPIC/FEAT scope
- Generate deep UI/TECH/TASK artifacts beyond seed/view/handoff
- Modify business logic unrelated to SSOT structure compliance
success_metrics:
- 100% of reverse workflow outputs align with canonical SSOT directory structure
- Zero violations of formal object constraints (SRC/EPIC/FEAT only)
- 100% success rate in generating required seed/view/handoff indices
- Pass all governance 审查员 (Governance Reviewer) validation checks
priority: P1
feat_split_principles:
- Split by Formal Object Lifecycle Stage (SRC vs EPIC vs FEAT)
- Split by Validation Dimension (Path Structure vs Content Metadata)
- Split by Artifact Depth (Seed Generation vs View Indexing vs Handoff)
ssot:
  identity_kind: ssot
  ssot_type: EPIC
  id: EPIC-SSOT-REV-001
  version: 1.0.0
  status: draft
