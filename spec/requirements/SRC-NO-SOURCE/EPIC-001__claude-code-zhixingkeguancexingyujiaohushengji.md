---
id: EPIC-001
ssot_type: epic
title: Claude Code 执行可观测性与交互升级
status: draft
version: v1
parent_id: null
derived_from_ids: []
source_refs:
- ADR-004
owner: codex
tags: []
properties: {}
---

# Claude Code 执行可观测性与交互升级

## Summary

把 LEE 中 `claude_code` 执行器从“结果可见、过程不可见”的黑盒执行，收敛为可实时观测、可渐进升级到流式交互协议的实现路径。

## Governing ADR

- `ADR-004`

## Scope

- 暴露 Claude Code 执行期间的实时输出到 `lee cli`
- 统一 live log 作为 CLI/runner 可消费的结构化执行证据
- 为后续切换 `stream-json` 协议保留演进边界

## Non-Goals

- 本阶段不引入新的并行执行器
- 本阶段不直接迁移 Rust runtime 模块
- 本阶段不一次性完成审批协议与前端事件总线

## Child Features

- `FEAT-026`
- `FEAT-027`

## Acceptance Direction

- 使用 `lee run` 或等价 CLI 路径执行 `claude_code` 步骤时，用户可以看到持续输出
- 执行证据路径可被 runner/CLI 稳定定位，而不是依赖人工猜测
- 后续协议升级不会要求替换整个 executor 路径
