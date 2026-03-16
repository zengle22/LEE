---
id: TASK-FEAT-087-002
ssot_type: task
title: 会话恢复 CLI 集成
status: frozen
version: v1
parent_id: FEAT-087
derived_from_ids: []
source_refs:
- FEAT-087#delivery
owner: null
tags: []
properties:
  contract_key: task_session_resume_cli
  identity_kind: ssot
frozen_at: '2026-03-11T16:23:57.966146'
---

# Objective

实现 `lee resume` 命令，支持从中断点恢复执行上下文。

# Description

实现恢复逻辑引擎，验证恢复后的执行连续性，并提供清晰的恢复入口。

## Acceptance Mapping

- FEAT-087 / AC-00403-001: 检查点恢复验证，系统从检查点恢复执行上下文
- FEAT-087 / AC-00403-002: 任务连续执行验证，任务从中断点继续

## Prerequisites

- TASK-FEAT-087-001

## Inputs

- 恢复请求
- 检查点数据

## Outputs

- 恢复提示 UI
- 继续执行入口

## Dependencies

- TASK-FEAT-087-001

## Definition Of Done

- `lee resume` 命令实现完成
- 恢复提示 UI 可用
- 恢复失败时有明确错误提示

## Observability

- Log Scope: session-resume-cli
- Audit Fields: run_id, resume_success

## Evidence Requirements

- Required Refs: TECH-FEAT-087
- Review Required: false

## Rollback Strategy

- Mode: revert
- Restore Targets: .workflow/workspace/wf_task_*/src/lee/cli/commands/resume.py
