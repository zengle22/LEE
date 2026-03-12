---
id: FEAT-129
ssot_type: feat
title: Bugfix Granularity Control Rules
status: active
version: v1
parent_id: EPIC-SRC-009
derived_from_ids: []
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: feat_011
  identity_kind: ssot
---

# Goal

定义 Bugfix 交付的粒度控制规则，避免 batch 混乱导致的审计困难和回滚风险
# User Value

Bugfix 交付获得明确的粒度控制规则，避免 batch 混乱导致的审计困难和回滚风险
# Inputs

- Inputs defined by EPIC scope
# Processing

- 定义默认规则（1 bug → 1 bugfix workflow instance）
- 定义五同原则 batch 例外（同服务/同根因/同代码位置/同发布单元/同验证方式）
- 设计 batch 审批流程
- 定义例外记录要求
- 编写粒度控制规则文档
# Outputs

- 粒度控制规则文档
- 默认规则定义
- 五同原则 batch 例外定义
- Batch 审批流程
- 例外记录模板
# Acceptance

- 粒度控制规则文档冻结
- 包含默认规则（1 bug → 1 bugfix workflow instance）
- 包含五同原则 batch 例外定义（同服务/同根因/同代码位置/同发布单元/同验证方式）
- 包含 batch 审批流程
- 包含例外记录要求
# Acceptance Checks

## AC-SRC-009-011-01

- Scenario: 规则文档冻结
- Given: EPIC-SRC-009-011 进入验收阶段
- When: 评审粒度控制规则文档
- Then: 文档包含默认规则、例外定义、审批流程、记录要求
- Trace Hints: TASK

## AC-SRC-009-011-02

- Scenario: 默认规则执行验证
- Given: 提交正常单个 bug
- When: 创建 bugfix workflow
- Then: 按默认规则创建单个 workflow instance
- Trace Hints: TASK, TESTSET

## AC-SRC-009-011-03

- Scenario: Batch 例外审批验证
- Given: 提交符合五同原则的多个 bug
- When: 申请 batch 合并并审批
- Then: 审批通过后允许合并为单个 workflow instance
- Trace Hints: TASK, TESTSET

## AC-SRC-009-011-04

- Scenario: 例外记录可追踪
- Given: 存在 batch 例外情况
- When: 查询例外记录
- Then: 可追溯所有 batch 例外的审批人和理由
- Trace Hints: TASK, TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-002
# Non Goals

- 不实现自动 batch 检测
- 不强制拆分历史 batch
- 不介入 bug 根因分析
