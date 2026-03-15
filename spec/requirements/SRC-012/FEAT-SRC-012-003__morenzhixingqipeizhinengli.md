---
id: FEAT-SRC-012-003
ssot_type: feat
title: 默认执行器配置能力
status: frozen
version: v1
parent_id: EPIC-SRC-012
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
frozen_at: '2026-03-13T00:44:58.057228'
---

# Goal

实现用户将 Kimi 设置为默认 coding executor 的配置能力，简化日常使用流程
# User Value

用户可以将 Kimi 设置为默认 coding executor，无需每次显式指定，简化日常使用流程
# Inputs

- user_preference_config
- default_executor_setting
- config_persistence_layer
# Processing

- 读取用户默认执行器配置
- 验证配置的执行器已在 registry 中注册
- 持久化用户默认执行器偏好设置
- 当无显式 --executor 参数时，使用默认执行器
- 配置变更即时生效（无需重启）
# Outputs

- persisted_default_executor_config
- config_change_confirmation
- fallback_executor_resolution
# Acceptance

- 配置默认执行器为 kimi 后，无显式参数的任务自动使用 Kimi
- 配置持久化与读取正常工作
- 配置变更即时生效
# Acceptance Checks

## AC-SRC-012-003-01

- Scenario: 默认执行器配置生效
- Given: 用户已将默认执行器设置为 kimi
- When: 发起无 --executor 参数的任务
- Then: 任务自动由 Kimi 执行器处理
- Trace Hints: UI, TECH, TASK

## AC-SRC-012-003-02

- Scenario: 配置持久化验证
- Given: 用户修改默认执行器配置
- When: 配置保存后重新加载
- Then: 配置值保持一致且可读取
- Trace Hints: TECH, TESTSET

## AC-SRC-012-003-03

- Scenario: 配置变更即时生效
- Given: 系统正在运行
- When: 用户修改默认执行器配置
- Then: 新配置在下一个任务立即生效，无需重启
- Trace Hints: TECH, TESTSET
# Dependencies

- EPIC-SRC-012
- FEAT-SRC-012-001
# Non Goals

- 用户显式指定执行器的能力（已由其他 FEAT 覆盖）
- 远端配置同步
- 多用户配置隔离
