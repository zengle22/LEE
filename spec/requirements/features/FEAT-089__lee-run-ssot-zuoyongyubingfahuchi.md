---
id: FEAT-089
ssot_type: feat
title: lee run SSOT 作用域并发互斥
status: draft
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- SRC-002
- ADR-009
owner: codex
tags:
- cli
- workflow
- concurrency
- ssot
properties: {}
---

# Goal

将 `lee run` 的同类 workflow 互斥从项目级 `workflow_key` 收敛到 SSOT 作用域级别，避免不同对象上的合法并发被错误拦截。

# Scope

- 为 `lee run` 引入 `concurrency_scope` 与 `concurrency_key`
- 第一阶段覆盖 `product.epic-to-feat`
- 同一 `workflow_key + concurrency_scope` 冲突时拦截
- 缺少关键输入时回退到保守项目级互斥
- 将作用域信息写入 `workflow_instances.data`
- CLI 冲突提示展示 `workflow_key` 与 `concurrency_scope`

# Acceptance

- 两个不同 `EPIC` 的 `product.epic-to-feat` 可并发启动
- 同一 `EPIC` 的重复 `product.epic-to-feat` 会冲突
- 冲突提示包含 `concurrency_scope`
- 实例数据包含 `concurrency_scope`、`concurrency_key`、`scope_source`
