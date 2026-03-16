---
name: lee-product-chain-validate
description: Run the canonical LEE product requirement-chain-validation workflow through Claude Code. Use when Claude should call `lee run product.requirement-chain-validation` to validate the product SSOT chain before final handoff instead of manually judging chain consistency.
author: LEE Team
date: 2026-03-15
version: 1.0
codex_source_skill: lee-product-chain-validate
---

# Lee Product Chain Validate

This Claude Code skill is a thin adapter over:

- workflow template: `spec-global/departments/product/workflows/templates/requirement-chain-validation/v1/workflow.yaml`
- CLI entry: `lee run product.requirement-chain-validation`

## Workflow

1. Resolve the active LEE project root.
2. Build a spec file with:
   - `source_freeze`
   - `epic_freeze_bundle`
   - `feat_freeze_bundle`
   - `delivery_prep_bundle`
3. Run:

```bash
lee run product.requirement-chain-validation --project-dir <repo> --spec <spec-file>
```

4. Confirm validation outputs, including chain test report and gate result.
5. Summarize blockers, warnings, and next action.

## Rules

- Do not replace workflow validation with an informal manual judgement.
- Use chain-test output and workflow review output as the source of truth.
- If blocker issues remain, report them and stop before handoff.
