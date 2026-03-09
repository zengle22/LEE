# Spec Governance L3 Usage

## Purpose

`core.spec-governance` is the governed L3 workflow for creating or updating:

- agent specs
- workflow specs
- contract specs

It is the canonical path for:

1. maintainer-generated spec updates
2. automatic writeback to the target spec file
3. exact diff generation
4. mandatory spec review
5. auto gate + human gate fallback
6. revise loop back to `spec_maintenance`

## Workflow Shape

The template lives at:

- `spec-global/core/workflows/templates/spec-governance-l3-template.yaml`

The executable workflow key is:

- `core.spec-governance`

The runtime sequence is:

1. `spec_maintenance`
2. `spec_review`
3. `review_gate`
4. `final_output`

### Gate Semantics

`review_gate` evaluates:

- `blocker_count == 0`
- or `blocker_count == 0 and major_count == 0` when `strict_review_gate=true`

If the auto check fails:

- `human_gate_required=true`:
  the workflow pauses at a human gate
- `human_gate_required=false`:
  the step fails directly

### Revise Loop

When a human reviewer chooses `revise` on the failed review gate:

- the gate is marked `revised`
- downstream gate state is invalidated
- the workflow rewinds to `spec_maintenance`
- the next review failure creates a new gate id

This is the canonical revise loop for spec governance.

## Automatic Writeback

`spec_maintenance` is configured with `spec_writeback.enabled=true`.

Expected maintainer outputs:

- generation summary
- target spec content at `params.target_path`
- maintenance notes

Runtime behavior:

1. the target spec content is written back to `params.target_path`
2. a unified diff is generated
3. both target spec and diff are registered as produced artifacts

Diff path:

- `docs/reports/governance/spec-review/{request_id}-spec.diff`

## Running The Workflow

Prepare a request YAML and pass it with `--spec`.

Example:

```powershell
python -m lee.cli.main run core.spec-governance `
  --project-dir E:\ai\LEE `
  --spec E:\ai\LEE\demo-test-artifacts\spec-governance-demo\request-agent-update.yaml `
  --skip-plan `
  --max-steps 6
```

## Request Fields

Required:

- `request_id`
- `spec_kind`
- `action`
- `change_request`

Optional:

- `target_path`
- `scope`
- `acceptance_brief_id`
- `ssot_root_id`
- `reviewer_mode`
- `strict_review_gate`
- `human_gate_required`
- `human_gate_reviewers`

## Human Gate Operations

List pending gates:

```powershell
python -m lee.cli.main gates list --project-dir E:\ai\LEE
```

Approve a gate:

```powershell
python -m lee.cli.main gates approve <workflow_id> <gate_id> --approver <name> --project-dir E:\ai\LEE
```

Revise a gate and trigger loopback:

```powershell
python -m lee.cli.main gates revise <workflow_id> <gate_id> `
  --reviewer <name> `
  --reason "Need maintainer to address findings" `
  --target-step spec_maintenance `
  --project-dir E:\ai\LEE
```

## Output Files

Typical outputs:

- `docs/reports/governance/spec-review/{request_id}-generation.md`
- `docs/reports/governance/spec-review/{request_id}-spec.diff`
- `docs/reports/governance/spec-review/{request_id}-review.json`
- `docs/reports/governance/spec-review/{request_id}-completion.md`

If writeback succeeds, the target spec file at `target_path` is also updated.

## Boundaries

- Formal SSOT still has priority when it exists.
- This workflow governs spec maintenance, not feature implementation.
- Human gate is only the fallback branch for failed review thresholds.
- `Acceptance Brief` is not required for spec maintenance unless the maintained spec itself is implementation-facing and not covered by formal SSOT.
