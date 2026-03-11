---
id: FEAT-052
ssot_type: feat
title: Workflow-First 高层命令入口
status: draft
version: v1
parent_id: EPIC-003
derived_from_ids:
  - EPIC-003
source_refs:
  - SRC-001
  - ADR-006
owner: codex
tags: [cli, workflow, product]
properties: {}
---

# Goal

为 `ADR / EPIC / FEAT` 提供 workflow-first 的高层入口或 alias，使用户默认通过 `lee` 高层命令触发正式治理链，而不是手工拼装底层关系字段。

# Scope

- 提供 `lee adr create`、`lee epic create`、`lee feat create` 或同等 alias
- 高层命令内部映射到 `lee run ...` workflow
- 高层入口默认收集 source、review、gate 所需上下文
- 不新增绕过 workflow 的“美化版 create”

# Acceptance

- 高层命令能路由到对应 workflow
- 普通用户无需直接调用 `ssot create`
- 高层入口与 workflow registry 保持一致

