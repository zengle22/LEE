---
id: FEAT-130
ssot_type: feat
title: Feature Delivery L2 工作流定义
status: frozen
version: v1
parent_id: EPIC-SRC-009
derived_from_ids: []
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
frozen_at: '2026-03-12T19:47:01.797764'
---

# Goal

定义 Dev 部门从 FEAT 到 Evidence Pack 的完整 Feature 交付主链，建立统一的 L2 编排层入口
# User Value

Dev 部门获得从 FEAT 到 Evidence Pack 的完整 Feature 交付主链，实现需求轴到交付轴的正式收口，团队可通过统一的 L2 入口执行特性开发任务
# Inputs

- {'formal_ssot_id': '上游 FEAT 的正式 SSOT ID'}
- {'source_refs': '需求来源引用列表'}
- {'governing_adrs': '影响范围声明的 ADR 引用'}
- {'repo_context': '代码库路径和分支规则'}
- {'repo_frontend': '前端代码库路径或标识'}
- {'repo_backend': '后端代码库路径或标识'}
# Processing

- 校验输入完整性（formal_ssot_id, source_refs, governing_adrs, repo_context, repo_frontend, repo_backend）
- 定义 L3 阶段编排顺序（Contract → Backend / Frontend 并行 → Integration → Evidence Pack）
- 定义状态机（Ready → In Progress → Evidence Pack Produced → Closed）
- 设计与上游 FEAT 的契约接口
- 设计与下游 Evidence Pack 的契约接口
# Outputs

- L2 工作流定义文档（冻结状态）
- 输入规范文档
- L3 阶段编排顺序定义
- 状态机定义文档
- 契约接口定义
# Acceptance

- L2 工作流定义文档已冻结并通过评审
- 输入规范包含 formal_ssot_id, source_refs, governing_adrs, repo_context, repo_frontend, repo_backend 六个字段定义
- L3 阶段编排顺序明确定义为 Contract → Backend / Frontend 并行 → Integration → Evidence Pack
- 状态机包含 Ready → In Progress → Evidence Pack Produced → Closed 四个状态
- 与上游 FEAT 的契约接口文档化
# Acceptance Checks

## AC-001-001

- Scenario: L2 工作流定义文档冻结
- Given: Feature Delivery L2 框架设计完成
- When: 提交评审并通过
- Then: 文档标记为 frozen 状态并存档
- Trace Hints: TASK, TECH

## AC-001-002

- Scenario: 输入规范完整性验证
- Given: L2 工作流定义文档已冻结
- When: 检查输入规范章节
- Then: 包含 formal_ssot_id, source_refs, governing_adrs, repo_context, repo_frontend, repo_backend 完整定义
- Trace Hints: TECH, TESTSET

## AC-001-003

- Scenario: L3 阶段编排顺序定义
- Given: L2 框架包含阶段编排定义
- When: 检查阶段编排章节
- Then: 明确定义 Contract → Backend / Frontend 并行 → Integration → Evidence Pack 顺序
- Trace Hints: TECH

## AC-001-004

- Scenario: 状态机定义完整性
- Given: L2 框架包含状态机定义
- When: 检查状态机章节
- Then: 包含 Ready → In Progress → Evidence Pack Produced → Closed 完整状态流转
- Trace Hints: TECH, TESTSET
# Dependencies

- EPIC-SRC-009
# Non Goals

- 实现 L3 阶段的具体逻辑
- 修改 FEAT 产生机制
- 实现具体技术代码生成
