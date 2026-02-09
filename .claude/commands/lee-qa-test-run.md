---
description: Execute Test Plan and run test batch using QA workflow
---

# QA Test Plan Execution

Execute a Test Plan to create a Test Run with full test execution.

## Workflow

1. **Test Run Init** - Create Test Run, bind build and environment
2. **Env Provision** - Prepare test environment
3. **Case Generation** - Generate test cases from Test Sets
4. **Script Translation** - Translate cases to executable scripts
5. **Script Execution** - Execute test scripts
6. **TSE Assembly** - Assemble Test Set Execution results
7. **Bug Drafting** - Draft bugs for failures
8. **Exit Evaluation** - Evaluate exit criteria

## Usage

### Start a Test Run

```bash
lee qa test-run start <test_plan_id> --build <version> --commit <hash> [--env <env>]

# Or use shortcut
lee qa run <test_plan_id> --build <version> --commit <hash>
```

### Parameters

- `test_plan_id`: Test Plan ID (e.g., `TP-DEMO-PHASE0`)
- `build`: Build version (e.g., `1.0.0`)
- `commit`: Git commit hash
- `env` (optional): Test environment name (default: `test`)

### Example

```bash
# Start Test Run for demo plan
lee qa run TP-DEMO-PHASE0 --build 1.0.0 --commit abc1234
```

## Prerequisites

Before running, ensure:

1. Test Plan exists: `lee qa test-plan list`
2. Test Sets exist: `lee qa test-set list`

### Create Test Plan (if not exists)

```bash
lee qa test-plan create <plan-id> \
  --scope <module1> --scope <module2> \
  --test-set TS-SMOKE --test-set TS-DAILY-PLAN
```

## Output

The workflow produces:

```
qa/
├── test-runs/
│   └── TR-{date}-{commit}/
│       ├── test-run.yaml           # Test Run record
│       ├── env-health.yaml         # Environment health check
│       ├── exit-evaluation.yaml    # Exit evaluation
│       ├── tse-{test-set}/
│       │   ├── cases.yaml          # Generated cases
│       │   ├── scripts/            # Translated scripts
│       │   ├── results.yaml        # Execution results
│       │   └── tse.yaml            # TSE summary
│       └── ...
└── bugs/
    └── BUG-{id}.yaml               # Discovered bugs
```

## Human Gates

1. **Case Review** - Confirm generated test cases
2. **Bug Confirmation** - Confirm bug drafts
3. **Exit Decision** - Final pass/fail/conditional decision

## Management Commands

```bash
# List Test Plans
lee qa test-plan list

# Show Test Plan details
lee qa test-plan show <plan-id>

# Check Test Run status
lee qa test-run status [run-id]

# Approve a gate
lee qa test-run approve <gate-id>
```

## Instructions for Claude

When the user asks to run tests:

1. Check if Test Plan exists with `lee qa test-plan list`
2. If not, help create one with `lee qa test-plan create`
3. Ask for build version and commit if not provided
4. Run `lee qa run <plan-id> --build <version> --commit <hash>`
5. Monitor the workflow execution
6. When blocked at a gate:
   - Show relevant artifacts (cases, bugs, etc.)
   - Ask for user approval
   - Use `lee qa test-run approve <gate-id>` to approve
7. Report final exit evaluation results
