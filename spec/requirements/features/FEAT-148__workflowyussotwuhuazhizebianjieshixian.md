---
id: FEAT-148
ssot_type: feat
title: workflow与SSOT物化职责边界实现
status: frozen
version: v1
parent_id: EPIC-017
derived_from_ids: []
source_refs:
- EPIC-017#scope
owner: null
tags: []
properties:
  contract_key: feat_004
  identity_kind: ssot
frozen_at: '2026-03-12T20:17:54.601950'
---

# Goal

实现治理链执行与最终物化的职责分离，workflow专注于治理流程执行，SSOT原语专注于数据持久化
# User Value

治理链执行与最终物化职责分离，workflow专注于治理流程，SSOT原语专注于数据持久化
# Inputs

- workflow模块核心实现
- SSOT模块核心实现
- 两模块间接口契约
- 治理状态机定义
# Processing

- 梳理workflow模块现有职责，提取治理流程相关逻辑
- 梳理SSOT模块现有职责，提取物化原语相关逻辑
- 设计清晰的模块间接口，定义workflow调用SSOT的时机和方式
- 实现workflow的gate状态流转、review流程执行功能
- 重构SSOT模块，仅在被workflow调用时执行物化
# Outputs

- 模块职责边界定义文档
- 重构后的workflow模块
- 重构后的SSOT模块
- 模块间接口实现
- 职责边界验证测试套件
# Acceptance

- workflow模块负责gate状态流转、review流程执行
- SSOT模块仅在被workflow调用时执行物化
- 两模块间通过明确接口交互
- 验收时验证：workflow可在不直接操作存储的情况下完成治理流程
- 物化操作仅由SSOT模块执行
# Acceptance Checks

## AC-017-004-01

- Scenario: workflow独立执行治理流程
- Given: workflow模块配置正确
- When: 执行完整的review/gate/freeze流程
- Then: workflow完成状态流转且不直接操作storage
- Trace Hints: TECH, TASK, TESTSET

## AC-017-004-02

- Scenario: SSOT仅受控物化
- Given: workflow完成gate验证
- When: workflow调用SSOT物化接口
- Then: SSOT执行物化操作并返回结果给workflow
- Trace Hints: TECH, TESTSET

## AC-017-004-03

- Scenario: 职责边界隔离验证
- Given: 系统运行中
- When: 监控模块间调用
- Then: 所有物化调用均来自workflow，无其他模块直接调用SSOT
- Trace Hints: TECH, TESTSET
# Dependencies

- FEAT-017-001
- FEAT-017-002
# Non Goals

- 不替换ADR与SRC的关系(治理型需求仍需先补薄SRC)
