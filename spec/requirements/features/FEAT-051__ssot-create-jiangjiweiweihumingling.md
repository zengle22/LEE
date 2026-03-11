---
id: FEAT-051
ssot_type: feat
title: ssot create 降级为维护命令
status: draft
version: v1
parent_id: EPIC-003
derived_from_ids:
  - EPIC-003
source_refs:
  - SRC-001
  - ADR-006
owner: codex
tags: [cli, ssot, governance]
properties: {}
---

# Goal

将 `lee ssot create` 从面向普通用户的创建入口降级为 internal/admin/maintenance 命令，只保留调试、修复、补录与 registry 维护用途。

# Scope

- CLI help 与命令说明中标注 internal/admin/maintenance
- 文档与 demo 不再把 `ssot create` 作为推荐主入口
- 与 `rebuild-registry`、`sync` 一起归类为系统维护命令
- 不改变其底层 materialize 能力

# Acceptance

- `ssot create` 明确被标识为维护命令
- 用户文档不再推荐用它创建日常业务对象
- 维护场景仍可使用该命令完成落盘和修复
