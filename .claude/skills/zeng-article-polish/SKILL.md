---
name: zeng-article-polish
description: End-to-end article polishing pipeline for Chinese long-form writing. Use when the user wants one pass that first humanizes prose, then applies publish-ready layout, and finally adds necessary structural diagrams or placeholders. Best for Markdown article drafts that are already substantively complete and need finalization for publishing.
author: LEE Team
date: 2026-03-19
version: 1.0
codex_source_skill: zeng-article-polish
---

# Zeng Article Polish

Use this skill as a fixed three-stage finishing pass:

1. humanize the prose
2. apply publish-ready layout
3. add only diagrams that materially improve comprehension

Do not change the order unless the user explicitly asks for a different
pipeline.

## Goal

Take an article draft from content-complete-but-rough to ready-for-publication:

- first remove AI-writing artifacts
- then produce clean publishing layout
- finally add only the diagrams that materially improve comprehension

This skill is for finalizing an article, not inventing its core argument from
scratch.

## Entry Conditions

Use this skill when:

- the input is a Chinese article draft, usually `.md`
- the author wants a full finishing pass rather than one isolated edit
- the article already has its main argument and structure

Do not use this skill if:

- the article is still missing core sections
- the user wants only one step
- the task is mostly factual rewriting or deep content restructuring

## Pipeline

### Step 1. Humanize

Goals:

- remove AI flavor
- preserve meaning and stance
- keep the author's tone

At this stage, you may:

- tighten wording
- vary rhythm
- replace vague AI phrasing with direct statements
- reduce terminology density when the draft leans too heavily on internal
  jargon, framework labels, or stacked abstractions

At this stage, you must not:

- change the article's thesis
- change factual claims without reason
- add layout wrappers or diagram instructions

### Step 2. Layout

Goals:

- improve heading rhythm
- normalize lists, quotes, and code blocks
- make the article readable in publishing contexts

At this stage, you may:

- split visually overloaded sections when the paragraph boundaries are already
  implied
- convert raw Markdown structure into cleaner final Markdown or HTML

At this stage, you must not:

- re-edit the article's core argument unless layout requires a minimal
  mechanical fix
- inject diagrams yet

### Step 3. Diagram Insert

Goals:

- identify the few sections that truly need diagrams
- generate Mermaid and optional image assets
- insert clear placeholders or references for publishing

At this stage, you may:

- add diagrams for workflows, layered models, gates, and object relationships

At this stage, you must not:

- add diagrams just because a heading looks abstract
- overload the article with visuals
- use diagrams to compensate for unresolved writing problems

## Output Pattern

Structure the work around:

1. `Input State`
2. `Humanize Pass`
3. `Layout Pass`
4. `Diagram Decisions`
5. `Final Output`

## Guardrails

- Do not silently add new arguments to the article.
- Do not turn the article into generic platform-style prose.
- Do not add diagrams unless they improve comprehension.
- If the draft is structurally incomplete, stop and say so instead of faking a
  polish pass.
