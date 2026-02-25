# Dev Workflow Runtime Instances

This directory contains automatically generated workflow instances created by `lee run`.

**DO NOT EDIT FILES IN THIS DIRECTORY MANUALLY**

Instances are generated from templates in:
- `spec-global/departments/dev/workflows/templates/`

## Structure

```
instances/
├── l2/    # L2 instances (Feature development, Bug fix)
│   ├── feature-{module}-{feature_point}.yaml
│   └── bug-fix-{bug_id}.yaml
└── l3/    # L3 instances (Contract design, FE/BE implementation, Integration)
    ├── feature-contract-{feature_point}-{timestamp}.yaml
    ├── feature-fe-{feature_point}-{timestamp}.yaml
    ├── feature-be-{feature_point}-{timestamp}.yaml
    └── feature-integration-{feature_point}-{timestamp}.yaml
```

## Usage

Execute L2 Feature workflow:
```bash
lee run spec-global/departments/dev/workflows/templates/feature-l2-template.yaml \
  --project running_master \
  --module timing \
  --feature-point-id F1 \
  --feature-spec docs/prd/timing_F1.md \
  --repo_frontend repos/running_master/frontend \
  --repo_backend repos/running_master/backend
```

Execute L2 Bug Fix workflow:
```bash
lee run spec-global/departments/dev/workflows/templates/bug-fix-l2-template.yaml \
  --project running_master \
  --bug-id BUG-1234 \
  --bug-description "Timing page crash on load"
  --repo repos/running_master/backend
```

Execute L3 Contract Design (direct, for debugging):
```bash
lee run spec-global/departments/dev/workflows/templates/feature-contract-l3-template.yaml \
  --feature-spec docs/prd/timing_F1.md \
  --project running_master \
  --module timing
```

## Workflow Templates

### L2 Templates
- `feature-l2-template.yaml` - Feature development (4 phases: contract, FE, BE, integration, smoke)
- `bug-fix-l2-template.yaml` - Bug fix (4 phases: analysis, fix, verify, review)

### L3 Templates
- `feature-contract-l3-template.yaml` - API Contract design and freeze (3 stages)
- `feature-fe-l3-template.yaml` - Frontend implementation (4 stages)
- `feature-be-l3-template.yaml` - Backend implementation (4 stages)
- `feature-integration-l3-template.yaml` - Integration testing (4 stages)
