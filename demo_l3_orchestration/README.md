---
title: L3 Test Orchestration Demo
author: LEE Team
date: 2026-02-06
version: 1.0
last_updated: 2026-02-19
---

# L3 Test Orchestration Demo

Complete demonstration of the L3 test orchestration workflow for result aggregation, bug generation, and gate evaluation.

## Overview

This demo implements the complete workflow defined in:
- `spec-global/departments/qa/workflows/test-orchestration-pipeline/v1/workflow.yaml`

## Workflow Stages

The demo implements all 8 stages of the L3 orchestration workflow:

1. **Load Test Execution Bundle** - Parse `test-execution-bundle.yaml`
2. **Parse Test Results** - Parse `test-results.yaml` from Claude Code execution
3. **Validate Completeness** - Ensure all test cases have results
4. **Generate Bug Contracts** - Auto-create bug contracts from failures
5. **Calculate Metrics** - Compute pass rates, bug counts, etc.
6. **Generate Reports** - Create JSON and Markdown reports
7. **Gate Evaluation** - Evaluate exit criteria
8. **Create Test Round Record** - Generate `test-round.yaml`

## File Structure

```
demo_l3_orchestration/
├── demo_l3.py                  # Main demo script
├── test-execution-bundle.yaml  # Input: Test execution bundle
├── test-results.yaml           # Input: Test execution results
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── output/                     # Generated output (created on run)
    ├── test-report.json        # Machine-readable report
    ├── test-report.md          # Human-readable report
    ├── test-round.yaml         # Round record (authoritative state)
    └── bugs/                   # Generated bug contracts
        ├── BUG-2026-0001.contract.yaml
        ├── BUG-2026-0002.contract.yaml
        └── BUG-2026-0003.contract.yaml
```

## Usage

### Prerequisites

- Python 3.10 or higher
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Running the Demo

```bash
python demo_l3.py
```

### Expected Output

The script will:
1. Load 10 test cases from the bundle
2. Parse 10 test results (6 passed, 3 failed, 1 blocked)
3. Generate 3 bug contracts from failed tests
4. Create comprehensive test reports
5. Evaluate exit criteria gate
6. Generate test-round.yaml

### Console Output

```
2026-02-05 10:00:00 [INFO    ] L3-Orchestration-Demo: ============================================================
2026-02-05 10:00:00 [INFO    ] L3-Orchestration-Demo: L3 Test Orchestration Demo - Starting
2026-02-05 10:00:00 [INFO    ] L3-Orchestration-Demo: ============================================================
...
2026-02-05 10:00:01 [INFO    ] L3-Orchestration-Demo: Generated bug BUG-2026-0001 from failed case F-P1-001
2026-02-05 10:00:01 [INFO    ] L3-Orchestration-Demo: Generated bug BUG-2026-0002 from failed case F-P1-002
2026-02-05 10:00:01 [INFO    ] L3-Orchestration-Demo: Generated bug BUG-2026-0003 from failed case F-P2-001
...
2026-02-05 10:00:01 [INFO    ] L3-Orchestration-Demo: Gate evaluation: FAILED, decision=next_round
...
```

## Contract Schemas

The demo adheres to these contract schemas:

- `test-execution-bundle`: `spec-global/departments/qa/contracts/test-execution-bundle/v1/schema.yaml`
- `test-result`: `spec-global/departments/qa/contracts/test-result/v1/schema.yaml`
- `bug-contract`: `spec-global/departments/qa/contracts/bug-contract/v1/schema.yaml`
- `test-round`: `spec-global/departments/qa/contracts/test-round/v1/schema.yaml`

## Gate Evaluation Rules

The demo implements these exit criteria:

1. **P0 Bug = 0** - No P0 bugs allowed
2. **Smoke 100%** - All smoke tests must pass
3. **P1 Threshold** - P1 bugs must not exceed 3
4. **Pass Rate** - Overall pass rate target 85%

## Next Actions Based on Gate Result

| Decision | Condition | Next Action |
|----------|-----------|-------------|
| `release_candidate` | All criteria met | Proceed to release |
| `next_round` | Any criteria failed | Fix bugs and retest |
| `blocked` | P0 bugs present | Block release until fixed |

## Example Bug Contract

Generated bugs include:

```yaml
bug_id: BUG-2026-0001
title: "跑者画像 - 数据保存功能 - 保存后数据未刷新，页面仍显示旧数据"
severity: P1
category: functional
detected_in:
  round_id: TSTR-0001
  version: v1.0.0-rc1
  test_case_id: F-P1-001
```

## Integration Points

This demo can be integrated with:

1. **Claude Code Agent** - For automated test execution
2. **Test Case Design Pipeline** - For generating test bundles
3. **Bug Sub Workflow** - For bug lifecycle management
4. **Human Approval Gates** - For conditional pass scenarios
