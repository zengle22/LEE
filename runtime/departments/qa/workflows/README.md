# QA Workflow Runtime Instances

This directory contains automatically generated workflow instances created by `lee run`.

**DO NOT EDIT FILES IN THIS DIRECTORY MANUALLY**

Instances are generated from templates in:
- `spec-global/departments/qa/workflows/templates/`

## Structure

```
instances/
├── l2/    # L2 instances (Test Plan execution)
│   └── test-plan-{test_run_id}.yaml
└── l3/    # L3 instances (Test Set execution)
    ├── test-set-{test_set_id}-{test_run_id}.yaml
    └── ...
```

## Usage

Execute L2 workflow:
```bash
lee run spec-global/departments/qa/workflows/templates/test-plan-l2-template.yaml \
  --test-plan-id TP-2026-Q1 \
  --build-version v1.2.3
```

Execute L3 workflow:
```bash
lee run spec-global/departments/qa/workflows/templates/test-set-l3-template.yaml \
  --test-run-id TR-2026-0224 \
  --test-set-id ts_auth
```
