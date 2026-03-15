---
name: lee-product-feat-to-delivery-prep
description: Run the canonical LEE product feat-to-delivery-prep workflow through Claude Code. Use when Claude should call `lee run product.feat-to-delivery-prep` to generate delivery prep outputs from a frozen FEAT instead of manually authoring UI, TECH, or TASK planning artifacts.
author: LEE Team
date: 2026-03-15
version: 1.0
codex_source_skill: lee-product-feat-to-delivery-prep
---

# Lee Product FEAT to Delivery Prep

This Claude Code skill is a thin adapter over:

- workflow template: `spec-global/departments/product/workflows/templates/feat-to-delivery-prep/v1/workflow.yaml`
- CLI entry: `lee run product.feat-to-delivery-prep`

## Workflow

1. Resolve the active LEE project root.
2. Build a spec file with:
   - `feat_freeze`
3. Add optional decision context when available:
   - `governing_adrs`
   - `decision_refs`
   - `decision_constraints`
   - `architecture_constraints`
   - `process_constraints`
4. Run:

```bash
lee run product.feat-to-delivery-prep --project-dir <repo> --spec <spec-file>
```

5. Confirm `tech_specs`, `task_plan`, optional `ui_specs`, and delivery prep
   freeze output.

## Rules

- Do not manually author Dev or QA artifacts in this skill.
- Treat UI as optional when the workflow marks it not applicable.
- Use workflow outputs as the source of truth for handoff preparation.
