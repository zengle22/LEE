---
name: lee-product-raw-to-src
description: Run the canonical LEE product raw-to-src workflow through Claude Code. Use when Claude should call `lee run product.raw-to-src` to normalize raw requirement, ADR, or business opportunity input into a frozen SRC instead of drafting SRC artifacts manually.
author: LEE Team
date: 2026-03-15
version: 1.0
codex_source_skill: lee-product-raw-to-src
---

# Lee Product Raw to SRC

This Claude Code skill is a thin adapter over:

- workflow template: `spec-global/departments/product/workflows/templates/raw-to-src/v1/workflow.yaml`
- CLI entry: `lee run product.raw-to-src`

## Workflow

1. Resolve the active LEE project root.
2. Build a spec file with one or more of:
   - `adr`
   - `raw_requirement`
   - `business_opportunity`
   - `business_opportunity_freeze`
3. Run:

```bash
lee run product.raw-to-src --project-dir <repo> --spec <spec-file>
```

4. Confirm `source_freeze`, `source_freeze_ref`, and `src_root_id`.
5. Summarize results and the likely next step.

## Rules

- Do not generate EPIC or FEAT in this skill.
- Use the workflow result as the source of truth for the frozen SRC.
- If the workflow returns a split-needed blocker, report it instead of forcing a
  single interpretation.
