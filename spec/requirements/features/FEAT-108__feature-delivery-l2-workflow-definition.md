---
id: FEAT-108
ssot_type: feat
title: Feature Delivery L2 Workflow Definition
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
frozen_at: '2026-03-12T17:47:40.468196'
---

# Goal

建立标准化的 Feature 交付 L2 编排工作流，实现从 FEAT 到 Evidence Pack 的完整主链治理
# User Value

Dev 团队获得标准化的 Feature 交付主入口，实现从 FEAT 到 Evidence Pack 的完整编排能力，消除多入口混乱
# Inputs

- Inputs defined by EPIC scope
# Processing

- 校验输入完整性（formal_ssot_id, source_refs, governing_adrs, repo_context, repo_frontend, repo_backend）
- 初始化 L2 编排上下文
- 按顺序编排 L3 阶段：Contract Design → Backend Development / Frontend Development 并行 → Integration → Evidence Pack
- 协调各阶段数据流转
- 汇总各阶段产出物生成 Evidence Pack
# Outputs

- TECH spec 文档
- Implementation artifacts
- Evidence Pack（包含 decision log + implementation artifacts + verification evidence + audit trail）
# Acceptance

- Feature Delivery L2 工作流定义文档冻结
- 包含触发条件（FEAT frozen）
- 包含阶段编排（Contract→BE/FE 并行→Integration→Evidence）
- 包含输出物清单（TECH spec + Implementation + Evidence Pack）
- 通过示例 FEAT 走通完整 L2 编排流程
# Acceptance Checks

## AC-SRC-009-001-01

- Scenario: L2 工作流定义文档完整性
- Given: Feature Delivery L2 工作流设计完成
- When: 提交工作流定义文档评审
- Then: 文档包含触发条件、阶段编排、输出物清单三大要素
- Trace Hints: TASK, TESTSET

## AC-SRC-009-001-02

- Scenario: 示例 FEAT 完整编排验证
- Given: 提供一个冻结状态的示例 FEAT
- When: 执行 Feature Delivery L2 工作流
- Then: 成功走完 Contract→BE/FE 并行→Integration→Evidence 全阶段，且 integration 仅在前后端产物齐备后启动
- Trace Hints: TASK, TECH, TESTSET

## AC-SRC-009-001-03

- Scenario: Evidence Pack 产出规范
- Given: L2 工作流所有阶段完成
- When: 进入 Evidence Pack 收口阶段
- Then: 产出包含 decision log + artifacts + evidence + audit trail 的标准化证据包
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- EPIC-SRC-009
# Non Goals

- 不实现具体的 L3 阶段逻辑
- 不修改 FEAT 定义流程
- 不生成实际业务代码
