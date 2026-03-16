---
description: Run the LEE product main pipeline from raw input through delivery prep
---

# LEE Product Main

Run the canonical product L2 pipeline through the LEE CLI.

## Usage

Prepare a spec file with one or more of:

- `adr`
- `raw_requirement`
- `business_opportunity_freeze`

Then run:

```bash
lee run product.main --project-dir <repo> --spec <spec-file>
```

## What To Report

- workflow id
- final status
- whether SRC, EPIC, FEAT, delivery prep, and validation outputs were produced
- blocking gate or failed step
