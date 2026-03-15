---
description: Run the LEE product feat-to-delivery-prep workflow to produce delivery prep outputs
---

# LEE Product FEAT to Delivery Prep

Use the canonical product feat-to-delivery-prep workflow.

## Usage

Prepare a spec file with:

- `feat_freeze`

Optional decision context:

- `governing_adrs`
- `decision_refs`
- `decision_constraints`
- `architecture_constraints`
- `process_constraints`

Then run:

```bash
lee run product.feat-to-delivery-prep --project-dir <repo> --spec <spec-file>
```

## What To Report

- workflow id
- final status
- FEAT input used
- presence of `ui_specs`, `tech_specs`, and `task_plan`
- blocking gate or failed step
