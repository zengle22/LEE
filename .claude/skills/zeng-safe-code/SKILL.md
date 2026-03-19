---
name: zeng-safe-code
description: Temporary coding guardrail for Claude Code. Use when Claude is asked to implement a feature, fix a bug, refactor code, or update workflow/spec artifacts and needs a strict engineering checklist around search, integration, tests, candidate result packaging, and independent review, without treating the skill as a LEE CLI capability.
author: LEE Team
date: 2026-03-19
version: 1.0
codex_source_skill: zeng-safe-coding
---

# Zeng Safe Code

Apply this skill as a temporary guard layer around coding work.

This skill is process control, not a LEE workflow entrypoint.

## Guard Rules

1. Search the repository before writing code.
2. Reuse existing modules and integration points before creating new ones.
3. Do not create parallel implementations.
4. Integrate changes into the real execution path.
5. Preserve the test bar. Do not weaken assertions or reduce coverage just to
   pass tests.
6. Keep new or materially rewritten content within hard limits:
   - code file <= 500 lines
   - document <= 1000 lines
   - function <= 100 lines
   - `if`/`for` nesting <= 3 levels
7. Produce a structured candidate result package before any completion claim.
8. Require an explicitly separate review pass before treating the task as
   complete.

## Candidate Result Package

Before using completion language, provide:

- original task goal
- completion criteria
- changed files
- integration points
- impact scan, including related but untouched areas
- validations actually run and outcomes
- tests added or changed
- explicit unverified items, risks, and assumptions
- criterion-by-criterion evidence

## Review Requirement

The review pass must return one of:

- `PASS`
- `REJECT`
- `ESCALATE_TO_HUMAN`

Only `PASS` allows closure.
