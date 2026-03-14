---
id: FEAT-117
ssot_type: feat
title: Shared Input Specification Implementation
status: frozen
version: v1
parent_id: EPIC-SRC-009
derived_from_ids: []
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: feat_010
  identity_kind: ssot
frozen_at: '2026-03-12T17:47:40.542767'
---

# Goal

落地共享输入规范，确保所有 Dev workflow 统一输入标准
# User Value

所有 Dev workflow 统一输入规范，确保工作流实例具备完整的上游追溯能力和治理上下文
# Inputs

- 现有 workflow 输入分析
- 共享输入规范需求
# Processing

- 分析现有 workflow 输入
- 设计共享输入 schema（基础四字段 + 按 workflow 类型扩展字段）
- 定义 formal_ssot_id 字段规范
- 定义 source_refs 字段规范
- 定义 governing_adrs 字段规范
- 定义 repo_context 字段规范
- 定义 Feature Delivery L2 的 repo_frontend / repo_backend 扩展字段规范
# Outputs

- 共享输入 schema 定义
- formal_ssot_id 字段规范
- source_refs 字段规范
- governing_adrs 字段规范
- repo_context 字段规范
- repo_frontend / repo_backend 扩展字段规范
# Acceptance

- 共享输入规范落地完成
- 包含 schema 定义（基础字段 formal_ssot_id, source_refs, governing_adrs, repo_context，以及 Feature Delivery L2 扩展字段 repo_frontend, repo_backend）
- 包含所有 L2/L3 workflow 输入校验逻辑
- 包含示例数据模板
- 所有新创建的 workflow 实例必须通过输入规范校验
# Acceptance Checks

## AC-SRC-009-010-01

- Scenario: 共享输入 schema 完整性
- Given: 共享输入规范设计完成
- When: 提交 schema 评审
- Then: schema 包含所有必填字段定义
- Trace Hints: TASK, TECH, TESTSET

## AC-SRC-009-010-02

- Scenario: L2 Workflow 输入校验
- Given: L2 workflow 输入校验实现完成
- When: 测试 L2 workflow 输入
- Then: 缺失必填字段时触发明确错误
- Trace Hints: TESTSET, TECH

## AC-SRC-009-010-03

- Scenario: L3 Workflow 输入校验
- Given: L3 workflow 输入校验实现完成
- When: 测试 L3 workflow 输入
- Then: 缺失必填字段时触发明确错误
- Trace Hints: TESTSET, TECH

## AC-SRC-009-010-04

- Scenario: 示例数据模板可用性
- Given: 示例数据模板编写完成
- When: 使用模板创建 workflow 实例
- Then: 实例通过输入规范校验
- Trace Hints: TASK, TECH
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-002
# Non Goals

- 不修改上游系统输出格式
- 不实现自动字段填充
- 不介入 repo_context 采集逻辑
