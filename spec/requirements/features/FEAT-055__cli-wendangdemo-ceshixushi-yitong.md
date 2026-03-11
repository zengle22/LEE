---
id: FEAT-055
ssot_type: feat
title: CLI 文档 Demo 测试叙事统一
status: draft
version: v1
parent_id: EPIC-003
derived_from_ids:
  - EPIC-003
source_refs:
  - SRC-001
  - ADR-006
owner: codex
tags: [cli, docs, tests]
properties: {}
---

# Goal

统一 CLI help、用户文档、demo 与测试中的命令叙事，使仓库公开表达的推荐路径与 workflow-first 治理模型一致。

# Scope

- CLI help 文案更新
- 用户文档与示例命令更新
- demo 场景从 `ssot create` 迁移到高层入口或 `lee run`
- 测试叙事与断言同步收敛

# Acceptance

- 文档与帮助文本默认推荐 workflow-first 入口
- demo 不再把 `ssot create` 当主入口
- 测试能覆盖新的推荐命令路径

