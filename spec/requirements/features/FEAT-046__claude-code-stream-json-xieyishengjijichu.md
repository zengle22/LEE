---
id: FEAT-046
ssot_type: feat
title: Claude Code stream-json 协议升级基础
status: draft
version: v1
derived_from_ids: []
source_refs:
- EPIC-001
- ADR-004
owner: codex
tags: []
properties: {}
---

# Claude Code stream-json 协议升级基础

## Upstream EPIC

- `EPIC-001`

## Governing ADR

- `ADR-004`

## Summary

为 LEE 的 `ClaudeCodeExecutor` 建立从 `--print --output-format json` 向 `stream-json` 双向协议模式演进的基础，使后续能够支持增量消息、会话恢复与交互控制。

## Scope

- 梳理并抽象当前 subprocess/stdout/stderr 采集层
- 定义 Python 侧轻量协议桥接边界
- 保留与现有 runner 返回结构的兼容性

## Inputs

- Claude CLI stdout/stderr
- prompt/system prompt
- session context

## Outputs

- 可演进的协议桥接层设计
- 与现有执行器兼容的流式消息处理入口

## Business Rules

- 不直接引入 Rust 模块运行时依赖
- 切换协议前必须保留现有 evidence/debug 能力
- follow-up / approval / interrupt 应基于统一协议层扩展

## Acceptance Criteria

- AC-001 当前 `ClaudeCodeExecutor` 的进程管理与日志采集可以与协议层解耦
- AC-002 未来切换到 `stream-json` 时，不需要新建 `claude_code_executor_v2`
- AC-003 协议升级方案与现有 runner 输出契约保持兼容
