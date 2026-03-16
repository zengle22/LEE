---
name: lee-product-epic-to-feat
description: Run the canonical LEE product epic-to-feat workflow through Claude Code. Use when Claude should call `lee run product.epic-to-feat` to decompose a frozen EPIC into a frozen FEAT bundle instead of manually drafting FEAT artifacts.
author: LEE Team
date: 2026-03-15
version: 1.0
codex_source_skill: lee-product-epic-to-feat
---

# Lee Product EPIC to FEAT

This Claude Code skill is a thin adapter over:

- workflow template: `spec-global/departments/product/workflows/templates/epic-to-feat/v1/workflow.yaml`
- CLI entry: `lee run product.epic-to-feat`

## Workflow

1. Resolve the active LEE project root.
2. Build a spec file with:
   - `epic_freeze`
3. Run:

```bash
lee run product.epic-to-feat --project-dir <repo> --spec <spec-file>
```

4. Confirm FEAT bundle outputs such as `feat_freeze` and `feat_freeze_ref`.
5. Summarize results and the likely delivery prep next step.

## Rules

- Do not create UI, TECH, or TASK outputs here.
- Use workflow output as the source of truth for FEAT freeze state.
- If acceptance structure is missing, return the workflow blocker instead of
  inventing FEAT details in the skill.
