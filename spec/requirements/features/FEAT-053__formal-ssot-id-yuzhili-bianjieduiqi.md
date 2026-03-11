---
id: FEAT-053
ssot_type: feat
title: Formal SSOT 编号与治理边界对齐
status: draft
version: v1
parent_id: EPIC-003
derived_from_ids:
  - EPIC-003
source_refs:
  - SRC-001
  - ADR-006
owner: codex
tags: [ssot, id, freeze, approval]
properties: {}
---

# Goal

将 formal SSOT 的 ID 分配与 review / freeze / approval 边界对齐，避免普通用户绕过治理链提前占用正式编号。

# Scope

- candidate 阶段不抢占正式 SSOT ID
- formal object 只在允许的 freeze / approval 边界生成
- `parent_id`、`derived_from_ids`、`source_refs` 由 workflow 上下文自动继承
- 编号冲突优先通过 workflow 约束而不是人工修复消除

# Acceptance

- 正式编号不再由普通用户手工抢占
- formal object 的父子关系与 source chain 自动对齐
- workflow 能追溯 formal object 的生成边界

