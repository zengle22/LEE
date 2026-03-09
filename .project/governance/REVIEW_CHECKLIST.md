# Review Checklist

## A. Scope

- Is the scope explicitly stated?
- Is out-of-scope explicitly stated?
- Is there a temporary truth source or a formal SSOT object?
- If this is temporary governance work, is there an Acceptance Brief or Module Contract?

## B. Truth Integrity

- Were acceptance criteria changed?
- Were pass thresholds weakened?
- Were failing tests deleted or bypassed?
- Was incomplete work described as complete?
- Was a temporary truth source silently promoted to formal truth?

## C. Path / Artifact Governance

- Are all governed outputs written to governed paths?
- Are formal outputs registered or materialized through the existing artifact flow?
- Are temporary outputs explicitly marked temporary?
- Are there unmanaged parallel directories?
- Are there hardcoded paths that should be governed?

## D. Reuse / Duplication

- Was existing implementation checked first?
- Was any duplicate module introduced?
- Is ownership of changed logic clear?
- Is there any overlapping implementation without a migration note?

## E. Evidence

- Are changed files listed?
- Are test results attached or explicitly missing?
- Are output artifact paths included?
- Are known risks or gaps explicitly declared?
- Are review notes included when required?

## F. Gate

- Does this change require human gate?
- If yes, is gate result recorded?
- If no, is the exemption justified?

## G. Completion Claim

- Is the completion statement evidence-backed?
- Are limitations clearly stated?
- Is anything still pending but hidden by wording?
- Does the output follow `.project/governance/COMPLETION_TEMPLATE.md`?
