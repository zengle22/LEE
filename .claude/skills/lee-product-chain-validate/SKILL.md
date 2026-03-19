---
name: lee-product-chain-validate
description: Run the canonical LEE product requirement-chain-validation workflow through Claude Code. Use when Claude should call `lee run product.requirement-chain-validation` instead of manually judging chain consistency. If the CLI is missing or broken, stop and report a LEE CLI bug.
author: LEE Team
date: 2026-03-19
version: 1.1
codex_source_skill: lee-product-chain-validate
---

# Lee Product Chain Validate

This Claude Code skill is a thin CLI adapter.

- workflow template: `spec-global/departments/product/workflows/templates/requirement-chain-validation/v1/workflow.yaml`
- CLI entry: `lee run product.requirement-chain-validation`

## Execution Contract

1. Resolve the active LEE project root and chain inputs.
2. Build the workflow spec.
3. Before execution, declare the exact `lee` command, expected outputs, failure
   fallback, and files that will not be edited directly.
4. Run:

```bash
lee run product.requirement-chain-validation --project-dir <repo> --spec <spec-file>
```

5. Summarize workflow id, status, validation outputs, blockers, and gate state.

## Rules

- Do not manually judge chain quality.
- Accept governed outputs only when provenance includes `run_id`, `workflow`,
  and `generated_by: lee-cli`.
- Follow CLI-returned `allowed_actions` and `forbidden_actions` when present.
- If the CLI fails, retry once only for corrected parameters; otherwise run a
  diagnostic `lee` help/doctor command and report a LEE CLI bug.
