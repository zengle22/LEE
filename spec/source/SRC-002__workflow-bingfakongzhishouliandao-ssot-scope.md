---
id: SRC-002
ssot_type: src
title: workflow 并发控制收敛到 SSOT scope
status: draft
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: governance
tags:
- workflow
- concurrency
- ssot
- product
properties: {}
---

# Background

当前 `lee run` 的并发控制按项目目录内的 `workflow_key` 做粗粒度互斥。

这会把不同 SSOT 对象上的合法并发一起拦住，尤其是：

- 不同 `EPIC` 并行执行 `product.epic-to-feat`
- 不同 `FEAT` 并行执行下游设计与交付 workflow

# Problem Statement

当前互斥规则把“同类 workflow”误等同于“同一事实源对象上的同类 workflow”。

这导致：

- 不同 `EPIC` 的需求分解被错误串行化
- 不同 `FEAT` 的交付链无法按对象粒度并发
- CLI 冲突提示只展示 `workflow_key`，用户无法判断被哪个对象维度拦截
- `workflow_instances` 中缺少可观察的并发作用域字段，排障成本高

# Target User

- 使用 `lee run` 启动产品与开发主链 workflow 的操作者
- 维护 workflow 编排、实例持久化与冲突检测逻辑的开发者
- 需要定位并发拦截原因的治理与运维角色

# Trigger Context

随着 Product 与 Dev 主链逐步转向 SSOT 驱动，单纯按项目级 `workflow_key` 互斥已经无法表达真实并发边界。

`product.epic-to-feat`、未来的 `dev.feature_delivery_l2`、`dev.bugfix_delivery_l2` 都需要围绕各自 SSOT 对象收敛互斥，而不是全项目全局互斥。

# Business Motivation

如果不把并发控制升级到 SSOT scope：

- 需求分解和交付吞吐会被人为压低
- 用户会持续误判系统“卡住”或“只能串行工作”
- 后续 Dev / QA 主链扩展会继续复制旧的错误互斥模型
- 冲突定位无法形成稳定的 UI 和运维解释语义

# Constraints

- 同一 SSOT 对象上的同类 workflow 仍需互斥
- 不同 SSOT 对象上的同类 workflow 应允许并发
- 缺少足够输入时必须回退到保守的旧策略，避免漏拦截
- 冲突检测结果必须可观察、可解释、可写入实例数据
- 第一阶段优先覆盖 `product.epic-to-feat`

# Non-Goals

- 本轮不直接完成所有 Dev / QA workflow 的 scope 规则覆盖
- 本轮不取消全部项目级串行约束以外的其他保护机制
- 本轮不重做全部实例存储模型或 UI

# Success Criteria

- 两个不同 `EPIC` 的 `product.epic-to-feat` 可并发启动
- 同一个 `EPIC` 的两个 `product.epic-to-feat` 仍会被识别为冲突
- `lee run` 冲突提示展示 `workflow_key` 与 `concurrency_scope`
- `workflow_instances.data` 中包含 `concurrency_scope`、`concurrency_key`、`scope_source`
- 缺失 `artifact_id` 时自动回退到保守互斥策略
