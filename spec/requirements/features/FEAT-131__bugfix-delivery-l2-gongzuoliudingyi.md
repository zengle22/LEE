---
id: FEAT-131
ssot_type: feat
title: Bugfix Delivery L2 工作流定义
status: frozen
version: v1
parent_id: EPIC-SRC-009
derived_from_ids: []
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-12T19:47:01.806001'
---

# Goal

定义 Dev 部门从 BUG 到 Evidence Pack 的完整 Bugfix 交付主链，建立 Bug 修复的标准化流程
# User Value

Dev 部门获得从 BUG 到 Evidence Pack 的完整 Bugfix 交付主链，实现 Bug 修复流程的标准化和可追溯，团队可通过统一的 L2 入口执行 Bug 修复任务
# Inputs

- {'bug_ssot_id': 'BUG 的正式 SSOT ID'}
- {'severity': 'BUG 严重程度分级'}
- {'reproduction_evidence': '复现证据'}
- {'batch_mode': '是否尝试 batch 修复'}
- {'batch_approval_record': '五同不满足时的审批例外记录（可选）'}
# Processing

- 校验输入完整性（bug_ssot_id, severity, reproduction_evidence, batch_mode, batch_approval_record）
- 定义 L3 阶段编排顺序（Triage → Root Cause → Fix Design → Fix Implementation → Verification → Evidence Pack）
- 定义 Bugfix 状态机
- 集成 Bugfix 粒度控制规则与 batch 例外审批机制
- 设计与上游 BUG 源的契约接口
# Outputs

- Bugfix Delivery L2 工作流定义文档（冻结状态）
- Bugfix 输入规范文档
- Bugfix L3 阶段编排顺序定义
- Bugfix 状态机定义
- 粒度控制规则集成规范
# Acceptance

- Bugfix Delivery L2 工作流定义文档已冻结并通过评审
- 输入规范包含 bug_ssot_id, severity, reproduction_evidence 字段定义
- L3 阶段编排顺序明确定义为 Triage → Root Cause → Fix Design → Fix Implementation → Verification → Evidence Pack
- 状态机定义完整
- Bugfix 粒度控制规则已集成，默认单 bug 与五同失败后的审批例外路径都已文档化
# Acceptance Checks

## AC-002-001

- Scenario: Bugfix L2 工作流定义文档冻结
- Given: Bugfix Delivery L2 框架设计完成
- When: 提交评审并通过
- Then: 文档标记为 frozen 状态并存档
- Trace Hints: TASK, TECH

## AC-002-002

- Scenario: Bugfix 输入规范完整性
- Given: Bugfix L2 工作流定义文档已冻结
- When: 检查输入规范章节
- Then: 包含 bug_ssot_id, severity, reproduction_evidence 完整定义
- Trace Hints: TECH, TESTSET

## AC-002-003

- Scenario: Bugfix L3 阶段编排定义
- Given: Bugfix L2 框架包含阶段编排定义
- When: 检查阶段编排章节
- Then: 明确定义 Triage → Root Cause → Fix Design → Fix Implementation → Verification → Evidence Pack 顺序
- Trace Hints: TECH

## AC-002-004

- Scenario: 粒度控制规则集成
- Given: Bugfix L2 框架设计完成
- When: 检查粒度控制章节
- Then: 已集成默认规则和五同原则 batch 例外机制
- Trace Hints: TECH, TESTSET
# Dependencies

- EPIC-SRC-009
# Non Goals

- 实现 L3 阶段的具体逻辑
- 修改 BUG 产生机制
- 实现具体修复代码
