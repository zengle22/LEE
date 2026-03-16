---
description: Run the LEE product epic-to-feat workflow to produce a frozen FEAT bundle
---

# LEE Product EPIC to FEAT

Use the canonical product epic-to-feat workflow.

## Usage

Prepare a spec file with:

- `epic_freeze`

Then run:

```bash
lee run product.epic-to-feat --project-dir <repo> --spec <spec-file>
```

## What To Report

- workflow id
- final status
- EPIC input used
- FEAT bundle reference
- blocking gate or failed step
