---
id: TASK-FEAT-090-002
ssot_type: task
title: 正式 ID rewrite 与 lint gate 集成
status: active
version: v1
parent_id: FEAT-090
derived_from_ids: []
source_refs:
- FEAT-090#delivery
- ADR-013
owner: null
tags:
- cli
- ssot
- id
- governance
properties: {}
---

# 正式 ID rewrite 与 lint gate 集成

- 实现从临时 ID 到正式 ID 的批量重写逻辑
- 覆盖文件名、front matter `id`、`parent_id`、`derived_from_ids`、`source_refs`、`related_ids`、`implements`、`verifies`
- 将 rewrite 后的一致性校验接入 `ssot lint`、git hook 或等效 gate
- 阻止重复正式 ID 与未 formalize 的临时 ID 进入主线
- 为最小 happy path 和冲突 path 补充自动化测试
