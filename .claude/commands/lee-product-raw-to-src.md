---
description: Run the LEE product raw-to-src workflow to produce a frozen SRC
---

# LEE Product Raw to SRC

Use the canonical product raw-to-src workflow.

## Usage

Prepare a spec file with one or more of:

- `adr`
- `raw_requirement`
- `business_opportunity`
- `business_opportunity_freeze`

Then run:

```bash
lee run product.raw-to-src --project-dir <repo> --spec <spec-file>
```

## What To Report

- workflow id
- final status
- `source_freeze_ref`
- `src_root_id`
- blocking gate or failed step
