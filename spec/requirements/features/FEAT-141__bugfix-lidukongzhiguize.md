---
id: FEAT-141
ssot_type: feat
title: Bugfix 粒度控制规则
status: frozen
version: v1
parent_id: EPIC-SRC-009
derived_from_ids: []
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: feat_012
  identity_kind: ssot
frozen_at: '2026-03-12T19:47:01.886462'
---

# Goal

定义 Bugfix 的粒度控制标准，确保默认单 bug 单 workflow instance，同时为合理的 batch 场景提供审批机制
# User Value

明确 Bugfix 的粒度控制标准，确保默认单 bug 单 workflow instance，同时为合理的 batch 场景提供审批机制
# Inputs

- {'formal_ssot_id': 'Bugfix Delivery L2 定义文档 ID'}
- {'source_refs': '规则来源引用'}
- {'governing_adrs': '粒度决策 ADR'}
- {'bug_classification': 'BUG 分类标准'}
# Processing

- 定义默认规则（1 bug → 1 bugfix workflow instance）
- 定义五同原则（同模块、同根因、同修复方案、同测试范围、同风险等级）
- 设计 batch 例外审批流程
- 创建粒度合规检查 checklist
- 定义合规率统计方法
# Outputs

- Bugfix 粒度控制规则文档
- 默认规则定义
- 五同原则定义
- Batch 例外审批流程
- 粒度合规检查 checklist
# Acceptance

- Bugfix 粒度控制规则文档已冻结
- 默认规则明确为 1 bug → 1 bugfix workflow instance
- 五同原则完整定义（同模块、同根因、同修复方案、同测试范围、同风险等级）
- Batch 例外审批流程清晰可执行
- 粒度合规检查 checklist 可用
# Acceptance Checks

## AC-012-001

- Scenario: Bugfix 粒度控制规则文档冻结
- Given: Bugfix 粒度控制规则设计完成
- When: 提交评审并通过
- Then: 文档标记为 frozen 状态
- Trace Hints: TASK, TECH

## AC-012-002

- Scenario: 默认规则明确性
- Given: 粒度控制规则文档已冻结
- When: 检查默认规则章节
- Then: 明确定义 1 bug → 1 bugfix workflow instance
- Trace Hints: TECH, TESTSET

## AC-012-003

- Scenario: 五同原则完整性
- Given: 粒度控制规则设计完成
- When: 检查五同原则定义
- Then: 覆盖同模块、同根因、同修复方案、同测试范围、同风险等级
- Trace Hints: TECH

## AC-012-004

- Scenario: Batch 审批流程可执行性
- Given: 粒度控制规则设计完成
- When: 检查 batch 例外审批流程
- Then: 流程步骤清晰、审批节点明确
- Trace Hints: TECH, TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-002
# Non Goals

- 实现自动化粒度检查
- 修改 BUG 报告机制
- 强制拆分历史 batch
