---
id: FEAT-170
ssot_type: feat
title: 执行器工厂可按配置创建可用的 qwen cli 执行器实例
status: frozen
version: v1
parent_id: EPIC-022
derived_from_ids: []
source_refs:
- EPIC-022#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-12T22:26:15.239944'
---

# Goal

执行器工厂能够基于配置创建 qwen cli 执行器实例
# User Value

系统能够动态实例化 qwen 执行器
# Inputs

- validated_executor_config
# Processing

- 检查 executor_type
- 初始化 qwen cli 客户端
- 验证实例可用性
- 返回执行器实例
# Outputs

- executor_instance
# Acceptance

- 工厂能基于 qwen 配置创建实例
- 实例符合统一执行器接口
- 实例化失败时返回可定位错误
# Acceptance Checks

## AC-001

- Scenario: 工厂创建 qwen 实例
- Given: 配置 valid_executor_config
- When: 调用工厂创建方法
- Then: 返回 qwen 执行器实例
- Trace Hints: TECH, TESTSET

## AC-002

- Scenario: 实例接口合规
- Given: 实例已创建
- When: 调用标准接口方法
- Then: 方法签名与现有执行器一致
- Trace Hints: TECH, TASK
# Dependencies

- EPIC-022
- FEAT-022-001
# Non Goals

- 不替换现有执行器
- 不新增平行 workflow
