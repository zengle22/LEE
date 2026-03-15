---
name: lee-product-main
description: Run the canonical LEE product main pipeline through Claude Code. Use when Claude should call `lee run product.main` to move raw requirement, ADR, or business opportunity input through the product SSOT chain instead of manually producing SRC, EPIC, FEAT, or delivery prep artifacts.
author: LEE Team
date: 2026-03-15
version: 1.0
codex_source_skill: lee-product-main
---

# Lee Product Main

This Claude Code skill is a thin adapter over the repository workflow:

- workflow template: `spec-global/departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml`
- CLI entry: `lee run product.main`

## Workflow

1. Resolve the active LEE project root.
2. Build a spec file with one or more of:
   - `adr`
   - `raw_requirement`
   - `business_opportunity_freeze`
3. Run:

```bash
lee run product.main --project-dir <repo> --spec <spec-file>
```

4. Track the workflow until completion or gate blocking.
5. Summarize workflow id, status, key outputs, and next step.

## Rules

- Do not manually recreate SRC, EPIC, FEAT, or delivery prep content in the
  skill.
- Treat checked-in workflow YAML as a template, not a runtime instance.
- If a gate blocks the run, surface the gate and wait for user decision.
