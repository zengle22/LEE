---
id: FEAT-084
ssot_type: feat
title: Workflow Template 与 Runtime Instance 边界定义
status: frozen
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_005
  identity_kind: ssot
frozen_at: '2026-03-11T15:17:41.942188'
---

# Goal

明确区分 workflow template（模板定义）与 runtime instance（运行实例），保持两者边界清晰
# User Value

用户可以清晰区分模板定义和运行实例，理解两者的生命周期差异
# Inputs

- Template 存储位置定义
- Instance 存储位置定义
- 命令接口设计
# Processing

- 模板定义存储在独立的 templates/ 目录或配置中
- 实现 lee workflow template list 命令
- 实现 lee workflow instance list 命令
- 确保模板升级不影响已存在的 runtime instance
# Outputs

- Template 存储结构
- Instance 存储结构
- template list 命令
- instance list 命令
# Acceptance

- 模板定义存储在独立的 templates/ 目录或配置中，与 runtime instance 分离
- lee workflow template list 命令可查看可用模板
- lee workflow instance list 命令可查看运行中的实例
- 模板升级不影响已存在的 runtime instance
- 文档中明确说明 template 和 instance 的生命周期差异
# Acceptance Checks

## AC-005-001

- Scenario: Template 与 Instance 存储分离
- Given: 系统配置
- When: 查看存储结构
- Then: templates/ 和 instances/ 目录或配置独立存在
- Trace Hints: TECH

## AC-005-002

- Scenario: 查看可用模板
- Given: 用户执行 lee workflow template list
- When: 命令执行
- Then: 返回可用模板列表
- Trace Hints: UI, TESTSET

## AC-005-003

- Scenario: 查看运行实例
- Given: 用户执行 lee workflow instance list
- When: 命令执行
- Then: 返回运行中的实例列表
- Trace Hints: UI, TESTSET

## AC-005-004

- Scenario: 模板升级不影响实例
- Given: 存在运行中的 workflow instance
- When: 模板版本升级
- Then: 已存在的 instance 继续正常运行，不受影响
- Trace Hints: TECH
# Dependencies

- None
# Non Goals

- 不实现具体的模板引擎
- 不处理 template 版本迁移
