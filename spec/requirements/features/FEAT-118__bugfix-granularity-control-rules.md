---
id: FEAT-118
ssot_type: feat
title: Bugfix Granularity Control Rules
status: frozen
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
frozen_at: '2026-03-12T17:47:40.553971'
---

# Goal

建立 Bugfix 粒度控制规则，避免 batch 混乱导致的审计困难和回滚风险
# User Value

Bugfix 交付获得明确的粒度控制规则，避免 batch 混乱导致的审计困难和回滚风险
# Inputs

- 现有 Bugfix 流程分析
- 粒度控制需求
# Processing

- 分析现有 Bugfix 流程
- 定义默认规则（1 bug → 1 bugfix workflow instance）
- 定义五同原则（同服务/同根因/同代码位置/同发布单元/同验证方式）
- 设计 batch 审批流程
- 定义例外记录要求
# Outputs

- 粒度控制规则文档
- 默认规则定义
- 五同原则 batch 例外定义
- batch 审批流程定义
- 例外记录要求定义
# Acceptance

- 粒度控制规则文档冻结
- 包含默认规则（1 bug → 1 bugfix workflow instance）
- 包含五同原则 batch 例外定义（同服务/同根因/同代码位置/同发布单元/同验证方式）
- 包含 batch 审批流程
- 包含例外记录要求
# Acceptance Checks

## AC-SRC-009-011-01

- Scenario: 粒度控制规则文档完整性
- Given: 粒度控制规则设计完成
- When: 提交规则文档评审
- Then: 文档包含默认规则、五同原则、审批流程、记录要求
- Trace Hints: TASK, TESTSET

## AC-SRC-009-011-02

- Scenario: 默认规则验证
- Given: 正常单个 bug 场景
- When: 创建 bugfix workflow
- Then: 按默认规则生成单个 workflow instance
- Trace Hints: TASK, TESTSET

## AC-SRC-009-011-03

- Scenario: 五同原则 batch 审批
- Given: 符合条件的 batch 场景（五同）
- When: 提交 batch 审批
- Then: 审批通过后允许合并为一个 workflow instance
- Trace Hints: TASK, TESTSET

## AC-SRC-009-011-04

- Scenario: 例外可追踪性
- Given: batch 审批通过
- When: 记录例外信息
- Then: 例外记录可被查询和追踪
- Trace Hints: TASK, TECH, TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-002
# Non Goals

- 不实现自动 batch 检测
- 不强制拆分历史 batch
- 不介入 bug 根因分析
