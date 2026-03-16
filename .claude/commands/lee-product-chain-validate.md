---
description: Run the LEE product requirement-chain-validation workflow before handoff
---

# LEE Product Chain Validate

Use the canonical product requirement-chain-validation workflow.

## Usage

Prepare a spec file with:

- `source_freeze`
- `epic_freeze_bundle`
- `feat_freeze_bundle`
- `delivery_prep_bundle`

Then run:

```bash
lee run product.requirement-chain-validation --project-dir <repo> --spec <spec-file>
```

## What To Report

- workflow id
- final status
- validation report paths
- blocker or warning summary
- gate result
