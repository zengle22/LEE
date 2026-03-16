---
id: SRC-004
ssot_type: src
title: Claude Code 实时反馈与可观测执行能力
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs:
- ADR-004
owner: product
tags:
- claude-code
- cli
- executor
- observability
- streaming
properties: {}
frozen_at: '2026-03-12T00:20:48.0005842+08:00'
---

# Background

LEE 当前已经通过 `claude code executor` 接入 Claude Code，但整体执行体验仍偏黑盒。

用户在 `lee cli` 中发起执行后，通常只能等待最终结果返回，难以观察中间过程、定位卡点、判断是否需要中断或继续。这使得 Claude Code 虽然已经被接入流程，但其交互价值和可观测价值没有真正暴露出来。

# Problem Statement

当前实现存在四个直接问题：

- 执行过程不可见，用户无法判断 Claude Code 是正常运行、卡死还是已接近完成
- CLI 只有最终结果，没有稳定的实时输出通道，调试和排障成本高
- 缺少会话级恢复基础，一旦中断，往往只能重新执行
- 运行日志、执行证据、会话事件和 CLI 展示边界不清晰，后续扩展审批、resume、观测都缺少稳定基础

这会导致 Claude Code 在 LEE 中仍表现为“黑盒代理”，而不是“可实时理解和干预的受控执行器”。

# Target User

- LEE CLI 用户，需要实时看到 Claude Code 的执行输出和当前状态
- LEE 框架维护者，需要建立 Claude Code 可观测执行的统一能力底座
- 调试与集成用户，需要结构化输出和更稳定的执行证据

# Trigger Context

当用户在 `lee cli` 中调用涉及 Claude Code 的 workflow 时，希望能够像看受控任务执行流一样，实时看到 Claude Code 的输出、判断进度，并在后续具备继续对话、恢复会话、审批放行的能力。

当前黑盒返回模式无法支撑这种交互方式，因此需要把 Claude Code 执行链从“最终结果导向”升级为“过程可见导向”。

# Business Motivation

这条源需求的核心动机是把 LEE 中的 Claude Code 执行能力升级为可观测、可实时反馈、可逐步交互的执行模式。

具体收益包括：

- 提升 CLI 使用体验，降低等待期间的不确定感
- 提升调试效率，让执行证据在问题发生时即可可见
- 为后续 resume、审批、继续追问等能力建立协议和状态基础
- 明确日志、证据、事件、展示的职责边界，避免后续能力继续耦合在黑盒 executor 中

# Constraints

- 现有 executor / workflow 主链需要兼容迁移，不能一次性推翻
- 优先解决“看不到过程输出”和“缺少流式交互基础”两个核心痛点
- 运行日志、执行证据、会话事件、CLI 展示必须边界清晰
- 本轮能力建设应优先复用现有 `lee cli`、orchestrator、artifact 和 gate 基础设施

# Non-Goals

- 本轮不处理 Gate 三分类治理模型
- 本轮不处理 CLI workflow-first 治理入口设计
- 本轮不处理 TASK SSOT 治理体系扩展
- 本轮不要求一次性把 Claude Code 切换为完整双向协议交互系统

# Success Signals

- `lee cli` 能实时看到 Claude Code 的关键输出
- 执行状态可判断，至少能区分运行中、完成、失败、异常停滞
- 为会话恢复和继续交互预留稳定的状态与协议基础
- Claude Code 相关日志、证据、事件、展示边界得到正式定义
