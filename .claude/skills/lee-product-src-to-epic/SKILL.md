---
name: lee-product-src-to-epic
description: Run the canonical LEE product src-to-epic workflow through Claude Code. Use when Claude should call `lee run product.src-to-epic` to convert a frozen SRC into a frozen EPIC instead of drafting EPIC artifacts manually.
author: LEE Team
date: 2026-03-15
version: 1.0
codex_source_skill: lee-product-src-to-epic
---

# Lee Product SRC to EPIC

This Claude Code skill is a thin adapter over:

- workflow template: `spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml`
- CLI entry: `lee run product.src-to-epic`

## Workflow

1. Resolve the active LEE project root.
2. Build a spec file with one of:
   - `src`
   - `source_freeze`
   - `source_freeze_ref`
3. Run:

```bash
lee run product.src-to-epic --project-dir <repo> --spec <spec-file>
```

4. Confirm `epic_freeze` or `epic_freeze_ref`.
5. Summarize results and likely downstream FEAT generation.

## Rules

- Accept only frozen SRC context for the canonical path.
- Do not pass raw requirement text directly to this workflow.
- Use workflow output as the source of truth for EPIC scope and freeze state.
