---
id: FEAT-119
ssot_type: feat
title: Feature Delivery L2 Workflow Definition
status: active
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
---

# Goal

建立 Dev 部门 Feature 交付的 L2 编排层工作流定义，实现从 FEAT 到 Evidence Pack 的完整主链治理
# User Value

Dev 团队获得标准化的 Feature 交付主入口，实现从 FEAT 到 Evidence Pack 的完整编排能力，消除多入口混乱
# Inputs

- Inputs defined by EPIC scope
# Processing

- 校验输入完整性（formal_ssot_id, source_refs, governing_adrs, repo_context, repo_frontend, repo_backend）
- 解析 FEAT 范围并分解为阶段任务
- 编排 Contract Design → Backend / Frontend 并行 → Integration → Evidence Pack 阶段
- 管理阶段间依赖与流转条件
- 收集各阶段产出物并聚合
# Outputs

- TECH spec 对象
- Implementation artifacts
- Evidence Pack（决策日志 + 实现物 + 验证证据 + 审计追踪）
# Acceptance

- Feature Delivery L2 工作流定义文档冻结
- 包含触发条件（FEAT frozen）
- 包含阶段编排（Contract→BE/FE 并行→Integration→Evidence）
- 包含输出物清单（TECH spec + Implementation + Evidence Pack）
- 通过示例 FEAT 走通完整 L2 编排流程
# Acceptance Checks

## AC-SRC-009-001-01

- Scenario: 工作流定义文档冻结
- Given: EPIC-SRC-009-001 进入验收阶段
- When: 评审 Feature Delivery L2 工作流定义
- Then: 文档包含触发条件、阶段编排、输出物清单完整定义
- Trace Hints: TASK, TECH

## AC-SRC-009-001-02

- Scenario: 示例 FEAT 端到端流程验证
- Given: 提供一个已冻结的示例 FEAT
- When: 执行 Feature Delivery L2 工作流
- Then: 成功走通 Contract→BE/FE 并行→Integration→Evidence 全阶段，并验证 integration 仅在前后端产物齐备后启动
- Trace Hints: TASK, TESTSET, TECH

## AC-SRC-009-001-03

- Scenario: Evidence Pack 产出物符合规范
- Given: L2 工作流执行完成
- When: 检查输出物
- Then: 产出包含决策日志、实现物、验证证据、审计追踪的标准化 Evidence Pack
- Trace Hints: TASK, TESTSET
# Dependencies

- EPIC-SRC-009
# Non Goals

- 不实现具体的 L3 阶段逻辑
- 不修改 FEAT 定义流程
- 不生成实际业务代码
