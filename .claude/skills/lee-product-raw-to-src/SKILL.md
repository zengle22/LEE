---
name: lee-product-raw-to-src
description: Run the canonical LEE product raw-to-src workflow through Claude Code. Use when Claude should call `lee run product.raw-to-src` instead of manually drafting SRC artifacts. If the CLI is missing or broken, stop and report a LEE CLI bug.
author: LEE Team
date: 2026-03-19
version: 1.1
codex_source_skill: lee-product-raw-to-src
---

# Lee Product Raw to SRC

This Claude Code skill is a thin CLI adapter.

- workflow template: `spec-global/departments/product/workflows/templates/raw-to-src/v1/workflow.yaml`
- CLI entry: `lee run product.raw-to-src`

## Execution Contract

1. Resolve the raw input source.
2. Build the workflow spec.
3. Before execution, declare the exact `lee` command, expected outputs, failure
   fallback, and files that will not be edited directly.
4. Run:

```bash
lee run product.raw-to-src --project-dir <repo> --spec <spec-file>
```

5. Summarize workflow id, status, SRC outputs, and blockers.

## Rules

- Do not manually draft SRC artifacts.
- Accept governed outputs only when provenance includes `run_id`, `workflow`,
  and `generated_by: lee-cli`.
- Follow CLI-returned `allowed_actions` and `forbidden_actions` when present.
- If the CLI fails, retry once only for corrected parameters; otherwise run a
  diagnostic `lee` help/doctor command and report a LEE CLI bug.
