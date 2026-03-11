---
id: FEAT-086
ssot_type: feat
title: 执行状态可视化
status: frozen
version: v1
parent_id: EPIC-004
derived_from_ids: []
source_refs:
- EPIC-004#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-11T16:07:19.709616'
---

# Goal

提供可程序化判断的执行状态指示器，使用户能够清晰判断 Claude Code 当前执行状态
# User Value

用户能够清晰判断 Claude Code 当前执行状态（运行中、卡死、完成、失败），便于决定下一步操作和及时干预异常情况
# Inputs

- 命令执行状态事件
- 输出时间戳
- 执行上下文
# Processing

- 监听命令执行状态变化
- 检测运行中状态（执行启动后至结束前）
- 检测卡死状态（超时阈值内无输出）
- 检测完成状态（正常执行结束信号）
- 检测失败状态（异常终止信号）
- 通过 CLI 展示当前状态
# Outputs

- 执行状态指示器（状态码/状态文件/事件）
- 实时状态展示
# Acceptance

- 提供可程序化判断的执行状态指示器（状态码/状态文件/事件）
- 运行中状态：执行启动后至结束前的持续状态，有明确的活动指示
- 卡死状态：可检测的长时无响应场景，需定义超时阈值（如 30s 无输出）
- 完成状态：正常执行结束，有明确的完成信号
- 失败状态：执行异常终止，有明确的错误信息输出
# Acceptance Checks

## AC-002-001

- Scenario: 状态指示器可用性
- Given: Claude Code 正在执行命令
- When: 用户查询执行状态
- Then: 系统返回可程序化判断的状态信息
- Trace Hints: UI, TECH, TESTSET

## AC-002-002

- Scenario: 运行中状态识别
- Given: 命令正在执行
- When: 系统检测执行状态
- Then: 状态显示为运行中，有明确的活动指示
- Trace Hints: UI, TECH, TESTSET

## AC-002-003

- Scenario: 卡死状态检测
- Given: 命令执行超过 30s 无输出
- When: 系统检测输出超时
- Then: 状态显示为卡死，提供超时提示
- Trace Hints: UI, TECH, TESTSET

## AC-002-004

- Scenario: 完成状态识别
- Given: 命令正常执行结束
- When: 系统检测完成信号
- Then: 状态显示为完成，提供完成信息
- Trace Hints: UI, TECH, TESTSET

## AC-002-005

- Scenario: 失败状态识别
- Given: 命令异常终止
- When: 系统检测异常信号
- Then: 状态显示为失败，提供错误信息
- Trace Hints: UI, TECH, TESTSET
# Dependencies

- FEAT-004-001
# Non Goals

- 不涉及 Gate 三分类逻辑
- 不自动执行干预操作，仅提供状态判断依据
