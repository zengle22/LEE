# Reverse EPIC FEAT Design

## Purpose

This design note documents the evidence strategy used by
`template.core.reverse_epic_feat`.

The workflow reverse-engineers an existing repository into SSOT-aligned
`EPIC` and `FEAT` outputs. It does not generate downstream artifacts such as
`TECH`, `TESTSET`, `TC`, `REPORT`, or trace outputs.

Checked-in workflow specs remain templates only. Runtime workflow instances are
created dynamically by the orchestrator or CLI.

## Evidence Model

Every generated feature must carry three evidence views:

1. `evidence_refs`
   The full ordered evidence set gathered from docs, code, tests, and runtime
   hints.
2. `evidence_layers`
   A structured split of the full evidence set into:
   - `impl_refs`
   - `api_refs`
   - `test_refs`
   - `doc_refs`
3. `primary_refs`
   The ranked implementation-facing subset used as the main supporting
   evidence in FEAT outputs.

`primary_refs` must follow `ordered_impl_api_first`:

- prefer `impl_refs` and `api_refs`
- fall back to `doc_refs` and `test_refs` only when implementation-facing
  evidence is unavailable
- preserve ranked order rather than re-sorting away local disambiguation

## Ranking Signals

The current workflow uses four ranking signals when selecting `primary_refs`:

1. `path_quality`
   Prefer implementation paths such as services, handlers, models, pages,
   components, stores, and composables. De-prioritize migrations, archives,
   reports, summaries, and temporary outputs.
2. `semantic_path_match`
   Boost files whose path segments semantically align with the feature title and
   summary.
3. `page_content_match`
   For frontend pages, inspect page content for role-specific cues such as
   welcome-page text, login/verification copy, Garmin binding text, and profile
   completion prompts.
4. `onboarding_local_rerank`
   When multiple onboarding pages are likely candidates, re-rank only within
   that local page family to avoid disturbing global evidence quality.

## High-Ambiguity Page Families

Some page clusters are structurally similar and require extra disambiguation.
The onboarding flow is the current explicit case:

- `welcome.vue`
- `login.vue`
- `garmin-login.vue`
- `profile-basic.vue`
- `data-sync.vue`
- `sync-complete.vue`

These pages may all share overlapping terms such as onboarding, login, sync,
and profile. The workflow therefore allows page-local reranking and page
content analysis before finalizing `primary_refs`.

## Review Expectations

Review should block or warn when:

- a FEAT lacks `primary_refs`
- a FEAT lacks `evidence_layers`
- implementation or API evidence exists but `primary_refs` still lead with
  doc/test-only evidence
- a high-ambiguity page feature does not appear to use local rerank or page
  content matching

## Non-Goals

This workflow does not:

- derive downstream design or test artifacts
- guarantee perfect semantic matching for every page family
- replace human review for high-risk ambiguity
