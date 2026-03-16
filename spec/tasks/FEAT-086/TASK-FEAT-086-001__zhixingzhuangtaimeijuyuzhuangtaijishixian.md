---
id: TASK-FEAT-086-001
ssot_type: task
title: 执行状态枚举与状态机实现
status: frozen
version: v1
parent_id: FEAT-086
derived_from_ids: []
source_refs:
- FEAT-086#delivery
owner: null
tags: []
properties:
  contract_key: task_state_machine
  identity_kind: ssot
frozen_at: '2026-03-11T16:23:57.951061'
---

# Objective

定义并实现状态枚举（运行中/卡死/完成/失败）及状态转换规则引擎。

# Description

使用枚举定义四种执行状态，建立心跳检测机制，实现超时判断逻辑，并记录状态变更事件。

## Acceptance Mapping

- FEAT-086 / AC-00402-001: 状态枚举定义验证，返回明确的状态枚举值（运行中/卡死/完成/失败）
- FEAT-086 / AC-00402-002: 状态转换规则验证，状态按预设规则正确转换
- FEAT-086 / AC-00402-003: 状态事件可查询验证，返回按时间排序的状态变更事件列表

## Prerequisites

- TECH-EPIC-004-状态检测架构设计冻结

## Inputs

- 进程心跳信号
- 进程状态查询接口
- 超时配置参数

## Outputs

- 当前执行状态展示
- 状态变更事件日志
- 状态判断依据数据

## Dependencies

- TASK-FEAT-085-001

## Definition Of Done

- StateDetector 核心类实现完成
- 状态枚举定义完成
- 状态转换规则引擎实现
- 心跳检测机制可用
- 30s 超时默认值生效

## Observability

- Log Scope: state-detection
- Audit Fields: run_id, state_transitions, event_log

## Evidence Requirements

- Required Refs: TECH-FEAT-086, UI-FEAT-086
- Review Required: true

## Rollback Strategy

- Mode: revert
- Restore Targets: .workflow/workspace/wf_task_*/src/lee/executor/state
