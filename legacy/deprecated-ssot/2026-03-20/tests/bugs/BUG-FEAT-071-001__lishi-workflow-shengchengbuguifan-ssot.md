---
id: BUG-FEAT-071-001
ssot_type: bug
title: 历史 workflow 生成不合规 SSOT 文件
status: active
version: v1
parent_id: FEAT-071
derived_from_ids:
  - FEAT-071
source_refs:
  - FEAT-071#scope
owner: codex
tags:
  - ssot
  - governance
  - cleanup
properties:
  severity: high
  source_report_id: REPORT-FEAT-071-20260311
  bug_state: open
  symptom_scope:
    - duplicate_ssot_ids
    - invalid_parent_id
    - invalid_source_refs
    - root_level_misplacement
---

# Problem

历史 workflow / script 在多个阶段产出了不符合当前 SSOT 规范的正式文件，包括重复 ID、错误 parent_id、错误 source_refs，以及落到错误目录的正式对象。

# Observed Symptoms

- `spec/requirements/` 根目录出现平铺的 `EPIC-*.md` / `FEAT-*.md`
- `spec/requirements/epics/` 与 `spec/requirements/features/` 中出现重复 SSOT ID
- 部分 `TASK` 和 `FEAT` 的 `source_refs` 指向不存在对象
- 部分 `FEAT` 的 `parent_id` 不是合法 `EPIC`

# Why This Matters

这些错误会直接污染 registry、破坏审计链，并让后续 AI 执行/回滚/观测建立在错误的正式对象上。

# Follow-up

- 追踪是哪条 workflow / script / legacy materializer 生成了这些不合规文件
- 给对应生成链补 provenance 与防重校验
- 将 `ssot lint` 纳入日常自动巡检
