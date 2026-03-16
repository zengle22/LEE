---
description: Execute Dev Smoke Test in local environment using Dev Smoke L3 workflow
---

# Dev Smoke Test

Execute Smoke Test in local dev environment using Dev Smoke L3 workflow.
This is a mandatory gate before merge - cannot merge without passing.

## Workflow

1. **Environment Check** - Verify local dev environment is ready
2. **Case Generation** - Generate test cases dynamically from Test Set
3. **Script Execution** - Execute test scripts and collect evidence
4. **Result Judgment** - Judge test results (Pass/Fail)
5. **Evidence Packaging** - Package evidence for Smoke Gate

## Usage

When user provides a Test Set path, run:

```bash
lee dev smoke run --test-set <test_set_path>
```

### Parameters

- `--test-set`: Path to Test Set YAML (required)
- `--feat`: Path to FEAT freeze (optional, for traceability)
- `--priority`: Priority filter, default: ["P0", "P1"] (optional)
- `--coverage`: Enable/disable coverage, default: true (optional)
- `--mode`: Execution mode: enforce|warn, default: enforce (optional)

### Example

```bash
# Run smoke test for user-auth module
lee dev smoke run --test-set qa_specs_dir/test-sets/ts-user-auth.yaml

# Run with specific FEAT traceability
lee dev smoke run \
  --test-set qa_specs_dir/test-sets/ts-checkout.yaml \
  --feat spec/ssot/feat/FEAT-023.yaml

# Run with custom priority filter
lee dev smoke run \
  --test-set qa_specs_dir/test-sets/ts-report.yaml \
  --priority ["P0", "P1", "P2"]
```

## Output

The workflow produces:

```
tests_dir/exec/{smoke_run_id}/
├── cases.yaml                    # Generated test cases (ephemeral)
├── scripts/                      # Executable test scripts
├── runner-output.json            # Test runner output
├── bundle/                       # Evidence bundle
├── compliance-result.json        # Compliance check result
├── results.yaml                  # Test results with Pass/Fail
└── tse.yaml                      # Test Set Execution record

.workflow/smoke-evidence-{smoke_run_id}/
├── evidence_pack.json            # Evidence pack for Smoke Gate
├── smoke_summary.json            # Smoke test summary
└── README.md                     # Summary report
```

## Smoke Gate

After successful execution, the evidence pack is automatically submitted to:

```
gate.dev.smoke_gate (Auto Gate, Blocker Priority)
```

**Gate Checks**:
- `smoke_test_pass`: Smoke Test must be 100% passed
- `smoke_result_pass`: Overall result must be PASS
- `coverage_threshold`: Coverage must be >= 80%
- `evidence_completeness`: Evidence pack must be complete
- `gate_handoff_ready`: Evidence pack must be ready for gate

**On Fail**:
- Merge is blocked
- Tech lead is notified
- Must fix and re-run smoke test

## List/Show Commands

```bash
# List all smoke runs
lee dev smoke list

# Show smoke run details
lee dev smoke show <smoke_run_id>

# Show smoke gate status
lee dev smoke gate-status
```

## Instructions for Claude

When the user asks to run smoke test:

1. **Verify Test Set exists**: Check that the provided Test Set YAML exists
2. **Run smoke workflow**: Execute `lee dev smoke run --test-set <path>`
3. **Monitor execution**: Watch for any failures during execution
4. **Check results**: Verify smoke_result.result == "PASS"
5. **Gate evaluation**: Check if Smoke Gate passed automatically
6. **On failure**: Help user identify root cause and fix

### Pre-flight Checklist

Before running smoke test:

- [ ] Test Set YAML exists and is valid
- [ ] FEAT freeze is available (optional but recommended)
- [ ] Local dev environment is ready (Python, dependencies)
- [ ] Code changes are committed
- [ ] No known blocking issues

### Post-execution Actions

After smoke test completes:

1. **If PASS**:
   - Evidence pack is ready for Smoke Gate
   - Gate evaluation is automatic
   - If gate passes, merge is allowed

2. **If FAIL**:
   - Review failure details in `smoke_summary.json`
   - Check `results.yaml` for specific failed cases
   - Bug drafts are created in `spec/testing/bugs/`
   - Fix the issues and re-run smoke test

3. **If INVALID_RUN**:
   - Check `compliance-result.json` for Anti-Mock Gate failure
   - Verify environment setup
   - Re-run with `--mode warn` for debugging

## Related Commands

- `/lee-qa-test-set` - Create Test Set (QA responsibility)
- `/lee-feature` - Feature development workflow
- `/lee-feature-integration` - Integration test after feature dev
- `/gate-review` - Review pending gates

## ADR References

- ADR-005: Gate 三分类治理模型
- ADR-023: Dev Smoke Gate 架构与测试职责分层
