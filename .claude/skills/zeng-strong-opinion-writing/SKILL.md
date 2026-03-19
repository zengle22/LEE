---
name: zeng-strong-opinion-writing
description: Draft Chinese long-form opinion articles with a strong thesis, high传播性, memorable phrasing, historical or cross-era analogies, and researched industry context. Use when the user wants a 公众号长文、评论文、行业观察或方法论文章 to become more forceful, more readable, more shareable, or explicitly asks for 强观点、历史类比、全景介绍、行业共识、先检索再写、金句、冲击力开头.
author: LEE Team
date: 2026-03-19
version: 1.0
codex_source_skill: zeng-strong-opinion-writing
---

# Zeng Strong Opinion Writing

Use this skill to write Chinese long-form opinion articles that are easy to
spread, easy to remember, and still anchored in enough real-world context to
feel credible.

Do not treat it as a pure fact-reporting skill. This skill is for
viewpoint-led writing with a clear thesis, controlled rhetoric, and a
research-backed opening frame.

## Core Principle

Write articles that feel like this:

- a hard claim up front
- a concrete present-day problem
- a larger historical or structural mirror
- a clean explanatory model
- a firm ending that tells the reader what the change means

The target is not neutral completeness.

The target is:

- strong viewpoint
- strong structure
- strong memorability
- enough evidence to hold the piece up

## Workflow

### 1. Lock the thesis first

Before drafting, reduce the article to one hard claim.

Use a sentence that sounds like a position, not a topic.

Good examples:

- `SSOT 管的不是文档数量，而是系统的指挥权。`
- `AI 工程最后会收敛的，不是更长的 prompt，而是更硬的控制结构。`
- `看起来是测试问题，实际是对象链断了。`

If the user gives a broad subject, convert it into:

- what is misunderstood
- what the article will argue instead

### 2. Build a reader entry layer

Before introducing your own system, give the reader a way in.

Choose one or more:

- a one-paragraph concept explanation
- a current concrete scene
- a common industry misunderstanding
- a short background section showing existing methods or consensus

Explain the problem in plain language first. Introduce the term second.

### 3. Research before claiming consensus

When the article mentions industry common practice, mainstream method, public
guidance, well-known framework, or recent product/company behavior, browse the
web first.

Prioritize:

- official documentation
- official engineering blogs
- standards bodies
- research institutions
- established vendors with primary documentation

Use browsing especially for:

- definitions such as `SSOT`, `ADR`, traceability, evaluation, governance
- recent company practices
- numbers, adoption claims, or market trends
- quotations

### 4. Build one historical mirror

Use historical or cross-era analogy to increase force and readability.

The analogy is for illumination, not proof.

Rules:

- choose a case with a mechanism that resembles the current problem
- explain the common mechanism clearly
- do not over-extend the analogy

### 5. Write for shareability, not slogans alone

Use:

- short punchy lines at section openings or endings
- one or two repeatable framing sentences
- a small number of quotable claims

Do not:

- turn every paragraph into a slogan
- use empty intensity with no model underneath

### 6. End with consequence

The ending should not merely summarize.

It should answer:

- what changes if this argument is true
- what readers should stop believing
- what system direction becomes clearer

## Output Pattern

Structure the work around:

1. `Thesis`
2. `Reader Entry`
3. `Evidence and Context`
4. `Historical Mirror`
5. `Article Draft`

## Guardrails

- Do not flatten the article into neutral consultant prose.
- Do not fake consensus claims without checking.
- Do not bury the thesis until the middle.
- Do not use historical analogy as a substitute for actual reasoning.
