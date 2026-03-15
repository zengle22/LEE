---
description: Run the LEE product src-to-epic workflow to produce a frozen EPIC
---

# LEE Product SRC to EPIC

Use the canonical product src-to-epic workflow.

## Usage

Prepare a spec file with one of:

- `src`
- `source_freeze`
- `source_freeze_ref`

Then run:

```bash
lee run product.src-to-epic --project-dir <repo> --spec <spec-file>
```

## What To Report

- workflow id
- final status
- SRC input used
- `epic_freeze_ref`
- blocking gate or failed step
