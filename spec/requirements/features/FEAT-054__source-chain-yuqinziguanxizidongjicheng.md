---
id: FEAT-054
ssot_type: feat
title: Source Chain 与父子关系自动继承
status: draft
version: v1
parent_id: EPIC-003
derived_from_ids:
  - EPIC-003
source_refs:
  - SRC-001
  - ADR-006
owner: codex
tags: [workflow, traceability, ssot]
properties: {}
---

# Goal

让 `SRC -> EPIC -> FEAT` 链路中的 `source_refs`、`derived_from_ids` 和父子关系由 workflow 自动传递，减少人工拼装和关系漂移。

# Scope

- `src-to-epic` 自动继承 `SRC` 与 governing ADR 引用
- `epic-to-feat` 自动继承 `EPIC` 与上游 source chain
- formal object 输出统一携带足够的 trace refs
- 下游 UI / TECH / TASK / TESTSET 可继续沿用这套关系链

# Acceptance

- `EPIC` 自动带上 `SRC` 来源引用
- `FEAT` 自动带上 `EPIC` 父子关系与上游 source chain
- 人工手填关系字段需求显著减少

