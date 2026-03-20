# SSOT Spec Cleanup Report (2026-03-20)

## Run Metadata
- Run time: 2026-03-20T04:05:19+08:00
- Repository: `C:\Users\shado\.codex\worktrees\ecdb\LEE`
- Automation: `Spec Cleanup LEE` (`spec-cleanup-lee`)

## Commands Executed
1. `lee ssot rebuild-registry`
2. `lee ssot lint`
3. `lee ssot validate`

## Command Results
- `lee ssot rebuild-registry`: success (`401 artifacts`)
- `lee ssot lint`: failed (`378` lint lines)
- `lee ssot validate`: success

## Findings Summary (from lint)
- Misplaced formal files (`expected placement`): `130`
- Duplicate ID clusters: `1`
- Invalid `parent_id` findings: `23`
- Invalid `source_refs` findings: `177`
- Invalid ID format findings: `14`
- YAML/front matter parse failures: `4`

Primary duplicate cluster:
- `ADR-025` appears in two files:
  - `spec/adr/ADR-025__materialization-verification-and-phase-gated-delivery-governance.md`
  - `spec/adr/ADR-028__ssot-requirement-axis-acceptance-governance.md` (filename/front-matter mismatch)

Malformed front matter/high-risk malformed files surfaced in this run:
- `spec/adr/ADR-028__ssot-requirement-axis-acceptance-governance.md` (`filename ID ADR-028 != front matter id ADR-025`)
- `spec/tech/SRC-NO-SOURCE/TECH-FEAT-143-013__feat-143-dongjiejizhujiagou.md` (`filename ID TECH-FEAT-143-013 != front matter id ARCH-FEAT-143`, plus YAML parse failure)
- Merge-conflict markers still present in task files (for example FEAT-170 / FEAT-172 task specs), causing YAML parse failures

## Safe Cleanup Actions Applied
This run intentionally applied only known-safe historical cleanup actions.

- Safe historical pattern checked: localized duplicate-testset files for one ID cluster under `spec/testing/testsets` (previously observed as `TESTSET-FEAT-123-001`).
- Pattern present in this run: `No`.
- Files cleaned: `0`
- Files deleted: `0`

## Cleaned/Deleted File Log
- None in this run.

## Remaining Findings Requiring Root-Cause Fixes
1. Legacy directory layout vs current placement rules (large `expected placement` backlog).
2. Mixed historical ID schemes (for example `TECH-FEAT-SRC-*`, `EPIC-LEE-SRC-FREEZE-*`) vs current ID parser.
3. Broken provenance references (`source_refs` and derived IDs pointing to non-existing FEAT artifacts).
4. Manual or conflicted edits causing malformed front matter and duplicate IDs.

## Evidence Files
- Lint raw output: `docs/reports/ssot-spec-cleanup-2026-03-20.lint.txt`
