---
id: ADR-009
ssot_type: adr
title: workflow 同类互斥收敛到 SSOT 作用域
status: draft
version: v1
parent_id: null
derived_from_ids: []
source_refs:
- SRC-002
owner: governance
tags:
- workflow
- concurrency
- ssot
- architecture
properties: {}
---

# Decision

将 `lee run` 的并发互斥维度从“项目内同 `workflow_key`”升级为“同 `workflow_key` 且同 `concurrency_scope`”。

系统统一引入 `concurrency_scope` 概念，用来表达 workflow 正在占用的 SSOT 作用域。

默认规则：

- `product.src-to-epic` -> `project:{project_dir}`
- `product.epic-to-feat` -> `epic:{artifact_id}`
- 未来 `product.feat-to-tech` / `dev.feature_delivery_l2` -> `feat:{artifact_id}`
- 未来 `dev.bugfix_delivery_l2` -> `bug:{bug_id}` 或 `bugbatch:{batch_id}`

当关键输入缺失时，回退到保守作用域：

- `project:{project_dir}:workflow:{workflow_key}`

同时要求在 workflow 实例数据中写入：

- `concurrency_scope`
- `concurrency_key`
- `scope_source`

CLI 冲突提示也必须展示上述信息，明确说明为什么被拦截。

# Status

Accepted as implementation direction for the first rollout, with phase 1 limited to `product.epic-to-feat`.

# Context

现有并发模型只按 `workflow_key` 检测冲突，误伤了不同 SSOT 对象上的合法并发。

在 Product 与 Dev 主链逐步按 `SRC -> EPIC -> FEAT -> TECH -> Delivery` 收口后，并发边界应该跟随事实源对象，而不是继续绑定到项目级 workflow 分类。

如果继续维持旧模型：

- `EPIC` 拆分无法按对象并发
- `FEAT` 级交付无法自然扩展
- CLI 无法向用户解释拦截维度
- 运维和排障缺少实例级证据

# Consequences

正向结果：

- 同类 workflow 可在不同 SSOT 对象上并发运行
- 同一对象上的重复执行仍然会被阻止
- 并发冲突具备稳定的可观察字段
- 后续 Dev / QA 主链可复用同一套 scope 推导接口

代价与约束：

- `run.py` 需要从硬编码检测升级为统一 scope 推导与冲突查询
- 实例创建链路需要补写新的 data 字段
- 仍需重新评估 `run.lock` 这类项目级锁是否与新模型冲突

# Rollout

第一阶段：

- 只覆盖 `product.epic-to-feat`
- 从 `params.epic_freeze.artifact_id` 推导 `epic:{artifact_id}`
- 更新 CLI 冲突提示

第二阶段：

- 提取公共模块 `lee.orchestrator.execution.concurrency_scope`
- 所有 workflow 统一复用 scope / conflict key 推导
- 实例 data 统一写入观察字段

第三阶段：

- 扩展到 `feat` 级与 `bug` 级 workflow
- 支持 batch bug 的特殊作用域
