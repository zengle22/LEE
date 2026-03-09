---
id: ADR-002
ssot_type: adr
title: Windows Hook Portability Gap
status: draft
version: v1
parent_id: null
derived_from_ids: []
source_refs:
- ADR-001
owner: governance
tags:
- ssot
- governance
- windows
- hooks
properties:
  adr_kind: strategic_followup
  risk_area: windows_hook_portability
  decision_scope: local_ci_portability
---

# Context

Current local git hooks work on this machine because Git provides a shell runtime. We have not yet hardened hook execution for Windows environments that lack a usable shell runtime exposed by Git.

# Risk

This leaves a governance portability gap: local CI may not execute consistently across all Windows developer environments.

# Proposed Follow-up

1. Add a Windows-native hook launcher path that does not rely on sh semantics.
2. Validate hook execution on a Windows environment without Git Bash style shell exposure.
