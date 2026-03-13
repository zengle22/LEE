---
id: FEAT-SRC-012-002
ssot_type: feat
title: 显式指定 Kimi 执行器能力
status: frozen
version: v1
parent_id: EPIC-SRC-012
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-13T00:44:58.041996'
---

# Goal

实现用户通过 --executor kimi 参数显式选择 Kimi 执行器执行编码任务的能力
# User Value

用户可以通过 `--executor kimi` 参数显式选择 Kimi 执行器执行编码任务，获得与 Claude Code 执行器同等的显式调用体验
# Inputs

- cli_arguments
- executor_selector
- task_context
# Processing

- 解析命令行参数 --executor kimi
- 根据 executor_type 路由到对应执行器
- 验证 Kimi 执行器已注册且可用
- 记录执行器选择信息到任务上下文
- 触发 Kimi 执行器执行编码任务
# Outputs

- executor_selection_record
- task_execution_result
- execution_logs
# Acceptance

- 用户可通过 --executor kimi 参数成功触发 Kimi 执行器完成编码任务
- 命令行参数解析与路由正常工作
- 执行器选择信息被正确记录
# Acceptance Checks

## AC-SRC-012-002-01

- Scenario: 显式指定 Kimi 执行器执行任务
- Given: 用户输入包含 --executor kimi 参数
- When: 系统解析参数并路由任务
- Then: 任务由 Kimi 执行器处理并返回结果
- Trace Hints: UI, TECH, TASK

## AC-SRC-012-002-02

- Scenario: 命令行参数解析正确
- Given: 用户提供有效的 --executor 参数
- When: 参数解析器处理输入
- Then: 正确识别 executor_type 为 kimi
- Trace Hints: TECH, TESTSET

## AC-SRC-012-002-03

- Scenario: 执行器选择信息记录
- Given: 任务已分配 Kimi 执行器
- When: 任务执行完成
- Then: 执行日志中包含 executor_type=kimi 记录
- Trace Hints: TECH, TESTSET
# Dependencies

- EPIC-SRC-012
- FEAT-SRC-012-001
# Non Goals

- 配置系统默认执行器
- 执行器切换时的上下文保持
- 输出格式兼容层实现
