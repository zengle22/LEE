---
id: TASK-FEAT-087-001
ssot_type: task
title: 会话持久化存储层实现
status: frozen
version: v1
parent_id: FEAT-087
derived_from_ids: []
source_refs:
- FEAT-087#delivery
owner: null
tags: []
properties:
  contract_key: task_session_persistence
  identity_kind: ssot
frozen_at: '2026-03-11T16:23:57.958188'
---

# Objective

实现 JSON 文件和 SQLite 双轨持久化机制，支持检查点创建和状态恢复。

# Description

使用 JSON 文件存储可读状态快照，使用 SQLite 存储结构化事件，建立会话状态的持久化和恢复机制。

## Acceptance Mapping

- FEAT-087 / AC-00403-001: 检查点恢复验证，系统从检查点恢复执行上下文
- FEAT-087 / AC-00403-002: 任务连续执行验证，任务从中断点继续，不重复执行已完成部分
- FEAT-087 / AC-00403-003: 会话状态持久化验证，返回完整的会话状态快照

## Prerequisites

- TECH-EPIC-004-会话持久化架构设计冻结

## Inputs

- 检查点数据
- 会话状态快照
- 恢复请求

## Outputs

- 恢复后的执行上下文
- 剩余任务列表
- 会话状态持久化数据

## Dependencies

- TASK-FEAT-086-001

## Definition Of Done

- SessionManager 核心类实现完成
- JSON 持久化层实现完成
- SQLite 事件存储实现完成
- 检查点创建机制可用
- 恢复逻辑引擎实现完成

## Observability

- Log Scope: session-persistence
- Audit Fields: run_id, checkpoint_id, restored_state

## Evidence Requirements

- Required Refs: TECH-FEAT-087, UI-FEAT-087
- Review Required: true

## Rollback Strategy

- Mode: revert
- Restore Targets: .workflow/workspace/wf_task_*/src/lee/session
