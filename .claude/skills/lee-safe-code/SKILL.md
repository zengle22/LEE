---
name: lee-safe-code
description: Enforce engineering guardrails before, during, and after AI-assisted coding work, with extra discipline for LEE-style workflow repositories. Claude Code should use this skill when asked to implement a feature, fix a bug, refactor code, update phase deliverables, touch workflow/spec artifacts, or make changes that must avoid duplication, broken integration, weakened tests, or self-certified completion.
author: LEE Team
date: 2026-03-12
version: 2.0
codex_source_skill: lee-safe-coding
compatibility: This Claude skill keeps the existing lee-safe-code entrypoint but is synchronized from Codex's lee-safe-coding skill.
---

# Lee Safe Coding

Apply this skill as a guard layer around coding work. Treat it as process control, not as a request to invent a new architecture.

The core control is simple:

- The generating agent may produce code and evidence, but it may not directly declare completion.
- The generating agent must submit a candidate result package.
- An independent supervisor gate such as `$lee-supervisor-gate` or the repository's gate-review path must return `PASS` before the task can be treated as complete.
- `REJECT` and `ESCALATE_TO_HUMAN` both block completion.

The generating agent must also respect these mandatory limits for newly added or materially rewritten content:

- code file limit: 500 lines
- document limit: 1000 lines
- function limit: 100 lines
- `if`/`for` nesting limit: 3 levels

Historical legacy debt may remain as-is unless the task explicitly includes refactoring it, but new work must comply. If an exception is unavoidable, route it to human special approval instead of assuming the supervisor can waive it.

## Claude Code Compatibility

- Repository entrypoint remains `lee-safe-code` for backward compatibility.
- Slash command remains `/lee-safe-code`.
- If a user refers to `lee-safe-coding`, treat it as the same skill in this repository.
- When Claude Code cannot call a dedicated supervisor skill directly, it must still perform an explicitly separate supervisor-style review pass before using completion language.

## Guard Rules

1. Search the repository before writing code.
   Reuse existing modules, helpers, conventions, and registration points before adding new files or abstractions.

2. Do not create parallel implementations.
   Avoid folders or files that signal duplication such as `*_v2`, `*_new`, `*_temp`, `copy`, or alternate service stacks unless the user explicitly asks for a replacement path.

3. Integrate new code into the real system.
   Wire handlers, routes, registries, workflows, exports, config, dependency injection, and documentation entry points required for the feature to actually run.

4. Preserve the test bar.
   Add or update tests that validate the intended behavior. Do not weaken assertions, remove cases, reduce coverage targets, or broaden acceptance criteria just to make tests pass.

5. Review before claiming completion.
   Check duplicate logic, edge cases, failure handling, naming, dead code, and whether the feature is reachable from the system boundary.

6. Do not self-certify completion.
   The generating agent may produce only a candidate result package, and it must not be treated as complete until an independent supervisor review returns `PASS`.

7. Escalate conflicts instead of guessing.
   If an existing implementation conflicts with the request, or the only way forward appears to be duplication or test weakening, stop and surface the constraint clearly.

8. Respect the active LEE workflow path.
   Prefer the current active project path, phase directory, `.workflow` state, and `openspec` outputs. Do not edit `legacy/` mirrors, archived evidence, or historical phase copies unless the user explicitly asks for a backfill or migration.

9. Keep new content within hard size and complexity limits.
   Newly added code files must stay within 500 lines, newly added documents within 1000 lines, newly added or materially rewritten functions within 100 lines, and newly added `if`/`for` logic within 3 nesting levels. If that cannot be achieved, stop and require human special approval.

## LEE-Specific Interpretation

In a LEE repository, "integrated into the system" means more than code compilation.

- If the task belongs to a phase, locate the active phase directory before editing.
- Treat `.workflow/`, `workflow.yaml`, `phase-config.yaml`, `openspec/`, `spec/`, and `tests/` as part of the delivery surface when they are relevant to the request.
- Distinguish active work from historical artifacts such as `legacy/` and `evidence/`.
- If the repository contains both implementation code and workflow evidence, update the canonical source first and only then update derived artifacts if the task requires them.
- Do not create a new phase-like directory, workflow copy, or spec branch just to isolate changes.

## Workflow

Use this minimum route by default:

```text
Task input
  -> Generator searches and edits canonical paths
  -> Generator runs validation and submits candidate result package
  -> Supervisor audits the candidate result package
  -> Route by decision:
       PASS -> task may be treated as complete
       REJECT -> send back for remediation
       ESCALATE_TO_HUMAN -> stop automatic closure
```

### Standard Invocation

Use this shape when you want one coding pass plus one independent closure decision:

```text
Use /lee-safe-code to implement the task in the canonical non-legacy path, preserve the test bar, and produce a structured candidate result package.
After the candidate result package is ready, run an independent supervisor pass and return PASS, REJECT, or ESCALATE_TO_HUMAN before any completion claim.
```

If the task is high-risk, say so in the request and require explicit attention to escalation boundaries.

### 1. Before Coding

- Search for existing implementations, similar names, and integration points.
- Identify the canonical module to extend.
- Identify the active workflow path and confirm that it is not a legacy mirror.
- Confirm which entry points must be updated for the change to be usable.
- If the request touches LEE delivery artifacts, determine whether code, `openspec`, tests, or workflow state must change together.
- State any structural risk before editing if duplication or ambiguous ownership is likely.

### 2. During Coding

- Modify the existing path whenever reasonable instead of creating a sibling path.
- Keep changes cohesive with the surrounding architecture and naming patterns.
- Wire the implementation into the actual execution path, not just helper code.
- Keep workflow-linked artifacts aligned with the implementation when the task requires phase deliverables.
- Add tests alongside the behavior change.
- Split new code or docs before they exceed the hard limits.

### 3. Before Completion

- Treat implementation output as a candidate result package, not a completed task.
- Verify the code is reachable from the system boundary.
- Verify phase or workflow deliverables still point to the correct implementation path.
- Verify tests cover the new or fixed behavior.
- Verify no existing tests were relaxed to manufacture a pass.
- Perform a brief self-review for duplication, edge cases, and error handling.
- Verify that new files, new documents, new functions, and newly added branch nesting still satisfy the hard limits.
- Do not use completion language such as "done", "fixed", "completed", or "ready to merge" before the supervisor gate passes.
- Hand the candidate result package to an independent supervisor review before using completion language.

### 4. Candidate Result Package

The generating agent must submit a structured candidate result package. Do not pass only a summary paragraph or a raw diff.

At minimum, include:

- original task goal and completion criteria, restated plainly
- changed files
- integration points and affected callers/interfaces
- impact scan summary, including theoretically related but untouched areas
- validations actually run and their outcomes
- tests changed or added, if any
- explicit unverified items, risks, and assumptions
- criterion-by-criterion evidence for why the task is believed to be ready for review

Preferred package shape:

```text
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
```

If a critical criterion has no evidence, say so explicitly. Do not hide it inside a generic summary.

### 5. Supervisor Gate

Run an independent supervisor pass after coding and verification. Prefer using the repository's gate-review path, a separate Claude review pass, or `$lee-supervisor-gate` when available. The supervisor is not there to write more code or defend the implementation. Its job is to decide whether the candidate result can be promoted to completion.

The generating agent must provide the supervisor with:

- the original task
- the completion criteria or acceptance bar
- the changed files and integration points
- the impact scan, including related but untouched locations
- the validations that were actually run
- the tests changed, if any
- explicit remaining risks and unknowns

The supervisor must audit these five areas:

1. Impact audit.
   List direct file changes, impacted modules/interfaces/callers, theoretically related but untouched locations, and whether those untouched locations create risk.

2. Real behavior verification audit.
   Explain how the original problem was reproduced, what evidence now shows the problem is gone, whether verification covers user behavior/system flow/local functions, and which critical behaviors remain unverified.

3. Completion-criteria playback.
   Restate the original task and completion criteria, match each criterion to evidence, and clearly separate evidence from inference.

4. Test-change audit.
   Check whether production code and tests changed together. If tests changed, explain why and determine whether assertions were weakened, edge cases removed, or validation standards lowered.

5. Unverified-risk disclosure.
   List what still has not been verified, what requires human confirmation, and the most likely risk that would be missed if the task were closed now.

The supervisor must also enforce these mandatory hard standards for new or materially rewritten content:

- code file must not exceed 500 lines
- document must not exceed 1000 lines
- function must not exceed 100 lines
- `if`/`for` nesting must not exceed 3 levels

If a candidate cannot satisfy these limits, it must not pass without explicit human special approval.

The supervisor may return only one of these decisions:

- `PASS`: Evidence is sufficient to allow completion, with remaining risks explicitly stated.
- `REJECT`: The candidate result is not complete and must be sent back for remediation.
- `ESCALATE_TO_HUMAN`: AI cannot independently close the task because risk, ambiguity, or missing end-to-end evidence is too high.

Interpret the decisions strictly:

- `PASS` does not mean no risk exists. It means the current completion bar is met and remaining risks are disclosed.
- `REJECT` means the task is not ready for closure and must be sent back with concrete remediation.
- `ESCALATE_TO_HUMAN` means the closure decision has crossed a boundary AI should not own.

Do not collapse `REJECT` or `ESCALATE_TO_HUMAN` into a soft warning. Both block completion.

Escalate to human instead of rejecting when the blocker is primarily a product, policy, access, or risk-ownership decision rather than missing implementation work. Common examples:

- the required behavior depends on a business tradeoff or backward-compatibility decision
- the only missing evidence requires real credentials, production data, or human approval
- the task touches payments, permissions, deletion, compliance, or similarly high-risk domains
- the repository contains conflicting canonical paths or unclear ownership that cannot be resolved safely from local evidence

### 6. Supervisor Prompt Template

Use this prompt shape when a dedicated supervisor review is needed and `$lee-supervisor-gate` is not available:

```text
You are an independent supervisor agent.

Your job is not to write code and not to help the generating agent justify itself.
Your job is to supervise the generation process and decide whether the result truly meets the bar for completion.

Do not accept summary claims such as "done", "verified", or "tests passed" without evidence.

Audit the result using exactly these five checks:

1. Impact audit
- List changed files
- Explain affected modules, interfaces, and callers
- Identify theoretically related but unchanged locations
- Judge whether unchanged locations create risk

2. Real behavior verification audit
- Explain how the original problem is reproduced
- Explain what evidence now proves the original problem is gone
- Judge whether evidence covers user behavior, system flow, or only local functions
- Identify critical behavior that remains unverified

3. Completion-criteria playback
- Restate the original task goal
- List the original completion criteria
- Match each criterion with evidence
- Mark which statements are evidence versus inference

4. Test-change audit
- Check whether production code and tests changed together
- If tests changed, explain why
- Judge whether assertions were weakened, edge cases removed, or validation standards lowered

5. Unverified-risk disclosure
- List still-unverified flows
- Identify what requires human confirmation
- Explain the most likely risk if the task is declared complete now

You may output only one final decision:
- PASS
- REJECT
- ESCALATE_TO_HUMAN

Output format:

Conclusion: PASS | REJECT | ESCALATE_TO_HUMAN

Review Summary:
- ...

Five Audit Results:
1. Impact audit: pass/fail + reason
2. Real behavior verification audit: pass/fail + reason
3. Completion-criteria playback: pass/fail + reason
4. Test-change audit: pass/fail + reason
5. Unverified-risk disclosure: pass/fail + reason

Required Remediation:
- ...

If the result is PASS, still state the remaining risks.
If the result is REJECT, state exactly why it is rejected.
If the result is ESCALATE_TO_HUMAN, state why AI cannot independently close the task.
```

## Response Pattern

When this skill is active, structure the work implicitly around this checklist:

- `Search`: what existing implementation or integration point was found.
- `Workflow`: which active phase, spec path, or non-legacy directory was treated as canonical.
- `Change`: what canonical path was updated.
- `Integration`: how the code is reachable in the system.
- `Tests`: what was added or verified without lowering standards.
- `Candidate`: the structured candidate result package produced before any completion claim.
- `Supervisor`: whether an independent supervisor pass returned `PASS`, `REJECT`, or `ESCALATE_TO_HUMAN`.
- `Review`: what risks, edge cases, and unverified areas remain after the supervisor decision.

## Refusal Conditions

Do not silently proceed if any of the following is true:

- The requested change obviously duplicates an existing implementation.
- The repository contains both active and historical phase paths and the canonical one cannot be inferred safely.
- The task can only be marked complete by loosening tests or removing assertions.
- The code compiles or exists locally but is not connected to runtime entry points.
- The repository structure suggests two competing canonical locations and the correct one cannot be inferred safely.
- The task is being declared complete without an independent supervisor gate or equivalent review boundary.
