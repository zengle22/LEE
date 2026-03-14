---
id: FEAT-128
ssot_type: feat
title: Shared Input Specification Implementation
status: active
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
---

# Goal

落地所有 Dev workflow 的统一输入规范，确保工作流实例具备完整的上游追溯能力和治理上下文
# User Value

所有 Dev workflow 统一输入规范，确保工作流实例具备完整的上游追溯能力和治理上下文
# Inputs

- Inputs defined by EPIC scope
# Processing

- 定义 schema（基础字段 formal_ssot_id, source_refs, governing_adrs, repo_context，以及 Feature Delivery L2 扩展字段 repo_frontend, repo_backend）
- 实现 L2 workflow 输入校验逻辑
- 实现 L3 workflow 输入校验逻辑
- 创建示例数据模板
- 编写输入规范文档
# Outputs

- Shared input schema 定义
- L2 workflow 输入校验逻辑
- L3 workflow 输入校验逻辑
- 示例数据模板
- 输入规范文档
# Acceptance

- 共享输入规范落地完成
- 包含 schema 定义（基础字段 formal_ssot_id, source_refs, governing_adrs, repo_context，以及 Feature Delivery L2 扩展字段 repo_frontend, repo_backend）
- 所有 L2/L3 workflow 输入校验逻辑实现
- 示例数据模板发布
- 所有新创建的 workflow 实例必须通过输入规范校验
# Acceptance Checks

## AC-SRC-009-010-01

- Scenario: Schema 定义冻结
- Given: EPIC-SRC-009-010 进入验收阶段
- When: 评审共享输入规范
- Then: schema 包含所有必填字段及类型定义
- Trace Hints: TASK, TECH

## AC-SRC-009-010-02

- Scenario: 校验逻辑实现
- Given: Schema 已定义
- When: 检查 L2/L3 workflow
- Then: 所有 workflow 实现输入校验逻辑
- Trace Hints: TASK, TECH

## AC-SRC-009-010-03

- Scenario: 示例数据模板
- Given: 校验逻辑已实现
- When: 检查文档
- Then: 存在完整的示例数据模板供参考
- Trace Hints: TASK

## AC-SRC-009-010-04

- Scenario: 校验生效验证
- Given: 校验逻辑已部署
- When: 创建缺失必填字段的 workflow 实例
- Then: 触发明确错误并提示缺失字段
- Trace Hints: TASK, TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-002
# Non Goals

- 不修改上游系统输出格式
- 不实现自动字段填充
- 不介入 repo_context 采集逻辑
