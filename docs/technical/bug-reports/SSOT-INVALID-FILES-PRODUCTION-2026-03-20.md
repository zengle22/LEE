# Bug Report: Invalid SSOT Files Produced by Non-Governed or Legacy Paths (2026-03-20)

## Bug ID
- `BUG-SSOT-INVALID-FILES-PRODUCTION-2026-03-20`

## Status
- Open
- Severity: High (governance fidelity + ongoing lint noise)

## Context
Automation run `spec-cleanup-lee` on 2026-03-20 rebuilt SSOT registry and ran lint/validation. Lint failed with broad invalid-file findings, while validate passed. This indicates a large historical debt set plus active malformed-file production paths.

## Observed Signals
- Duplicate ID cluster still exists (`ADR-025`) due filename/front-matter mismatch in `ADR-028` file.
- Multiple malformed/YAML-broken formal files (including unresolved merge-conflict markers in formal task specs).
- Large placement-rule mismatch backlog (`expected placement` findings).
- Widespread invalid `source_refs` and inconsistent `parent_id` constraints.

## Likely Production Root Causes
1. Legacy generation workflows wrote formal files to historical directory conventions that no longer match current placement policy.
2. Some formal artifacts were created or modified through manual copy/rename flows without governance normalization, causing filename/front-matter divergence and duplicate IDs.
3. Merge conflict resolution was not enforced for `spec/**` files before commit in some paths, leaving conflict markers in formal front matter blocks.
4. ID parser/rule evolution outpaced legacy IDs; older IDs remain in active formal sets without migration.

## Why Current Cleanup Is Limited
This automation run applies only known-safe historical cleanup actions. The previously safe action is deleting exact localized duplicates for a single known duplicate-testset pattern. Current findings are broader and require governed migration or producer fixes, not blind deletion.

## Immediate Guardrail Actions Recommended
1. Enforce `lee ssot lint` as required CI gate for any changes under `spec/**`.
2. Add pre-commit/pre-push hard failure on merge markers (`<<<<<<<`, `=======`, `>>>>>>>`) under formal SSOT paths.
3. Block direct manual authoring in formal SSOT directories unless output includes governed provenance (`run_id`, workflow, generated_by).
4. Add a migration workflow to normalize legacy IDs/placement in batches, with approval checkpoints.

## Owner and Follow-up
- Owner: SSOT governance maintainers
- Follow-up artifact: `docs/reports/ssot-spec-cleanup-2026-03-20.md`
- Next action: Define and run a governed migration plan for placement + ID normalization before further auto-cleanups.
