---
description: Apply the temporary safe-coding guardrail in Claude Code and require an independent review before completion
---

# Zeng Safe Code

Use the repository skill `zeng-safe-code` as the temporary guard layer for
coding work in this repository.

This command is synchronized from Codex's `zeng-safe-coding` skill.

## When To Use

Use this command when the task involves any of the following:

- implementing a feature
- fixing a bug
- refactoring existing code
- updating workflow, spec, phase, or integration artifacts
- making a change that must avoid duplicate implementations, broken entrypoints,
  weakened tests, or premature completion claims

## Required Execution Rules

1. Search the repository before editing and identify the canonical non-legacy
   path.
2. Reuse existing modules and integration points instead of creating parallel
   implementations.
3. Update runtime wiring, workflow/spec references, exports, config, and tests
   when the task requires them.
4. Preserve the test bar. Do not weaken assertions, remove coverage, or alter
   pass criteria just to get green results.
5. Keep newly added or materially rewritten content within hard limits: code
   file <= 500 lines, document <= 1000 lines, function <= 100 lines, and
   `if`/`for` nesting <= 3 levels.
6. If those limits cannot be met, stop and require explicit human special
   approval instead of assuming an AI waiver.
7. Produce a structured candidate result package before any completion claim.
8. Run an explicitly separate review pass after implementation.
9. Treat the task as complete only if that review returns `PASS`.
