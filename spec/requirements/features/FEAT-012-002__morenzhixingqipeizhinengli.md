---
id: FEAT-012-002
ssot_type: feat
title: 默认执行器配置能力
status: frozen
version: v1
parent_id: EPIC-012
derived_from_ids: []
source_refs:
- EPIC-012#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-12T22:32:02.112665'
---

# Goal

实现配置系统对默认 coding executor 的支持，允许用户通过配置文件设置默认执行器，简化日常使用流程
# User Value

用户可通过配置文件设置默认 coding executor，避免每次执行都需显式指定，提升使用效率，特别适合固定使用某一执行器的场景
# Inputs

- 配置文件路径与格式（支持 YAML/JSON）
- 配置项 `default_coding_executor` 的值
- 配置变更事件（文件修改检测）
# Processing

- 在 CLI 启动时加载配置文件
- 解析 `default_coding_executor` 配置项
- 校验配置值有效性（是否在支持列表中）
- 当 CLI 未指定 `--executor` 时，使用配置的默认执行器
- 监听配置变更事件（如文件修改），在下次执行时重新加载
# Outputs

- 生效的默认执行器配置值
- 配置加载状态与错误信息
- 配置变更生效通知
# Acceptance

- 配置系统支持 `default_coding_executor` 配置项（可选值包含 kimi、qwen 等）
- 配置读取逻辑在 CLI 启动时生效
- 当 CLI 未指定 `--executor` 参数时，自动使用配置的默认执行器
- 配置变更后无需重启即可在后续执行中生效
- 配置缺失或无效时提供降级策略和明确提示
# Acceptance Checks

## AC-012-002-01

- Scenario: 配置项读取与生效
- Given: 配置文件中设置 default_coding_executor 为 kimi
- When: CLI 启动且未指定 --executor 参数
- Then: 系统使用 kimi 作为执行器
- Trace Hints: TECH, TASK, TESTSET

## AC-012-002-02

- Scenario: 配置与 CLI 参数的优先级
- Given: 配置文件默认执行器为 qwen，CLI 未指定 --executor
- When: 执行器选择逻辑执行
- Then: 系统使用 qwen（配置文件生效）
- Trace Hints: TECH, TASK

## AC-012-002-03

- Scenario: 配置变更后生效
- Given: 用户修改配置文件将默认执行器从 claude 改为 kimi
- When: 下一次 CLI 执行启动时
- Then: 新配置生效，使用 kimi 执行器
- Trace Hints: TECH, TASK

## AC-012-002-04

- Scenario: 无效配置降级策略
- Given: 配置文件中 default_coding_executor 设置为不存在的执行器
- When: 配置加载与校验
- Then: 记录警告日志，使用系统预设执行器（如 claude），并提供明确提示
- Trace Hints: UI, TECH, TASK

## AC-012-002-05

- Scenario: 配置缺失处理
- Given: 配置文件不存在或未设置 default_coding_executor
- When: 配置加载
- Then: 使用系统预设默认执行器，不产生错误
- Trace Hints: TECH, TASK
# Dependencies

- EPIC-012
- FEAT-012-001
# Non Goals

- 不提供配置热重载实时生效能力（允许在下次执行时生效）
- 不提供配置校验的 UI 界面
- 不涉及多环境配置隔离
