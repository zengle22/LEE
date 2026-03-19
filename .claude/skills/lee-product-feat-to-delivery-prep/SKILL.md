---
name: lee-product-feat-to-delivery-prep
description: Run the canonical LEE product feat-to-delivery-prep workflow through Claude Code. Use when Claude should call `lee run product.feat-to-delivery-prep` instead of manually authoring delivery prep outputs. If the CLI is missing or broken, stop and report a LEE CLI bug.
author: LEE Team
date: 2026-03-19
version: 1.1
codex_source_skill: lee-product-feat-to-delivery-prep
---

# Lee Product FEAT to Delivery Prep

This Claude Code skill is a thin CLI adapter.

- workflow template: `spec-global/departments/product/workflows/templates/feat-to-delivery-prep/v1/workflow.yaml`
- CLI entry: `lee run product.feat-to-delivery-prep`

## Execution Contract

1. Resolve the frozen FEAT input.
2. Build the workflow spec.
3. Before execution, declare the exact `lee` command, expected outputs, failure
   fallback, and files that will not be edited directly.
4. Run:

```bash
lee run product.feat-to-delivery-prep --project-dir <repo> --spec <spec-file>
```

5. Summarize workflow id, status, delivery-prep outputs, and blockers.

## Rules

- Do not manually author UI, TECH, or TASK outputs.
- Accept governed outputs only when provenance includes `run_id`, `workflow`,
  and `generated_by: lee-cli`.
- Follow CLI-returned `allowed_actions` and `forbidden_actions` when present.
- If the CLI fails, retry once only for corrected parameters; otherwise run a
  diagnostic `lee` help/doctor command and report a LEE CLI bug.
