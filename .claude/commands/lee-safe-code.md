---
description: Apply the synchronized LEE safe coding guardrail in Claude Code and require an independent supervisor-style closure decision
---

# Lee Safe Code

Use the repository skill `lee-safe-code` as the mandatory guard layer for coding work in this repository.

This command is synchronized from Codex's `lee-safe-coding` skill and keeps the Claude-compatible entrypoint name.

## When To Use

Use this command when the task involves any of the following:

- implementing a feature
- fixing a bug
- refactoring existing code
- updating workflow, spec, phase, or integration artifacts
- making a change that must avoid duplicate implementations, broken entrypoints, weakened tests, or premature completion claims

## Required Execution Rules

1. Search the repository before editing and identify the canonical non-legacy path.
2. Reuse existing modules and integration points instead of creating parallel implementations.
3. Update runtime wiring, workflow/spec references, exports, config, and tests when the task requires them.
4. Preserve the test bar. Do not weaken assertions, remove coverage, or alter pass criteria just to get green results.
5. Produce a structured candidate result package before any completion claim.
6. Run an explicitly separate supervisor-style review pass after implementation.
7. Treat the task as complete only if that review returns `PASS`.

## Required Output Shape

Before using any completion language, provide:

```text
Search:
- ...

Workflow:
- ...

Change:
- ...

Integration:
- ...

Tests:
- ...

Candidate:
Original Task:
- ...

Completion Criteria:
- ...

Changed Files:
- ...

Integration Points:
- ...

Impact Scan:
- changed:
- related but untouched:
- reason untouched:

Validation Run:
- command / check:
- result:

Tests Changed:
- ...

Unverified Items:
- ...

Remaining Risks:
- ...

Completion Criteria Playback:
- criterion:
  evidence:
  inference:

Supervisor:
Conclusion: PASS | REJECT | ESCALATE_TO_HUMAN
- ...

Review:
- ...
```

## Supervisor Review Requirement

If a dedicated supervisor skill or tool is unavailable, perform a separate supervisor-style review using these five audits:

1. Impact audit
2. Real behavior verification audit
3. Completion-criteria playback
4. Test-change audit
5. Unverified-risk disclosure

The final decision may only be:

- `PASS`
- `REJECT`
- `ESCALATE_TO_HUMAN`

`REJECT` and `ESCALATE_TO_HUMAN` both block completion.
