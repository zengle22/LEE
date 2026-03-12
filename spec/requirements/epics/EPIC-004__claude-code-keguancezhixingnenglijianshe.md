---
id: EPIC-004
ssot_type: epic
title: Claude Code 可观测执行能力建设
status: frozen
version: v1
parent_id: null
derived_from_ids:
- SRC-004
source_refs:
- SRC-004
- ADR-004
owner: product
tags:
- product
- epic
- workflow
properties:
  priority: P0
  published_via_gate: true
frozen_at: '2026-03-11T15:41:56.117227'
---

# Problem
将 Claude Code executor 从黑盒执行模式改造为可观测的流式执行模式，使用户能够实时查看执行过程、判断执行状态、实现流式交互和会话恢复，同时确保运行日志、执行证据、会话事件和 CLI 展示的边界清晰定义。

# Scope
- 流式输出能力：实现 Claude Code 执行过程的流式输出，延迟控制在 500ms 以内
- 执行状态可视化：提供执行状态（运行中、卡死、完成、失败）的清晰判断依据
- 会话恢复能力：支持中断后会话恢复，无需从头开始
- 边界清晰化：明确分离运行日志、执行证据、会话事件和 CLI 展示的职责边界
- CLI 实时输出覆盖率需达到 90% 以上

# Non-Goals
- 不涉及 Gate 三分类逻辑 - 聚焦于执行能力本身，Gate 逻辑作为独立后续任务
- 不支持 CLI workflow-first 治理模式 - 保持现有工作流架构不变
- 不实现 TASK SSOT 统一管理 - 聚焦于可观测执行能力，不改变任务管理架构
- 不改造现有黑盒执行的所有功能 - 采用渐进式改造，优先解决核心痛点

# Success Criteria
- CLI 实时输出覆盖率达到 90% 以上
- 流式输出延迟控制在 500ms 以内
- 用户能够清晰判断执行状态（运行中/卡死/完成/失败）
- 支持会话中断后恢复，恢复后能够继续执行
- 运行日志、执行证据、会话事件、CLI 展示边界清晰可区分
