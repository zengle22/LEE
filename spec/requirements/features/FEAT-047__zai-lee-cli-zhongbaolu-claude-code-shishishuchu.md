---
id: FEAT-047
ssot_type: feat
title: 在 LEE CLI 中暴露 Claude Code 实时输出
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

# 在 LEE CLI 中暴露 Claude Code 实时输出

## Upstream EPIC

- `EPIC-001`

## Governing ADR

- `ADR-004`

## Summary

让 `lee run` / `lee watch` 在执行 `claude_code` 与同类代码代理步骤时，能够跟随并显示执行过程中的实时输出，而不是只显示工作流状态。

## Scope

- 复用现有 `conversation.live.log`
- 把 live log 路径提升为上层可稳定消费的字段
- 在 CLI 中增加实时 tail/跟随显示

## Inputs

- workflow execution id
- 当前运行 step
- evidence/live log path

## Outputs

- CLI 实时输出流
- 稳定的 live log 路径暴露

## Business Rules

- 不新增平行 executor
- 终端输出必须可中断、可清理、避免重复刷屏
- 失败时仍保留原有 evidence 路径与错误返回

## Acceptance Criteria

- AC-001 运行 `claude_code` 步骤时，CLI 能持续显示新增日志行
- AC-002 执行完成或失败后，日志跟随线程能正确停止
- AC-003 没有 live log 时，CLI 退化为现有状态显示，不阻断工作流
