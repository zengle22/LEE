---
id: EPIC-003
ssot_type: epic
title: LEE CLI Workflow-First 治理入口重构
status: frozen
version: v1
parent_id: null
derived_from_ids:
  - SRC-001
source_refs:
  - SRC-001#scope
  - ADR-006
owner: product
tags: [cli, workflow, governance, ssot]
properties: {}
frozen_at: '2026-03-13T01:20:00'
---

# Problem

LEE 当前同时暴露 workflow 主入口和 `ssot create` 直写入口，导致普通用户可以绕过 review、gate、freeze 与 source chain 约束，直接生成正式 SSOT 对象。

# Goal

将 LEE CLI 重构为 workflow-first 的治理入口体系，明确高层命令负责业务治理，低层 SSOT 原语只负责对象物化与维护。

# Scope

- 将 `ssot create` 降级为 internal/admin/maintenance 命令
- 为 `ADR / EPIC / FEAT` 提供 workflow-first 高层入口或 alias
- 将 formal object 的编号、父子关系和 source refs 绑定到 workflow / freeze / approval 边界
- 统一 CLI help、文档、demo 与测试叙事
- 保持 workflow template 与 runtime instance 的边界清晰

# Non-Goals

- 不在本 EPIC 中一次性删除全部历史命令和旧文档
- 不在本 EPIC 中重做全部 runtime 存储实现
- 不把 `ADR` 直接当作业务主链 source object

# Success Criteria

- 普通用户默认从 workflow-first 入口生成 `ADR / EPIC / FEAT`
- `ssot create` 不再被视为推荐主入口
- formal object 的 `source_refs`、`parent_id`、`derived_from_ids` 能由 workflow 自动继承
- CLI 文档、帮助文案与测试叙事统一收敛到同一治理模型

